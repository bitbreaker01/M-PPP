#!/usr/bin/env python3
"""Construye UN security role de Dataverse, desde un playbook de tipo `rol`.
Contrato: `power-platform-construir`, `references/seguridad/patrones.md`.

    python3 herramientas/construir/rol.py <playbook.md> [--solo-verificar] [--completar]

El rol se crea en la unidad de negocio raíz y recibe los privilegios del rol
`base` (leídos del entorno EN EL MOMENTO: no hay API para copiar un rol, y la
lista de un rol de Microsoft cambia con las actualizaciones) más los del
playbook. Si los dos nombran el mismo privilegio, gana el playbook.

Es seguridad, así que la verificación es estricta: un privilegio que falta, uno
con otro alcance y uno DE MÁS son `difiere`. Nunca quita privilegios ni cambia
alcances. Una sola salvedad explícita: `--completar` agrega los que faltan,
cuando esa es la única diferencia (una corrida que se cortó entre crear el rol
y darle los privilegios, o una actualización que amplió el rol base).

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
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "rol"
LARGO_MAXIMO_NOMBRE = 100  # columna `name` de la tabla role
COMPONENTE_ROL = 20  # ensayo del 2026-09-21: un rol SÍ es un componente propio; sus privilegios viajan dentro de él

ACCIONES = {"crear": "Create", "leer": "Read", "escribir": "Write", "borrar": "Delete", "anexar": "Append", "anexar_a": "AppendTo",
            "asignar": "Assign", "compartir": "Share"}
ALCANCES = {"usuario": "Basic", "unidad": "Local", "unidad_e_hijas": "Deep", "organizacion": "Global"}
ADMITE = {"Basic": "CanBeBasic", "Local": "CanBeLocal", "Deep": "CanBeDeep", "Global": "CanBeGlobal"}

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "descripcion": str, "base": str, "tablas": dict, "otros_privilegios": dict}


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_estructura(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        raise ErrorPlaybook(f"claves del rol inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
    for clave, tipo in CLAVES.items():
        valor = datos[clave]
        if tipo is str and (not isinstance(valor, str) or not valor.strip()):
            raise ErrorPlaybook(f"'{clave}' tiene que ser texto no vacío, no {valor!r}")
        if tipo is dict and not isinstance(valor, dict):
            raise ErrorPlaybook(f"'{clave}' tiene que ser un objeto, no {valor!r}")

    prefijo, abrev = identidad["prefijo"], identidad["abrev"]
    inicio = f"SR - {abrev.upper()} - "
    if not datos["nombre"].startswith(inicio) or len(datos["nombre"]) == len(inicio):
        raise ErrorPlaybook(f"'nombre' = {datos['nombre']!r} tiene que empezar con {inicio!r} y seguir con el nombre del rol")
    if len(datos["nombre"]) > LARGO_MAXIMO_NOMBRE:
        raise ErrorPlaybook(f"'nombre' tiene {len(datos['nombre'])} caracteres; el máximo de un rol es {LARGO_MAXIMO_NOMBRE}")

    patron_tabla = rf"{prefijo}_{abrev}_tbl_[a-z0-9]+"
    for tabla, acciones in datos["tablas"].items():
        if not re.fullmatch(patron_tabla, tabla):
            raise ErrorPlaybook(f"tablas: {tabla!r} no cumple {patron_tabla}; un privilegio sobre una tabla ajena va en 'otros_privilegios' con su nombre")
        if not isinstance(acciones, dict) or not acciones:
            raise ErrorPlaybook(f"tablas.{tabla} tiene que ser un objeto no vacío acción → alcance; una tabla sin privilegios no se lista")
        for accion, alcance in acciones.items():
            if accion not in ACCIONES:
                raise ErrorPlaybook(f"tablas.{tabla}: la acción {accion!r} no existe; son {sorted(ACCIONES)}")
            if alcance not in ALCANCES:
                raise ErrorPlaybook(f"tablas.{tabla}.{accion}: el alcance {alcance!r} no existe; son {sorted(ALCANCES)}")
    for nombre, alcance in datos["otros_privilegios"].items():
        if not re.fullmatch(r"prv[A-Za-z0-9_]+", nombre):
            raise ErrorPlaybook(f"otros_privilegios: {nombre!r} no es el nombre de un privilegio (prv…)")
        if re.search(patron_tabla + "$", nombre):
            raise ErrorPlaybook(f"otros_privilegios: {nombre!r} es de una tabla de la solución: va en 'tablas'")
        if alcance not in ALCANCES:
            raise ErrorPlaybook(f"otros_privilegios.{nombre}: el alcance {alcance!r} no existe; son {sorted(ALCANCES)}")
    if not datos["tablas"] and not datos["otros_privilegios"]:
        raise ErrorPlaybook("el rol no declara ningún privilegio propio ('tablas' y 'otros_privilegios' vacíos): sería una copia del rol base")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)
    exigir_sin_tildes(datos["nombre"], "'nombre'")


# ---------------------------------------------------------------------------
# Lectura del entorno
# ---------------------------------------------------------------------------
def _comilla(texto):
    return texto.replace("'", "''")


def _privilegios_de(dv, role_id, consulta):
    cuerpo = leer_entorno(dv, f"RetrieveRolePrivilegesRole(RoleId={role_id})", consulta)
    resultado = {}
    for i, p in enumerate(exigir_forma(cuerpo.get("RolePrivileges"), [dict], consulta, "RolePrivileges")):
        nombre = exigir_forma(p.get("PrivilegeName"), str, consulta, f"RolePrivileges[{i}].PrivilegeName", no_vacio=True)
        resultado[nombre] = {"id": exigir_forma(p.get("PrivilegeId"), str, consulta, f"RolePrivileges[{i}].PrivilegeId", no_vacio=True),
                             "alcance": exigir_forma(p.get("Depth"), str, consulta, f"RolePrivileges[{i}].Depth", no_vacio=True)}
    return resultado


def comprobar_precondiciones(dv, datos):
    """Devuelve (id de la unidad de negocio raíz, privilegios esperados):
    `{nombre: {"id", "alcance"}}`, los de la base más los del playbook."""
    cb = "la consulta de la unidad de negocio raíz (GET businessunits)"
    bus = exigir_forma(leer_entorno(dv, "businessunits?$select=businessunitid&$filter=_parentbusinessunitid_value eq null", cb).get("value"), [dict], cb, "value")
    if len(bus) != 1:
        raise ErrorEntorno(f"{cb} devolvió {len(bus)} unidades raíz; tiene que haber exactamente una")
    bu = exigir_forma(bus[0].get("businessunitid"), str, cb, "value[0].businessunitid", no_vacio=True)

    cr = f"la consulta del rol base (GET roles '{datos['base']}')"
    bases = exigir_forma(leer_entorno(dv, f"roles?$select=roleid,name&$filter=name eq '{_comilla(datos['base'])}' and _businessunitid_value eq {bu}", cr).get("value"), [dict], cr, "value")
    if len(bases) != 1:
        raise Bloqueado(f"el rol base '{datos['base']}' aparece {len(bases)} veces en la unidad de negocio raíz; tiene que estar exactamente una")
    id_base = exigir_forma(bases[0].get("roleid"), str, cr, "value[0].roleid", no_vacio=True)
    esperados = _privilegios_de(dv, id_base, f"la consulta de los privilegios del rol base (RetrieveRolePrivilegesRole '{datos['base']}')")

    def exigir_alcance(nombre, admite, alcance):
        if not admite:
            raise Bloqueado(f"el privilegio {nombre} no admite el alcance {alcance} que pide el playbook")

    for tabla, acciones in datos["tablas"].items():
        ct = f"la consulta de los privilegios de la tabla '{tabla}' (GET EntityDefinitions Privileges)"
        t = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')?$select=LogicalName,Privileges", ct, admite_404=True)
        if t is None:
            raise Bloqueado(f"la tabla '{tabla}' no existe en el entorno: se construye antes que los roles que la nombran")
        por_tipo = {}
        for i, p in enumerate(exigir_forma(t.get("Privileges"), [dict], ct, "Privileges")):
            por_tipo[exigir_forma(p.get("PrivilegeType"), str, ct, f"Privileges[{i}].PrivilegeType", no_vacio=True)] = (i, p)
        for accion, alcance in acciones.items():
            tipo, depth = ACCIONES[accion], ALCANCES[alcance]
            if tipo not in por_tipo:
                raise Bloqueado(f"la tabla '{tabla}' no tiene privilegio de tipo {tipo}")
            i, p = por_tipo[tipo]
            nombre = exigir_forma(p.get("Name"), str, ct, f"Privileges[{i}].Name", no_vacio=True)
            id_priv = exigir_forma(p.get("PrivilegeId"), str, ct, f"Privileges[{i}].PrivilegeId", no_vacio=True)
            exigir_alcance(nombre, exigir_forma(p.get(ADMITE[depth]), bool, ct, f"Privileges[{i}].{ADMITE[depth]}"), depth)
            esperados[nombre] = {"id": id_priv, "alcance": depth}

    for nombre, alcance in datos["otros_privilegios"].items():
        cp = f"la consulta del privilegio '{nombre}' (GET privileges)"
        filas = exigir_forma(leer_entorno(dv, f"privileges?$select=privilegeid,name,canbebasic,canbelocal,canbedeep,canbeglobal&$filter=name eq '{nombre}'", cp).get("value"), [dict], cp, "value")
        if len(filas) != 1:
            raise Bloqueado(f"el privilegio '{nombre}' aparece {len(filas)} veces en el entorno; tiene que existir exactamente uno")
        depth = ALCANCES[alcance]
        id_priv = exigir_forma(filas[0].get("privilegeid"), str, cp, "value[0].privilegeid", no_vacio=True)
        exigir_alcance(nombre, exigir_forma(filas[0].get(ADMITE[depth].lower()), bool, cp, f"value[0].{ADMITE[depth].lower()}"), depth)
        esperados[nombre] = {"id": id_priv, "alcance": depth}
    return bu, esperados


def _verificar(dv, datos, identidad, solution_id, bu, esperados):
    """La única función de verificación, para todos los caminos."""
    cr = f"la consulta del rol (GET roles '{datos['nombre']}')"
    filas = exigir_forma(leer_entorno(dv, f"roles?$select=roleid,name,description,ismanaged&$filter=name eq '{_comilla(datos['nombre'])}' and _businessunitid_value eq {bu}", cr).get("value"), [dict], cr, "value")
    if not filas:
        return {"existe": False}
    if len(filas) > 1:
        raise ErrorEntorno(f"{cr} devolvió {len(filas)} roles con ese nombre en la unidad de negocio raíz; no se puede saber cuál es")
    role_id = exigir_forma(filas[0].get("roleid"), str, cr, "value[0].roleid", no_vacio=True)
    difs = []
    if exigir_forma(filas[0].get("ismanaged"), bool, cr, "value[0].ismanaged"):
        difs.append("ismanaged: entorno=True playbook=False")
    descripcion = exigir_forma(filas[0].get("description"), str, cr, "value[0].description", permite_nulo=True) or ""
    if descripcion != datos["descripcion"]:
        difs.append(f"description: entorno={descripcion!r} playbook={datos['descripcion']!r}")

    reales = _privilegios_de(dv, role_id, f"la consulta de los privilegios del rol (RetrieveRolePrivilegesRole '{datos['nombre']}')")
    faltan = sorted(n for n in esperados if n not in reales)
    otros = [f"{n}: entorno={reales[n]['alcance']!r} playbook={e['alcance']!r}" for n, e in sorted(esperados.items()) if n in reales and reales[n]["alcance"] != e["alcance"]]
    otros += [f"sobra {n} ({reales[n]['alcance']}): no está en el rol base ni en el playbook" for n in sorted(reales) if n not in esperados]

    cs = "la consulta de pertenencia a la solución (GET solutioncomponents)"
    sc = leer_entorno(dv, f"solutioncomponents?$select=solutioncomponentid&$filter=_solutionid_value eq {solution_id} and objectid eq {role_id} and componenttype eq {COMPONENTE_ROL}", cs)
    if len(exigir_forma(sc.get("value"), [dict], cs, "value")) != 1:
        otros.append(f"pertenencia a la solución: el rol no figura en '{identidad['solucion']}' (solutioncomponents, tipo {COMPONENTE_ROL})")
    return {"existe": True, "role_id": role_id, "faltan": faltan, "diffs": difs + [f"falta {n} ({esperados[n]['alcance']})" for n in faltan] + otros,
            "solo_faltan": bool(faltan) and not difs and not otros}


def _agregar(dv, role_id, esperados, nombres, solucion):
    cuerpo = {"Privileges": [{"PrivilegeId": esperados[n]["id"], "Depth": esperados[n]["alcance"]} for n in nombres]}
    est, resp, _ = escribir_metadatos(dv, "POST", f"roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole", cuerpo, solucion=solucion)
    return None if est == 204 else f"HTTP {est} {resp}"


def _contra_entorno(dv, datos, identidad, solo_verificar, componente, completar):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    bu, esperados = comprobar_precondiciones(dv, datos)
    actual = _verificar(dv, datos, identidad, solution_id, bu, esperados)

    if solo_verificar and not actual["existe"]:
        return "error", componente, "el rol no existe en el entorno; --solo-verificar no crea nada, correr la herramienta sin ese flag primero"
    if actual["existe"]:
        if completar and not solo_verificar and actual["solo_faltan"]:
            agregados = actual["faltan"]
            problema = _agregar(dv, actual["role_id"], esperados, agregados, solucion)
            if problema:
                return "error", componente, f"falló agregar los privilegios que faltaban: {problema}"
            actual = _verificar(dv, datos, identidad, solution_id, bu, esperados)
            if not actual["diffs"]:
                return "ya_existia", componente, (f"roleid {actual['role_id']}; el rol existía y solo le faltaban privilegios; se agregaron {len(agregados)} "
                                                  f"({', '.join(agregados)}) y ahora coincide en todo; pertenece a '{solucion}'")
        if actual["diffs"]:
            return "difiere", componente, "; ".join(actual["diffs"])
        return "ya_existia", componente, f"roleid {actual['role_id']}; {len(esperados)} privilegios, coincide en todo lo que exige la receta y pertenece a '{solucion}'; no se modificó nada"

    cuerpo = {"name": datos["nombre"], "description": datos["descripcion"], "businessunitid@odata.bind": f"/businessunits({bu})"}
    est, resp, _ = escribir_metadatos(dv, "POST", "roles", cuerpo, solucion=solucion)
    if est != 204:
        return "error", componente, f"la creación falló: HTTP {est} {resp}"
    creado = _verificar(dv, datos, identidad, solution_id, bu, esperados)
    if not creado["existe"]:
        return "error", componente, "se creó (204) pero no aparece al releer del entorno"
    problema = _agregar(dv, creado["role_id"], esperados, sorted(esperados), solucion)
    if problema:
        return "error", componente, f"el rol se creó pero quedó sin sus privilegios: {problema}. Volver a correr con --completar"
    final = _verificar(dv, datos, identidad, solution_id, bu, esperados)
    if final["diffs"]:
        return "error", componente, f"se creó pero no coincide con el playbook al releer: {'; '.join(final['diffs'])}"
    propios = sum(len(a) for a in datos["tablas"].values()) + len(datos["otros_privilegios"])
    return "creado", componente, f"roleid {final['role_id']}, con {len(esperados)} privilegios ({propios} del playbook y el resto de '{datos['base']}'), en la solución '{solucion}'"


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
        paso = "validar el bloque del rol"
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
        return salida("error", "desconocido", "uso incorrecto: rol.py <playbook.md> [--solo-verificar] [--completar]")
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(rutas[0], "--solo-verificar" in argv, Dataverse, completar="--completar" in argv)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
