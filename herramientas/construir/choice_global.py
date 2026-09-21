#!/usr/bin/env python3
"""Construye un choice global de Dataverse a partir de un playbook `choice-global`.

Contrato: `power-platform-construir/references/modelo-datos/patrones.md` §1 y §2.1.
Formato de playbook: `power-platform-especificar` §3 (común, con Identidad
como bloque ```json```) y `references/choice-global.md` (del tipo).

Uso:
    python3 herramientas/construir/choice_global.py <ruta playbook> [--solo-verificar]

Con `--solo-verificar` no crea nada: solo corre, contra el entorno, las
mismas comprobaciones que corre después de crear y que corre para decidir si
"ya existía" (una sola función de verificación para los tres caminos).

Salida: texto legible por stdout y, en la última línea, un JSON de una línea
con `estado` (creado | ya_existia | difiere | bloqueado | error), `componente`
y `detalle`. Código de salida 0 solo para `creado` y `ya_existia`.

Python 3.12, solo librería estándar. Nunca abre `local/pp_secrets.env`: todo
lo habla el cliente que le inyectan (`dataverse_api.Dataverse` en `main()`;
un doble de prueba en las pruebas). La herramienta nunca lee prosa ni tablas
del playbook, y nunca deduce un dato de otro.
"""
import os
import re
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_HERRAMIENTAS = os.path.dirname(_AQUI)
if _HERRAMIENTAS not in sys.path:
    sys.path.insert(0, _HERRAMIENTAS)

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

TIPO = "choice-global"

CLAVES_COMPONENTE = {"tipo", "nombre", "displayname", "descripcion", "opciones"}

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)


# ---------------------------------------------------------------------------
# Validación previa (offline, sin tocar el entorno)
# ---------------------------------------------------------------------------
def validar_json_componente(datos):
    """Valida claves, tipos y coherencia interna del bloque
    '## 2. Qué se crea'. No valida el patrón del nombre (necesita el
    prefijo/abreviatura de Identidad: eso es `validar_nombres`), ni el rango
    numérico de los valores (`validar_rango_offline`)."""
    claves = set(datos.keys())
    if claves != CLAVES_COMPONENTE:
        faltan = sorted(CLAVES_COMPONENTE - claves)
        sobran = sorted(claves - CLAVES_COMPONENTE)
        raise ErrorPlaybook(
            f"claves de '## 2. Qué se crea' inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}"
        )
    if not isinstance(datos["nombre"], str) or not datos["nombre"]:
        raise ErrorPlaybook("'nombre' tiene que ser texto no vacío")
    if not isinstance(datos["displayname"], str) or not datos["displayname"]:
        raise ErrorPlaybook("'displayname' tiene que ser texto no vacío")
    if not isinstance(datos["descripcion"], str) or not datos["descripcion"].strip():
        raise ErrorPlaybook("'descripcion' es obligatoria y no puede estar vacía")
    opciones = datos["opciones"]
    if not isinstance(opciones, list) or not opciones:
        raise ErrorPlaybook("'opciones' tiene que ser una lista no vacía")
    etiquetas, valores = [], []
    for i, op in enumerate(opciones):
        if not isinstance(op, dict) or set(op.keys()) != {"valor", "etiqueta", "descripcion"}:
            raise ErrorPlaybook(f"opciones[{i}] tiene que tener exactamente las claves valor, etiqueta, descripcion")
        if not isinstance(op["valor"], int) or isinstance(op["valor"], bool):
            raise ErrorPlaybook(f"opciones[{i}].valor tiene que ser un entero, no {op['valor']!r}")
        if not isinstance(op["etiqueta"], str) or not op["etiqueta"].strip():
            raise ErrorPlaybook(f"opciones[{i}].etiqueta tiene que ser texto no vacío")
        if not isinstance(op["descripcion"], str):
            raise ErrorPlaybook(f"opciones[{i}].descripcion tiene que ser texto (puede ser vacío)")
        etiquetas.append(op["etiqueta"])
        valores.append(op["valor"])
    if len(etiquetas) != len(set(etiquetas)):
        raise ErrorPlaybook("hay etiquetas repetidas dentro de 'opciones'; no puede haberlas")
    if len(valores) != len(set(valores)):
        raise ErrorPlaybook("hay valores repetidos dentro de 'opciones'; no puede haberlos")


