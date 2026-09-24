#!/usr/bin/env python3
"""Crea (o verifica) los datos de negocio que necesitan los casos de prueba
funcionales, y los borra cuando se termina.

    python3 herramientas/pruebas/preparar_datos.py --remitente <correo>
    python3 herramientas/pruebas/preparar_datos.py --verificar
    python3 herramientas/pruebas/preparar_datos.py --limpiar

`--remitente` es la dirección DESDE la que se van a mandar los correos de
prueba. Tiene que ser una casilla real a la que tengas acceso, porque varios
casos se comprueban leyendo la respuesta que llega a ese buzón.

**Qué crea** (todo con nombres que empiezan en `PR`, para poder borrarlo sin
tocar nada del cliente):

| Qué | Para qué caso |
|---|---|
| Cliente `PR - Pruebas MPPP SA` | dueño de todos los planes de prueba |
| Plan `PR11` formato 11, COR | el camino feliz, y las reglas de formato 11 |
| Plan `PR06` formato 06, COR | que la referencia NO se derive (DD-15) |
| Plan `PR10` formato 10, USD | `MONEDA_DEL_PLAN` |
| Plan `PRIN` formato 06, COR, **inactivo** | `PLAN_EXISTE` con un plan que existe pero no vale |
| Plan `PRNA` formato 06, COR | `AUTORIZACION_CORREO_PLAN`: existe, pero el remitente no está autorizado |
| Autorizado = el remitente | `REMITENTE_RECONOCIDO` |
| Autorizaciones a PR11, PR06, PR10 y PRIN | **a PRNA NO**, a propósito |

Última línea: JSON de una línea, igual que las herramientas de construcción.
"""
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))

PREFIJO = "PR"
CLIENTE = "PR - Pruebas MPPP SA"
CIF_BAC = "900100200"      # `sanic_cifbac` admite 9, y usa los 9
CIF_COM = "PRUEBASMPPP"    # `sanic_cifcom` admite 12: NO pasarse (antes decía 13 y fallaba)

# Largos máximos reales, leídos de la metadata el 2026-09-22. Se comprueban
# ANTES de tocar la red: un 400 de la plataforma a mitad de la preparación deja
# datos a medias y obliga a limpiar a mano.
LARGOS = {"CLIENTE": (CLIENTE, 200), "CIF_BAC": (CIF_BAC, 9), "CIF_COM": (CIF_COM, 12)}

FORMATO = {"06": 159460001, "10": 159460002, "11": 159460003}
MONEDA = {"COR": 159460001, "USD": 159460002}

PLANES = [
    {"codigo": "PR11", "formato": "11", "moneda": "COR", "activo": True,  "autorizado": True},
    {"codigo": "PR06", "formato": "06", "moneda": "COR", "activo": True,  "autorizado": True},
    {"codigo": "PR10", "formato": "10", "moneda": "USD", "activo": True,  "autorizado": True},
    {"codigo": "PRIN", "formato": "06", "moneda": "COR", "activo": False, "autorizado": True},
    {"codigo": "PRNA", "formato": "06", "moneda": "COR", "activo": True,  "autorizado": False},
]


def salida(estado, detalle):
    print(json.dumps({"estado": estado, "componente": "datos de prueba", "detalle": detalle},
                     ensure_ascii=False))
    return 0 if estado in ("creado", "ya_existia", "limpio") else 1


def uno(dv, conjunto, filtro, select="*"):
    sel = "" if select == "*" else f"$select={select}&"
    est, r, _ = dv.call("GET", f"{conjunto}?{sel}$filter={filtro}")
    v = r.get("value") or []
    return v[0] if v else None


def crear(dv, conjunto, cuerpo, sol="sanic_mppp_sol_mantenimientoppp"):
    from dataverse_api import Dataverse

    est, r, cab = dv.call("POST", conjunto, cuerpo)
    if est not in (200, 201, 204):
        raise RuntimeError(f"POST {conjunto} devolvió HTTP {est}: {str(r)[:220]}")
    return Dataverse.id_creado(cab)


def comprobar_largos(remitente):
    """Sin red. Un largo pasado se ve acá y no a mitad de la preparación."""
    malos = [f"{k}={v!r} usa {len(v)} y el máximo es {n}" for k, (v, n) in LARGOS.items() if len(v) > n]
    if len(remitente) > 320:
        malos.append(f"el remitente usa {len(remitente)} y el máximo es 320")
    for p in PLANES:
        if len(p["codigo"]) > 4:
            malos.append(f"el código de plan {p['codigo']!r} usa {len(p['codigo'])} y el máximo es 4")
        if len(f"{p['codigo']} - {CLIENTE}") > 100:
            malos.append(f"el nombre del plan {p['codigo']} pasa de 100")
        if len(f"{remitente} → {p['codigo']}") > 400:
            malos.append(f"el nombre de la autorización de {p['codigo']} pasa de 400")
    return malos


