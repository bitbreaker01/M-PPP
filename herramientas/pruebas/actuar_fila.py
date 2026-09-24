#!/usr/bin/env python3
"""Ejecuta acciones sobre las Filas de una Solicitud **en nombre del service principal**.

**Por qué existe.** Aprobar exige rol Supervisor Y que el aprobador no sea quien
digitó (`AutorizarAprobar`, `diseno/03` §4). Con un solo usuario humano ese
camino no se puede recorrer: es segregación de funciones y está bien que sea
así. La salida NO es apagar el control, es que digite otro.

Esta herramienta escribe con el service principal, que para el plugin es una
identidad distinta de la persona que usa la app. Entonces:

    el SP digita  →  `sanic_digitadapor` queda apuntando al SP
    vos aprobás   →  `DigitadaPor != Actor.UsuarioId`  →  el control SE CUMPLE

No se saltea nada. Es el mismo camino que va a usar el RPA en fase 2.

**Esta herramienta no tiene poderes especiales.** Escribe por la Web API como
cualquier cliente, y `TransicionDeFilaStep` la evalúa igual que a un humano. Si
el plugin rechaza, acá se ve el motivo. Que una accion funcione desde aca
significa que funcionaria desde la app con ese mismo rol; no significa que el
control se haya desactivado.

Uso:
    # ver el estado de las filas, sin tocar nada (por defecto)
    python3 herramientas/pruebas/actuar_fila.py MPPP-00001008

    # digitar todas las filas que se puedan
    python3 herramientas/pruebas/actuar_fila.py MPPP-00001008 digitar

    # una sola fila, o varias
    python3 herramientas/pruebas/actuar_fila.py MPPP-00001008 digitar --fila 2
    python3 herramientas/pruebas/actuar_fila.py MPPP-00001008 digitar --fila 1,3

    # las que piden motivo lo exigen antes de tocar el servidor
    python3 herramientas/pruebas/actuar_fila.py MPPP-00001008 anular --fila 2 --motivo "prueba F-07"
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataverse_api import Dataverse  # noqa: E402

FILAS = "sanic_mppp_tbl_filas"          # conjunto de entidades (para la Web API)
SOLICITUDES = "sanic_mppp_tbl_solicituds"

# sanic_estado. Leidos de la metadata, no de memoria.
VALIDADA = 159460003
DIGITADA = 159460004
APROBADA = 159460005
RECHAZADA_AS400 = 159460006
ANULADA = 159460007
POR_DIGITAR = 159460002   # estado inicial de la fila validada por la Custom API

NOMBRE_ESTADO = {
    POR_DIGITAR: "Por digitar",
    VALIDADA: "Validada",
    DIGITADA: "Digitada",
    APROBADA: "Aprobada",
    RECHAZADA_AS400: "Rechazada en AS400",
    ANULADA: "Anulada",
}

# Para MOSTRAR no se usa el mapa de arriba: se le piden a la plataforma los
# valores formateados. El mapa es solo para DECIDIR (la tabla de transiciones
# trabaja con los numeros de `sanic_estado`).
#
# La razon es concreta: la primera version de esta herramienta mostraba el
# estado de la SOLICITUD con el mapa de estados de FILA, que son choices
# distintos, y decia "Aprobada" donde la solicitud decia otra cosa. Un mapa
# escrito a mano al lado del de la plataforma tarde o temprano miente.
FORMATEADO = {"Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'}
SUFIJO = "@OData.Community.Display.V1.FormattedValue"


def texto(fila, columna, por_defecto="-"):
    """El valor formateado de una columna, o el crudo si no vino la anotacion."""
    return fila.get(columna + SUFIJO) or (str(fila[columna]) if fila.get(columna) is not None else por_defecto)

# La tabla de `Dominio/TransicionesDeFila.cs`, y NADA MAS. Si una accion no esta
# aca es porque el dominio no la define: inventarla solo lograria que el plugin
# la rechace despues de haber golpeado el servidor.
ACCIONES = {
    "digitar":  {"desde": [VALIDADA], "hacia": DIGITADA,
                 "motivo": False, "rol": "SR - MPPP - Ejecutivo"},
    "aprobar":  {"desde": [DIGITADA], "hacia": APROBADA,
                 "motivo": False, "rol": "SR - MPPP - Supervisor (y distinto de quien digito)"},
    "devolver": {"desde": [DIGITADA], "hacia": VALIDADA,
                 "motivo": True, "rol": "SR - MPPP - Supervisor"},
    "rechazar": {"desde": [VALIDADA, DIGITADA], "hacia": RECHAZADA_AS400,
                 "motivo": True, "rol": "SR - MPPP - Ejecutivo"},
    "anular":   {"desde": [VALIDADA, DIGITADA], "hacia": ANULADA,
                 "motivo": True, "rol": "SR - MPPP - Ejecutivo"},
}

# Los unicos tres roles que `PlomeriaDeFila.DeterminarRoles` mira. El resto de
# los roles del usuario (System Administrator incluido) es invisible para el
# plugin: evalua roles de NEGOCIO, no privilegios de plataforma.
ROLES_DE_NEGOCIO = ("SR - MPPP - Ejecutivo", "SR - MPPP - Supervisor", "SR - MPPP - RPA")


def salir(mensaje):
    print(f"\n  {mensaje}")
    raise SystemExit(1)


def motivo_del_rechazo(cuerpo):
    """El texto que puso el plugin, saliendo de donde de verdad viene.

    OJO: el TERCER valor que devuelve `dv.call` son las CABECERAS de la
    respuesta, no el error. La primera version de esta funcion lo leia de ahi e
    imprimia `{}` en cada rechazo, que es peor que no imprimir nada: parecia que
    el plugin rechazaba sin motivo. El mensaje viaja en el CUERPO, y Dataverse lo
    manda de dos formas segun el caso: `{"error": "texto"}` o el sobre OData
    completo `{"error": {"code": ..., "message": "texto"}}`.
    """
    if isinstance(cuerpo, dict):
        error = cuerpo.get("error")
        if isinstance(error, str):
            return error
        if isinstance(error, dict):
            return error.get("message") or str(error)
    return str(cuerpo) if cuerpo else "sin mensaje (revisar el trace del plugin)"


def solicitud_por_numero(dv, numero):
    """Acepta el numero (MPPP-00001008) o el GUID."""
    if "-" in numero and numero.upper().startswith("MPPP"):
        ruta = (f"{SOLICITUDES}?$select=sanic_mppp_tbl_solicitudid,sanic_nombre,sanic_estadoprocesamiento"
                f"&$filter=sanic_nombre eq '{numero}'&$top=1")
    else:
        ruta = f"{SOLICITUDES}({numero})?$select=sanic_mppp_tbl_solicitudid,sanic_nombre,sanic_estadoprocesamiento"
    codigo, cuerpo, _ = dv.call("GET", ruta, cabeceras=FORMATEADO)
    if codigo != 200:
        salir(f"no se pudo leer la solicitud {numero!r} (HTTP {codigo})")
    filas = cuerpo.get("value", [cuerpo]) if isinstance(cuerpo, dict) else []
    if not filas or not filas[0].get("sanic_mppp_tbl_solicitudid"):
        salir(f"no existe ninguna solicitud {numero!r}")
    return filas[0]


def filas_de(dv, solicitud_id):
    ruta = (f"{FILAS}?$select=sanic_mppp_tbl_filaid,sanic_numerofila,sanic_estado,sanic_gestion,"
            "sanic_referencia,sanic_mensaje,_sanic_digitadapor_value,_sanic_aprobadapor_value"
            f"&$filter=_sanic_solicitudid_value eq {solicitud_id}&$orderby=sanic_numerofila asc")
    codigo, cuerpo, _ = dv.call("GET", ruta, cabeceras=FORMATEADO)
    if codigo != 200:
        salir(f"no se pudieron leer las filas (HTTP {codigo})")
    return cuerpo.get("value", [])


def nombre_de_usuario(dv, cache, uid):
    if not uid:
        return None
    if uid not in cache:
        codigo, u, _ = dv.call("GET", f"systemusers({uid})?$select=fullname")
        cache[uid] = u.get("fullname") if codigo == 200 else uid[:8]
    return cache[uid]


def quien_soy(dv):
    """El usuario con el que esta herramienta escribe, y sus roles de negocio.

    Se muestra SIEMPRE: si no queda claro en nombre de quien se actua, el
    resultado de una prueba de segregacion de funciones no significa nada.
    """
    codigo, who, _ = dv.call("GET", "WhoAmI")
    uid = who["UserId"]
    codigo, u, _ = dv.call("GET", f"systemusers({uid})?$select=fullname,applicationid")
    codigo, r, _ = dv.call("GET", f"systemusers({uid})/systemuserroles_association?$select=name")
    todos = [x.get("name") for x in r.get("value", [])]
    negocio = [n for n in todos if n in ROLES_DE_NEGOCIO]
    return uid, u.get("fullname"), bool(u.get("applicationid")), negocio


def mostrar(dv, solicitud, filas, cache):
    print(f"\n{solicitud['sanic_nombre']}  ·  estado de la solicitud: "
          f"{texto(solicitud, 'sanic_estadoprocesamiento')}")
    print(f"{'fila':>5}  {'estado':<20} {'gestion':<14} {'digitada por':<22} {'aprobada por':<22} referencia")
    for f in filas:
        print(f"{f.get('sanic_numerofila'):>5}  "
              f"{texto(f, 'sanic_estado'):<20} "
              f"{texto(f, 'sanic_gestion')[:14]:<14} "
              f"{str(nombre_de_usuario(dv, cache, f.get('_sanic_digitadapor_value')) or '-')[:22]:<22} "
              f"{str(nombre_de_usuario(dv, cache, f.get('_sanic_aprobadapor_value')) or '-')[:22]:<22} "
              f"{str(f.get('sanic_referencia') or '')[:24]}")


def aplicar(dv, accion, conf, filas, motivo):
    """Una fila por vez, igual que los comandos del ribbon.

    No se usa un lote a proposito: una fila que el plugin rechaza no tiene por
    que arrastrar a las demas, y asi el motivo de cada rechazo se ve por
    separado. Es el mismo criterio de `recursos/js/comandos.js`.
    """
    print(f"\naplicando '{accion}' a {len(filas)} fila(s):")
    ok, fallas = 0, []
    for f in filas:
        cambio = {"sanic_estado": conf["hacia"]}
        if conf["motivo"]:
            cambio["sanic_mensaje"] = motivo
        codigo, cuerpo, _ = dv.call("PATCH", f"{FILAS}({f['sanic_mppp_tbl_filaid']})", cambio)
        if codigo in (200, 204):
            ok += 1
            print(f"   fila {f.get('sanic_numerofila')}: OK → {NOMBRE_ESTADO[conf['hacia']]}")
        else:
            fallas.append((f.get("sanic_numerofila"), motivo_del_rechazo(cuerpo)))
            print(f"   fila {f.get('sanic_numerofila')}: RECHAZADA → {fallas[-1][1][:200]}")
    print(f"\n{ok} de {len(filas)} aplicada(s).")
    if fallas:
        print("Las rechazadas las rechazo el plugin, no esta herramienta: el control funciono.")
    return ok, fallas


def main():
    p = argparse.ArgumentParser(description="Acciones sobre las Filas de una Solicitud, como el service principal.")
    p.add_argument("solicitud", help="numero (MPPP-00001008) o GUID")
    p.add_argument("accion", nargs="?", choices=sorted(ACCIONES), help="sin accion, solo muestra el estado")
    p.add_argument("--fila", help="numero(s) de fila separados por coma; sin esto, todas las que se puedan")
    p.add_argument("--motivo", help="texto obligatorio en devolver, rechazar y anular")
    args = p.parse_args()

    dv = Dataverse()
    cache = {}
    uid, nombre, es_app, roles = quien_soy(dv)
    print(f"escribiendo como: {nombre!r}  (identidad de aplicacion: {'si' if es_app else 'NO'})")
    print(f"roles de negocio que el plugin le ve: {roles or 'ninguno'}")

    solicitud = solicitud_por_numero(dv, args.solicitud)
    filas = filas_de(dv, solicitud["sanic_mppp_tbl_solicitudid"])
    if not filas:
        salir("la solicitud no tiene filas")

    mostrar(dv, solicitud, filas, cache)
    if not args.accion:
        print("\n(solo lectura: no se toco nada. Pasa una accion para aplicar: "
              f"{', '.join(sorted(ACCIONES))})")
        return

    conf = ACCIONES[args.accion]
    if conf["motivo"] and not (args.motivo or "").strip():
        salir(f"'{args.accion}' exige --motivo: la transicion lo pide (RequiereMensaje) y sin el "
              "el plugin la rechaza igual, pero despues de escribir al servidor.")

    if not es_app:
        print(f"\n  OJO: esta corriendo con '{nombre}', que NO es identidad de aplicacion. "
              "El sentido de esta herramienta es actuar como OTRO que la persona de la app.")

    if conf["rol"].split(" (")[0] not in roles:
        salir(f"'{args.accion}' necesita el rol {conf['rol']!r} y '{nombre}' no lo tiene.\n"
              f"  Asignaselo en el admin center. OJO: el plugin exige EXACTAMENTE UN rol de negocio "
              f"(EsSoloEsteRol), asi que si ya tuviera otro de {ROLES_DE_NEGOCIO} habria que quitarlo.")

    if args.fila:
        pedidas = {int(n) for n in args.fila.replace(" ", "").split(",") if n}
        elegidas = [f for f in filas if f.get("sanic_numerofila") in pedidas]
        faltan = pedidas - {f.get("sanic_numerofila") for f in elegidas}
        if faltan:
            salir(f"la solicitud no tiene la(s) fila(s) {sorted(faltan)}")
    else:
        elegidas = filas

    aplicables = [f for f in elegidas if f.get("sanic_estado") in conf["desde"]]
    descartadas = [f for f in elegidas if f not in aplicables]
    if descartadas:
        print(f"\nse saltean {len(descartadas)} fila(s) que no estan en un estado de origen valido "
              f"({', '.join(NOMBRE_ESTADO[e] for e in conf['desde'])}):")
        for f in descartadas:
            print(f"   fila {f.get('sanic_numerofila')}: esta en "
                  f"{NOMBRE_ESTADO.get(f.get('sanic_estado'), f.get('sanic_estado'))}")
    if not aplicables:
        salir("no queda ninguna fila a la que aplicarle la accion.")

    aplicar(dv, args.accion, conf, aplicables, args.motivo)
    mostrar(dv, solicitud, filas_de(dv, solicitud["sanic_mppp_tbl_solicitudid"]), cache)


if __name__ == "__main__":
    main()
