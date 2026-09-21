#!/usr/bin/env python3
"""Construye UNA tabla de Dataverse con sus columnas propias, desde un playbook
de tipo `tabla`. Contrato: `power-platform-construir`,
`references/modelo-datos/patrones.md` §1 y §2.2.

    python3 herramientas/construir/tabla.py <playbook.md> [--solo-verificar]
                                            [--permitir-no-verificadas] [--corregir-primaria]

La tabla y sus columnas propias viajan en un solo POST: o existe completa o
no existe. La única excepción son las columnas protegidas (seguridad de
columna): la plataforma rechaza con un 400 genérico una columna con
`IsSecured = true` dentro del POST que crea la tabla, y sí la acepta agregada
después (verificado el 2026-09-20); esas se agregan una por una enseguida.
Segunda excepción, también verificada: al crear la tabla la plataforma IGNORA
el largo y el "requerida" de la columna primaria (la deja en 850 y opcional),
salvo que sea autonumérica. Enseguida de crear se reenvía su definición
completa con PUT y se publica. `--corregir-primaria` repara una tabla que ya
existe cuando su ÚNICA diferencia es la primaria: largo, requerida, o pasar
de texto común a autonumérica (nunca otra cosa, y nunca al revés).
Las columnas lookup no van acá: nacen con su relación.
Nunca modifica ni borra: si la tabla existe y no coincide, informa `difiere`.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
import re
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

from _comun import (  # noqa: E402
    Bloqueado,
    ErrorEntorno,
    ErrorPlaybook,
    Rastro,
    comprobar_solucion_e_idioma,
    dividir_secciones,
    escribir_metadatos,
    etiqueta_web_api,
    etiqueta_y_otros_idiomas,
    exigir_etiqueta,
    exigir_forma,
    exigir_sin_tildes,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "tabla"
LARGO_MAXIMO_IDENTIFICADOR = 95  # verificado contra la plataforma (2026-09-20)
COMPONENTE_TABLA = 1  # tipo de componente de una tabla en solutioncomponents
ENTERO_MIN, ENTERO_MAX = -2147483648, 2147483647
MARCADOR_AUTONUMERICO = re.compile(r"\{(SEQNUM:\d+|RANDSTRING:[1-6]|DATETIMEUTC:[^}]+)\}")

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

# Claves de cada bloque y su tipo. `bool` y `int` se validan estrictos.
CLAVES_TABLA = {"tipo": str, "nombre": str, "displayname": str, "displayname_plural": str, "descripcion": str,
                "propiedad": str, "notas": bool, "actividades": bool, "auditoria": bool, "primaria": dict, "columnas": list}
CLAVES_PRIMARIA = {"nombre": str, "displayname": str, "descripcion": str, "largo": int, "requerida": bool, "autonumerico": "texto_o_vacio"}
CLAVES_COLUMNA = {"nombre": str, "displayname": str, "descripcion": str, "tipo": str, "requerida": bool, "protegida": bool, "auditoria": bool}
CLAVES_POR_TIPO = {
    "texto": {"largo": int},
    "autonumerico": {"largo": int, "formato": str},
    "memo": {"largo": int},
    "entero": {"minimo": int, "maximo": int},
    "choice": {"choice": str},
    "sino": {"etiqueta_si": str, "etiqueta_no": str, "defecto": bool},
    "fecha": {},
    "fechahora": {},
    "archivo": {"tamano_kb": int},
}
PROPIEDAD = {"usuario": "UserOwned", "organizacion": "OrganizationOwned"}

# Todo lo que el formato admite…
CARACTERISTICAS = frozenset({f"tipo:{t}" for t in CLAVES_POR_TIPO} | {"tabla:auditoria", "columna:auditoria", "columna:protegida", "primaria:autonumerica"})
# …y lo que ya se comprobó contra la plataforma real. Un playbook que usa algo
# que no está acá se bloquea: primero se ensaya sobre una tabla descartable
# (`…_tbl_zz…`, con --permitir-no-verificadas) y recién después se agrega acá.
# Ensayo del 2026-09-20 sobre `sanic_mppp_tbl_zzensayo` (playbooks/tabla/ensayos/): los 9 tipos, primaria
# autonumérica, auditoría de tabla y de columna, y una columna protegida; creado, releído y `ya_existia`.
VERIFICADAS_EN_PLATAFORMA = frozenset(CARACTERISTICAS)
INFIJO_DESCARTABLE = "_tbl_zz"

# Cast del Web API y propiedades propias de cada familia de columna.
FAMILIAS = {
    "String": ("StringType", "LogicalName,MaxLength,FormatName,AutoNumberFormat", ""),
    "Memo": ("MemoType", "LogicalName,MaxLength", ""),
    "Integer": ("IntegerType", "LogicalName,MinValue,MaxValue", ""),
    "Picklist": ("PicklistType", "LogicalName", "&$expand=GlobalOptionSet($select=Name,IsGlobal)"),
    "Boolean": ("BooleanType", "LogicalName,DefaultValue", "&$expand=OptionSet"),
    "DateTime": ("DateTimeType", "LogicalName,Format,DateTimeBehavior", ""),
    "File": ("FileType", "LogicalName,MaxSizeInKB", ""),
}
FAMILIA_DE = {"texto": "String", "autonumerico": "String", "memo": "Memo", "entero": "Integer", "choice": "Picklist",
              "sino": "Boolean", "fecha": "DateTime", "fechahora": "DateTime", "archivo": "File"}
# Columnas propias que NO declara el playbook de la tabla y son legítimas.
TIPOS_AJENOS = {"LookupType", "OwnerType", "CustomerType", "UniqueidentifierType", "VirtualType", "EntityNameType", "PartyListType"}


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_bloque(datos, claves, de_donde):
    if not isinstance(datos, dict):
        raise ErrorPlaybook(f"{de_donde} tiene que ser un objeto, no {datos!r}")
    faltan, sobran = sorted(set(claves) - set(datos)), sorted(set(datos) - set(claves))
    if faltan or sobran:
        raise ErrorPlaybook(f"claves de {de_donde} inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
    for clave, tipo in claves.items():
        valor, donde = datos[clave], f"{de_donde}.{clave}" if de_donde != "la tabla" else f"'{clave}'"
        if tipo is bool:
            if not isinstance(valor, bool):
                raise ErrorPlaybook(f"{donde} tiene que ser true o false, no {valor!r}")
        elif tipo is int:
            if not isinstance(valor, int) or isinstance(valor, bool):
                raise ErrorPlaybook(f"{donde} tiene que ser un entero, no {valor!r}")
        elif tipo is str:
            if not isinstance(valor, str) or not valor.strip():
                raise ErrorPlaybook(f"{donde} tiene que ser texto no vacío, no {valor!r}")
        elif tipo == "texto_o_vacio":
            if not isinstance(valor, str):
                raise ErrorPlaybook(f"{donde} tiene que ser texto (vacío si no aplica), no {valor!r}")
        elif not isinstance(valor, tipo):
            raise ErrorPlaybook(f"{donde} tiene que ser {'un objeto' if tipo is dict else 'una lista'}, no {valor!r}")


def _validar_nombre(nombre, patron, donde):
    if not re.fullmatch(patron, nombre):
        raise ErrorPlaybook(f"{donde} = {nombre!r} no cumple el patrón {patron} (todo en minúscula, BP-PP-184)")
    if len(nombre) > LARGO_MAXIMO_IDENTIFICADOR:
        raise ErrorPlaybook(f"{donde} tiene {len(nombre)} caracteres; el máximo de la plataforma es {LARGO_MAXIMO_IDENTIFICADOR}")


def _validar_autonumerico(formato, donde):
    if not MARCADOR_AUTONUMERICO.search(formato):
        raise ErrorPlaybook(f"{donde} = {formato!r} no tiene ningún marcador ({{SEQNUM:n}}, {{RANDSTRING:n}} o {{DATETIMEUTC:formato}})")


def _validar_estructura(datos, identidad):
    _validar_bloque(datos, CLAVES_TABLA, "la tabla")
    prefijo, abrev = identidad["prefijo"], identidad["abrev"]
    _validar_nombre(datos["nombre"], rf"{prefijo}_{abrev}_tbl_[a-z0-9]+", "'nombre'")
    if datos["propiedad"] not in PROPIEDAD:
        raise ErrorPlaybook(f"'propiedad' tiene que ser una de {sorted(PROPIEDAD)}, no {datos['propiedad']!r}")

    p = datos["primaria"]
    _validar_bloque(p, CLAVES_PRIMARIA, "primaria")
    _validar_nombre(p["nombre"], rf"{prefijo}_[a-z0-9]+", "primaria.nombre")
    if not 1 <= p["largo"] <= 4000:
        raise ErrorPlaybook(f"primaria.largo tiene que estar entre 1 y 4000, no {p['largo']}")
    if p["autonumerico"]:
        _validar_autonumerico(p["autonumerico"], "primaria.autonumerico")

    nombres = {p["nombre"]}
    for i, c in enumerate(datos["columnas"]):
        d = f"columnas[{i}]"
        if not isinstance(c, dict):
            raise ErrorPlaybook(f"{d} tiene que ser un objeto, no {c!r}")
        tipo = c.get("tipo")
        if tipo not in CLAVES_POR_TIPO:
            raise ErrorPlaybook(f"{d}.tipo tiene que ser uno de {sorted(CLAVES_POR_TIPO)}, no {tipo!r} (un lookup nace con su relación, no acá)")
        _validar_bloque(c, {**CLAVES_COLUMNA, **CLAVES_POR_TIPO[tipo]}, d)
        _validar_nombre(c["nombre"], rf"{prefijo}_[a-z0-9]+", f"{d}.nombre")
        if c["nombre"] in nombres:
            raise ErrorPlaybook(f"{d}.nombre = {c['nombre']!r} está repetido en la tabla")
        nombres.add(c["nombre"])
        if tipo in ("texto", "autonumerico") and not 1 <= c["largo"] <= 4000:
            raise ErrorPlaybook(f"{d}.largo tiene que estar entre 1 y 4000, no {c['largo']}")
        if tipo == "memo" and not 1 <= c["largo"] <= 1048576:
            raise ErrorPlaybook(f"{d}.largo tiene que estar entre 1 y 1048576, no {c['largo']}")
        if tipo == "entero":
            for k in ("minimo", "maximo"):
                if not ENTERO_MIN <= c[k] <= ENTERO_MAX:
                    raise ErrorPlaybook(f"{d}.{k} = {c[k]} está fuera del rango de un entero de Dataverse")
            if c["minimo"] > c["maximo"]:
                raise ErrorPlaybook(f"{d}: minimo ({c['minimo']}) es mayor que maximo ({c['maximo']})")
        if tipo == "choice":
            _validar_nombre(c["choice"], rf"{prefijo}_{abrev}_ch_[a-z0-9]+", f"{d}.choice")
        if tipo == "archivo":
            if not 1 <= c["tamano_kb"] <= 10485760:
                raise ErrorPlaybook(f"{d}.tamano_kb tiene que estar entre 1 y 10485760, no {c['tamano_kb']}")
            if c["requerida"]:
                raise ErrorPlaybook(f"{d}: una columna de archivo no puede ser requerida (el archivo se carga después de crear el registro)")
        if tipo == "autonumerico":
            _validar_autonumerico(c["formato"], f"{d}.formato")


def caracteristicas_usadas(datos):
    usadas = {f"tipo:{c['tipo']}" for c in datos["columnas"]}
    if datos["auditoria"]:
        usadas.add("tabla:auditoria")
    if any(c["auditoria"] for c in datos["columnas"]):
        usadas.add("columna:auditoria")
    if any(c["protegida"] for c in datos["columnas"]):
        usadas.add("columna:protegida")
    if datos["primaria"]["autonumerico"]:
        usadas.add("primaria:autonumerica")
    return usadas


def comprobar_verificadas(datos, verificadas, permitir_no_verificadas):
    faltan = sorted(caracteristicas_usadas(datos) - set(verificadas))
    if not faltan:
        return
    if not permitir_no_verificadas:
        raise Bloqueado(
            f"el playbook usa características todavía no verificadas contra la plataforma: {faltan}. "
            f"Primero se ensayan sobre una tabla descartable ('…{INFIJO_DESCARTABLE}…') con --permitir-no-verificadas"
        )
    if INFIJO_DESCARTABLE not in datos["nombre"]:
        raise Bloqueado(
            f"--permitir-no-verificadas solo vale sobre una tabla descartable, con '{INFIJO_DESCARTABLE}' en el nombre; "
            f"{datos['nombre']!r} no lo es. Sin verificar: {faltan}"
        )


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)
    exigir_sin_tildes(datos["displayname"], "'displayname'")
    exigir_sin_tildes(datos["displayname_plural"], "'displayname_plural'")
    exigir_sin_tildes(datos["primaria"]["displayname"], "primaria.displayname")
    for i, c in enumerate(datos["columnas"]):
        exigir_sin_tildes(c["displayname"], f"columnas[{i}].displayname ({c['nombre']})")
        for etiqueta in ("etiqueta_si", "etiqueta_no"):
            if etiqueta in c:
                exigir_sin_tildes(c[etiqueta], f"columnas[{i}].{etiqueta} ({c['nombre']})")


# ---------------------------------------------------------------------------
# Cuerpo del POST
# ---------------------------------------------------------------------------
def _nivel(requerida):
    return {"Value": "ApplicationRequired" if requerida else "None", "CanBeChanged": True,
            "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"}


def _auditoria(activa):
    return {"Value": activa, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyauditsettings"}


def _columna_payload(c, lcid, choices):
    tipo = c["tipo"]
    a = {
        "SchemaName": c["nombre"],
        "DisplayName": etiqueta_web_api(c["displayname"], lcid),
        "Description": etiqueta_web_api(c["descripcion"], lcid),
        "RequiredLevel": _nivel(c["requerida"]),
        "IsSecured": c["protegida"],
        "IsAuditEnabled": _auditoria(c["auditoria"]),
    }
    if tipo in ("texto", "autonumerico"):
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata", "AttributeType": "String",
                  "AttributeTypeName": {"Value": "StringType"}, "FormatName": {"Value": "Text"}, "MaxLength": c["largo"]})
        if tipo == "autonumerico":
            a["AutoNumberFormat"] = c["formato"]
    elif tipo == "memo":
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata", "AttributeType": "Memo",
                  "AttributeTypeName": {"Value": "MemoType"}, "Format": "TextArea", "MaxLength": c["largo"]})
    elif tipo == "entero":
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata", "AttributeType": "Integer",
                  "AttributeTypeName": {"Value": "IntegerType"}, "Format": "None", "MinValue": c["minimo"], "MaxValue": c["maximo"]})
    elif tipo == "choice":
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata", "AttributeType": "Picklist",
                  "AttributeTypeName": {"Value": "PicklistType"}, "SourceTypeMask": 0,
                  "GlobalOptionSet@odata.bind": f"/GlobalOptionSetDefinitions({choices[c['choice']]})"})
    elif tipo == "sino":
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata", "AttributeType": "Boolean",
                  "AttributeTypeName": {"Value": "BooleanType"}, "DefaultValue": c["defecto"],
                  "OptionSet": {"OptionSetType": "Boolean",
                                "TrueOption": {"Value": 1, "Label": etiqueta_web_api(c["etiqueta_si"], lcid)},
                                "FalseOption": {"Value": 0, "Label": etiqueta_web_api(c["etiqueta_no"], lcid)}}})
    elif tipo in ("fecha", "fechahora"):
        solo_fecha = tipo == "fecha"
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata", "AttributeType": "DateTime",
                  "AttributeTypeName": {"Value": "DateTimeType"}, "Format": "DateOnly" if solo_fecha else "DateAndTime",
                  "DateTimeBehavior": {"Value": "DateOnly" if solo_fecha else "UserLocal"}})
    elif tipo == "archivo":
        a.update({"@odata.type": "Microsoft.Dynamics.CRM.FileAttributeMetadata", "AttributeTypeName": {"Value": "FileType"},
                  "MaxSizeInKB": c["tamano_kb"]})
    return a


def construir_payload(datos, identidad, choices):
    """`choices`: {nombre del choice global: su MetadataId}, ya comprobados."""
    lcid, p = identidad["lcid"], datos["primaria"]
    primaria = _columna_payload({**p, "tipo": "autonumerico" if p["autonumerico"] else "texto", "formato": p["autonumerico"],
                                 "protegida": False, "auditoria": datos["auditoria"]}, lcid, choices)
    primaria["IsPrimaryName"] = True
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": datos["nombre"],
        "DisplayName": etiqueta_web_api(datos["displayname"], lcid),
        "DisplayCollectionName": etiqueta_web_api(datos["displayname_plural"], lcid),
        "Description": etiqueta_web_api(datos["descripcion"], lcid),
        "OwnershipType": PROPIEDAD[datos["propiedad"]],
        "HasNotes": datos["notas"],
        "HasActivities": datos["actividades"],
        "IsActivity": False,
        "IsAuditEnabled": _auditoria(datos["auditoria"]),
        # Las protegidas no pueden ir acá: ver `columnas_protegidas_payload`.
        "Attributes": [primaria] + [_columna_payload(c, lcid, choices) for c in datos["columnas"] if not c["protegida"]],
    }


def columnas_protegidas_payload(datos, identidad, choices):
    """Las columnas con seguridad de columna, para agregarlas con
    `POST EntityDefinitions(LogicalName='<tabla>')/Attributes` después de
    crear la tabla, en el orden del playbook."""
    return [_columna_payload(c, identidad["lcid"], choices) for c in datos["columnas"] if c["protegida"]]


# ---------------------------------------------------------------------------
# Lectura del entorno y comparación: una sola función para los tres caminos
# ---------------------------------------------------------------------------
def _get(dv, ruta, consulta, admite_404=False):
    est, cuerpo, _ = dv.call("GET", ruta)
    if est == 404 and admite_404:
        return None
    if est != 200:
        raise ErrorEntorno(f"{consulta} devolvió HTTP {est} (se esperaba 200{' o 404' if admite_404 else ''}): {cuerpo}")
    return exigir_forma(cuerpo, dict, consulta, "cuerpo")


def _lista(dv, ruta, consulta):
    return exigir_forma(_get(dv, ruta, consulta).get("value"), [dict], consulta, "value")


def _administrada(objeto, tipo, consulta, campo):
    """Propiedad administrada del Web API: `{Value, CanBeChanged, …}`."""
    exigir_forma(objeto, dict, consulta, campo)
    return exigir_forma(objeto.get("Value"), tipo, consulta, f"{campo}.Value")


def _texto_de(etiqueta, lcid, que, esperado, difs, consulta, campo, permite_nulo=False):
    exigir_etiqueta(etiqueta, consulta, campo, permite_nulo=permite_nulo)
    texto, otros = etiqueta_y_otros_idiomas(etiqueta, lcid)
    if (texto or "") != esperado:
        difs.append(f"{que}: entorno={texto!r} playbook={esperado!r}")
    if otros:
        difs.append(f"{que} tiene etiquetas en otro idioma: {otros}")


def comprobar_choices(dv, datos):
    """Precondición: cada choice global que usa una columna existe. Devuelve
    {nombre: MetadataId} para enlazarlos al crear."""
    encontrados = {}
    for nombre in sorted({c["choice"] for c in datos["columnas"] if c["tipo"] == "choice"}):
        consulta = f"la consulta del choice global '{nombre}' (GET GlobalOptionSetDefinitions)"
        cuerpo = _get(dv, f"GlobalOptionSetDefinitions(Name='{nombre}')?$select=Name,IsGlobal", consulta, admite_404=True)
        if cuerpo is None:
            raise Bloqueado(f"el choice global '{nombre}' no existe en el entorno: se construye antes que la tabla que lo usa")
        encontrados[nombre] = exigir_forma(cuerpo.get("MetadataId"), str, consulta, "MetadataId", no_vacio=True)
    return encontrados


def _verificar(dv, datos, identidad, solution_id):
    lcid, tabla, difs = identidad["lcid"], datos["nombre"], []
    ct = f"la consulta de la tabla (GET EntityDefinitions '{tabla}')"
    t = _get(dv, f"EntityDefinitions(LogicalName='{tabla}')?$select=LogicalName,SchemaName,OwnershipType,HasNotes,HasActivities,"
                 "IsAuditEnabled,IsManaged,IsCustomEntity,PrimaryNameAttribute,DisplayName,DisplayCollectionName,Description", ct, admite_404=True)
    if t is None:
        return {"existe": False, "diffs": None, "metadata_id": None}

    metadata_id = exigir_forma(t.get("MetadataId"), str, ct, "MetadataId", no_vacio=True)
    esperado = [("SchemaName", str, tabla), ("OwnershipType", str, PROPIEDAD[datos["propiedad"]]), ("HasNotes", bool, datos["notas"]),
                ("HasActivities", bool, datos["actividades"]), ("IsManaged", bool, False), ("IsCustomEntity", bool, True),
                ("PrimaryNameAttribute", str, datos["primaria"]["nombre"])]
    for campo, tipo, valor in esperado:
        real = exigir_forma(t.get(campo), tipo, ct, campo)
        if real != valor:
            difs.append(f"{campo}: entorno={real!r} playbook={valor!r}")
    if _administrada(t.get("IsAuditEnabled"), bool, ct, "IsAuditEnabled") != datos["auditoria"]:
        difs.append(f"IsAuditEnabled: entorno={t['IsAuditEnabled']['Value']!r} playbook={datos['auditoria']!r}")
    _texto_de(t.get("DisplayName"), lcid, "DisplayName", datos["displayname"], difs, ct, "DisplayName")
    _texto_de(t.get("DisplayCollectionName"), lcid, "DisplayCollectionName", datos["displayname_plural"], difs, ct, "DisplayCollectionName")
    _texto_de(t.get("Description"), lcid, "Description", datos["descripcion"], difs, ct, "Description", permite_nulo=True)

    # Columnas: lo común a todas, en una consulta…
    ca = f"la consulta de las columnas (GET EntityDefinitions '{tabla}' /Attributes)"
    genericas = _lista(dv, f"EntityDefinitions(LogicalName='{tabla}')/Attributes?$select=LogicalName,SchemaName,AttributeOf,AttributeTypeName,"
                           "IsCustomAttribute,IsPrimaryName,RequiredLevel,IsSecured,IsAuditEnabled,DisplayName,Description", ca)
    en_entorno = {}
    for i, g in enumerate(genericas):
        nombre = exigir_forma(g.get("LogicalName"), str, ca, f"value[{i}].LogicalName", no_vacio=True)
        g["_tipo"] = _administrada(g.get("AttributeTypeName"), str, ca, f"value[{i}].AttributeTypeName")
        g["_propia"] = exigir_forma(g.get("IsCustomAttribute"), bool, ca, f"value[{i}].IsCustomAttribute")
        exigir_forma(g.get("AttributeOf"), str, ca, f"value[{i}].AttributeOf", permite_nulo=True)
        g["_i"] = i
        en_entorno[nombre] = g

    p = datos["primaria"]
    declaradas = [{**p, "tipo": "autonumerico" if p["autonumerico"] else "texto", "formato": p["autonumerico"], "protegida": False,
                   "auditoria": datos["auditoria"], "_primaria": True}] + [dict(c, _primaria=False) for c in datos["columnas"]]
    presentes = []
    for c in declaradas:
        n, g = c["nombre"], en_entorno.get(c["nombre"])
        if g is None:
            difs.append(f"falta la columna {n}")
            continue
        i = g["_i"]
        familia = FAMILIA_DE[c["tipo"]]
        if g["_tipo"] != FAMILIAS[familia][0]:
            difs.append(f"{n}.tipo: entorno={g['_tipo']!r} playbook={FAMILIAS[familia][0]!r}")
            continue
        presentes.append(c)
        nivel = _administrada(g.get("RequiredLevel"), str, ca, f"value[{i}].RequiredLevel")
        if nivel != ("ApplicationRequired" if c["requerida"] else "None"):
            difs.append(f"{n}.RequiredLevel: entorno={nivel!r} playbook={'ApplicationRequired' if c['requerida'] else 'None'!r}")
        if exigir_forma(g.get("IsSecured"), bool, ca, f"value[{i}].IsSecured") != c["protegida"]:
            difs.append(f"{n}.IsSecured: entorno={g['IsSecured']!r} playbook={c['protegida']!r}")
        if _administrada(g.get("IsAuditEnabled"), bool, ca, f"value[{i}].IsAuditEnabled") != c["auditoria"]:
            difs.append(f"{n}.IsAuditEnabled: entorno={g['IsAuditEnabled']['Value']!r} playbook={c['auditoria']!r}")
        if exigir_forma(g.get("IsPrimaryName"), bool, ca, f"value[{i}].IsPrimaryName") != c["_primaria"]:
            difs.append(f"{n}.IsPrimaryName: entorno={g['IsPrimaryName']!r} playbook={c['_primaria']!r}")
        _texto_de(g.get("DisplayName"), lcid, f"{n}.DisplayName", c["displayname"], difs, ca, f"value[{i}].DisplayName")
        _texto_de(g.get("Description"), lcid, f"{n}.Description", c["descripcion"], difs, ca, f"value[{i}].Description", permite_nulo=True)

    declaradas_nombres = {c["nombre"] for c in declaradas}
    for nombre, g in sorted(en_entorno.items()):
        if g["_propia"] and g.get("AttributeOf") is None and g["_tipo"] not in TIPOS_AJENOS and nombre not in declaradas_nombres:
            difs.append(f"columna propia que el playbook no declara: {nombre} ({g['_tipo']})")

    # …y lo propio de cada familia, con un cast por familia presente.
    for familia in sorted({FAMILIA_DE[c["tipo"]] for c in presentes}):
        _, select, expand = FAMILIAS[familia]
        cf = f"la consulta de columnas {familia}AttributeMetadata de '{tabla}'"
        filas = _lista(dv, f"EntityDefinitions(LogicalName='{tabla}')/Attributes/Microsoft.Dynamics.CRM.{familia}AttributeMetadata?$select={select}{expand}", cf)
        por_nombre = {}
        for i, f in enumerate(filas):
            por_nombre[exigir_forma(f.get("LogicalName"), str, cf, f"value[{i}].LogicalName", no_vacio=True)] = (i, f)
        for c in presentes:
            if FAMILIA_DE[c["tipo"]] != familia:
                continue
            n = c["nombre"]
            if n not in por_nombre:
                raise ErrorEntorno(f"{cf} devolvió 200 con forma inesperada: '{n}' no vino entre las columnas de esa familia")
            i, f = por_nombre[n]
            _comparar_familia(c, f, i, cf, lcid, difs)

    cs = "la consulta de pertenencia a la solución (GET solutioncomponents)"
    filas_sc = _lista(dv, f"solutioncomponents?$filter=_solutionid_value eq {solution_id} and objectid eq {metadata_id} and componenttype eq {COMPONENTE_TABLA}", cs)
    if len(filas_sc) != 1:
        difs.append(f"pertenencia a la solución: {len(filas_sc)} filas en solutioncomponents, se esperaba 1")
    return {"existe": True, "diffs": difs, "metadata_id": metadata_id}


def _comparar_familia(c, f, i, consulta, lcid, difs):
    n, tipo = c["nombre"], c["tipo"]

    def igual(campo, tipo_py, esperado, permite_nulo=False):
        real = exigir_forma(f.get(campo), tipo_py, consulta, f"value[{i}].{campo}", permite_nulo=permite_nulo)
        if real != esperado:
            difs.append(f"{n}.{campo}: entorno={real!r} playbook={esperado!r}")

    if tipo in ("texto", "autonumerico"):
        igual("MaxLength", int, c["largo"])
        igual("AutoNumberFormat", str, c.get("formato") or None, permite_nulo=True)
    elif tipo == "memo":
        igual("MaxLength", int, c["largo"])
    elif tipo == "entero":
        igual("MinValue", int, c["minimo"])
        igual("MaxValue", int, c["maximo"])
    elif tipo == "archivo":
        igual("MaxSizeInKB", int, c["tamano_kb"])
    elif tipo in ("fecha", "fechahora"):
        solo_fecha = tipo == "fecha"
        igual("Format", str, "DateOnly" if solo_fecha else "DateAndTime")
        real = _administrada(f.get("DateTimeBehavior"), str, consulta, f"value[{i}].DateTimeBehavior")
        if real != ("DateOnly" if solo_fecha else "UserLocal"):
            difs.append(f"{n}.DateTimeBehavior: entorno={real!r} playbook={'DateOnly' if solo_fecha else 'UserLocal'!r}")
    elif tipo == "choice":
        g = exigir_forma(f.get("GlobalOptionSet"), dict, consulta, f"value[{i}].GlobalOptionSet")
        real = exigir_forma(g.get("Name"), str, consulta, f"value[{i}].GlobalOptionSet.Name")
        if real != c["choice"]:
            difs.append(f"{n}.choice: entorno={real!r} playbook={c['choice']!r}")
    elif tipo == "sino":
        igual("DefaultValue", bool, c["defecto"])
        o = exigir_forma(f.get("OptionSet"), dict, consulta, f"value[{i}].OptionSet")
        for clave, que, esperado in (("TrueOption", "etiqueta_si", c["etiqueta_si"]), ("FalseOption", "etiqueta_no", c["etiqueta_no"])):
            op = exigir_forma(o.get(clave), dict, consulta, f"value[{i}].OptionSet.{clave}")
            _texto_de(op.get("Label"), lcid, f"{n}.{que}", esperado, difs, consulta, f"value[{i}].OptionSet.{clave}.Label")


# ---------------------------------------------------------------------------
def ajustar_primaria(dv, datos, identidad):
    """Reenvía la definición completa de la columna primaria con el largo, el
    nivel de requerida y la auditoría del playbook, y publica la tabla. Devuelve `None` si
    salió bien, o el texto del problema. PUT reemplaza la definición entera:
    por eso se parte de la que devuelve el entorno y se cambian solo esas dos
    propiedades. El GET con cast no trae '@odata.type' y el PUT lo exige."""
    tabla, p = datos["nombre"], datos["primaria"]
    ruta = f"EntityDefinitions(LogicalName='{tabla}')/Attributes(LogicalName='{p['nombre']}')"
    consulta = f"la lectura de la columna primaria (GET Attributes '{p['nombre']}')"
    actual = _get(dv, ruta + "/Microsoft.Dynamics.CRM.StringAttributeMetadata", consulta)
    nivel = exigir_forma(actual.get("RequiredLevel"), dict, consulta, "RequiredLevel")
    definicion = {k: v for k, v in actual.items() if k != "@odata.context"}
    definicion["@odata.type"] = "Microsoft.Dynamics.CRM.StringAttributeMetadata"
    definicion["MaxLength"] = p["largo"]
    # El nombre visible y la descripción viajan en el mismo PUT (con MSCRM.MergeLabels).
    definicion["DisplayName"] = etiqueta_web_api(p["displayname"], identidad["lcid"])
    definicion["Description"] = etiqueta_web_api(p["descripcion"], identidad["lcid"])
    if p["autonumerico"]:
        # Volver autonumérica una primaria de texto que ya existe es el mismo PUT (ensayado el 2026-09-20).
        definicion["AutoNumberFormat"] = p["autonumerico"]
    definicion["RequiredLevel"] = {**nivel, "Value": "ApplicationRequired" if p["requerida"] else "None"}
    # La primaria hereda la auditoría de la tabla, y la plataforma también la ignora al crear: la deja auditada.
    aud = exigir_forma(actual.get("IsAuditEnabled"), dict, consulta, "IsAuditEnabled")
    definicion["IsAuditEnabled"] = {**aud, "Value": datos["auditoria"]}
    est, cuerpo, _ = escribir_metadatos(dv, "PUT", ruta, definicion, solucion=identidad["solucion"], cabeceras={"MSCRM.MergeLabels": "true"})
    if est != 204:
        return f"falló ajustar la columna primaria {p['nombre']}: HTTP {est} {cuerpo}"
    xml = f"<importexportxml><entities><entity>{tabla}</entity></entities></importexportxml>"
    est, cuerpo, _ = escribir_metadatos(dv, "POST", "PublishXml", {"ParameterXml": xml})
    if est != 204:
        return f"se ajustó la columna primaria {p['nombre']} pero falló publicar la tabla: HTTP {est} {cuerpo}"
    return None


def _solo_difiere_la_primaria(datos, diffs):
    """Lo único que `--corregir-primaria` acepta reparar, y solo en la primaria:
    largo, requerida, auditoría, nombre visible, descripción y,
    si el playbook la quiere autonumérica, darle su formato. Quitarle el
    formato a una columna que ya es autonumérica NO: eso no lo pide ningún
    playbook y cambiaría cómo se numeran los registros."""
    n = datos["primaria"]["nombre"]
    admitidas = [f"{n}.MaxLength:", f"{n}.RequiredLevel:", f"{n}.DisplayName:", f"{n}.Description:", f"{n}.IsAuditEnabled:"]
    if datos["primaria"]["autonumerico"]:
        admitidas.append(f"{n}.AutoNumberFormat:")
    return bool(diffs) and all(d.startswith(tuple(admitidas)) for d in diffs)


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, corregir_primaria=False, publicar=False):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    choices = comprobar_choices(dv, datos)
    actual = _verificar(dv, datos, identidad, solution_id)

    if solo_verificar and not actual["existe"]:
        return "error", componente, "la tabla no existe en el entorno; --solo-verificar no crea nada, correr la herramienta sin ese flag primero"
    if actual["existe"] and corregir_primaria and not solo_verificar and _solo_difiere_la_primaria(datos, actual["diffs"]):
        problema = ajustar_primaria(dv, datos, identidad)
        if problema:
            return "error", componente, problema
        actual = _verificar(dv, datos, identidad, solution_id)
        if not actual["diffs"]:
            return "ya_existia", componente, (
                "la tabla existía y su única diferencia era la columna primaria, que la plataforma había creado con sus valores "
                f"por defecto o como texto común; se corrigió (largo, requerida o formato autonumérico) y ahora coincide en todo; pertenece a '{solucion}'"
            )
    if actual["existe"] and publicar and not solo_verificar and not actual["diffs"]:
        # Publicar es inofensivo y se puede repetir: sirve cuando una corrida anterior ajustó la primaria y el publicar falló.
        xml = f"<importexportxml><entities><entity>{datos['nombre']}</entity></entities></importexportxml>"
        est, cuerpo, _ = escribir_metadatos(dv, "POST", "PublishXml", {"ParameterXml": xml})
        if est != 204:
            return "error", componente, f"la tabla coincide con el playbook pero falló publicarla: HTTP {est} {cuerpo}"
        return "ya_existia", componente, f"MetadataId {actual['metadata_id']}; coincide en todo lo que exige la receta y pertenece a '{solucion}'; se publicó de nuevo y no se modificó nada más"
    if actual["existe"]:
        if actual["diffs"]:
            return "difiere", componente, "; ".join(actual["diffs"])
        return "ya_existia", componente, f"MetadataId {actual['metadata_id']}; coincide en todo lo que exige la receta y pertenece a '{solucion}'; no se modificó nada"

    est, cuerpo, _ = escribir_metadatos(dv, "POST", "EntityDefinitions", construir_payload(datos, identidad, choices), solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {cuerpo}"
    for extra in columnas_protegidas_payload(datos, identidad, choices):
        est, cuerpo, _ = escribir_metadatos(dv, "POST", f"EntityDefinitions(LogicalName='{datos['nombre']}')/Attributes", extra, solucion=solucion)
        if est != 204:
            return (
                "error",
                componente,
                f"la tabla se creó pero quedó incompleta: falló agregar la columna protegida {extra['SchemaName']}: HTTP {est} {cuerpo}. "
                "La herramienta no repara una tabla existente: borrar la tabla (está vacía) y volver a correr",
            )
    if not datos["primaria"]["autonumerico"]:
        problema = ajustar_primaria(dv, datos, identidad)
        if problema:
            return "error", componente, f"la tabla se creó pero quedó incompleta: {problema}. Volver a correr con --corregir-primaria; si la verificación ya coincide y solo faltó publicar, con --publicar"
    final = _verificar(dv, datos, identidad, solution_id)
    if not final["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    if final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(final['diffs'])}"
    return "creado", componente, f"MetadataId {final['metadata_id']}, con {1 + len(datos['columnas'])} columnas, en la solución '{solucion}'"


def construir(ruta_playbook, solo_verificar, fabrica_cliente, verificadas=VERIFICADAS_EN_PLATAFORMA, permitir_no_verificadas=False,
              corregir_primaria=False, publicar=False):
    """Nunca lanza: siempre devuelve `(estado, componente, detalle)`."""
    componente = os.path.basename(ruta_playbook)
    paso = "leer el playbook"
    try:
        secciones = dividir_secciones(leer_texto(ruta_playbook))
        paso = "leer el bloque '## 2. Qué se crea'"
        datos = obtener_componente(secciones, TIPO)
        if isinstance(datos.get("nombre"), str):
            componente = datos["nombre"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque de la tabla"
        validar_playbook(datos, identidad)
        paso = "comprobar qué características están verificadas"
        comprobar_verificadas(datos, verificadas, permitir_no_verificadas)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} nombre={componente} columnas={1 + len(datos['columnas'])}")
    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, componente, corregir_primaria, publicar)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except ErrorEntorno as e:
        return "error", componente, str(e)
    except Exception as e:
        return "error", componente, f"fallo inesperado hablando con Dataverse, durante {rastro.en_curso}: {type(e).__name__}: {e}"


def main():
    argv = sys.argv[1:]
    rutas = [a for a in argv if not a.startswith("--")]
    if len(rutas) != 1:
        return salida("error", "desconocido", "uso incorrecto: tabla.py <playbook.md> [--solo-verificar] [--permitir-no-verificadas] [--corregir-primaria] [--publicar]")
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(rutas[0], "--solo-verificar" in argv, Dataverse,
                                            permitir_no_verificadas="--permitir-no-verificadas" in argv,
                                            corregir_primaria="--corregir-primaria" in argv, publicar="--publicar" in argv)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