def preparar(dv, remitente):
    hechos = []

    cli = uno(dv, "sanic_mppp_tbl_clientes", f"sanic_nombre eq '{CLIENTE}'",
              "sanic_mppp_tbl_clienteid,sanic_nombre")
    if cli is None:
        idc = crear(dv, "sanic_mppp_tbl_clientes",
                    {"sanic_nombre": CLIENTE, "sanic_cifbac": CIF_BAC, "sanic_cifcom": CIF_COM})
        hechos.append(f"cliente {CLIENTE}")
    else:
        idc = cli["sanic_mppp_tbl_clienteid"]

    ids_plan = {}
    for p in PLANES:
        nombre = f"{p['codigo']} - {CLIENTE}"
        pl = uno(dv, "sanic_mppp_tbl_plans", f"sanic_codigo eq '{p['codigo']}'",
                 "sanic_mppp_tbl_planid,sanic_codigo,statecode")
        if pl is None:
            idp = crear(dv, "sanic_mppp_tbl_plans", {
                "sanic_nombre": nombre, "sanic_codigo": p["codigo"],
                "sanic_tipoformato": FORMATO[p["formato"]], "sanic_moneda": MONEDA[p["moneda"]],
                "sanic_clienteid@odata.bind": f"/sanic_mppp_tbl_clientes({idc})"})
            hechos.append(f"plan {p['codigo']} (formato {p['formato']}, {p['moneda']})")
        else:
            idp = pl["sanic_mppp_tbl_planid"]
        ids_plan[p["codigo"]] = idp
        # El plan inactivo se desactiva DESPUÉS de crear su autorización, más abajo.

    aut = uno(dv, "sanic_mppp_tbl_autorizados", f"sanic_nombre eq '{remitente}'",
              "sanic_mppp_tbl_autorizadoid,sanic_nombre")
    if aut is None:
        ida = crear(dv, "sanic_mppp_tbl_autorizados", {"sanic_nombre": remitente})
        hechos.append(f"autorizado {remitente}")
    else:
        ida = aut["sanic_mppp_tbl_autorizadoid"]

    for p in PLANES:
        if not p["autorizado"]:
            continue
        nombre = f"{remitente} → {p['codigo']}"
        ap = uno(dv, "sanic_mppp_tbl_autorizacionplans", f"sanic_nombre eq '{nombre}'",
                 "sanic_mppp_tbl_autorizacionplanid")
        if ap is None:
            crear(dv, "sanic_mppp_tbl_autorizacionplans", {
                "sanic_nombre": nombre,
                "sanic_autorizadoid@odata.bind": f"/sanic_mppp_tbl_autorizados({ida})",
                "sanic_planid@odata.bind": f"/sanic_mppp_tbl_plans({ids_plan[p['codigo']]})"})
            hechos.append(f"autorizacion {nombre}")

    # Recién ahora se desactiva el plan inactivo: su autorización ya existe, así
    # el caso prueba "el plan no vale", no "falta la autorización".
    for p in PLANES:
        if p["activo"]:
            continue
        est, _, _ = dv.call("PATCH", f"sanic_mppp_tbl_plans({ids_plan[p['codigo']]})",
                            {"statecode": 1, "statuscode": 2})
        if est in (200, 204):
            hechos.append(f"plan {p['codigo']} DESACTIVADO a propósito")

    return hechos