def validar_nombres(datos, identidad):
    """Patrón de `nombre` y `displayname` contra `prefijo`/`abrev`, los dos
    ya explícitos en Identidad (nunca deducidos de otro dato)."""
    prefijo, abrev = identidad["prefijo"], identidad["abrev"]
    nombre = datos["nombre"]
    if not re.fullmatch(rf"{re.escape(prefijo)}_{re.escape(abrev)}_ch_[a-z0-9]+", nombre) or len(nombre) > 95:
        raise ErrorPlaybook(
            f"'nombre' ({nombre!r}) no cumple ^{prefijo}_{abrev}_ch_[a-z0-9]+$ o supera 95 caracteres"
        )
    esperado_dn = f"CH - {abrev.upper()} - "
    if not datos["displayname"].startswith(esperado_dn) or datos["displayname"] == esperado_dn:
        raise ErrorPlaybook(f"'displayname' ({datos['displayname']!r}) no cumple 'CH - {abrev.upper()} - Nombre'")
    exigir_sin_tildes(datos["displayname"], "'displayname'")
    for i, op in enumerate(datos["opciones"]):
        exigir_sin_tildes(op["etiqueta"], f"opciones[{i}].etiqueta")


def validar_rango_offline(datos, identidad):
    """Precondición 2 de la receta ('Todo valor está en el rango del
    publisher'), calculada offline con el `prefijo_opciones` que ya declaró
    Identidad. La precondición 1 (contra el entorno) confirma además que ese
    valor declarado coincide con el publisher real antes de crear nada."""
    prefijo_num = identidad["prefijo_opciones"]
    rango_min, rango_max = prefijo_num * 10000, (prefijo_num + 1) * 10000
    fuera_de_rango = [op["valor"] for op in datos["opciones"] if not (rango_min <= op["valor"] < rango_max)]
    if fuera_de_rango:
        raise Bloqueado(
            f"valores fuera del rango del publisher declarado en Identidad [{rango_min}, {rango_max}): {fuera_de_rango}"
        )


# ---------------------------------------------------------------------------
# Cuerpo del POST
# ---------------------------------------------------------------------------
def construir_payload(datos, identidad):
    lcid = identidad["lcid"]

    def etiqueta(texto):
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.Label",
            "LocalizedLabels": [
                {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": texto, "LanguageCode": lcid}
            ],
        }

    return {
        "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
        "Name": datos["nombre"],
        "IsGlobal": True,
        "OptionSetType": "Picklist",
        "DisplayName": etiqueta(datos["displayname"]),
        "Description": etiqueta(datos["descripcion"]),
        "Options": [
            {
                "Value": op["valor"],
                "Label": etiqueta(op["etiqueta"]),
                "Description": etiqueta(op.get("descripcion") or ""),
            }
            for op in datos["opciones"]
        ],
    }


# ---------------------------------------------------------------------------
# Comparación contra el entorno: una sola función, la usan los tres caminos.
# ---------------------------------------------------------------------------
def comparar_contra_playbook(cuerpo_choice, datos, identidad):
    """Devuelve la lista de diferencias (vacía si coincide) entre lo que hay
    en el entorno y el playbook, con **todo** lo que `patrones.md` §2.1 lista
    en 'Verificación': IsGlobal, OptionSetType, IsManaged, display name y
    descripción en el lcid de Identidad (sin etiquetas en otro idioma), y la
    lista ordenada de opciones (valor, etiqueta y descripción, sin etiquetas
    en otro idioma). No mira pertenencia a la solución: eso lo hace
    `_verificar`, que además necesita el `MetadataId`."""
    lcid = identidad["lcid"]
    diffs = []

    if cuerpo_choice.get("Name") != datos["nombre"]:
        diffs.append(f"Name: entorno={cuerpo_choice.get('Name')!r} playbook={datos['nombre']!r}")
    if cuerpo_choice.get("IsGlobal") is not True:
        diffs.append(f"IsGlobal: entorno={cuerpo_choice.get('IsGlobal')!r} esperado=True")
    if cuerpo_choice.get("OptionSetType") != "Picklist":
        diffs.append(f"OptionSetType: entorno={cuerpo_choice.get('OptionSetType')!r} esperado='Picklist'")
    if cuerpo_choice.get("IsManaged") is not False:
        diffs.append(f"IsManaged: entorno={cuerpo_choice.get('IsManaged')!r} esperado=False")

    dn, dn_otros = etiqueta_y_otros_idiomas(cuerpo_choice.get("DisplayName"), lcid)
    if dn != datos["displayname"]:
        diffs.append(f"DisplayName[{lcid}]: entorno={dn!r} playbook={datos['displayname']!r}")
    if dn_otros:
        diffs.append(f"DisplayName tiene etiquetas en otro idioma: {dn_otros}")

    desc, desc_otros = etiqueta_y_otros_idiomas(cuerpo_choice.get("Description"), lcid)
    if (desc or "") != datos["descripcion"]:
        diffs.append(f"Description[{lcid}]: entorno={desc!r} playbook={datos['descripcion']!r}")
    if desc_otros:
        diffs.append(f"Description tiene etiquetas en otro idioma: {desc_otros}")

    opciones_entorno = cuerpo_choice.get("Options") or []
    opciones_playbook = datos["opciones"]
    if len(opciones_entorno) != len(opciones_playbook):
        diffs.append(f"cantidad de opciones: entorno={len(opciones_entorno)} playbook={len(opciones_playbook)}")

    for i, op_p in enumerate(opciones_playbook):
        if i >= len(opciones_entorno):
            break
        op_e = opciones_entorno[i]
        if op_e.get("Value") != op_p["valor"]:
            diffs.append(f"opciones[{i}].Value: entorno={op_e.get('Value')!r} playbook={op_p['valor']!r}")
        et, et_otros = etiqueta_y_otros_idiomas(op_e.get("Label"), lcid)
        if et != op_p["etiqueta"]:
            diffs.append(f"opciones[{i}].etiqueta: entorno={et!r} playbook={op_p['etiqueta']!r}")
        if et_otros:
            diffs.append(f"opciones[{i}].Label tiene etiquetas en otro idioma: {et_otros}")
        de, de_otros = etiqueta_y_otros_idiomas(op_e.get("Description"), lcid)
        de_esperado = op_p.get("descripcion") or ""
        if (de or "") != de_esperado:
            diffs.append(f"opciones[{i}].descripcion: entorno={de!r} playbook={de_esperado!r}")
        if de_otros:
            diffs.append(f"opciones[{i}].Description tiene etiquetas en otro idioma: {de_otros}")

    return diffs


