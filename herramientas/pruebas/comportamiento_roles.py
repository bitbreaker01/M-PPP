#!/usr/bin/env python3
"""Ejercita la matriz de `diseno/04` §5 contra el ENTORNO, con usuarios reales.

**Por qué existe.** Las 800 pruebas de C# prueban la lógica de los steps con un doble
de `IOrganizationService` que no modela privilegios: devuelve lo que se le pide, venga
de quien venga. Por eso ninguna vio el defecto del 2026-09-23 — los plugins leían la
tabla Parametro con la identidad de quien llamaba, y ningún rol de negocio tiene lectura
ahí, así que **ninguna persona podía transicionar una fila**. Eso solo se ve contra la
plataforma y con un usuario de verdad.

`verificar_accesos.py` responde "¿qué privilegios TIENE cada uno?". Esta responde la otra
mitad: "¿qué puede HACER?". Las dos hacen falta: un privilegio correcto con un plugin que
falla da un usuario bloqueado, y un plugin correcto con un privilegio de más da un agujero.

**Cómo suplanta.** Cabecera `MSCRMCallerID`, que exige `prvActOnBehalfOfAnotherUser` en
quien llama. El plugin ve exactamente el mismo contexto que si la persona hubiera entrado
a la app: mismo `InitiatingUserId`, mismos roles, mismos privilegios.

**Qué escribe.** Por defecto, NADA: solo los casos de rechazo, donde el servidor frena
antes de tocar el registro. Con `--con-escritura` corre además el recorrido completo de
una fila (digitar → devolver → digitar → aprobar) sobre datos de prueba.

Uso:
    python3 herramientas/pruebas/comportamiento_roles.py
    python3 herramientas/pruebas/comportamiento_roles.py --con-escritura
    → sale con 0 si todos los casos dan lo esperado, 1 si alguno no.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataverse_api import Dataverse  # noqa: E402

# Los tres usuarios de prueba, por su nombre de inicio de sesión. Se resuelven al arrancar:
# un GUID escrito a mano en un script envejece sin avisar.
ALIAS = {"ejecutivo": "User1", "supervisor": "User2", "admin_planes": "User3"}

# Qué rol de MPPP tiene que tener cada uno para que esta suite signifique algo. Se comprueba al
# arrancar: el 2026-09-24 a `User1` le cambiaron el rol a Administrador de planes para probar otra
# cosa, y dos casos salieron en rojo con un `403` que parecía un defecto del producto. Un usuario
# de prueba con otro rol no es una falla: es una suite que ya no prueba lo que dice probar.
ROL_ESPERADO = {
    "ejecutivo": "SR - MPPP - Ejecutivo",
    "supervisor": "SR - MPPP - Supervisor",
    "admin_planes": "SR - MPPP - Administrador de planes",
}

FILA = "sanic_mppp_tbl_filas"
SOLICITUD = "sanic_mppp_tbl_solicituds"

VALIDADA, DIGITADA, APROBADA, ANULADA = 159460003, 159460004, 159460005, 159460007


class Entorno:
    def __init__(self):
        self.dv = Dataverse()
        self.usuarios = {}
        for papel, alias in ALIAS.items():
            e, b, _ = self.dv.call(
                "GET",
                "systemusers?$select=systemuserid,fullname,domainname"
                f"&$filter=startswith(domainname,'{alias}@') and applicationid eq null")
            filas = b.get("value", []) if e == 200 else []
            if len(filas) != 1:
                raise SystemExit(f"{alias!r} no identifica a un usuario único: {filas}")
            self.usuarios[papel] = filas[0]

        desalineados = []
        for papel, u in self.usuarios.items():
            e, b, _ = self.dv.call(
                "GET", f"systemusers({u['systemuserid']})/systemuserroles_association?$select=name")
            roles = [r["name"] for r in b.get("value", [])] if e == 200 else []
            if ROL_ESPERADO[papel] not in roles:
                desalineados.append(
                    f"  {ALIAS[papel]} tendría que tener {ROL_ESPERADO[papel]!r} y tiene {roles}")
        if desalineados:
            raise SystemExit(
                "Los usuarios de prueba no tienen los roles que esta suite asume:\n"
                + "\n".join(desalineados)
                + "\n\nNo se corre nada: con otros roles los casos dan 403 y parecen defectos del "
                  "producto cuando el problema son los datos de prueba. Devolvé los roles o "
                  "cambiá ALIAS/ROL_ESPERADO.")

        e, b, _ = self.dv.call("GET", "WhoAmI")
        ruta = (f"systemusers({b['UserId']})/Microsoft.Dynamics.CRM."
                'RetrieveUserSetOfPrivilegesByNames(PrivilegeNames=@p1)'
                '?@p1=["prvActOnBehalfOfAnotherUser"]')
        e, b, _ = self.dv.call("GET", ruta)
        if not b.get("RolePrivileges"):
            raise SystemExit(
                "Quien corre esto no puede suplantar usuarios (le falta prvActOnBehalfOfAnotherUser).\n"
                "Sin eso no hay forma de probar el comportamiento de cada rol sin la sesión de cada persona.")

    def como(self, papel, metodo, ruta, cuerpo=None):
        return self.dv.call(metodo, ruta, cuerpo,
                            cabeceras={"MSCRMCallerID": self.usuarios[papel]["systemuserid"]})

    def una_fila_en(self, estado):
        e, b, _ = self.dv.call(
            "GET",
            f"{FILA}?$select=sanic_mppp_tbl_filaid,sanic_nombre,sanic_numerocuenta"
            f"&$filter=sanic_estado eq {estado}&$top=1")
        filas = b.get("value", []) if e == 200 else []
        return filas[0] if filas else None

    def una_solicitud(self):
        e, b, _ = self.dv.call("GET", f"{SOLICITUD}?$select=sanic_mppp_tbl_solicitudid,sanic_nombre&$top=1")
        filas = b.get("value", []) if e == 200 else []
        return filas[0] if filas else None


class Tablero:
    """Acumula los resultados y decide el código de salida. Un caso que no se pudo correr
    (faltan datos de prueba) NO cuenta como aprobado: cuenta como no probado, y se ve."""

    def __init__(self):
        self.lineas = []
        self.malos = 0
        self.sin_probar = 0

    def caso(self, nombre, ok, detalle=""):
        self.lineas.append((("OK  " if ok else "FALLA"), nombre, detalle))
        if not ok:
            self.malos += 1

    def omitido(self, nombre, motivo):
        self.lineas.append(("—   ", nombre, motivo))
        self.sin_probar += 1

    def imprimir(self):
        for estado, nombre, detalle in self.lineas:
            print(f"  [{estado}] {nombre}")
            if detalle:
                print(f"           {detalle}")
        print(f"\n{len(self.lineas)} casos · {self.malos} fallas · {self.sin_probar} sin probar")


def recorte(cuerpo, largo=110):
    texto = (cuerpo or {}).get("error", "")
    return texto[:largo] + ("…" if len(texto) > largo else "")


def rechazos(ent, t):
    """Los casos donde el servidor tiene que decir que no. Ninguno escribe: si el control
    funciona, el registro ni se toca; y si NO funciona, el caso sale en rojo."""
    print("\nLo que cada rol NO tiene que poder — nada de esto escribe\n")

    # --- el administrador de planes no ve datos de gestiones (04 §2, el caso más importante)
    e, b, _ = ent.como("admin_planes", "GET", f"{FILA}?$select=sanic_numerofila&$top=1")
    t.caso("El administrador de planes no puede leer Filas", e in (401, 403),
           f"HTTP {e}" + (" · LEYÓ DATOS BANCARIOS QUE NO LE TOCAN" if e == 200 else ""))

    e, b, _ = ent.como("admin_planes", "GET", f"{SOLICITUD}?$select=sanic_nombre&$top=1")
    t.caso("El administrador de planes no puede leer Solicitudes", e in (401, 403),
           f"HTTP {e}" + (" · el Excel crudo del cliente está ahí" if e == 200 else ""))

    # --- la lista blanca de columnas (04 §1): el control que compensa que `W` sea por fila entera
    fila = ent.una_fila_en(VALIDADA) or ent.una_fila_en(DIGITADA) or ent.una_fila_en(APROBADA)
    if not fila:
        t.omitido("La lista blanca frena el cambio de cuenta", "no hay ninguna Fila en el entorno")
    else:
        fid = fila["sanic_mppp_tbl_filaid"]
        # Se manda el MISMO valor que ya tiene: si el control fallara, no cambia nada.
        e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({fid})",
                           {"sanic_numerocuenta": fila.get("sanic_numerocuenta")})
        t.caso("El ejecutivo no puede cambiar el número de cuenta",
               e == 400 and "sanic_numerocuenta" in recorte(b, 400), f"HTTP {e} · {recorte(b)}")

        # Regresión del 2026-09-23: las columnas de auditoría que agrega la plataforma no
        # se cuentan como intento de escritura. Si volviera el defecto, este caso lo canta.
        e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({fid})", {"sanic_mensaje": "prueba de lista blanca"})
        t.caso("Las columnas de auditoría de la plataforma no molestan",
               "modifiedby" not in recorte(b, 400), f"HTTP {e} · {recorte(b)}")

        e, b, _ = ent.como("ejecutivo", "DELETE", f"{FILA}({fid})")
        t.caso("Ningún rol humano puede borrar una Fila", e in (401, 403), f"HTTP {e}")

        e, b, _ = ent.como("admin_planes", "PATCH", f"{FILA}({fid})", {"sanic_estado": DIGITADA})
        t.caso("El administrador de planes no puede transicionar una Fila", e in (400, 401, 403),
               f"HTTP {e} · {recorte(b)}")

    solicitud = ent.una_solicitud()
    if not solicitud:
        t.omitido("Ningún rol humano puede borrar una Solicitud", "no hay ninguna Solicitud")
    else:
        e, b, _ = ent.como("supervisor", "DELETE", f"{SOLICITUD}({solicitud['sanic_mppp_tbl_solicitudid']})")
        t.caso("Ningún rol humano puede borrar una Solicitud", e in (401, 403), f"HTTP {e}")

    # --- quién hace cada transición (03 §4)
    validada = ent.una_fila_en(VALIDADA)
    if not validada:
        t.omitido("El supervisor no puede digitar", "no hay ninguna Fila en Validada")
        t.omitido("Anular exige un motivo", "no hay ninguna Fila en Validada")
    else:
        fid = validada["sanic_mppp_tbl_filaid"]
        e, b, _ = ent.como("supervisor", "PATCH", f"{FILA}({fid})", {"sanic_estado": DIGITADA})
        t.caso("El supervisor no puede digitar", e == 400 and "rol" in recorte(b, 400).lower(),
               f"HTTP {e} · {recorte(b)}")

        e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({fid})", {"sanic_estado": ANULADA})
        t.caso("Anular exige un motivo", e == 400 and "mensaje" in recorte(b, 400).lower(),
               f"HTTP {e} · {recorte(b)}")

    # "El ejecutivo no puede aprobar" NO se prueba acá a propósito: necesita una fila en Digitada,
    # que solo existe si alguien digitó antes. Lo cubre el recorrido completo, y mejor, porque ahí
    # la fila la digitó el propio ejecutivo y se prueban las dos cosas a la vez: el rol y la
    # segregación de funciones.


def recorrido_completo(ent, t):
    """Digitar → devolver → digitar → aprobar, sobre una fila de prueba. Es el único camino
    que prueba la segregación de funciones de verdad: que el sistema RECUERDE quién digitó."""
    print("\nEl recorrido completo de una fila — esto SÍ escribe, sobre datos de prueba\n")

    # Hacen falta DOS filas: una termina Aprobada y la otra se usa para la devolución. Con una
    # sola, el caso de la devolución quedaba sin probar porque el de la aprobación ya la cerró.
    e, b, _ = ent.dv.call(
        "GET",
        f"{FILA}?$select=sanic_mppp_tbl_filaid,sanic_nombre&$filter=sanic_estado eq {VALIDADA}&$top=2")
    disponibles = b.get("value", []) if e == 200 else []
    if len(disponibles) < 2:
        t.omitido("Recorrido completo de una fila",
                  f"hacen falta 2 Filas en Validada y hay {len(disponibles)}")
        return
    aprobar, devolver = disponibles[0], disponibles[1]
    print(f"  para aprobar: {aprobar['sanic_nombre']}   ·   para devolver: {devolver['sanic_nombre']}\n")

    # --- camino 1: digitar y aprobar, con la segregación en el medio
    fid = aprobar["sanic_mppp_tbl_filaid"]
    e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({fid})", {"sanic_estado": DIGITADA})
    t.caso("El ejecutivo digita", e == 204, f"HTTP {e} · {recorte(b)}")
    if e != 204:
        return  # sin esto, todo lo que sigue mide otra cosa

    e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({fid})", {"sanic_estado": APROBADA})
    t.caso("El ejecutivo no puede aprobar lo que él mismo digitó",
           e == 400, f"HTTP {e} · {recorte(b)}")

    e, b, _ = ent.como("supervisor", "PATCH", f"{FILA}({fid})", {"sanic_estado": APROBADA})
    t.caso("El supervisor puede aprobar lo que digitó OTRO", e == 204, f"HTTP {e} · {recorte(b)}")

    e, b, _ = ent.dv.call(
        "GET",
        f"{FILA}({fid})?$select=sanic_estado&$expand=sanic_digitadapor($select=systemuserid),"
        "sanic_aprobadapor($select=systemuserid)")
    digito = (b.get("sanic_digitadapor") or {}).get("systemuserid")
    aprobo = (b.get("sanic_aprobadapor") or {}).get("systemuserid")
    t.caso("Quedó registrado quién digitó y quién aprobó, y son DISTINTOS",
           bool(digito) and bool(aprobo) and digito != aprobo,
           f"digitó={digito} · aprobó={aprobo}")

    # --- camino 2: digitar y devolver. Al devolver, el sistema OLVIDA quién digitó, para que
    # la segregación se vuelva a exigir entera en la próxima vuelta (03 §4).
    oid = devolver["sanic_mppp_tbl_filaid"]
    e, b, _ = ent.como("ejecutivo", "PATCH", f"{FILA}({oid})", {"sanic_estado": DIGITADA})
    if e != 204:
        t.caso("El ejecutivo digita la segunda fila", False, f"HTTP {e} · {recorte(b)}")
        return

    e, b, _ = ent.como("supervisor", "PATCH", f"{FILA}({oid})", {"sanic_estado": VALIDADA})
    t.caso("Devolver sin motivo se rechaza", e == 400 and "mensaje" in recorte(b, 400).lower(),
           f"HTTP {e} · {recorte(b)}")

    e, b, _ = ent.como("supervisor", "PATCH", f"{FILA}({oid})",
                       {"sanic_estado": VALIDADA, "sanic_mensaje": "Prueba automatizada: devuelta"})
    t.caso("El supervisor devuelve con motivo", e == 204, f"HTTP {e} · {recorte(b)}")

    e, b, _ = ent.dv.call("GET", f"{FILA}({oid})?$select=sanic_estado,_sanic_digitadapor_value")
    t.caso("Al devolver se olvida quién digitó",
           b.get("sanic_estado") == VALIDADA and b.get("_sanic_digitadapor_value") is None,
           f"estado={b.get('sanic_estado')} · digitadapor={b.get('_sanic_digitadapor_value')}")


def main():
    con_escritura = "--con-escritura" in sys.argv
    ent = Entorno()
    t = Tablero()

    print("=" * 78)
    for papel, u in ent.usuarios.items():
        print(f"  {papel:14} {u['fullname']} · {u['domainname']}")
    print("=" * 78)

    rechazos(ent, t)
    if con_escritura:
        recorrido_completo(ent, t)
    else:
        print("\n(El recorrido completo no corrió: agregá --con-escritura. Escribe sobre datos de prueba.)")

    print()
    t.imprimir()
    return 1 if t.malos else 0


if __name__ == "__main__":
    sys.exit(main())
