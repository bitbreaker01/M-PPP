#!/usr/bin/env python3
"""Construye UN column security profile de Dataverse con sus permisos, desde
un playbook de tipo `perfil-columnas`. Contrato: `power-platform-construir`,
`references/seguridad/patrones.md` §2.2.

    python3 herramientas/construir/perfil_columnas.py <playbook.md> [--solo-verificar] [--completar]

Crea el perfil y un permiso por columna. NO le asigna miembros: un perfil se
asigna a usuarios o equipos (nunca a roles), y eso no viaja en la solución; es
una tarea de administración en cada entorno.

Es seguridad, así que la verificación es estricta: un permiso que falta, uno
con otro valor y uno DE MÁS son `difiere`. Nunca quita ni cambia un permiso.
Una sola salvedad explícita: `--completar` agrega los permisos que faltan,
cuando esa es la única diferencia (una corrida que se cortó a mitad).

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
    exigir_forma,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "perfil-columnas"
COMPONENTE_PERFIL = 70  # ensayo del 2026-09-21: el perfil es un componente propio; sus permisos viajan dentro de él
PERMITIDO, NO_PERMITIDO = 4, 0
CAMPOS = {"leer": "canread", "crear": "cancreate", "actualizar": "canupdate"}

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "descripcion": str, "permisos": list}
CLAVES_PERMISO = {"tabla": str, "columna": str, "leer": bool, "crear": bool, "actualizar": bool}


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def validar_playbook(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        raise ErrorPlaybook(f"claves del perfil inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
    for clave in ("tipo", "nombre", "descripcion"):
        if not isinstance(datos[clave], str) or not datos[clave].strip():
            raise ErrorPlaybook(f"'{clave}' tiene que ser texto no vacío, no {datos[clave]!r}")
    inicio = f"CSP - {identidad['abrev'].upper()} - "
    if not datos["nombre"].startswith(inicio) or len(datos["nombre"]) == len(inicio):
        raise ErrorPlaybook(f"'nombre' = {datos['nombre']!r} tiene que empezar con {inicio!r} y seguir con el nombre del perfil")
    if not isinstance(datos["permisos"], list) or not datos["permisos"]:
        raise ErrorPlaybook(f"'permisos' tiene que ser una lista no vacía, no {datos['permisos']!r}")

    patron_tabla = rf"{identidad['prefijo']}_{identidad['abrev']}_tbl_[a-z0-9]+"
    vistos = set()
    for i, p in enumerate(datos["permisos"]):
        if not isinstance(p, dict):
            raise ErrorPlaybook(f"permisos[{i}] tiene que ser un objeto, no {p!r}")
        faltan, sobran = sorted(set(CLAVES_PERMISO) - set(p)), sorted(set(p) - set(CLAVES_PERMISO))
        if faltan or sobran:
            raise ErrorPlaybook(f"claves de permisos[{i}] inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
        if not isinstance(p["tabla"], str) or not re.fullmatch(patron_tabla, p["tabla"]):
            raise ErrorPlaybook(f"permisos[{i}].tabla = {p['tabla']!r} no cumple {patron_tabla}")
        if not isinstance(p["columna"], str) or not re.fullmatch(r"[a-z][a-z0-9_]*", p["columna"]):
            raise ErrorPlaybook(f"permisos[{i}].columna = {p['columna']!r} tiene que ser el nombre lógico de una columna, en minúscula")
        for campo in CAMPOS:
            if not isinstance(p[campo], bool):
                raise ErrorPlaybook(f"permisos[{i}].{campo} tiene que ser true o false, no {p[campo]!r}")
        if not any(p[c] for c in CAMPOS):
            raise ErrorPlaybook(f"permisos[{i}] ({p['columna']}) no da ningún permiso: una columna sin acceso no se lista")
        if (p["tabla"], p["columna"]) in vistos:
            raise ErrorPlaybook(f"permisos[{i}]: la columna {p['tabla']}.{p['columna']} está repetida")
        vistos.add((p["tabla"], p["columna"]))


def _cuerpo_permiso(p, perfil_id):
    return {"entityname": p["tabla"], "attributelogicalname": p["columna"],
            **{api: PERMITIDO if p[campo] else NO_PERMITIDO for campo, api in CAMPOS.items()},
            "canreadunmasked": NO_PERMITIDO, "fieldsecurityprofileid@odata.bind": f"/fieldsecurityprofiles({perfil_id})"}


# ---------------------------------------------------------------------------
# Lectura del entorno
# ---------------------------------------------------------------------------
def _comilla(texto):
    return texto.replace("'", "''")


def comprobar_columnas(dv, datos):
    """Precondición: cada tabla existe y cada columna existe y TIENE seguridad
    de columna (si no, la plataforma rechaza el permiso con un 400)."""
    for tabla in sorted({p["tabla"] for p in datos["permisos"]}):
        ca = f"la consulta de las columnas de '{tabla}' (GET Attributes)"
        cuerpo = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')/Attributes?$select=LogicalName,IsSecured", ca, admite_404=True)
        if cuerpo is None:
            raise Bloqueado(f"la tabla '{tabla}' no existe en el entorno: se construye antes que el perfil que nombra sus columnas")
        protegida = {}
        for i, a in enumerate(exigir_forma(cuerpo.get("value"), [dict], ca, "value")):
            nombre = exigir_forma(a.get("LogicalName"), str, ca, f"value[{i}].LogicalName", no_vacio=True)
            protegida[nombre] = exigir_forma(a.get("IsSecured"), bool, ca, f"value[{i}].IsSecured")
        for p in datos["permisos"]:
            if p["tabla"] != tabla:
                continue
            if p["columna"] not in protegida:
                raise Bloqueado(f"la columna '{p['columna']}' no existe en la tabla '{tabla}'")
            if not protegida[p["columna"]]:
                raise Bloqueado(f"la columna '{tabla}.{p['columna']}' no tiene seguridad de columna: la plataforma no admite un permiso sobre una columna sin proteger")


def _verificar(dv, datos, identidad, solution_id):
    """La única función de verificación, para todos los caminos."""
    cp = f"la consulta del perfil (GET fieldsecurityprofiles '{datos['nombre']}')"
    filas = exigir_forma(leer_entorno(dv, f"fieldsecurityprofiles?$select=fieldsecurityprofileid,name,description,ismanaged&$filter=name eq '{_comilla(datos['nombre'])}'", cp).get("value"), [dict], cp, "value")
    if not filas:
        return {"existe": False}
    if len(filas) > 1:
        raise ErrorEntorno(f"{cp} devolvió {len(filas)} perfiles con ese nombre; no se puede saber cuál es")
    perfil_id = exigir_forma(filas[0].get("fieldsecurityprofileid"), str, cp, "value[0].fieldsecurityprofileid", no_vacio=True)
    difs = []
    if exigir_forma(filas[0].get("ismanaged"), bool, cp, "value[0].ismanaged"):
        difs.append("ismanaged: entorno=True playbook=False")
    descripcion = exigir_forma(filas[0].get("description"), str, cp, "value[0].description", permite_nulo=True) or ""
    if descripcion != datos["descripcion"]:
        difs.append(f"description: entorno={descripcion!r} playbook={datos['descripcion']!r}")

    cf = "la consulta de los permisos del perfil (GET fieldpermissions)"
    cuerpo = leer_entorno(dv, f"fieldpermissions?$select=entityname,attributelogicalname,canread,cancreate,canupdate,canreadunmasked&$filter=_fieldsecurityprofileid_value eq {perfil_id}", cf)
    reales = {}
    for i, f in enumerate(exigir_forma(cuerpo.get("value"), [dict], cf, "value")):
        clave = (exigir_forma(f.get("entityname"), str, cf, f"value[{i}].entityname", no_vacio=True),
                 exigir_forma(f.get("attributelogicalname"), str, cf, f"value[{i}].attributelogicalname", no_vacio=True))
        reales[clave] = {api: exigir_forma(f.get(api), int, cf, f"value[{i}].{api}") for api in list(CAMPOS.values()) + ["canreadunmasked"]}

    faltan, otros = [], []
    for p in datos["permisos"]:
        clave = (p["tabla"], p["columna"])
        if clave not in reales:
            faltan.append(p)
            continue
        esperado = {k: v for k, v in _cuerpo_permiso(p, perfil_id).items() if k in reales[clave]}
        otros += [f"{p['tabla']}.{p['columna']}.{api}: entorno={reales[clave][api]} playbook={v}" for api, v in esperado.items() if reales[clave][api] != v]
    declarados = {(p["tabla"], p["columna"]) for p in datos["permisos"]}
    otros += [f"sobra el permiso sobre {t}.{c}: el playbook no lo declara" for t, c in sorted(reales) if (t, c) not in declarados]

    cs = "la consulta de pertenencia a la solución (GET solutioncomponents)"
    sc = leer_entorno(dv, f"solutioncomponents?$select=solutioncomponentid&$filter=_solutionid_value eq {solution_id} and objectid eq {perfil_id} and componenttype eq {COMPONENTE_PERFIL}", cs)
    if len(exigir_forma(sc.get("value"), [dict], cs, "value")) != 1:
        otros.append(f"pertenencia a la solución: el perfil no figura en '{identidad['solucion']}' (solutioncomponents, tipo {COMPONENTE_PERFIL})")
    return {"existe": True, "perfil_id": perfil_id, "faltan": faltan, "solo_faltan": bool(faltan) and not difs and not otros,
            "diffs": difs + [f"falta el permiso sobre {p['tabla']}.{p['columna']}" for p in faltan] + otros}


def _agregar(dv, perfil_id, permisos, solucion):
    for p in permisos:
        est, resp, _ = escribir_metadatos(dv, "POST", "fieldpermissions", _cuerpo_permiso(p, perfil_id), solucion=solucion)
        if est != 204:
            return f"falló el permiso sobre {p['tabla']}.{p['columna']}: HTTP {est} {resp}"
    return None


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, completar):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    comprobar_columnas(dv, datos)
    actual = _verificar(dv, datos, identidad, solution_id)

    if solo_verificar and not actual["existe"]:
        return "error", componente, "el perfil no existe en el entorno; --solo-verificar no crea nada, correr la herramienta sin ese flag primero"
    if actual["existe"]:
        if completar and not solo_verificar and actual["solo_faltan"]:
            agregados = [f"{p['tabla']}.{p['columna']}" for p in actual["faltan"]]
            problema = _agregar(dv, actual["perfil_id"], actual["faltan"], solucion)
            if problema:
                return "error", componente, f"no se pudo completar el perfil: {problema}"
            actual = _verificar(dv, datos, identidad, solution_id)
            if not actual["diffs"]:
                return "ya_existia", componente, (f"fieldsecurityprofileid {actual['perfil_id']}; el perfil existía y solo le faltaban permisos; se agregaron {len(agregados)} "
                                                  f"({', '.join(agregados)}) y ahora coincide en todo; pertenece a '{solucion}'")
        if actual["diffs"]:
            return "difiere", componente, "; ".join(actual["diffs"])
        return "ya_existia", componente, (f"fieldsecurityprofileid {actual['perfil_id']}; {len(datos['permisos'])} permisos, coincide en todo lo que exige la receta "
                                          f"y pertenece a '{solucion}'; no se modificó nada")

    est, resp, _ = escribir_metadatos(dv, "POST", "fieldsecurityprofiles", {"name": datos["nombre"], "description": datos["descripcion"]}, solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {resp}"
    creado = _verificar(dv, datos, identidad, solution_id)
    if not creado["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    problema = _agregar(dv, creado["perfil_id"], datos["permisos"], solucion)
    if problema:
        return "error", componente, f"el perfil se creó pero quedó incompleto: {problema}. Volver a correr con --completar"
    final = _verificar(dv, datos, identidad, solution_id)
    if final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(final['diffs'])}"
    return "creado", componente, f"fieldsecurityprofileid {final['perfil_id']}, con {len(datos['permisos'])} permisos, sin miembros, en la solución '{solucion}'"


def construir(ruta_playbook, solo_verificar, fabrica_cliente, completar=False):
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
        paso = "validar el bloque del perfil"
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
        return _contra_entorno(rastro, datos, identidad, solo_verificar, componente, completar)
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
        return salida("error", "desconocido", "uso incorrecto: perfil_columnas.py <playbook.md> [--solo-verificar] [--completar]")
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(rutas[0], "--solo-verificar" in argv, Dataverse, completar="--completar" in argv)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