C_CHOICE = "el GET de existencia del choice (GET GlobalOptionSetDefinitions)"
C_PERTENENCIA = "la consulta de pertenencia a la solución (GET solutioncomponents)"


def _exigir_forma_choice(cuerpo):
    """Valida por tipo TODO lo que `comparar_contra_playbook` y `_verificar`
    leen del choice, antes de comparar nada: así una respuesta con forma rara
    termina en `error` y nunca se lee como una diferencia (`difiere`) ni como
    una coincidencia (`ya_existia` / `creado`). `Description` puede ser nula:
    un choice o una opción sin descripción es legítimo."""
    exigir_forma(cuerpo, dict, C_CHOICE, "cuerpo")
    exigir_forma(cuerpo.get("MetadataId"), str, C_CHOICE, "MetadataId", no_vacio=True)
    exigir_forma(cuerpo.get("Name"), str, C_CHOICE, "Name")
    exigir_forma(cuerpo.get("IsGlobal"), bool, C_CHOICE, "IsGlobal")
    exigir_forma(cuerpo.get("IsManaged"), bool, C_CHOICE, "IsManaged")
    exigir_forma(cuerpo.get("OptionSetType"), str, C_CHOICE, "OptionSetType")
    exigir_etiqueta(cuerpo.get("DisplayName"), C_CHOICE, "DisplayName")
    exigir_etiqueta(cuerpo.get("Description"), C_CHOICE, "Description", permite_nulo=True)
    opciones = exigir_forma(cuerpo.get("Options"), [dict], C_CHOICE, "Options")
    for i, op in enumerate(opciones):
        exigir_forma(op.get("Value"), int, C_CHOICE, f"Options[{i}].Value")
        exigir_etiqueta(op.get("Label"), C_CHOICE, f"Options[{i}].Label")
        exigir_etiqueta(op.get("Description"), C_CHOICE, f"Options[{i}].Description", permite_nulo=True)


