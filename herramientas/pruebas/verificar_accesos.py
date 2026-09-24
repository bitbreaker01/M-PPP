#!/usr/bin/env python3
"""Compara los privilegios EFECTIVOS de un usuario con la matriz de `diseno/04-matriz-privilegios.md`.

**Por qué existe.** Probar permisos a mano tiene un problema: cuando el usuario de
prueba puede hacer algo que no debería, no se sabe QUIEN se lo permitió. En Dataverse
los privilegios se SUMAN: los de sus roles directos más los de cada equipo al que
pertenece. Un usuario reciclado de otro proyecto arrastra los roles de ese proyecto,
y entonces "pudo hacerlo" no prueba que el rol de MPPP se lo haya dado.

Esta herramienta responde las tres preguntas en una sola corrida:
  1. ¿Le FALTA algún privilegio que la matriz le da? → no va a poder trabajar.
  2. ¿Le SOBRA alguno que la matriz no le da? → y, si sobra, QUE ROL se lo dio.
  3. ¿Puede leer las dos columnas protegidas? (es un mecanismo aparte de los roles).

Se usa `RetrieveUserSetOfPrivilegesByNames` y no `RetrieveUserPrivileges`: Learn
advierte que la segunda devuelve profundidad **Basic** para todo lo que el usuario
hereda de un equipo, sin importar la profundidad real del rol del equipo. Con esa
función, un privilegio Global heredado por equipo se leería como Basic y la
comparación mentiría justo en el caso que más importa.
  https://learn.microsoft.com/power-apps/developer/data-platform/security-access-coding

No escribe nada: son lecturas y una función. Se puede correr en cualquier entorno.

Uso:
    python3 herramientas/pruebas/verificar_accesos.py                 # los tres de prueba
    python3 herramientas/pruebas/verificar_accesos.py User1 User2     # por nombre de inicio de sesión
    python3 herramientas/pruebas/verificar_accesos.py --json
    → sale con 0 si todo coincide, 1 si hay algo que falta o que sobra.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataverse_api import Dataverse  # noqa: E402

SOLUCION = "sanic_mppp"

# Las diez tablas de la matriz, con el nombre que usa el diseño. `motivoaccion` NO está
# en la matriz: es la tabla técnica del diálogo de motivo (05 DA-03), y se lista igual
# porque sin `Create` sobre ella los botones que piden motivo no funcionan.
TABLAS = [
    ("sanic_mppp_tbl_cliente", "Cliente"),
    ("sanic_mppp_tbl_plan", "Plan"),
    ("sanic_mppp_tbl_autorizado", "Autorizado"),
    ("sanic_mppp_tbl_autorizacionplan", "AutorizacionPlan"),
    ("sanic_mppp_tbl_parametro", "Parametro"),
    ("sanic_mppp_tbl_regla", "Regla"),
    ("sanic_mppp_tbl_solicitud", "Solicitud"),
    ("sanic_mppp_tbl_fila", "Fila"),
    ("sanic_mppp_tbl_resultadoregla", "ResultadoRegla"),
    ("sanic_mppp_tbl_bitacora", "Bitacora"),
    ("sanic_mppp_tbl_motivoaccion", "MotivoAccion"),
]

# El prefijo del privilegio por cada derecho de la notación del diseño.
DERECHOS = {
    "C": "prvCreate",
    "R": "prvRead",
    "W": "prvWrite",
    "D": "prvDelete",
    "Ap": "prvAppend",
    "At": "prvAppendTo",
    "As": "prvAssign",
    "Sh": "prvShare",
}

# `04-matriz-privilegios.md` §2, una entrada por celda con privilegio. Alcance:
# O = Global (organización), U = Basic (propio). Toda celda ausente es "sin privilegio",
# y eso incluye `D` (borrado) en TODAS las tablas: "Nadie borra" (§2).
MATRIZ = {
    "SR - MPPP - Ejecutivo": {
        "Cliente": {"R": "O"},
        "Plan": {"R": "O"},
        "Autorizado": {"R": "O"},
        "AutorizacionPlan": {"R": "O"},
        "Regla": {"R": "O"},
        "Solicitud": {"R": "O", "W": "O", "At": "O"},
        "Fila": {"R": "O", "W": "O", "Ap": "O"},
        "ResultadoRegla": {"R": "O"},
        "Bitacora": {"R": "O"},
        # No está en `04` §2 — sale de `playbooks/rol/sr_mppp_ejecutivo.md`. Es el registro
        # descartable del diálogo de motivo, y por eso va en alcance `U`: cada quien
        # solo toca el suyo. Falta documentarlo en la matriz (ver `PENDIENTES.md`).
        "MotivoAccion": {"C": "U", "R": "U", "W": "U", "D": "U"},
    },
    "SR - MPPP - Supervisor": {
        "Cliente": {"R": "O"},
        "Plan": {"R": "O"},
        "Autorizado": {"R": "O"},
        "AutorizacionPlan": {"R": "O"},
        "Regla": {"R": "O"},
        "Solicitud": {"R": "O", "At": "O"},
        "Fila": {"R": "O", "W": "O", "Ap": "O"},
        "ResultadoRegla": {"R": "O"},
        "Bitacora": {"R": "O"},
        "MotivoAccion": {"C": "U", "R": "U", "W": "U", "D": "U"},  # ídem, `sr_mppp_supervisor.md`
    },
    "SR - MPPP - Administrador de planes": {
        "Cliente": {"C": "O", "R": "O", "W": "O", "Ap": "O", "At": "O", "As": "O"},
        "Plan": {"C": "O", "R": "O", "W": "O", "Ap": "O", "At": "O"},
        "Autorizado": {"C": "O", "R": "O", "W": "O", "Ap": "O", "At": "O"},
        "AutorizacionPlan": {"C": "O", "R": "O", "W": "O", "Ap": "O", "At": "O"},
        "Regla": {"R": "O"},
    },
    "SR - MPPP - Administrador tecnico": {
        "Parametro": {"C": "O", "R": "O", "W": "O"},
        "Regla": {"C": "O", "R": "O", "W": "O"},
    },
}

# Las dos columnas de `04` §4, que NO se gobiernan con roles sino con un perfil de
# seguridad de columna. Quién tiene que poder leerlas: Ejecutivo y Supervisor.
COLUMNAS_PROTEGIDAS = [
    ("sanic_mppp_tbl_fila", "sanic_numeroidentificacion"),
    ("sanic_mppp_tbl_fila", "sanic_numerocuenta"),
]
PERFIL_COLUMNAS = "CSP - MPPP - Datos sensibles"
NECESITAN_LAS_COLUMNAS = {"SR - MPPP - Ejecutivo", "SR - MPPP - Supervisor"}

ALCANCE = {"Basic": "U", "Local": "BU", "Deep": "BU+", "Global": "O"}

USUARIOS_POR_DEFECTO = ["User1", "User2", "User3"]


def privilegio(derecho, tabla_logica):
    return DERECHOS[derecho] + tabla_logica


def todos_los_privilegios():
    return [privilegio(d, t) for t, _ in TABLAS for d in DERECHOS]


def buscar_usuario(dv, alias):
    """El usuario cuyo `domainname` empieza con el alias. Nunca uno parecido: si hay
    más de uno, se corta, porque probar permisos sobre el usuario equivocado es peor
    que no probar."""
    e, b, _ = dv.call(
        "GET",
        "systemusers?$select=systemuserid,fullname,domainname,isdisabled"
        f"&$filter=startswith(domainname,'{alias}') and applicationid eq null")
    if e != 200:
        raise SystemExit(f"no se pudo buscar {alias!r}: {b}")
    candidatos = b.get("value", [])
    exactos = [u for u in candidatos
               if u["domainname"].split("@")[0].lower() == alias.lower()]
    elegidos = exactos or candidatos
    if len(elegidos) != 1:
        nombres = [u["domainname"] for u in candidatos]
        raise SystemExit(f"{alias!r} no identifica a un usuario único: {nombres}")
    return elegidos[0]


def exigir(estado, cuerpo, que):
    """Un 404 o un 429 tragado devuelve lista vacía, y una lista vacía acá se lee como
    'este usuario no tiene nada', que es la conclusión más tranquilizadora y la más
    peligrosa. Cualquier respuesta que no sea 200 corta."""
    if estado != 200:
        raise SystemExit(f"{que} falló (HTTP {estado}): {cuerpo}")
    return cuerpo.get("value", [])


def roles_del_usuario(dv, uid):
    """(roles directos, roles por equipo, ids de sus equipos). Los dos primeros cuentan:
    Dataverse los SUMA, no elige el más restrictivo."""
    e, b, _ = dv.call("GET", f"systemusers({uid})/systemuserroles_association?$select=roleid,name")
    directos = {r["roleid"]: r["name"] for r in exigir(e, b, "roles directos")}

    e, b, _ = dv.call("GET", f"systemusers({uid})/teammembership_association?$select=teamid,name&$top=500")
    equipos = exigir(e, b, "equipos del usuario")

    porequipo = {}
    for t in equipos:
        e2, b2, _ = dv.call("GET", f"teams({t['teamid']})/teamroles_association?$select=roleid,name")
        for r in exigir(e2, b2, f"roles del equipo {t['name']!r}"):
            porequipo.setdefault(r["roleid"], (r["name"], []))[1].append(t["name"])
    return directos, porequipo, {t["teamid"] for t in equipos}


def quien_otorga(dv, roleids, privilegios_mppp):
    """privilegio → [roles que lo traen]. Es lo que convierte un 'SOBRA' en accionable:
    sin esto, el hallazgo dice que algo sobra pero no a quién sacárselo."""
    por_id = {p["privilegeid"]: p["name"] for p in privilegios_mppp}
    fuente = {}
    for rid, nombre in roleids.items():
        # NO existe un conjunto de entidades `roleprivileges` en el Web API: consultarlo
        # da 404, y un 404 tragado hace que TODO quede "origen no identificado" — que es
        # justo el dato por el que existe esta función. Se va por la navegación del rol.
        e, b, _ = dv.call(
            "GET", f"roles({rid})/roleprivileges_association?$select=privilegeid,name&$top=5000")
        if e != 200:
            raise SystemExit(f"no se pudieron leer los privilegios del rol {nombre!r} ({e}): {b}")
        for p in b.get("value", []):
            if p["privilegeid"] in por_id:
                fuente.setdefault(p["name"], []).append(nombre)
    return fuente


def efectivos(dv, uid, nombres):
    """privilegio → profundidad efectiva, sumando roles directos y de equipo."""
    resultado = {}
    for i in range(0, len(nombres), 40):  # la URL tiene largo máximo; se pide por tandas
        tanda = nombres[i:i + 40]
        ruta = (f"systemusers({uid})/Microsoft.Dynamics.CRM."
                f"RetrieveUserSetOfPrivilegesByNames(PrivilegeNames=@p1)?@p1={json.dumps(tanda)}")
        e, b, _ = dv.call("GET", ruta)
        if e != 200:
            raise SystemExit(f"RetrieveUserSetOfPrivilegesByNames falló ({e}): {b}")
        for rp in b.get("RolePrivileges", []):
            resultado[rp["PrivilegeName"]] = rp["Depth"]
    return resultado


def perfiles_de_columna(dv, uid, equipos_del_usuario):
    """Los perfiles de seguridad de columna que alcanzan al usuario, por asignación
    directa o por alguno de sus equipos."""
    alcanzan = []
    e, b, _ = dv.call("GET", "fieldsecurityprofiles?$select=fieldsecurityprofileid,name")
    for p in exigir(e, b, "perfiles de seguridad de columna"):
        pid = p["fieldsecurityprofileid"]
        e2, b2, _ = dv.call("GET", f"fieldsecurityprofiles({pid})/systemuserprofiles_association?$select=systemuserid")
        directo = any(u["systemuserid"] == uid
                      for u in exigir(e2, b2, f"usuarios del perfil {p['name']!r}"))
        e3, b3, _ = dv.call("GET", f"fieldsecurityprofiles({pid})/teamprofiles_association?$select=teamid,name")
        via = [t["name"] for t in exigir(e3, b3, f"equipos del perfil {p['name']!r}")
               if t["teamid"] in equipos_del_usuario]
        if directo or via:
            alcanzan.append((p["name"], pid, "directo" if directo else f"equipo {via}"))
    return alcanzan


APP = "sanic_mppp_mda_mantenimientoppp"


def puede_abrir_la_app(dv, uid):
    """Si el usuario puede ABRIR la app, no solo si tiene los privilegios.

    **Por qué es una comprobación aparte.** Los privilegios y la LICENCIA son dos
    mecanismos distintos y ninguno implica al otro. El 2026-09-24 `User3` coincidía con
    la matriz celda por celda y aun así la app le daba un `502` en pantalla: su
    `userlicensetype` era 69 y el de los otros dos 20, y sin la licencia adecuada
    Dataverse no lo deja leer el `appmodule`. Esta herramienta lo declaraba en verde.

    Se prueba suplantándolo y pidiendo la app POR SU ID: es la misma llamada que hace el
    cargador de contexto del navegador, y devuelve el motivo exacto. Sin permiso para
    suplantar no se puede probar, y eso se dice — no se da por bueno.

    **Tiene que ser por id, no una consulta con `$filter`.** Una consulta filtrada
    devuelve `200` con una lista VACÍA cuando el usuario no puede ver la app, y un 200
    vacío se lee como "todo bien": la primera versión de esta función lo hacía así y
    declaró a `User3` en verde el mismo día que no podía entrar."""
    e, b, _ = dv.call("GET", f"appmodules?$select=appmoduleid&$filter=uniquename eq '{APP}'")
    filas = b.get("value", []) if e == 200 else []
    if len(filas) != 1:
        return ("no_probado", f"no se encontró la app {APP!r} en el entorno")

    e, b, _ = dv.call("GET", f"appmodules({filas[0]['appmoduleid']})?$select=name",
                      cabeceras={"MSCRMCallerID": uid})
    texto = str((b or {}).get("error", ""))
    if e == 200:
        return ("ok", None)
    if "CrmLicensingNoUserPass" in texto or "appropriate license" in texto:
        return ("licencia", "no tiene una licencia que le permita abrir apps custom "
                            "(en el navegador esto se ve como un 502, no como un error de permisos)")
    if e in (401, 403):
        return ("privilegio", texto[:160])
    return ("no_probado", f"HTTP {e}: {texto[:160]}")


def revisar(dv, alias, privilegios_mppp):
    usuario = buscar_usuario(dv, alias)
    uid = usuario["systemuserid"]
    directos, porequipo, ids_equipos = roles_del_usuario(dv, uid)

    roles_mppp = [n for n in directos.values() if n in MATRIZ]
    if len(roles_mppp) != 1:
        esperado = {}
        nota = (f"NO tiene exactamente un rol de MPPP asignado directo: {roles_mppp or 'ninguno'}. "
                "Sin un rol de referencia no hay contra qué comparar.")
    else:
        esperado = MATRIZ[roles_mppp[0]]
        nota = None

    efec = efectivos(dv, uid, todos_los_privilegios())
    todos_los_roles = dict(directos)
    todos_los_roles.update({rid: v[0] for rid, v in porequipo.items()})
    fuente = quien_otorga(dv, todos_los_roles, privilegios_mppp)

    hallazgos = []
    for tabla_logica, tabla in TABLAS:
        quiere = esperado.get(tabla, {})
        for derecho in DERECHOS:
            nombre = privilegio(derecho, tabla_logica)
            tiene = efec.get(nombre)
            debe = quiere.get(derecho)
            if debe and not tiene:
                hallazgos.append(("FALTA", tabla, derecho, f"la matriz le da {debe} y no lo tiene"))
            elif debe and ALCANCE.get(tiene, tiene) != debe:
                hallazgos.append(("ALCANCE", tabla, derecho,
                                  f"la matriz le da {debe} y tiene {ALCANCE.get(tiene, tiene)}"))
            elif not debe and tiene:
                de = fuente.get(nombre, ["origen no identificado"])
                hallazgos.append(("SOBRA", tabla, derecho,
                                  f"tiene {ALCANCE.get(tiene, tiene)} · lo trae: " + "; ".join(de)))

    perfiles = perfiles_de_columna(dv, uid, ids_equipos)

    necesita_columnas = bool(roles_mppp) and roles_mppp[0] in NECESITAN_LAS_COLUMNAS
    tiene_perfil_mppp = any(nombre == PERFIL_COLUMNAS for nombre, _, _ in perfiles)
    es_admin = any(nombre == "System Administrator" for nombre, _, _ in perfiles)
    if necesita_columnas and not tiene_perfil_mppp and not es_admin:
        hallazgos.append(("COLUMNAS", "Fila", "R",
                          f"no está en {PERFIL_COLUMNAS!r}: NO va a ver identificación ni cuenta, "
                          "que es justo lo que tiene que digitar"))

    estado_app, detalle_app = puede_abrir_la_app(dv, uid)
    if estado_app == "licencia":
        hallazgos.append(("LICENCIA", "App", "—", detalle_app))
    elif estado_app == "privilegio":
        hallazgos.append(("APP", "App", "R", "no puede leer la app: " + detalle_app))
    elif estado_app == "no_probado":
        hallazgos.append(("SIN PROBAR", "App", "—",
                          "no se pudo comprobar si puede abrir la app · " + detalle_app))

    return {
        "alias": alias,
        "usuario": usuario["fullname"],
        "upn": usuario["domainname"],
        "id": uid,
        "rol_mppp": roles_mppp[0] if len(roles_mppp) == 1 else None,
        "roles_directos": sorted(directos.values()),
        "roles_por_equipo": sorted({v[0] for v in porequipo.values()}),
        "perfiles_de_columna": [n for n, _, _ in perfiles],
        "nota": nota,
        "hallazgos": [{"tipo": t, "tabla": tb, "derecho": d, "detalle": x} for t, tb, d, x in hallazgos],
    }


def main():
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    como_json = "--json" in sys.argv
    alias = argumentos or USUARIOS_POR_DEFECTO

    dv = Dataverse()
    e, b, _ = dv.call(
        "GET",
        f"privileges?$select=privilegeid,name&$filter=contains(name,'{SOLUCION}')&$top=500")
    if e != 200:
        raise SystemExit(f"no se pudo leer el catálogo de privilegios: {b}")
    privilegios_mppp = b.get("value", [])

    informes = [revisar(dv, a, privilegios_mppp) for a in alias]

    if como_json:
        print(json.dumps(informes, ensure_ascii=False, indent=1))
    else:
        for inf in informes:
            print("=" * 78)
            print(f"{inf['alias']}  ·  {inf['usuario']}  ·  {inf['upn']}")
            print(f"  rol de MPPP      : {inf['rol_mppp'] or '(ninguno o más de uno)'}")
            print(f"  roles directos   : {', '.join(inf['roles_directos']) or '—'}")
            print(f"  roles por equipo : {', '.join(inf['roles_por_equipo']) or '—'}")
            print(f"  perfiles de columna: {', '.join(inf['perfiles_de_columna']) or '—'}")
            if inf["nota"]:
                print(f"  ! {inf['nota']}")
            if not inf["hallazgos"]:
                print("\n  Coincide con la matriz, celda por celda.")
            for h in inf["hallazgos"]:
                print(f"\n  [{h['tipo']:8}] {h['tabla']}.{h['derecho']}")
                print(f"             {h['detalle']}")
            print()

    hay_problemas = any(inf["hallazgos"] or inf["nota"] for inf in informes)
    return 1 if hay_problemas else 0


if __name__ == "__main__":
    sys.exit(main())
