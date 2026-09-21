#!/usr/bin/env python3
"""Construye UNA clave alternativa de Dataverse, desde un playbook de tipo
`clave`. Contrato: `power-platform-construir`,
`references/modelo-datos/patrones.md` §1 y §2.4.

    python3 herramientas/construir/clave.py <playbook.md> [--solo-verificar]

La clave se crea con un POST y su índice se arma DESPUÉS, en un trabajo del
sistema: la herramienta espera a que `EntityKeyIndexStatus` llegue a `Active`.
Una clave que no está `Active` no sirve (no garantiza unicidad ni resuelve un
upsert), así que no se informa `creado` hasta verla activa.

Nunca modifica ni borra: si la clave existe y no coincide, informa `difiere`.
Tampoco reactiva sola un índice `Failed`: casi siempre falló porque ya hay
datos duplicados, y eso lo resuelve una persona.

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
    comparar_etiqueta,
    comprobar_solucion_e_idioma,
    dividir_secciones,
    escribir_metadatos,
    etiqueta_web_api,
    exigir_forma,
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
    valor_administrado,
)

TIPO = "clave"
LARGO_MAXIMO_IDENTIFICADOR = 95
MAXIMO_COLUMNAS = 16  # Learn, "Define alternate keys"
MAXIMO_BYTES = 900
COMPONENTE_TABLA = 1  # la clave viaja dentro de su tabla: no tiene fila propia en solutioncomponents (ensayo del 2026-09-21)
INCLUYE_SUBCOMPONENTES = 0  # rootcomponentbehavior de una tabla agregada con todo lo suyo
ESPERA_INDICE_SEGUNDOS = 10
INTENTOS_INDICE = 30
ESTADOS_EN_CURSO = ("Pending", "InProgress")

# Bytes que ocupa en el índice cada tipo que admite clave. Un texto ocupa 2 por carácter.
BYTES_POR_TIPO = {"IntegerType": 4, "DecimalType": 17, "DateTimeType": 8, "LookupType": 16, "PicklistType": 4}
TIPOS_ADMITIDOS = sorted(list(BYTES_POR_TIPO) + ["StringType"])

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "displayname": str, "tabla": str, "columnas": list}


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_estructura(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        raise ErrorPlaybook(f"claves de la clave alternativa inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
    for clave, tipo in CLAVES.items():
        valor = datos[clave]
        if tipo is str and (not isinstance(valor, str) or not valor.strip()):
            raise ErrorPlaybook(f"'{clave}' tiene que ser texto no vacío, no {valor!r}")
        if tipo is list and (not isinstance(valor, list) or not valor):
            raise ErrorPlaybook(f"'{clave}' tiene que ser una lista no vacía de nombres lógicos de columna, no {valor!r}")

    prefijo, abrev = identidad["prefijo"], identidad["abrev"]
    inicio_tabla = f"{prefijo}_{abrev}_tbl_"
    if not re.fullmatch(rf"{inicio_tabla}[a-z0-9]+", datos["tabla"]):
        raise ErrorPlaybook(f"'tabla' = {datos['tabla']!r} no cumple {inicio_tabla}[a-z0-9]+: la clave se crea en una tabla de la solución")

    # BP-PP-188: <prefijo>_<abrev>_key_<tabla>_<campos>
    inicio = f"{prefijo}_{abrev}_key_{datos['tabla'][len(inicio_tabla):]}_"
    if not re.fullmatch(rf"{re.escape(inicio)}[a-z0-9_]+", datos["nombre"]):
        raise ErrorPlaybook(f"'nombre' = {datos['nombre']!r} tiene que empezar con {inicio!r} y seguir con los campos, todo en minúscula")
    if len(datos["nombre"]) > LARGO_MAXIMO_IDENTIFICADOR:
        raise ErrorPlaybook(f"'nombre' tiene {len(datos['nombre'])} caracteres; el máximo es {LARGO_MAXIMO_IDENTIFICADOR}")
    inicio_visible = f"KEY - {abrev.upper()} - "
    if not datos["displayname"].startswith(inicio_visible):
        raise ErrorPlaybook(f"'displayname' = {datos['displayname']!r} tiene que empezar con {inicio_visible!r}")

    columnas = datos["columnas"]
    if len(columnas) > MAXIMO_COLUMNAS:
        raise ErrorPlaybook(f"'columnas' trae {len(columnas)}; una clave admite {MAXIMO_COLUMNAS} como máximo")
    for i, c in enumerate(columnas):
        if not isinstance(c, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", c):
            raise ErrorPlaybook(f"columnas[{i}] = {c!r} tiene que ser el nombre lógico de una columna, en minúscula")
    repetidas = sorted({c for c in columnas if columnas.count(c) > 1})
    if repetidas:
        raise ErrorPlaybook(f"'columnas' trae una columna repetida: {repetidas}")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)
    exigir_sin_tildes(datos["displayname"], "'displayname'")


# ---------------------------------------------------------------------------
# Cuerpo del POST
# ---------------------------------------------------------------------------
def construir_payload(datos, identidad):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityKeyMetadata",
        "SchemaName": datos["nombre"],
        "DisplayName": etiqueta_web_api(datos["displayname"], identidad["lcid"]),
        "KeyAttributes": list(datos["columnas"]),
    }


# ---------------------------------------------------------------------------
# Lectura del entorno
# ---------------------------------------------------------------------------
def comprobar_tabla_y_columnas(dv, datos):
    """Precondiciones: la tabla existe; cada columna existe, es de un tipo que
    admite clave, no lleva seguridad de columna, y entre todas no pasan de 900
    bytes. Devuelve el MetadataId de la tabla, que usa la verificación."""
    tabla = datos["tabla"]
    ct = f"la consulta de la tabla '{tabla}' (GET EntityDefinitions)"
    t = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')?$select=LogicalName", ct, admite_404=True)
    if t is None:
        raise Bloqueado(f"la tabla '{tabla}' no existe en el entorno: se construye antes que sus claves")
    id_tabla = exigir_forma(t.get("MetadataId"), str, ct, "MetadataId", no_vacio=True)

    ca = f"la consulta de las columnas de '{tabla}' (GET Attributes)"
    cuerpo = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')/Attributes?$select=LogicalName,AttributeTypeName,IsSecured", ca)
    tipos = {}
    for i, a in enumerate(exigir_forma(cuerpo.get("value"), [dict], ca, "value")):
        nombre = exigir_forma(a.get("LogicalName"), str, ca, f"value[{i}].LogicalName", no_vacio=True)
        if nombre not in datos["columnas"]:
            continue
        tipos[nombre] = valor_administrado(a.get("AttributeTypeName"), str, ca, f"value[{i}].AttributeTypeName")
        if exigir_forma(a.get("IsSecured"), bool, ca, f"value[{i}].IsSecured"):
            raise Bloqueado(f"la columna '{nombre}' tiene seguridad de columna: una columna protegida no puede ir en una clave alternativa")
    for c in datos["columnas"]:
        if c not in tipos:
            raise Bloqueado(f"la columna '{c}' no existe en la tabla '{tabla}': las columnas (y los lookups, con su relación) se construyen antes que la clave")
        if tipos[c] not in TIPOS_ADMITIDOS:
            raise Bloqueado(f"la columna '{c}' es de tipo {tipos[c]}, que no admite clave alternativa (admiten: {', '.join(TIPOS_ADMITIDOS)})")

    largos = {}
    if "StringType" in tipos.values():
        cl = f"la consulta del largo de los textos de '{tabla}' (GET Attributes StringAttributeMetadata)"
        cuerpo = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')/Attributes/Microsoft.Dynamics.CRM.StringAttributeMetadata?$select=LogicalName,MaxLength", cl)
        for i, a in enumerate(exigir_forma(cuerpo.get("value"), [dict], cl, "value")):
            nombre = exigir_forma(a.get("LogicalName"), str, cl, f"value[{i}].LogicalName", no_vacio=True)
            if tipos.get(nombre) == "StringType":
                largos[nombre] = exigir_forma(a.get("MaxLength"), int, cl, f"value[{i}].MaxLength")
        sin_largo = [c for c in datos["columnas"] if tipos[c] == "StringType" and c not in largos]
        if sin_largo:
            raise ErrorEntorno(f"{cl} no trajo el largo de {sin_largo}")
    total = sum(2 * largos[c] if tipos[c] == "StringType" else BYTES_POR_TIPO[tipos[c]] for c in datos["columnas"])
    if total > MAXIMO_BYTES:
        raise Bloqueado(f"la clave ocuparía unos {total} bytes y el máximo es {MAXIMO_BYTES} (un texto ocupa 2 bytes por carácter): hay que achicar una columna o sacarla de la clave. "
                        "Es el límite documentado; la plataforma NO lo comprueba al crear la clave (ensayo del 2026-09-21), por eso lo comprueba esta herramienta")
    return id_tabla


def _verificar(dv, datos, identidad, solution_id, id_tabla):
    """La única función de verificación, para los tres caminos."""
    difs = []
    ck = f"la consulta de la clave (GET EntityDefinitions/Keys '{datos['nombre']}')"
    k = leer_entorno(dv, f"EntityDefinitions(LogicalName='{datos['tabla']}')/Keys(LogicalName='{datos['nombre']}')", ck, admite_404=True)
    if k is None:
        return {"existe": False, "diffs": None, "metadata_id": None, "indice": None}
    metadata_id = exigir_forma(k.get("MetadataId"), str, ck, "MetadataId", no_vacio=True)
    indice = exigir_forma(k.get("EntityKeyIndexStatus"), str, ck, "EntityKeyIndexStatus", no_vacio=True)
    # La plataforma devuelve las columnas en su propio orden: la unicidad no depende del orden.
    columnas = exigir_forma(k.get("KeyAttributes"), [str], ck, "KeyAttributes")
    if sorted(columnas) != sorted(datos["columnas"]):
        difs.append(f"KeyAttributes: entorno={sorted(columnas)!r} playbook={sorted(datos['columnas'])!r}")
    if exigir_forma(k.get("IsManaged"), bool, ck, "IsManaged"):
        difs.append("IsManaged: entorno=True playbook=False")
    comparar_etiqueta(k.get("DisplayName"), identidad["lcid"], "DisplayName", datos["displayname"], difs, ck, "DisplayName")

    cs = "la consulta de pertenencia a la solución (GET solutioncomponents)"
    sc = leer_entorno(dv, f"solutioncomponents?$select=rootcomponentbehavior&$filter=_solutionid_value eq {solution_id} and objectid eq {id_tabla} and componenttype eq {COMPONENTE_TABLA}", cs)
    filas = exigir_forma(sc.get("value"), [dict], cs, "value")
    if len(filas) != 1:
        difs.append(f"pertenencia a la solución: la tabla '{datos['tabla']}' tiene {len(filas)} filas en solutioncomponents, se esperaba 1 (la clave viaja dentro de ella)")
    else:
        alcance = exigir_forma(filas[0].get("rootcomponentbehavior"), int, cs, "value[0].rootcomponentbehavior")
        if alcance != INCLUYE_SUBCOMPONENTES:
            difs.append(f"la tabla '{datos['tabla']}' está en la solución pero no incluye todos sus subcomponentes (rootcomponentbehavior={alcance}): la clave no viajaría con ella")
    return {"existe": True, "diffs": difs, "metadata_id": metadata_id, "indice": indice}


def _problema_de_indice(datos, indice):
    """`None` si el índice está activo; si no, (estado, texto)."""
    if indice == "Active":
        return None
    if indice in ESTADOS_EN_CURSO:
        return "error", (f"el índice de la clave todavía se está armando (EntityKeyIndexStatus={indice}): "
                         "la clave no sirve hasta que esté Active; volver a correr en unos minutos")
    return "difiere", (f"EntityKeyIndexStatus: entorno={indice!r} playbook='Active'. Casi siempre falla porque ya hay registros duplicados: "
                       f"corregir los datos y reactivar con POST ReactivateEntityKey (EntityLogicalName='{datos['tabla']}', EntityKeyLogicalName='{datos['nombre']}')")


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    id_tabla = comprobar_tabla_y_columnas(dv, datos)
    actual = _verificar(dv, datos, identidad, solution_id, id_tabla)

    if solo_verificar and not actual["existe"]:
        return "error", componente, "la clave no existe en el entorno; --solo-verificar no crea nada, correr la herramienta sin ese flag primero"
    if actual["existe"]:
        if actual["diffs"]:
            return "difiere", componente, "; ".join(actual["diffs"])
        problema = _problema_de_indice(datos, actual["indice"])
        if problema:
            return problema[0], componente, problema[1]
        return "ya_existia", componente, f"MetadataId {actual['metadata_id']}; coincide en todo lo que exige la receta, su índice está Active y pertenece a '{solucion}'; no se modificó nada"

    est, cuerpo, _ = escribir_metadatos(dv, "POST", f"EntityDefinitions(LogicalName='{datos['tabla']}')/Keys", construir_payload(datos, identidad), dormir=dormir, solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {cuerpo}"

    final = _verificar(dv, datos, identidad, solution_id, id_tabla)
    esperas = 0
    while final["existe"] and final["indice"] in ESTADOS_EN_CURSO and esperas < INTENTOS_INDICE:
        print(f"El índice de la clave está {final['indice']}; espero {ESPERA_INDICE_SEGUNDOS} s ({esperas + 1}/{INTENTOS_INDICE}).", flush=True)
        dormir(ESPERA_INDICE_SEGUNDOS)
        esperas += 1
        final = _verificar(dv, datos, identidad, solution_id, id_tabla)
    if not final["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    if final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(final['diffs'])}"
    problema = _problema_de_indice(datos, final["indice"])
    if problema:
        return "error", componente, f"la clave se creó pero su índice no quedó activo: {problema[1]}"
    return "creado", componente, f"MetadataId {final['metadata_id']}, sobre {datos['tabla']} ({', '.join(datos['columnas'])}), índice Active, en la solución '{solucion}'"


def construir(ruta_playbook, solo_verificar, fabrica_cliente, dormir=None):
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
        paso = "validar el bloque de la clave"
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
        return _contra_entorno(rastro, datos, identidad, solo_verificar, componente, dormir)
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
        return salida("error", "desconocido", "uso incorrecto: clave.py <playbook.md> [--solo-verificar]")
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(rutas[0], "--solo-verificar" in argv, Dataverse)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