def _verificar(dv, datos, identidad, solution_id):
    """Consulta el entorno y devuelve todo lo que necesitan los tres caminos
    (creado / ya_existia / --solo-verificar): existencia, diferencias contra
    el playbook (comparar_contra_playbook) y pertenencia a la solución. Nunca
    modifica nada. Un GET de existencia que no es 200 ni 404, o un 200 con
    forma inesperada, **nunca** se trata como 'no existe': se propaga como
    `ErrorEntorno`, para que la herramienta termine en `error` y no cree
    nada."""
    ruta_choice = f"GlobalOptionSetDefinitions(Name='{datos['nombre']}')"
    est, cuerpo, _ = dv.call("GET", ruta_choice)
    if est == 404:
        return {"existe": False, "diffs": None, "metadata_id": None}
    if est != 200:
        raise ErrorEntorno(f"{C_CHOICE} devolvió HTTP {est} (ni 200 ni 404): {cuerpo}")
    _exigir_forma_choice(cuerpo)

    diffs = comparar_contra_playbook(cuerpo, datos, identidad)
    metadata_id = cuerpo["MetadataId"]

    ruta_sc = f"solutioncomponents?$filter=_solutionid_value eq {solution_id} and objectid eq {metadata_id}"
    est_sc, cuerpo_sc, _ = dv.call("GET", ruta_sc)
    if est_sc != 200:
        raise ErrorEntorno(f"{C_PERTENENCIA} devolvió HTTP {est_sc} (se esperaba 200): {cuerpo_sc}")
    exigir_forma(cuerpo_sc, dict, C_PERTENENCIA, "cuerpo")
    filas_sc = exigir_forma(cuerpo_sc.get("value"), [dict], C_PERTENENCIA, "value")
    if len(filas_sc) != 1:
        # 0 (o más de 1) filas SÍ es una respuesta de negocio legítima: el
        # choice no pertenece (o pertenece más de una vez) a la solución.
        diffs = diffs + [f"pertenencia a la solución: {len(filas_sc)} filas en solutioncomponents, se esperaba 1"]

    return {"existe": True, "diffs": diffs, "metadata_id": metadata_id}


# ---------------------------------------------------------------------------
# Precondiciones contra el entorno + los tres caminos
# ---------------------------------------------------------------------------
def _nombres_que_difieren(datos, identidad, diffs):
    """Si TODAS las diferencias son de nombres visibles (el del choice o la
    etiqueta de una opción), devuelve (cambia el nombre, índices de opciones);
    si hay cualquier otra, `None`: no se toca nada."""
    cambia_nombre, opciones = False, []
    for d in diffs:
        m = re.match(r"opciones\[(\d+)\]\.etiqueta: ", d)
        if d.startswith(f"DisplayName[{identidad['lcid']}]: "):
            cambia_nombre = True
        elif m:
            opciones.append(int(m.group(1)))
        else:
            return None
    return (cambia_nombre, opciones) if diffs else None