def verificar(dv, remitente=None):
    faltan, bien = [], []
    cli = uno(dv, "sanic_mppp_tbl_clientes", f"sanic_nombre eq '{CLIENTE}'", "sanic_nombre")
    (bien if cli else faltan).append(f"cliente {CLIENTE}")
    for p in PLANES:
        pl = uno(dv, "sanic_mppp_tbl_plans", f"sanic_codigo eq '{p['codigo']}'",
                 "sanic_codigo,statecode,sanic_tipoformato,sanic_moneda")
        if pl is None:
            faltan.append(f"plan {p['codigo']}")
            continue
        activo_ok = (pl["statecode"] == 0) == p["activo"]
        formato_ok = pl["sanic_tipoformato"] == FORMATO[p["formato"]]
        moneda_ok = pl["sanic_moneda"] == MONEDA[p["moneda"]]
        if activo_ok and formato_ok and moneda_ok:
            bien.append(f"plan {p['codigo']}")
        else:
            faltan.append(f"plan {p['codigo']} mal configurado "
                          f"(activo={activo_ok}, formato={formato_ok}, moneda={moneda_ok})")
    if remitente:
        aut = uno(dv, "sanic_mppp_tbl_autorizados", f"sanic_nombre eq '{remitente}'", "sanic_nombre")
        (bien if aut else faltan).append(f"autorizado {remitente}")
        for p in PLANES:
            nombre = f"{remitente} → {p['codigo']}"
            ap = uno(dv, "sanic_mppp_tbl_autorizacionplans", f"sanic_nombre eq '{nombre}'", "sanic_nombre")
            existe = ap is not None
            if existe == p["autorizado"]:
                bien.append(f"autorizacion {p['codigo']}: {'existe' if existe else 'NO existe (correcto)'}")
            else:
                faltan.append(f"autorizacion {p['codigo']}: se esperaba "
                              f"{'que existiera' if p['autorizado'] else 'que NO existiera'}")
    return bien, faltan


def limpiar(dv, remitente=None):
    borrados = []
    # Orden inverso a las dependencias: autorizaciones, autorizados, planes, cliente.
    est, r, _ = dv.call("GET", "sanic_mppp_tbl_autorizacionplans?$select=sanic_mppp_tbl_autorizacionplanid,sanic_nombre")
    for x in r.get("value", []):
        if any(f"→ {p['codigo']}" in (x.get("sanic_nombre") or "") for p in PLANES):
            dv.call("DELETE", f"sanic_mppp_tbl_autorizacionplans({x['sanic_mppp_tbl_autorizacionplanid']})")
            borrados.append(x["sanic_nombre"])
    if remitente:
        aut = uno(dv, "sanic_mppp_tbl_autorizados", f"sanic_nombre eq '{remitente}'",
                  "sanic_mppp_tbl_autorizadoid")
        if aut:
            dv.call("DELETE", f"sanic_mppp_tbl_autorizados({aut['sanic_mppp_tbl_autorizadoid']})")
            borrados.append(remitente)
    for p in PLANES:
        pl = uno(dv, "sanic_mppp_tbl_plans", f"sanic_codigo eq '{p['codigo']}'", "sanic_mppp_tbl_planid")
        if pl:
            dv.call("DELETE", f"sanic_mppp_tbl_plans({pl['sanic_mppp_tbl_planid']})")
            borrados.append(p["codigo"])
    cli = uno(dv, "sanic_mppp_tbl_clientes", f"sanic_nombre eq '{CLIENTE}'", "sanic_mppp_tbl_clienteid")
    if cli:
        dv.call("DELETE", f"sanic_mppp_tbl_clientes({cli['sanic_mppp_tbl_clienteid']})")
        borrados.append(CLIENTE)
    return borrados


def main():
    argv = sys.argv[1:]
    remitente = next((a.split("=", 1)[1] for a in argv if a.startswith("--remitente=")), None)
    if remitente is None and "--remitente" in argv:
        i = argv.index("--remitente")
        remitente = argv[i + 1] if i + 1 < len(argv) else None

    from dataverse_api import Dataverse

    dv = Dataverse()
    try:
        if "--limpiar" in argv:
            borrados = limpiar(dv, remitente)
            return salida("limpio", f"borrados {len(borrados)}: {borrados}" if borrados
                          else "no había nada que borrar")
        if "--verificar" in argv:
            bien, faltan = verificar(dv, remitente)
            if faltan:
                return salida("difiere", f"faltan o están mal: {faltan}")
            return salida("ya_existia", f"{len(bien)} comprobaciones en verde")
        if not remitente or "@" not in remitente:
            return salida("error", "hace falta --remitente <correo desde el que vas a enviar las pruebas>")
        malos = comprobar_largos(remitente)
        if malos:
            return salida("error", "hay valores más largos de lo que admite la tabla: " + "; ".join(malos))
        hechos = preparar(dv, remitente)
        bien, faltan = verificar(dv, remitente)
        if faltan:
            return salida("error", f"se escribió pero no quedó bien: {faltan}")
        return salida("creado" if hechos else "ya_existia",
                      (f"{len(hechos)} altas: {hechos}; " if hechos else "ya estaba todo; ")
                      + f"{len(bien)} comprobaciones en verde")
    except Exception as e:
        return salida("error", f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(main())
