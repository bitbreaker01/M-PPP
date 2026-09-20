#!/usr/bin/env python3
"""Limpieza del spike C-05 parte B. Borra SOLO lo que este spike crea (todo lleva "zz"
en el nombre, dentro de la solucion sanic_mppp_sol_zzspikec05). Idempotente: se puede
correr las veces que haga falta, incluso si nunca se creo nada o si ya se borro todo.

Nunca toca sanic_mppp_sol_mantenimientoppp ni ningun otro componente sin "zz".

Uso:
    python3 herramientas/dataverse_api.py ...   # (no se usa directo aca)
    python3 spikes/c05-parseo-excel/parte-b/limpiar.py
"""
import os
import sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))
from dataverse_api import Dataverse  # noqa: E402

TABLA = "sanic_mppp_tbl_zzspike"
SOLUCION = "sanic_mppp_sol_zzspikec05"


def listar(dv, coleccion, filtro, select="name"):
    estado, cuerpo, _ = dv.call("GET", f"{coleccion}?$select={select}&$filter={filtro}")
    if estado != 200:
        print(f"  [aviso] no se pudo listar {coleccion}: {estado} {cuerpo.get('error')}")
        return []
    return cuerpo.get("value", [])


def borrar(dv, coleccion, id_, etiqueta):
    estado, cuerpo, _ = dv.call("DELETE", f"{coleccion}({id_})")
    if estado in (204, 200):
        print(f"  OK borrado: {etiqueta} ({id_})")
        return True
    if estado == 404:
        print(f"  ya no existe: {etiqueta} ({id_})")
        return True
    print(f"  [FALLO] {etiqueta} ({id_}): {estado} {cuerpo.get('error')}")
    return False


def limpiar_steps(dv):
    print("-- Steps de plugin (sdkmessageprocessingsteps) --")
    filas = listar(
        dv, "sdkmessageprocessingsteps",
        "contains(name,'zz')", select="name,sdkmessageprocessingstepid",
    )
    ok = True
    for f in filas:
        ok &= borrar(dv, "sdkmessageprocessingsteps", f["sdkmessageprocessingstepid"], f["name"])
    if not filas:
        print("  nada que borrar")
    return ok


def limpiar_customapis(dv):
    print("-- Custom APIs (parametros + custom api) --")
    apis = listar(dv, "customapis", "contains(uniquename,'zz')", select="uniquename,customapiid")
    ok = True
    for api in apis:
        capiid = api["customapiid"]
        params = listar(
            dv, "customapirequestparameters", f"_customapiid_value eq {capiid}",
            select="name,customapirequestparameterid",
        )
        for p in params:
            ok &= borrar(dv, "customapirequestparameters", p["customapirequestparameterid"], p["name"])
        resp = listar(
            dv, "customapiresponseproperties", f"_customapiid_value eq {capiid}",
            select="name,customapiresponsepropertyid",
        )
        for r in resp:
            ok &= borrar(dv, "customapiresponseproperties", r["customapiresponsepropertyid"], r["name"])
        ok &= borrar(dv, "customapis", capiid, api["uniquename"])
    if not apis:
        print("  nada que borrar")
    return ok


def limpiar_plugintypes_y_paquetes(dv):
    print("-- Plugin types y plugin packages (y sus plugin assemblies) --")
    ok = True
    tipos = listar(
        dv, "plugintypes", "contains(typename,'ZzSpikeC05') or contains(typename,'Zzspikec05')",
        select="typename,plugintypeid",
    )
    for t in tipos:
        ok &= borrar(dv, "plugintypes", t["plugintypeid"], t["typename"])
    asambleas = listar(
        dv, "pluginassemblies", "contains(name,'ZzSpikeC05') or contains(name,'Zzspikec05')",
        select="name,pluginassemblyid",
    )
    for a in asambleas:
        ok &= borrar(dv, "pluginassemblies", a["pluginassemblyid"], a["name"])
    paquetes = listar(dv, "pluginpackages", "contains(uniquename,'zz')", select="uniquename,pluginpackageid")
    for p in paquetes:
        ok &= borrar(dv, "pluginpackages", p["pluginpackageid"], p["uniquename"])
    if not tipos and not asambleas and not paquetes:
        print("  nada que borrar")
    return ok