def corregir_nombres(dv, datos, identidad, metadata_id, cambia_nombre, opciones):
    """Ensayado contra la plataforma el 2026-09-21: el nombre se cambia con un
    PUT de la definición completa (con '@odata.type', que el GET no trae) y la
    etiqueta de una opción con `UpdateOptionValue`. Devuelve `None` o el problema."""
    solucion, lcid = identidad["solucion"], identidad["lcid"]
    if cambia_nombre:
        consulta = "la lectura completa del choice (GET GlobalOptionSetDefinitions)"
        est, actual, _ = dv.call("GET", f"GlobalOptionSetDefinitions(Name='{datos['nombre']}')")
        if est != 200:
            return f"{consulta} devolvió HTTP {est}: {actual}"
        definicion = {k: v for k, v in exigir_forma(actual, dict, consulta, "cuerpo").items() if k != "@odata.context"}
        definicion["@odata.type"] = "Microsoft.Dynamics.CRM.OptionSetMetadata"
        definicion["DisplayName"] = etiqueta_web_api(datos["displayname"], lcid)
        est, resp, _ = escribir_metadatos(dv, "PUT", f"GlobalOptionSetDefinitions({metadata_id})", definicion, solucion=solucion, cabeceras={"MSCRM.MergeLabels": "true"})
        if est != 204:
            return f"falló cambiar el nombre visible del choice: HTTP {est} {resp}"
    for i in opciones:
        op = datos["opciones"][i]
        cuerpo = {"OptionSetName": datos["nombre"], "Value": op["valor"], "Label": etiqueta_web_api(op["etiqueta"], lcid), "MergeLabels": True, "SolutionUniqueName": solucion}
        est, resp, _ = escribir_metadatos(dv, "POST", "UpdateOptionValue", cuerpo)
        if est != 204:
            return f"falló cambiar la etiqueta de opciones[{i}] ({op['valor']}): HTTP {est} {resp}"
    xml = f"<importexportxml><optionsets><optionset>{datos['nombre']}</optionset></optionsets></importexportxml>"
    est, resp, _ = escribir_metadatos(dv, "POST", "PublishXml", {"ParameterXml": xml})
    return None if est == 204 else f"se cambiaron los nombres pero falló publicar: HTTP {est} {resp}"


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, corregir=False):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)

    estado_actual = _verificar(dv, datos, identidad, solution_id)

    if estado_actual["existe"] and corregir and not solo_verificar:
        nombres = _nombres_que_difieren(datos, identidad, estado_actual["diffs"])
        if nombres:
            problema = corregir_nombres(dv, datos, identidad, estado_actual["metadata_id"], *nombres)
            if problema:
                return "error", componente, problema
            estado_actual = _verificar(dv, datos, identidad, solution_id)
            if not estado_actual["diffs"]:
                cuantos = int(nombres[0]) + len(nombres[1])
                return "ya_existia", componente, (f"MetadataId {estado_actual['metadata_id']}; el choice existía y solo diferían nombres visibles; se corrigieron {cuantos} "
                                                  f"y ahora coincide en todo; pertenece a '{solucion}'")

    if solo_verificar:
        if not estado_actual["existe"]:
            return (
                "error",
                componente,
                "el choice no existe en el entorno; --solo-verificar no crea nada, "
                "correr la herramienta sin ese flag primero",
            )
        if estado_actual["diffs"]:
            return "difiere", componente, "; ".join(estado_actual["diffs"])
        return "ya_existia", componente, f"verificado contra el entorno: coincide en todo y pertenece a '{solucion}'"

    if estado_actual["existe"]:
        if estado_actual["diffs"]:
            return "difiere", componente, "; ".join(estado_actual["diffs"])
        return "ya_existia", componente, "ya existía y coincide en todo lo que exige la receta; no se modificó nada"

    payload = construir_payload(datos, identidad)
    est, cuerpo_post, _ = escribir_metadatos(dv, "POST", "GlobalOptionSetDefinitions", payload, solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {cuerpo_post}"

    estado_final = _verificar(dv, datos, identidad, solution_id)
    if not estado_final["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    if estado_final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(estado_final['diffs'])}"
    return "creado", componente, f"MetadataId {estado_final['metadata_id']}, en la solución '{solucion}'"


# ---------------------------------------------------------------------------
# Punto de entrada, inyectable para las pruebas.
# ---------------------------------------------------------------------------
def construir(ruta_playbook, solo_verificar, fabrica_cliente, corregir_nombres=False):
    """Núcleo de la herramienta. `fabrica_cliente` es un callable sin
    argumentos que devuelve un cliente con el mismo `call()` que
    `dataverse_api.Dataverse` (la real en `main()`, un doble de prueba en las
    pruebas). Nunca lanza: captura toda excepción, prevista o no, y siempre
    devuelve `(estado, componente, detalle)` — nunca una traza."""
    componente = os.path.basename(ruta_playbook)
    paso = "leer el playbook"
    try:
        texto = leer_texto(ruta_playbook)
        paso = "separar las secciones del playbook"
        secciones = dividir_secciones(texto)
        paso = "leer el bloque '## 2. Qué se crea'"
        datos = obtener_componente(secciones, TIPO)
        componente = datos.get("nombre", componente)
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque del componente"
        validar_json_componente(datos)
        paso = "validar los nombres"
        validar_nombres(datos, identidad)
        paso = "validar el rango de los valores"
        validar_rango_offline(datos, identidad)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        # Red de contención propia de esta fase: cualquier excepción no
        # prevista (p. ej. un TypeError por un dato con forma rara) nunca
        # escapa como traza; termina en 'error' igual que cualquier otra
        # falla de esta fase.
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={datos.get('tipo')} nombre={datos.get('nombre')}")

    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, componente, corregir=corregir_nombres)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except ErrorEntorno as e:
        # Error previsto: una consulta contra el entorno no se pudo
        # interpretar (HTTP inesperado o forma inesperada). Se distingue del
        # 'fallo inesperado' de más abajo por el mensaje, que siempre nombra
        # la consulta.
        return "error", componente, str(e)
    except Exception as e:
        return "error", componente, f"fallo inesperado hablando con Dataverse, durante {rastro.en_curso}: {type(e).__name__}: {e}"


def main():
    argv = sys.argv[1:]
    solo_verificar = "--solo-verificar" in argv
    posicionales = [a for a in argv if not a.startswith("--")]
    if len(posicionales) != 1:
        sys.stderr.write("uso: choice_global.py <ruta playbook> [--solo-verificar] [--corregir-nombres]\n")
        return salida("error", "desconocido", "uso incorrecto: falta la ruta del playbook")

    from dataverse_api import Dataverse  # import tardío: no hace falta para las pruebas

    estado, componente, detalle = construir(posicionales[0], solo_verificar, Dataverse, corregir_nombres="--corregir-nombres" in argv)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
