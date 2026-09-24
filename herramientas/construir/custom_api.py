#!/usr/bin/env python3
"""Construye UNA Custom API de Dataverse con sus parámetros de entrada y sus
propiedades de salida, desde un playbook de tipo `custom-api`. Contrato:
`power-platform-construir`, `references/dataverse/patrones.md`; Learn,
"CustomAPI tables".

    python3 herramientas/construir/custom_api.py <playbook.md> [--solo-verificar] [--completar]

Por qué esta herramienta es más desconfiada que las otras: en una Custom API
CASI TODO es inmutable. No se pueden cambiar, una vez guardados:

  - de la API:        uniquename, bindingtype, boundentitylogicalname,
                      isfunction, allowedcustomprocessingsteptype,
                      workflowsdkstepenabled
  - de un parámetro:  uniquename, type, isoptional, logicalentityname
  - de una salida:    uniquename, type, logicalentityname

Equivocarse en cualquiera de esos NO se arregla con un PATCH: hay que borrar la
API entera y rehacerla con todos sus parámetros. Por eso el playbook se valida
entero sin red antes de tocar nada, y por eso una diferencia en un campo
inmutable se informa como `difiere` diciendo explícitamente que hay que borrar.

`--completar` solo toca lo que SÍ se puede cambiar (displayname, descripción,
privilegio de ejecución, isprivate, el plugin asociado) y agrega los parámetros
que falten. Nunca borra ni pisa un campo inmutable.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
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
    exigir_forma,
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "custom-api"

# Learn, "CustomAPI tables" (verificado 2026-09-22). Se nombran por su etiqueta
# en el playbook, no por el número: un playbook que dice `7` no se lee.
TIPOS_DE_PARAMETRO = {
    "Boolean": 0, "DateTime": 1, "Decimal": 2, "Entity": 3, "EntityCollection": 4,
    "EntityReference": 5, "Float": 6, "Integer": 7, "Money": 8, "Picklist": 9,
    "String": 10, "StringArray": 11, "Guid": 12,
}

BINDING = {"Global": 0, "Entity": 1, "EntityCollection": 2}
PASOS_DE_TERCEROS = {"None": 0, "AsyncOnly": 1, "SyncAndAsync": 2}

# `logicalentityname` solo tiene sentido en estos tipos (Learn). En una salida,
# EntityCollection NO lo admite.
TIPOS_CON_TABLA = {"Entity", "EntityReference"}
TIPOS_CON_TABLA_ENTRADA = {"Entity", "EntityCollection", "EntityReference"}

LARGO_UNIQUENAME = 128
LARGO_NOMBRE = 256

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {
    "tipo": str, "nombre": str, "displayname": str, "descripcion": str, "plugintype": str,
    "esfuncion": bool, "esprivada": bool, "binding": str, "pasosdeterceros": str,
    "habilitadaenflujos": bool, "privilegio": str, "entrada": list, "salida": list,
}
CLAVES_PARAMETRO = {"nombre": str, "displayname": str, "descripcion": str, "tipo": str, "opcional": bool}
CLAVES_SALIDA = {"nombre": str, "displayname": str, "descripcion": str, "tipo": str}

C_API = "la consulta de la Custom API (GET customapis)"
C_TIPO_PLUGIN = "la consulta del tipo de plugin (GET plugintypes)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"

# Campos que NO se pueden cambiar después de guardados (Learn). Se comparan
# siempre, incluso con `--completar`, y una diferencia frena la herramienta.
INMUTABLES_API = ("uniquename", "bindingtype", "isfunction", "allowedcustomprocessingsteptype", "workflowsdkstepenabled")


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _solo_minusculas_y_digitos(texto):
    """Un unique name de parámetro, por rango de caracteres: nada de expresiones
    regulares ni de `str.isalnum()`, que acepta letras de cualquier alfabeto."""
    return texto != "" and all(("a" <= c <= "z") or ("0" <= c <= "9") for c in texto)


def _validar_bloque(datos, claves, de_donde):
    faltan, sobran = sorted(set(claves) - set(datos)), sorted(set(datos) - set(claves))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"{de_donde} no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in claves.items():
        # Un booleano en False es legítimo; un texto vacío no.
        exigir_forma(datos[clave], tipo, de_donde, clave, no_vacio=(tipo is str))


def _validar_parametro(p, indice, claves, es_salida, vistos):
    donde = f"{'la salida' if es_salida else 'el parámetro'} [{indice}]"
    _validar_bloque(p, claves, donde)

    nombre = p["nombre"]
    if not _solo_minusculas_y_digitos(nombre):
        raise ErrorPlaybook(
            f"{donde}: nombre = {nombre!r} solo puede llevar minúsculas ASCII y dígitos. "
            "Es el nombre con el que se llama al parámetro y es INMUTABLE"
        )
    if nombre in vistos:
        raise ErrorPlaybook(f"{donde}: el nombre {nombre!r} está repetido")
    vistos.add(nombre)

    if p["tipo"] not in TIPOS_DE_PARAMETRO:
        raise ErrorPlaybook(
            f"{donde}: tipo = {p['tipo']!r} no es un tipo de Custom API. Los válidos son {sorted(TIPOS_DE_PARAMETRO)}"
        )
    admitidos = TIPOS_CON_TABLA if es_salida else TIPOS_CON_TABLA_ENTRADA
    if p["tipo"] in admitidos:
        # No se soporta todavía: ninguna API de fase 1 lo necesita, y declararlo
        # a medias dejaría `logicalentityname` (inmutable) sin poner.
        raise ErrorPlaybook(
            f"{donde}: tipo = {p['tipo']!r} necesita `logicalentityname`, que este playbook no sabe declarar todavía"
        )
    exigir_sin_tildes(p["displayname"], f"{donde}.displayname")


def _validar_estructura(datos, identidad):
    _validar_bloque(datos, CLAVES, "el bloque de la Custom API")
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque de la Custom API dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    nombre = datos["nombre"]
    prefijo_esperado = f"{identidad['prefijo']}_{identidad['abrev']}_capi_"
    if not nombre.startswith(prefijo_esperado):
        # Learn: el unique name de una Custom API TIENE que llevar el prefijo
        # del publisher. El resto del patrón es nuestro (`01-convenciones` §2).
        raise ErrorPlaybook(f"nombre = {nombre!r} no sigue el patrón {prefijo_esperado}<nombre>")
    resto = nombre[len(prefijo_esperado):]
    if not _solo_minusculas_y_digitos(resto):
        raise ErrorPlaybook(f"nombre = {nombre!r}: después de {prefijo_esperado!r} solo van minúsculas ASCII y dígitos")
    if len(nombre) > LARGO_UNIQUENAME:
        raise ErrorPlaybook(f"nombre tiene {len(nombre)} caracteres; el máximo de la columna es {LARGO_UNIQUENAME}")

    exigir_sin_tildes(datos["displayname"], "displayname")
    if datos["binding"] not in BINDING:
        raise ErrorPlaybook(f"binding = {datos['binding']!r} no es válido; los válidos son {sorted(BINDING)}")
    if datos["binding"] != "Global":
        raise ErrorPlaybook(
            f"binding = {datos['binding']!r}: esta herramienta solo sabe crear API unbound, "
            "porque una atada a una tabla necesita `boundentitylogicalname` (inmutable)"
        )
    if datos["pasosdeterceros"] not in PASOS_DE_TERCEROS:
        raise ErrorPlaybook(
            f"pasosdeterceros = {datos['pasosdeterceros']!r} no es válido; los válidos son {sorted(PASOS_DE_TERCEROS)}"
        )
    if "." not in datos["plugintype"]:
        raise ErrorPlaybook(f"plugintype = {datos['plugintype']!r} no parece un nombre de tipo .NET completo")

    vistos = set()
    for i, p in enumerate(datos["entrada"]):
        exigir_forma(p, dict, "el bloque de la Custom API", f"entrada[{i}]")
        _validar_parametro(p, i, CLAVES_PARAMETRO, es_salida=False, vistos=vistos)
    for i, p in enumerate(datos["salida"]):
        exigir_forma(p, dict, "el bloque de la Custom API", f"salida[{i}]")
        _validar_parametro(p, i, CLAVES_SALIDA, es_salida=True, vistos=vistos)

    if datos["esfuncion"] and not datos["salida"]:
        # Learn: una Action puede no devolver nada; una Function TIENE que devolver.
        raise ErrorPlaybook("esfuncion = true pero no hay ninguna salida declarada; una Function tiene que devolver algo")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)


def nombre_largo(api_uniquename, identidad, es_salida, nombre_corto):
    """`name` (nombre primario) de un parámetro, calculado y no escrito a mano
    (`01-convenciones.md` §2): `sanic_mppp_capiip_<api>_<parametro>`. Calcularlo
    es lo que impide que se despegue del nombre real de la API."""
    prefijo_api = f"{identidad['prefijo']}_{identidad['abrev']}_capi_"
    corto_api = api_uniquename[len(prefijo_api):]
    medio = "capiop" if es_salida else "capiip"
    return f"{identidad['prefijo']}_{identidad['abrev']}_{medio}_{corto_api}_{nombre_corto}"


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _id_del_tipo_de_plugin(dv, typename):
    ruta = f"plugintypes?$select=plugintypeid,typename&$filter=typename eq '{typename}'"
    cuerpo = leer_entorno(dv, ruta, C_TIPO_PLUGIN)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_TIPO_PLUGIN, "value")
    if not filas:
        raise Bloqueado(
            f"el tipo de plugin '{typename}' no está registrado en el entorno; "
            "primero hay que registrar el paquete con `herramientas/construir/paquete_plugins.py`"
        )
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_TIPO_PLUGIN} devolvió {len(filas)} filas para '{typename}'; se esperaba una")
    return exigir_forma(filas[0].get("plugintypeid"), str, C_TIPO_PLUGIN, "plugintypeid", no_vacio=True)


def _leer_api(dv, uniquename):
    ruta = (
        "customapis?$select=customapiid,uniquename,name,displayname,description,executeprivilegename,"
        "isfunction,isprivate,bindingtype,allowedcustomprocessingsteptype,workflowsdkstepenabled,ismanaged"
        "&$expand=CustomAPIRequestParameters($select=customapirequestparameterid,uniquename,name,displayname,description,type,isoptional),"
        "CustomAPIResponseProperties($select=customapiresponsepropertyid,uniquename,name,displayname,description,type),"
        "PluginTypeId($select=plugintypeid,typename)"
        f"&$filter=uniquename eq '{uniquename}'"
    )
    cuerpo = leer_entorno(dv, ruta, C_API)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_API, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_API} devolvió {len(filas)} filas para '{uniquename}'; se esperaba a lo sumo una")
    return filas[0] if filas else None


def _cuerpo_api(datos, plugintype_id):
    return {
        "uniquename": datos["nombre"],
        "name": datos["nombre"],
        "displayname": datos["displayname"],
        "description": datos["descripcion"],
        "bindingtype": BINDING[datos["binding"]],
        "isfunction": datos["esfuncion"],
        "isprivate": datos["esprivada"],
        "allowedcustomprocessingsteptype": PASOS_DE_TERCEROS[datos["pasosdeterceros"]],
        "workflowsdkstepenabled": datos["habilitadaenflujos"],
        "executeprivilegename": datos["privilegio"],
        "PluginTypeId@odata.bind": f"/plugintypes({plugintype_id})",
    }


def _cuerpo_parametro(datos, identidad, p, api_id, es_salida):
    cuerpo = {
        "uniquename": p["nombre"],
        "name": nombre_largo(datos["nombre"], identidad, es_salida, p["nombre"]),
        "displayname": p["displayname"],
        "description": p["descripcion"],
        "type": TIPOS_DE_PARAMETRO[p["tipo"]],
        "CustomAPIId@odata.bind": f"/customapis({api_id})",
    }
    if not es_salida:
        cuerpo["isoptional"] = p["opcional"]
    return cuerpo


def _diferencias_de_parametros(datos, identidad, api, es_salida):
    """Compara lo declarado contra lo que hay. Devuelve (difs, faltantes)."""
    clave = "CustomAPIResponseProperties" if es_salida else "CustomAPIRequestParameters"
    declarados = datos["salida"] if es_salida else datos["entrada"]
    que = "salida" if es_salida else "entrada"
    existentes = {}
    for fila in exigir_forma(api.get(clave) or [], [dict], C_API, clave):
        existentes[exigir_forma(fila.get("uniquename"), str, C_API, f"{clave}.uniquename", no_vacio=True)] = fila

    difs, faltantes = [], []
    numero_a_nombre = {v: k for k, v in TIPOS_DE_PARAMETRO.items()}
    for p in declarados:
        fila = existentes.get(p["nombre"])
        if fila is None:
            faltantes.append(p)
            continue
        tipo_actual = exigir_forma(fila.get("type"), int, C_API, f"{clave}.type")
        if tipo_actual != TIPOS_DE_PARAMETRO[p["tipo"]]:
            difs.append(
                f"{que} '{p['nombre']}': el tipo es {numero_a_nombre.get(tipo_actual, tipo_actual)} y el playbook dice "
                f"{p['tipo']} (INMUTABLE: hay que borrar la Custom API entera y rehacerla)"
            )
        if not es_salida:
            opcional_actual = exigir_forma(fila.get("isoptional"), bool, C_API, f"{clave}.isoptional")
            if opcional_actual != p["opcional"]:
                difs.append(
                    f"entrada '{p['nombre']}': isoptional es {opcional_actual} y el playbook dice {p['opcional']} "
                    "(INMUTABLE: hay que borrar la Custom API entera y rehacerla)"
                )
        esperado_name = nombre_largo(datos["nombre"], identidad, es_salida, p["nombre"])
        for campo, esperado in (("name", esperado_name), ("displayname", p["displayname"]), ("description", p["descripcion"])):
            actual = fila.get(campo)
            if actual != esperado:
                difs.append(f"{que} '{p['nombre']}': {campo} es {actual!r} y el playbook dice {esperado!r}")

    sobrantes = sorted(set(existentes) - {p["nombre"] for p in declarados})
    if sobrantes:
        difs.append(f"la API tiene {que}s que el playbook no declara: {sobrantes} (esta herramienta nunca borra)")
    return difs, faltantes


def _diferencias_de_la_api(datos, api, plugintype_id):
    difs, corregibles = [], {}
    esperado = {
        "bindingtype": BINDING[datos["binding"]],
        "isfunction": datos["esfuncion"],
        "allowedcustomprocessingsteptype": PASOS_DE_TERCEROS[datos["pasosdeterceros"]],
        "workflowsdkstepenabled": datos["habilitadaenflujos"],
        "uniquename": datos["nombre"],
    }
    for campo in INMUTABLES_API:
        actual = api.get(campo)
        if actual != esperado[campo]:
            difs.append(
                f"{campo} es {actual!r} y el playbook dice {esperado[campo]!r} "
                "(INMUTABLE: hay que borrar la Custom API entera y rehacerla)"
            )

    for campo, valor in (
        ("name", datos["nombre"]), ("displayname", datos["displayname"]), ("description", datos["descripcion"]),
        ("executeprivilegename", datos["privilegio"]), ("isprivate", datos["esprivada"]),
    ):
        if api.get(campo) != valor:
            difs.append(f"{campo} es {api.get(campo)!r} y el playbook dice {valor!r}")
            corregibles[campo] = valor

    tipo = api.get("PluginTypeId") or {}
    if tipo.get("typename") != datos["plugintype"]:
        difs.append(f"el plugin asociado es {tipo.get('typename')!r} y el playbook dice {datos['plugintype']!r}")
        corregibles["PluginTypeId@odata.bind"] = f"/plugintypes({plugintype_id})"

    if api.get("ismanaged"):
        difs.append("la Custom API está managed en este entorno; no se toca desde acá")
        corregibles.clear()
    return difs, corregibles


def _en_la_solucion(dv, solution_id, api_id):
    """Igual que en el paquete: NO se filtra por `componenttype`, porque Learn
    no publica el de `customapi`. Se lee el que la plataforma haya puesto."""
    ruta = (
        "solutioncomponents?$select=componenttype,objectid"
        f"&$filter=_solutionid_value eq {solution_id} and objectid eq {api_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _crear_parametros(dv, datos, identidad, api_id, solucion, faltantes, es_salida, dormir):
    ruta = "customapiresponseproperties" if es_salida else "customapirequestparameters"
    for p in faltantes:
        cuerpo = _cuerpo_parametro(datos, identidad, p, api_id, es_salida)
        est, resp, _ = escribir_metadatos(dv, "POST", ruta, cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return f"el alta de '{p['nombre']}' devolvió HTTP {est} (se esperaba 204): {resp}"
    return None


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    plugintype_id = _id_del_tipo_de_plugin(dv, datos["plugintype"])
    api = _leer_api(dv, datos["nombre"])

    hubo_escritura = False
    if api is None:
        if solo_verificar:
            return "difiere", componente, f"la Custom API '{datos['nombre']}' no existe en el entorno"
        est, resp, _ = escribir_metadatos(
            dv, "POST", "customapis", _cuerpo_api(datos, plugintype_id), dormir=dormir, solucion=solucion
        )
        if est not in (200, 201, 204):
            return "error", componente, f"el alta de la Custom API devolvió HTTP {est} (se esperaba 204): {resp}"
        api = _leer_api(dv, datos["nombre"])
        if api is None:
            return "error", componente, "el alta no devolvió error pero la Custom API no aparece al releer"
        api_id = exigir_forma(api.get("customapiid"), str, C_API, "customapiid", no_vacio=True)
        for es_salida in (False, True):
            declarados = datos["salida"] if es_salida else datos["entrada"]
            problema = _crear_parametros(dv, datos, identidad, api_id, solucion, declarados, es_salida, dormir)
            if problema:
                return "error", componente, f"la Custom API se creó pero {problema}"
        hubo_escritura = True
    else:
        api_id = exigir_forma(api.get("customapiid"), str, C_API, "customapiid", no_vacio=True)
        if completar and not solo_verificar:
            corregir, corregibles = _diferencias_de_la_api(datos, api, plugintype_id)
            # Un campo inmutable mal puesto no se intenta arreglar: se informa y
            # se frena, para que nadie crea que quedó corregido.
            if not [d for d in corregir if "INMUTABLE" in d]:
                for es_salida in (False, True):
                    _, faltantes = _diferencias_de_parametros(datos, identidad, api, es_salida)
                    if faltantes:
                        problema = _crear_parametros(dv, datos, identidad, api_id, solucion, faltantes, es_salida, dormir)
                        if problema:
                            return "error", componente, problema
                        hubo_escritura = True
                if corregibles:
                    est, resp, _ = escribir_metadatos(
                        dv, "PATCH", f"customapis({api_id})", corregibles, dormir=dormir, solucion=solucion
                    )
                    if est not in (200, 204):
                        return "error", componente, f"la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
                    hubo_escritura = True

    accion = "creado" if hubo_escritura else "ya_existia"
    if hubo_escritura:
        # Toda escritura se verifica contra una lectura fresca: lo que importa
        # no es que el POST diera 204, sino que el entorno haya quedado así.
        api = _leer_api(dv, datos["nombre"])
        if api is None:
            return "error", componente, "la Custom API desapareció al releer después de escribir"

    difs, _ = _diferencias_de_la_api(datos, api, plugintype_id)
    for es_salida in (False, True):
        d, faltantes = _diferencias_de_parametros(datos, identidad, api, es_salida)
        difs.extend(d)
        difs.extend(f"falta {'la salida' if es_salida else 'el parámetro'} '{p['nombre']}'" for p in faltantes)

    fila = _en_la_solucion(dv, solution_id, api_id)
    if fila is None:
        difs.append(f"la Custom API no figura como componente de la solución (solutionid {solution_id})")

    if difs:
        estado = "error" if accion == "creado" else "difiere"
        prefijo = "se escribió pero no quedó bien: " if accion == "creado" else ""
        return estado, componente, prefijo + "; ".join(difs)

    return accion, componente, (
        f"customapiid {api_id}, {len(datos['entrada'])} de entrada y {len(datos['salida'])} de salida, "
        f"plugin {datos['plugintype']}, privilegio {datos['privilegio']}, "
        f"en la solución '{solucion}' con componenttype {fila.get('componenttype')}"
    )


def construir(ruta_playbook, solo_verificar, fabrica_cliente, completar=False, dormir=None):
    """Nunca lanza: siempre devuelve `(estado, componente, detalle)`."""
    if dormir is None:
        import time

        dormir = time.sleep
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
        paso = "validar el bloque de la Custom API"
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
        return _contra_entorno(rastro, datos, identidad, solo_verificar, completar, componente, dormir)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except ErrorEntorno as e:
        return "error", componente, str(e)
    except Exception as e:
        return "error", componente, f"fallo inesperado hablando con Dataverse, durante {rastro.en_curso}: {type(e).__name__}: {e}"


def main():
    argv = sys.argv[1:]
    rutas = [a for a in argv if not a.startswith("--")]
    banderas = {a for a in argv if a.startswith("--")}
    desconocidas = sorted(banderas - {"--solo-verificar", "--completar"})
    if len(rutas) != 1 or desconocidas:
        return salida(
            "error", "desconocido",
            "uso incorrecto: custom_api.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas
    )
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