def limpiar_claves_y_tabla(dv):
    print(f"-- Claves alternativas y tabla {TABLA} --")
    ok = True
    estado, cuerpo, _ = dv.call(
        "GET",
        f"EntityDefinitions(LogicalName='{TABLA}')/Keys?$select=SchemaName,MetadataId",
    )
    if estado == 200:
        for k in cuerpo.get("value", []):
            e2, c2, _ = dv.call(
                "DELETE",
                f"EntityDefinitions(LogicalName='{TABLA}')/Keys({k['MetadataId']})",
            )
            if e2 in (204, 200, 404):
                print(f"  OK borrada clave: {k['SchemaName']}")
            else:
                print(f"  [FALLO] borrar clave {k['SchemaName']}: {e2} {c2.get('error')}")
                ok = False
    elif estado != 404:
        print(f"  [aviso] no se pudo listar claves: {estado} {cuerpo.get('error')}")

    estado, cuerpo, _ = dv.call("GET", f"EntityDefinitions(LogicalName='{TABLA}')?$select=LogicalName")
    if estado == 200:
        e2, c2, _ = dv.call("DELETE", f"EntityDefinitions(LogicalName='{TABLA}')")
        if e2 in (204, 200):
            print(f"  OK borrada tabla: {TABLA}")
        else:
            print(f"  [FALLO] borrar tabla {TABLA}: {e2} {c2.get('error')}")
            ok = False
    elif estado == 404:
        print(f"  la tabla {TABLA} ya no existe")
    else:
        print(f"  [aviso] no se pudo verificar la tabla: {estado} {cuerpo.get('error')}")
    return ok


def limpiar_solucion(dv):
    print(f"-- Solucion {SOLUCION} --")
    sols = listar(dv, "solutions", "contains(uniquename,'zzspike')", select="uniquename,solutionid")
    ok = True
    for s in sols:
        ok &= borrar(dv, "solutions", s["solutionid"], s["uniquename"])
    if not sols:
        print("  nada que borrar")
    return ok


def comprobacion_final(dv):
    print()
    print("=== Comprobacion final (todo debe dar vacio) ===")
    consultas = [
        ("solutions", "uniquename", "contains(uniquename,'zzspike')"),
        ("customapis", "uniquename", "contains(uniquename,'zz')"),
        ("pluginpackages", "uniquename", "contains(uniquename,'zz')"),
    ]
    todo_vacio = True
    for coleccion, campo, filtro in consultas:
        estado, cuerpo, _ = dv.call("GET", f"{coleccion}?$select={campo}&$filter={filtro}")
        valores = cuerpo.get("value", []) if estado == 200 else cuerpo
        print(f"{coleccion}: {estado} {valores}")
        if estado == 200 and valores:
            todo_vacio = False
    estado, cuerpo, _ = dv.call(
        "GET", f"EntityDefinitions?$select=LogicalName&$filter=LogicalName eq '{TABLA}'"
    )
    valores = cuerpo.get("value", []) if estado == 200 else cuerpo
    print(f"EntityDefinitions ({TABLA}): {estado} {valores}")
    if estado == 200 and valores:
        todo_vacio = False
    print()
    print("LIMPIEZA COMPLETA Y VERIFICADA" if todo_vacio else "LIMPIEZA INCOMPLETA: queda algo con 'zz'")
    return todo_vacio


def main():
    dv = Dataverse()
    ok = True
    ok &= limpiar_steps(dv)
    ok &= limpiar_customapis(dv)
    ok &= limpiar_plugintypes_y_paquetes(dv)
    ok &= limpiar_claves_y_tabla(dv)
    ok &= limpiar_solucion(dv)
    todo_vacio = comprobacion_final(dv)
    sys.exit(0 if (ok and todo_vacio) else 1)


if __name__ == "__main__":
    main()
