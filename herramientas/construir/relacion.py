#!/usr/bin/env python3
"""Construye UNA relación 1:N de Dataverse con su columna lookup, desde un
playbook de tipo `relacion`. Contrato: `power-platform-construir`,
`references/modelo-datos/patrones.md` §1 y §2.3.

    python3 herramientas/construir/relacion.py <playbook.md> [--solo-verificar] [--publicar]

La relación y su lookup nacen juntos, en un solo POST; después se publican
las tablas tocadas (una relación, a diferencia de una tabla, no se publica
sola). Nunca modifica ni borra: si la relación existe y no coincide, informa
`difiere`. `--publicar` vuelve a publicar solo si coincide en todo.

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
    auditoria_administrada,
    comparar_etiqueta,
    comprobar_solucion_e_idioma,
    dividir_secciones,
    escribir_metadatos,
    etiqueta_web_api,
    exigir_forma,
    leer_entorno,
    leer_texto,
    nivel_requerido,
    obtener_componente,
    obtener_identidad,
    salida,
    valor_administrado,
)

TIPO = "relacion"
LARGO_MAXIMO_RELACION = 100  # schema name de una relación (Learn, tabla EntityRelationship)
LARGO_MAXIMO_IDENTIFICADOR = 95
COMPONENTE_RELACION = 10  # tipo de componente de una relación en solutioncomponents
TABLAS_DEL_SISTEMA = {"systemuser"}  # únicas tablas ajenas que el formato admite como padre

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "tabla_padre": str, "tabla_hija": str, "comportamiento": str, "lookup": dict}
CLAVES_LOOKUP = {"nombre": str, "displayname": str, "descripcion": str, "requerida": bool, "auditoria": bool}

# Cascadas de cada comportamiento estándar (Learn, "Edit relationships").
_SIN = {"Assign": "NoCascade", "Merge": "NoCascade", "Reparent": "NoCascade", "Share": "NoCascade", "Unshare": "NoCascade", "RollupView": "NoCascade"}
CASCADAS = {
    "parental": {"Assign": "Cascade", "Delete": "Cascade", "Merge": "NoCascade", "Reparent": "Cascade", "Share": "Cascade", "Unshare": "Cascade", "RollupView": "NoCascade"},
    "restringido": dict(_SIN, Delete="Restrict"),
    "quitar_vinculo": dict(_SIN, Delete="RemoveLink"),
}


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
        valor = datos[clave]
        donde = f"'{clave}'" if de_donde == "la relación" else f"{de_donde}.{clave}"
        if tipo is bool and not isinstance(valor, bool):
            raise ErrorPlaybook(f"{donde} tiene que ser true o false, no {valor!r}")
        if tipo is str and (not isinstance(valor, str) or not valor.strip()):
            raise ErrorPlaybook(f"{donde} tiene que ser texto no vacío, no {valor!r}")
        if tipo is dict and not isinstance(valor, dict):
            raise ErrorPlaybook(f"{donde} tiene que ser un objeto, no {valor!r}")


def _corto(tabla, prefijo, abrev):
    """`sanic_mppp_tbl_cliente` → `cliente`; una tabla del sistema queda igual."""
    inicio = f"{prefijo}_{abrev}_tbl_"
    return tabla[len(inicio):] if tabla.startswith(inicio) else tabla


def validar_playbook(datos, identidad):
    _validar_bloque(datos, CLAVES, "la relación")
    prefijo, abrev = identidad["prefijo"], identidad["abrev"]
    patron_tabla = rf"{prefijo}_{abrev}_tbl_[a-z0-9]+"
    if not re.fullmatch(patron_tabla, datos["tabla_hija"]):
        raise ErrorPlaybook(f"'tabla_hija' = {datos['tabla_hija']!r} no cumple {patron_tabla}: el lookup se crea en una tabla de la solución")
    if datos["tabla_padre"] not in TABLAS_DEL_SISTEMA and not re.fullmatch(patron_tabla, datos["tabla_padre"]):
        raise ErrorPlaybook(f"'tabla_padre' = {datos['tabla_padre']!r} no cumple {patron_tabla} ni es una de {sorted(TABLAS_DEL_SISTEMA)}")
    if datos["comportamiento"] not in CASCADAS:
        raise ErrorPlaybook(f"'comportamiento' tiene que ser uno de {sorted(CASCADAS)}, no {datos['comportamiento']!r}")

    # BP-PP-188: <prefijo>_<abrev>_<padre>_<hijo>, con sufijo libre si hay más de una relación entre el mismo par.
    base = f"{prefijo}_{abrev}_{_corto(datos['tabla_padre'], prefijo, abrev)}_{_corto(datos['tabla_hija'], prefijo, abrev)}"
    if not re.fullmatch(rf"{re.escape(base)}(_[a-z0-9]+)?", datos["nombre"]):
        raise ErrorPlaybook(f"'nombre' = {datos['nombre']!r} tiene que ser {base!r}, o {base + '_<sufijo>'!r} si hay más de una relación entre esas dos tablas (BP-PP-188, todo en minúscula)")
    if len(datos["nombre"]) > LARGO_MAXIMO_RELACION:
        raise ErrorPlaybook(f"'nombre' tiene {len(datos['nombre'])} caracteres; el máximo de una relación es {LARGO_MAXIMO_RELACION}")

    k = datos["lookup"]
    _validar_bloque(k, CLAVES_LOOKUP, "lookup")
    if not re.fullmatch(rf"{prefijo}_[a-z0-9]+", k["nombre"]):
        raise ErrorPlaybook(f"lookup.nombre = {k['nombre']!r} no cumple {prefijo}_[a-z0-9]+ (todo en minúscula, BP-PP-184)")
    if len(k["nombre"]) > LARGO_MAXIMO_IDENTIFICADOR:
        raise ErrorPlaybook(f"lookup.nombre tiene {len(k['nombre'])} caracteres; el máximo es {LARGO_MAXIMO_IDENTIFICADOR}")


# ---------------------------------------------------------------------------
# Cuerpo del POST
# ---------------------------------------------------------------------------
def construir_payload(datos, identidad, atributo_referenciado):
    lcid, k = identidad["lcid"], datos["lookup"]
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": datos["nombre"],
        "ReferencedEntity": datos["tabla_padre"],
        "ReferencedAttribute": atributo_referenciado,
        "ReferencingEntity": datos["tabla_hija"],
        "CascadeConfiguration": dict(CASCADAS[datos["comportamiento"]]),
        "AssociatedMenuConfiguration": {"Behavior": "UseCollectionName", "Group": "Details", "Order": 10000},
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "AttributeType": "Lookup",
            "AttributeTypeName": {"Value": "LookupType"},
            "SchemaName": k["nombre"],
            "DisplayName": etiqueta_web_api(k["displayname"], lcid),
            "Description": etiqueta_web_api(k["descripcion"], lcid),
            "RequiredLevel": nivel_requerido(k["requerida"]),
            "IsAuditEnabled": auditoria_administrada(k["auditoria"]),
        },
    }


# ---------------------------------------------------------------------------
# Lectura del entorno: una sola función para los tres caminos
# ---------------------------------------------------------------------------
def comprobar_tablas(dv, datos):
    """Precondición: las dos tablas existen. Devuelve la clave primaria de la
    tabla padre, que es el atributo referenciado."""
    claves = {}
    for rol in ("tabla_padre", "tabla_hija"):
        tabla = datos[rol]
        consulta = f"la consulta de la tabla '{tabla}' (GET EntityDefinitions)"
        t = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')?$select=LogicalName,PrimaryIdAttribute,IsCustomEntity", consulta, admite_404=True)
        if t is None:
            raise Bloqueado(f"la tabla '{tabla}' ({rol}) no existe en el entorno: se construye antes que sus relaciones")
        claves[rol] = exigir_forma(t.get("PrimaryIdAttribute"), str, consulta, "PrimaryIdAttribute", no_vacio=True)
    return claves["tabla_padre"]


def _verificar(dv, datos, identidad, solution_id, atributo_referenciado):
    lcid, difs, k = identidad["lcid"], [], datos["lookup"]
    cr = f"la consulta de la relación (GET RelationshipDefinitions '{datos['nombre']}')"
    r = leer_entorno(dv, f"RelationshipDefinitions(SchemaName='{datos['nombre']}')/Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata", cr, admite_404=True)
    if r is None:
        return {"existe": False, "diffs": None, "metadata_id": None}
    metadata_id = exigir_forma(r.get("MetadataId"), str, cr, "MetadataId", no_vacio=True)
    for campo, tipo, esperado in [("ReferencedEntity", str, datos["tabla_padre"]), ("ReferencedAttribute", str, atributo_referenciado),
                                  ("ReferencingEntity", str, datos["tabla_hija"]), ("ReferencingAttribute", str, k["nombre"]),
                                  ("IsCustomRelationship", bool, True), ("IsManaged", bool, False)]:
        real = exigir_forma(r.get(campo), tipo, cr, campo)
        if real != esperado:
            difs.append(f"{campo}: entorno={real!r} playbook={esperado!r}")
    cascada = exigir_forma(r.get("CascadeConfiguration"), dict, cr, "CascadeConfiguration")
    for accion, esperado in CASCADAS[datos["comportamiento"]].items():
        real = exigir_forma(cascada.get(accion), str, cr, f"CascadeConfiguration.{accion}")
        if real != esperado:
            difs.append(f"CascadeConfiguration.{accion}: entorno={real!r} playbook={esperado!r} (comportamiento '{datos['comportamiento']}')")

    n = k["nombre"]
    cl = f"la consulta de la columna lookup (GET Attributes '{n}' LookupAttributeMetadata)"
    a = leer_entorno(dv, f"EntityDefinitions(LogicalName='{datos['tabla_hija']}')/Attributes(LogicalName='{n}')/Microsoft.Dynamics.CRM.LookupAttributeMetadata"
                         "?$select=LogicalName,SchemaName,AttributeTypeName,Targets,RequiredLevel,IsAuditEnabled,IsSecured,DisplayName,Description", cl)
    tipo_real = valor_administrado(a.get("AttributeTypeName"), str, cl, "AttributeTypeName")
    if tipo_real != "LookupType":
        difs.append(f"{n}.tipo: entorno={tipo_real!r} playbook='LookupType'")
    destinos = exigir_forma(a.get("Targets"), [str], cl, "Targets")
    if destinos != [datos["tabla_padre"]]:
        difs.append(f"{n}.Targets: entorno={destinos!r} playbook={[datos['tabla_padre']]!r}")
    nivel = valor_administrado(a.get("RequiredLevel"), str, cl, "RequiredLevel")
    if nivel != ("ApplicationRequired" if k["requerida"] else "None"):
        difs.append(f"{n}.RequiredLevel: entorno={nivel!r} playbook={'ApplicationRequired' if k['requerida'] else 'None'!r}")
    if valor_administrado(a.get("IsAuditEnabled"), bool, cl, "IsAuditEnabled") != k["auditoria"]:
        difs.append(f"{n}.IsAuditEnabled: entorno={a['IsAuditEnabled']['Value']!r} playbook={k['auditoria']!r}")
    if exigir_forma(a.get("IsSecured"), bool, cl, "IsSecured"):
        difs.append(f"{n}.IsSecured: entorno=True playbook=False")
    comparar_etiqueta(a.get("DisplayName"), lcid, f"{n}.DisplayName", k["displayname"], difs, cl, "DisplayName")
    comparar_etiqueta(a.get("Description"), lcid, f"{n}.Description", k["descripcion"], difs, cl, "Description", permite_nulo=True)

    cs = "la consulta de pertenencia a la solución (GET solutioncomponents)"
    sc = leer_entorno(dv, f"solutioncomponents?$filter=_solutionid_value eq {solution_id} and objectid eq {metadata_id} and componenttype eq {COMPONENTE_RELACION}", cs)
    filas = exigir_forma(sc.get("value"), [dict], cs, "value")
    if len(filas) != 1:
        difs.append(f"pertenencia a la solución: {len(filas)} filas en solutioncomponents, se esperaba 1")
    return {"existe": True, "diffs": difs, "metadata_id": metadata_id}


def _publicar(dv, datos):
    tablas = [t for t in (datos["tabla_padre"], datos["tabla_hija"]) if t not in TABLAS_DEL_SISTEMA]
    xml = "<importexportxml><entities>" + "".join(f"<entity>{t}</entity>" for t in tablas) + "</entities></importexportxml>"
    est, cuerpo, _ = escribir_metadatos(dv, "POST", "PublishXml", {"ParameterXml": xml})
    return None if est == 204 else f"HTTP {est} {cuerpo}"


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, publicar):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    atributo = comprobar_tablas(dv, datos)
    actual = _verificar(dv, datos, identidad, solution_id, atributo)

    if solo_verificar and not actual["existe"]:
        return "error", componente, "la relación no existe en el entorno; --solo-verificar no crea nada, correr la herramienta sin ese flag primero"
    if actual["existe"]:
        if actual["diffs"]:
            return "difiere", componente, "; ".join(actual["diffs"])
        extra = "no se modificó nada"
        if publicar and not solo_verificar:
            problema = _publicar(dv, datos)
            if problema:
                return "error", componente, f"la relación coincide con el playbook pero falló publicar: {problema}"
            extra = "se publicó de nuevo y no se modificó nada más"
        return "ya_existia", componente, f"MetadataId {actual['metadata_id']}; coincide en todo lo que exige la receta y pertenece a '{solucion}'; {extra}"

    est, cuerpo, _ = escribir_metadatos(dv, "POST", "RelationshipDefinitions", construir_payload(datos, identidad, atributo), solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {cuerpo}"
    problema = _publicar(dv, datos)
    if problema:
        return "error", componente, f"la relación se creó pero falló publicar: {problema}. Verificar con --solo-verificar y, si coincide, volver a correr con --publicar"
    final = _verificar(dv, datos, identidad, solution_id, atributo)
    if not final["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    if final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(final['diffs'])}"
    return "creado", componente, f"MetadataId {final['metadata_id']}, con su lookup {datos['tabla_hija']}.{datos['lookup']['nombre']}, en la solución '{solucion}'"


def construir(ruta_playbook, solo_verificar, fabrica_cliente, publicar=False):
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
        paso = "validar el bloque de la relación"
        validar_playbook(datos, identidad)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} nombre={componente}")
    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, componente, publicar)
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
        return salida("error", "desconocido", "uso incorrecto: relacion.py <playbook.md> [--solo-verificar] [--publicar]")
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(rutas[0], "--solo-verificar" in argv, Dataverse, publicar="--publicar" in argv)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
