#!/usr/bin/env python3
"""Crea o actualiza un cloud flow (Power Automate) desde un playbook de tipo
`flujo`. El contenido NO va en el playbook: vive en un `.json` del repositorio,
se edita y se revisa como un archivo, y la herramienta lo sube.

    python3 herramientas/construir/flujo.py <playbook.md> [--solo-verificar] [--completar]

**Qué es un cloud flow por debajo.** Una fila de `workflows` con
`category = 5` (Modern Flow), `type = 1` y un `clientdata`: el JSON de la
definición Logic Apps más el mapa de connection references. Microsoft no
documenta ese JSON; el esquema de acá se sacó leyendo 37 flujos reales del
entorno el 2026-09-22.

**Por qué el archivo trae la definición casi cruda.** Un DSL propio que
generara Logic Apps sería reinventar Logic Apps, con más superficie para
equivocarse y sin nada a cambio. Lo que la herramienta sí resuelve, porque son
datos del ENTORNO y no del diseño, son tres sustituciones:

- `@@conr:<clave>@@`   → el alias de una connection reference del playbook
- `@@flujo:<nombre>@@` → el `workflowid` de otro flujo, para llamarlo como hijo
- `@@ev:<schemaname>@@`→ la clave `"<DisplayName> (<schemaname>)"` con que una
                         environment variable entra como parámetro

Así el archivo queda legible y sin un solo GUID escrito a mano: los GUID de un
entorno no valen en otro, y el repositorio tiene que poder viajar a Test y a
Producción.

**Activación.** Un flujo se crea desactivado y se activa con `statecode = 1`,
`statuscode = 2`. Los flujos HIJOS no se activan: se ejecutan cuando el padre
los llama. El playbook lo declara con `activar`.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import json
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
    exigir_forma,
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "flujo"

CATEGORIA_MODERNA = 5   # Modern Flow
TIPO_DEFINICION = 1     # Definition
ESTADO_ACTIVO = (1, 2)
ESTADO_INACTIVO = (0, 1)

ESQUEMA = ("https://schema.management.azure.com/providers/Microsoft.Logic/schemas/"
           "2016-06-01/workflowdefinition.json#")

CLAVES = {"tipo": str, "nombre": str, "descripcion": str, "archivo": str,
          "conexiones": dict, "variables": list, "hijos": list, "activar": bool}

# Funciones del lenguaje de expresiones de Logic Apps (Learn, "Reference guide
# to workflow expression functions"). Esta lista existe por un motivo concreto:
# **`filter(...)` NO es una función** —filtrar es una ACCIÓN—, y una definición
# que la use se sube sin protestar y revienta recién AL EJECUTARSE, con
# "The template function 'filter' is not defined or not valid". Pasó en Dev el
# 2026-09-22 con MPPP-VIG, en la primera corrida de la recurrencia.
# Si falta alguna, se agrega con su respaldo en Learn, nunca por intuición.
FUNCIONES = {
    "contains", "empty", "first", "intersection", "join", "last", "length", "skip", "sort",
    "take", "union", "createArray", "range", "reverse", "chunk",
    "array", "base64", "base64ToBinary", "base64ToString", "binary", "bool", "coalesce",
    "createGuid", "dataUri", "dataUriToBinary", "dataUriToString", "decodeBase64",
    "decodeDataUri", "decodeUriComponent", "encodeUriComponent", "float", "int", "json",
    "string", "uriComponent", "uriComponentToBinary", "uriComponentToString", "xml",
    "addDays", "addHours", "addMinutes", "addSeconds", "addToTime", "convertFromUtc",
    "convertTimeZone", "convertToUtc", "dayOfMonth", "dayOfWeek", "dayOfYear", "formatDateTime",
    "getFutureTime", "getPastTime", "startOfDay", "startOfHour", "startOfMonth",
    "subtractFromTime", "ticks", "utcNow", "dateDifference", "parseDateTime",
    "and", "equals", "greater", "greaterOrEquals", "if", "less", "lessOrEquals", "not", "or",
    "add", "div", "max", "min", "mod", "mul", "rand", "sub",
    "concat", "endswith", "endsWith", "guid", "indexof", "indexOf", "lastindexof", "lastIndexOf",
    "nthindexof", "replace", "split", "startswith", "startsWith", "substring", "toLower",
    "toUpper", "trim", "slice", "formatNumber", "isFloat", "isInt",
    "action", "actionBody", "actionOutputs", "actions", "body", "item", "items",
    "iterationIndexes", "outputs", "parameters", "result", "trigger", "triggerBody",
    "triggerFormDataMultiValues", "triggerFormDataValue", "triggerMultipartBody",
    "triggerOutputs", "variables", "workflow",
    "addProperty", "removeProperty", "setProperty", "xpath",
}

C_FLUJO = "la consulta del flujo (GET workflows)"
C_CONR = "la consulta de una connection reference (GET connectionreferences)"
C_EV = "la consulta de una variable de entorno (GET environmentvariabledefinitions)"

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def validar_playbook(datos, identidad, raiz):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque del flujo no tiene las claves esperadas: {'; '.join(partes)}")
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")
    for clave in ("nombre", "descripcion", "archivo"):
        exigir_forma(datos[clave], str, "el bloque del flujo", clave, no_vacio=True)
    exigir_forma(datos["activar"], bool, "el bloque del flujo", "activar")
    exigir_sin_tildes(datos["nombre"], "nombre")

    # `01-convenciones.md`: el nombre lleva el identificador corto del flujo (DF-11).
    prefijo = f"Cloud Flow - {identidad['abrev'].upper()} - "
    if not datos["nombre"].startswith(prefijo):
        raise ErrorPlaybook(f"nombre = {datos['nombre']!r} no empieza con {prefijo!r} (`07-flujos.md` DF-11)")

    conexiones = exigir_forma(datos["conexiones"], dict, "el bloque del flujo", "conexiones")
    for alias, conr in conexiones.items():
        exigir_forma(conr, dict, f"conexiones['{alias}']", "conexion")
        if sorted(conr) != ["api", "referencia"]:
            raise ErrorPlaybook(f"conexiones['{alias}']: se admite exactamente {{referencia, api}}")
        for campo in ("referencia", "api"):
            exigir_forma(conr[campo], str, f"conexiones['{alias}']", campo, no_vacio=True)

    exigir_forma(datos["variables"], [str], "el bloque del flujo", "variables")
    exigir_forma(datos["hijos"], [str], "el bloque del flujo", "hijos")
    if len(set(datos["hijos"])) != len(datos["hijos"]):
        raise ErrorPlaybook("la lista de hijos tiene repetidos")
    if datos["nombre"] in datos["hijos"]:
        raise ErrorPlaybook(f"el flujo '{datos['nombre']}' se declara como hijo de sí mismo")

    ruta = os.path.join(raiz, datos["archivo"])
    if not datos["archivo"].endswith(".json"):
        raise ErrorPlaybook(f"archivo = {datos['archivo']!r} no termina en '.json'")
    try:
        definicion = json.loads(leer_texto(ruta))
    except OSError as e:
        raise ErrorPlaybook(f"no se pudo leer la definición '{datos['archivo']}': {e}")
    except ValueError as e:
        raise ErrorPlaybook(f"la definición '{datos['archivo']}' no es JSON válido: {e}")
    _validar_definicion(definicion, datos)
    return definicion


def _comprobar_funciones(texto):
    """Rechaza una expresión que llame a algo que no es una función del
    lenguaje. La plataforma acepta la definición igual y solo falla al
    EJECUTAR, o sea después de que alguien la activó y creyó que andaba."""
    usadas = set(re.findall(r"@\{?([A-Za-z_][A-Za-z0-9_]*)\s*\(", texto))
    desconocidas = sorted(usadas - FUNCIONES)
    if desconocidas:
        raise ErrorPlaybook(
            f"la definición llama a {desconocidas}, que no es una función del lenguaje de "
            "expresiones de Logic Apps. Ojo con `filter`: filtrar una colección es una ACCIÓN "
            "(Foreach + If, o Query), no una función. Si la función existe y falta en la lista, "
            "agregala a FUNCIONES con su respaldo en Learn")


def _validar_definicion(definicion, datos):
    exigir_forma(definicion, dict, "la definición", "definicion")
    faltan = sorted({"triggers", "actions"} - set(definicion))
    if faltan:
        raise ErrorPlaybook(f"la definición no trae {faltan}")
    sobran = sorted(set(definicion) - {"triggers", "actions", "parameters", "outputs", "contentVersion", "$schema"})
    if sobran:
        raise ErrorPlaybook(f"la definición trae claves que la herramienta no arma: {sobran}")
    triggers = exigir_forma(definicion["triggers"], dict, "la definición", "triggers", no_vacio=True)
    if len(triggers) != 1:
        raise ErrorPlaybook(f"la definición tiene {len(triggers)} disparadores; un cloud flow tiene exactamente uno")
    acciones = exigir_forma(definicion["actions"], dict, "la definición", "actions", no_vacio=True)

    # Un flujo HIJO (disparador manual) tiene que terminar con una acción
    # `Response`: sin ella la plataforma deja crearlo, pero rechaza ACTIVAR al
    # padre con `ChildFlowMissingResponseOperation`, y el error aparece lejos
    # del archivo que lo causa (verificado en Dev el 2026-09-22).
    disparador = next(iter(triggers.values()))
    if disparador.get("type") == "Request" and not datos["activar"]:
        if not any(isinstance(a, dict) and a.get("type") == "Response" for a in acciones.values()):
            raise ErrorPlaybook(
                "es un flujo hijo (disparador manual) y su definición no tiene ninguna acción "
                "'Response'; sin ella el padre no se puede activar "
                "(ChildFlowMissingResponseOperation)")

    texto = json.dumps(definicion, ensure_ascii=False)
    _comprobar_funciones(texto)

    # Toda marca del texto tiene que estar declarada: si no, se sube una
    # definición con un `@@...@@` crudo y el flujo revienta en ejecución.
    for marca, declaradas, que in (("@@conr:", set(datos["conexiones"]), "conexiones"),
                                   ("@@flujo:", set(datos["hijos"]), "hijos"),
                                   ("@@ev:", set(datos["variables"]), "variables")):
        usadas = set()
        desde = 0
        while True:
            i = texto.find(marca, desde)
            if i < 0:
                break
            j = texto.find("@@", i + len(marca))
            if j < 0:
                raise ErrorPlaybook(f"la definición tiene una marca '{marca}' sin cerrar")
            usadas.add(texto[i + len(marca):j])
            desde = j + 2
        sin_declarar = sorted(usadas - declaradas)
        if sin_declarar:
            raise ErrorPlaybook(f"la definición usa {marca}{sin_declarar} y el playbook no lo declara en '{que}'")
        sin_usar = sorted(declaradas - usadas)
        if sin_usar:
            raise ErrorPlaybook(f"el playbook declara en '{que}' {sin_usar} y la definición no los usa")


# ---------------------------------------------------------------------------
# Armado del clientdata
# ---------------------------------------------------------------------------
def sustituir(texto, marca, valores):
    for clave, valor in valores.items():
        texto = texto.replace(f"@@{marca}:{clave}@@", valor)
    return texto


def clientdata(definicion, datos, ids_hijos, claves_variables, parametros_variables):
    """El `clientdata` completo, listo para `workflows`."""
    cuerpo = json.dumps(definicion, ensure_ascii=False)
    cuerpo = sustituir(cuerpo, "conr", {a: a for a in datos["conexiones"]})
    cuerpo = sustituir(cuerpo, "flujo", ids_hijos)
    cuerpo = sustituir(cuerpo, "ev", claves_variables)
    definicion = json.loads(cuerpo)

    parametros = {"$connections": {"defaultValue": {}, "type": "Object"},
                  "$authentication": {"defaultValue": {}, "type": "SecureObject"}}
    parametros.update(parametros_variables)
    definicion["$schema"] = ESQUEMA
    definicion["contentVersion"] = "1.0.0.0"
    definicion["parameters"] = parametros

    referencias = {}
    for alias, conr in datos["conexiones"].items():
        referencias[alias] = {
            "runtimeSource": "embedded",
            "connection": {"connectionReferenceLogicalName": conr["referencia"]},
            "api": {"name": conr["api"]},
        }
    return json.dumps({
        "properties": {"connectionReferences": referencias, "definition": definicion, "templateName": ""},
        "schemaVersion": "1.0.0.0",
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _leer_flujo(dv, nombre):
    ruta = ("workflows?$select=workflowid,name,description,category,type,statecode,statuscode,clientdata,ismanaged"
            f"&$filter=name eq '{nombre.replace(chr(39), chr(39) * 2)}' and category eq {CATEGORIA_MODERNA}")
    cuerpo = leer_entorno(dv, ruta, C_FLUJO)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_FLUJO, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_FLUJO} devolvió {len(filas)} flujos llamados '{nombre}'")
    return filas[0] if filas else None


def _conexiones(dv, datos):
    for alias, conr in datos["conexiones"].items():
        ruta = ("connectionreferences?$select=connectionreferencelogicalname,connectionid,statuscode"
                f"&$filter=connectionreferencelogicalname eq '{conr['referencia']}'")
        filas = exigir_forma(leer_entorno(dv, ruta, C_CONR).get("value"), [dict], C_CONR, "value")
        if not filas:
            raise Bloqueado(f"la connection reference '{conr['referencia']}' no existe; hay que crearla primero")
        if not filas[0].get("connectionid"):
            raise Bloqueado(
                f"la connection reference '{conr['referencia']}' existe pero no tiene conexión asociada; "
                "una persona tiene que conectarla desde el portal")


def _variables(dv, datos):
    """Devuelve `(claves, parametros)`: la clave con que cada variable entra en
    la definición y su bloque de parámetro."""
    claves, parametros = {}, {}
    for schemaname in datos["variables"]:
        ruta = ("environmentvariabledefinitions?$select=schemaname,displayname,defaultvalue,type"
                f"&$filter=schemaname eq '{schemaname}'")
        filas = exigir_forma(leer_entorno(dv, ruta, C_EV).get("value"), [dict], C_EV, "value")
        if not filas:
            raise Bloqueado(f"la variable de entorno '{schemaname}' no existe; hay que crearla primero")
        visible = filas[0].get("displayname") or schemaname
        clave = f"{visible} ({schemaname})"
        claves[schemaname] = clave
        parametros[clave] = {"defaultValue": filas[0].get("defaultvalue") or "",
                             "type": "String", "metadata": {"schemaName": schemaname}}
    return claves, parametros


def _ids_hijos(dv, datos):
    ids = {}
    for nombre in datos["hijos"]:
        hijo = _leer_flujo(dv, nombre)
        if hijo is None:
            raise Bloqueado(
                f"el flujo hijo '{nombre}' no existe en el entorno; hay que construirlo antes que este")
        ids[nombre] = exigir_forma(hijo.get("workflowid"), str, C_FLUJO, "workflowid", no_vacio=True)
    return ids


def _normalizar(texto):
    """Compara definiciones sin que el formato mande. `operationMetadataId` es
    un identificador que el diseñador regenera y no cambia el comportamiento:
    compararlo daría diferencias eternas."""
    try:
        objeto = json.loads(texto or "{}")
    except ValueError:
        return texto

    def limpiar(nodo):
        if isinstance(nodo, dict):
            return {k: limpiar(v) for k, v in sorted(nodo.items())
                    if k not in ("metadata", "operationMetadataId")}
        if isinstance(nodo, list):
            return [limpiar(x) for x in nodo]
        return nodo

    return json.dumps(limpiar(objeto), ensure_ascii=False, sort_keys=True)


def _contra_entorno(dv, datos, identidad, definicion, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    comprobar_solucion_e_idioma(dv, identidad)
    _conexiones(dv, datos)
    claves, parametros = _variables(dv, datos)
    ids = _ids_hijos(dv, datos)
    cuerpo_esperado = clientdata(definicion, datos, ids, claves, parametros)

    estado, estatus = ESTADO_ACTIVO if datos["activar"] else ESTADO_INACTIVO
    flujo = _leer_flujo(dv, datos["nombre"])
    hubo_escritura = False

    if flujo is None:
        if solo_verificar:
            return "difiere", componente, f"el flujo '{datos['nombre']}' no existe en el entorno"
        alta = {"name": datos["nombre"], "description": datos["descripcion"],
                "category": CATEGORIA_MODERNA, "type": TIPO_DEFINICION,
                "primaryentity": "none", "clientdata": cuerpo_esperado}
        est, resp, _ = escribir_metadatos(dv, "POST", "workflows", alta, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta del flujo devolvió HTTP {est} (se esperaba 204): {resp}"
        flujo = _leer_flujo(dv, datos["nombre"])
        if flujo is None:
            return "error", componente, "el alta del flujo no dio error pero no aparece al releer"
        hubo_escritura = True

    id_flujo = exigir_forma(flujo.get("workflowid"), str, C_FLUJO, "workflowid", no_vacio=True)
    if flujo.get("ismanaged"):
        return "difiere", componente, "el flujo está managed en este entorno; no se toca desde acá"

    difs = []
    if _normalizar(flujo.get("clientdata")) != _normalizar(cuerpo_esperado):
        difs.append("la definición del entorno no es la del archivo del repositorio")
    if (flujo.get("description") or "") != datos["descripcion"]:
        difs.append(f"description es {flujo.get('description')!r} y el playbook dice {datos['descripcion']!r}")

    if difs and (completar or hubo_escritura) and not solo_verificar:
        # Un flujo ACTIVO no acepta que le cambien la definición: se apaga,
        # se corrige y se vuelve a encender.
        if flujo.get("statecode") == 1:
            escribir_metadatos(dv, "PATCH", f"workflows({id_flujo})",
                               {"statecode": 0, "statuscode": 1}, dormir=dormir)
        est, resp, _ = escribir_metadatos(
            dv, "PATCH", f"workflows({id_flujo})",
            {"clientdata": cuerpo_esperado, "description": datos["descripcion"]}, dormir=dormir)
        if est not in (200, 204):
            return "error", componente, f"la corrección del flujo devolvió HTTP {est}: {resp}"
        hubo_escritura = True
        difs = []
        flujo = _leer_flujo(dv, datos["nombre"])

    estado_actual = (flujo.get("statecode"), flujo.get("statuscode"))
    if estado_actual != (estado, estatus) and not solo_verificar:
        est, resp, _ = escribir_metadatos(dv, "PATCH", f"workflows({id_flujo})",
                                          {"statecode": estado, "statuscode": estatus}, dormir=dormir)
        if est not in (200, 204):
            texto = str(resp)
            if "ConnectionAuthorizationFailed" in texto:
                # No es un defecto del flujo: la plataforma no deja que quien
                # corre esta herramienta active un flujo que usa una conexión
                # de OTRA persona. El flujo queda creado y correcto.
                raise Bloqueado(
                    "el flujo quedó creado y correcto, pero no se puede ACTIVAR desde acá: alguna de "
                    f"sus conexiones ({', '.join(c['referencia'] for c in datos['conexiones'].values())}) "
                    "pertenece a otra persona, y la plataforma responde ConnectionAuthorizationFailed. "
                    "Lo resuelve el dueño de la conexión: activando el flujo desde el portal, o "
                    "compartiendo la conexión con la identidad que corre esta herramienta")
            if "XrmEnvironmentVariableAttributeNotFound" in texto:
                # Una variable de entorno SIN VALOR no deja activar el flujo.
                # No es "falla después en ejecución": no arranca (verificado en
                # Dev el 2026-09-22 con `sanic_mppp_ev_carpetaprocesados`).
                sin_valor = [v for v in datos["variables"] if v in texto] or datos["variables"]
                raise Bloqueado(
                    f"el flujo quedó creado, pero no se puede activar: la variable de entorno "
                    f"{sin_valor} no tiene valor cargado en este entorno. Una variable sin valor "
                    "no deja activar el flujo (XrmEnvironmentVariableAttributeNotFound); hay que "
                    "cargarlo antes")
            if "ChildFlowNeverPublished" in texto:
                raise Bloqueado(
                    "el flujo quedó creado, pero no se puede activar porque un flujo hijo suyo nunca "
                    "se publicó. Un hijo tiene que activarse AL MENOS UNA VEZ antes de que un padre "
                    "activo pueda llamarlo: hay que activar primero el hijo")
            return "error", componente, (
                f"el flujo quedó bien pero no se pudo {'activar' if datos['activar'] else 'desactivar'}: "
                f"HTTP {est}: {resp}")
        hubo_escritura = True
        flujo = _leer_flujo(dv, datos["nombre"])
        estado_actual = (flujo.get("statecode"), flujo.get("statuscode"))

    if difs:
        return ("difiere" if not hubo_escritura else "error"), componente, "; ".join(difs) + (
            "" if not hubo_escritura else " (se escribió pero no quedó bien)")
    if estado_actual != (estado, estatus):
        return "difiere", componente, (
            f"el flujo existe pero está en statecode {estado_actual[0]}/{estado_actual[1]} y el playbook "
            f"pide {estado}/{estatus}")

    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"workflowid {id_flujo}, {'activado' if datos['activar'] else 'desactivado (es un flujo hijo)'}, "
        f"{len(datos['conexiones'])} conexion(es), {len(datos['variables'])} variable(s), "
        f"{len(datos['hijos'])} hijo(s), desde '{datos['archivo']}'")


def construir(ruta_playbook, solo_verificar, fabrica_cliente, completar=False, dormir=None, raiz=None):
    """Nunca lanza: siempre devuelve `(estado, componente, detalle)`."""
    if dormir is None:
        import time

        dormir = time.sleep
    if raiz is None:
        raiz = os.path.dirname(os.path.dirname(_AQUI))
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
        paso = "validar el bloque del flujo y su definición"
        definicion = validar_playbook(datos, identidad, raiz)
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
        return _contra_entorno(rastro, datos, identidad, definicion, solo_verificar, completar, componente, dormir)
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
            "uso incorrecto: flujo.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
