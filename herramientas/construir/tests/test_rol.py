"""Herramienta `rol.py`: un security role, desde un playbook. Ninguna prueba
toca la red."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import rol as rl  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents, es_ruta_solutions, playbook_md  # noqa: E402

BORRAR = object()
IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="rol", inventario="6.2")
BU, ID_ROL, ID_BASE = "b" * 8 + "-0000-0000-0000-000000000001", "a" * 8 + "-0000-0000-0000-000000000002", "c" * 8 + "-0000-0000-0000-000000000003"
T1, T2 = "sanic_mppp_tbl_cliente", "sanic_mppp_tbl_fila"
BASE = {"tipo": "rol", "nombre": "SR - MPPP - Ejecutivo", "descripcion": "Gestiona las filas de sus clientes.", "base": "App Opener",
        "tablas": {T1: {"leer": "organizacion"}, T2: {"leer": "organizacion", "escribir": "organizacion", "anexar": "usuario"}},
        "otros_privilegios": {"prvBulkDelete": "organizacion"}}
PRIVS_BASE = [("prvReadAppModule", "Global"), ("prvReadUserSettings", "Basic")]
ACCIONES = ["Create", "Read", "Write", "Delete", "Assign", "Share", "Append", "AppendTo"]


def con_cambio(obj, ruta, valor):
    n = copy.deepcopy(obj)
    nodo = n
    for p in ruta[:-1]:
        nodo = nodo[p]
    if valor is BORRAR:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    return n


def pid(nombre):
    return f"id-{nombre}"


def privilegios_de_tabla(tabla, **cambios):
    return [dict({"Name": f"prv{a}{tabla}", "PrivilegeId": pid(f"prv{a}{tabla}"), "PrivilegeType": a,
                  "CanBeBasic": True, "CanBeLocal": True, "CanBeDeep": True, "CanBeGlobal": True}, **cambios) for a in ACCIONES]


def rp(nombre, depth):
    return {"PrivilegeId": pid(nombre), "PrivilegeName": nombre, "Depth": depth, "BusinessUnitId": BU, "RecordFilterId": None, "RecordFilterUniqueName": None}


def esperados(d):
    e = dict(PRIVS_BASE)
    for t, acciones in d["tablas"].items():
        for a, alcance in acciones.items():
            e[f"prv{rl.ACCIONES[a]}{t}"] = rl.ALCANCES[alcance]
    for n, alcance in d["otros_privilegios"].items():
        e[n] = rl.ALCANCES[alcance]
    return e


def fila_rol(d, **cambios):
    return dict({"roleid": ID_ROL, "name": d["nombre"], "description": d["descripcion"], "ismanaged": False}, **cambios)


def armar(cliente, d, existe=True, rol=None, privilegios=None, componentes=None, bus=None, bases=None, tablas=None, otros=None):
    """Configura TODAS las rutas del camino feliz."""
    armar_cliente_precondiciones_ok(cliente, IDENT)
    st = {"existe": existe, "privs": None if privilegios is None else list(privilegios)}
    cliente.responder("GET", lambda r: r.startswith("businessunits?"), (200, {"value": bus if bus is not None else [{"businessunitid": BU}]}, {}))
    cliente.responder("GET", lambda r: r.startswith("roles?") and f"'{d['base']}'" in r,
                      (200, {"value": bases if bases is not None else [{"roleid": ID_BASE, "name": d["base"]}]}, {}))
    cliente.responder("GET", lambda r: r.startswith("roles?"), lambda *_: (200, {"value": [rol or fila_rol(d)] if st["existe"] else []}, {}))
    cliente.responder("GET", f"RetrieveRolePrivilegesRole(RoleId={ID_BASE})", (200, {"RolePrivileges": [rp(n, x) for n, x in PRIVS_BASE]}, {}))

    def privs(*_):
        actuales = st["privs"] if st["privs"] is not None else [rp(n, x) for n, x in esperados(d).items()]
        return (200, {"RolePrivileges": actuales}, {})

    cliente.responder("GET", f"RetrieveRolePrivilegesRole(RoleId={ID_ROL})", privs)
    for t in d["tablas"]:
        cuerpo = (tablas or {}).get(t, {"LogicalName": t, "Privileges": privilegios_de_tabla(t)})
        cliente.responder("GET", f"EntityDefinitions(LogicalName='{t}')?$select=LogicalName,Privileges", (404, {"error": "x"}, {}) if cuerpo is None else (200, cuerpo, {}))
    for n in d["otros_privilegios"]:
        fila = (otros or {}).get(n, {"privilegeid": pid(n), "name": n, "canbebasic": False, "canbelocal": False, "canbedeep": False, "canbeglobal": True})
        cliente.responder("GET", lambda r, n=n: r.startswith("privileges?") and f"'{n}'" in r, (200, {"value": [] if fila is None else [fila]}, {}))
    cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": componentes if componentes is not None else [{"solutioncomponentid": "x"}]}, {}))

    def al_crear(*_):
        st["existe"] = True
        if st["privs"] is None:
            st["privs"] = [rp("prvReadAppModule", "Global")]  # nace con algunos privilegios propios
        return (204, None, {})

    def al_agregar(ruta, cuerpo, solucion):
        por_id = {pid(n): n for n in esperados(d)}
        actuales = {p["PrivilegeName"]: p for p in (st["privs"] or [])}
        for p in cuerpo["Privileges"]:
            actuales[por_id[p["PrivilegeId"]]] = rp(por_id[p["PrivilegeId"]], p["Depth"])
        st["privs"] = list(actuales.values())
        return (204, None, {})

    cliente.responder("POST", "roles", al_crear)
    cliente.responder("POST", f"roles({ID_ROL})/Microsoft.Dynamics.CRM.AddPrivilegesRole", al_agregar)
    return cliente


class Base(unittest.TestCase):
    def correr(self, fabrica, datos, **kw):
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "playbook.md")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(playbook_md(IDENT, datos))
            return rl.construir(ruta, kw.pop("solo_verificar", False), fabrica, **kw)

    def con_cliente(self, cliente, datos, **kw):
        return self.correr(lambda: cliente, datos, **kw)


class ValidacionSinRed(Base):
    CASOS = [
        (["tipo"], "tabla", "tipo"),
        (["nombre"], "Ejecutivo", "SR - MPPP - "),
        (["nombre"], "SR - MPPP - " + "x" * 100, "100"),
        (["descripcion"], "", "descripcion"),
        (["base"], "", "base"),
        (["tablas"], [], "tablas"),
        (["tablas"], {"cliente": {"leer": "organizacion"}}, "cliente"),
        (["tablas", T1], {}, T1),
        (["tablas", T1], {"mirar": "organizacion"}, "mirar"),
        (["tablas", T1], {"leer": "global"}, "global"),
        (["tablas", T1], {"leer": 8}, "leer"),
        (["otros_privilegios"], [], "otros_privilegios"),
        (["otros_privilegios"], {"BulkDelete": "organizacion"}, "BulkDelete"),
        (["otros_privilegios"], {"prvBulkDelete": "todo"}, "todo"),
        (["otros_privilegios"], {f"prvRead{T1}": "organizacion"}, "tablas"),
        (["sobra"], 1, "sobra"),
        (["base"], BORRAR, "base"),
    ]

    def test_cada_dato_invalido_es_error_nombra_la_clave_y_no_toca_la_red(self):
        for ruta, valor, esperado in self.CASOS:
            with self.subTest(f"{ruta} <- {'BORRAR' if valor is BORRAR else repr(valor)[:40]}"):
                centinela = FabricaCentinela()
                estado, _, detalle = self.correr(centinela, con_cambio(BASE, ruta, valor))
                self.assertEqual(estado, "error", detalle)
                self.assertIn(esperado, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(centinela.llamada)

    def test_un_rol_sin_tablas_ni_otros_privilegios_no_tiene_sentido(self):
        estado, _, detalle = self.correr(FabricaCentinela(), dict(BASE, tablas={}, otros_privilegios={}))
        self.assertEqual(estado, "error")
        self.assertIn("ningún privilegio", detalle)


class Precondiciones(Base):
    def bloquea(self, esperado, datos=BASE, **kw):
        cliente = armar(ClienteSimulado(), datos, existe=False, **kw)
        estado, _, detalle = self.con_cliente(cliente, datos)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn(esperado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_rol_base_no_existe(self):
        self.bloquea("App Opener", bases=[])

    def test_la_tabla_no_existe(self):
        self.bloquea(T2, tablas={T2: None})

    def test_el_privilegio_suelto_no_existe(self):
        self.bloquea("prvBulkDelete", otros={"prvBulkDelete": None})

    def test_un_alcance_que_el_privilegio_no_admite(self):
        self.bloquea("prvBulkDelete", datos=con_cambio(BASE, ["otros_privilegios", "prvBulkDelete"], "usuario"))
        self.bloquea(f"prvRead{T1}", tablas={T1: {"LogicalName": T1, "Privileges": privilegios_de_tabla(T1, CanBeGlobal=False)}})

    def test_mas_de_una_unidad_de_negocio_raiz_es_error_no_bloqueo(self):
        cliente = armar(ClienteSimulado(), BASE, bus=[{"businessunitid": BU}, {"businessunitid": "otra"}])
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("businessunits", detalle)


class Caminos(Base):
    def test_se_crea_con_los_privilegios_de_la_base_mas_los_del_playbook(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, comp, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual(comp, BASE["nombre"])
        self.assertIn(ID_ROL, detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["ruta"] for p in posts], ["roles", f"roles({ID_ROL})/Microsoft.Dynamics.CRM.AddPrivilegesRole"])
        self.assertEqual([p["solucion"] for p in posts], [IDENT["solucion"]] * 2)
        self.assertEqual(posts[0]["cuerpo"], {"name": BASE["nombre"], "description": BASE["descripcion"], "businessunitid@odata.bind": f"/businessunits({BU})"})
        enviados = {p["PrivilegeId"]: p["Depth"] for p in posts[1]["cuerpo"]["Privileges"]}
        self.assertEqual(enviados, {pid(n): x for n, x in esperados(BASE).items()})

    def test_el_playbook_gana_a_la_base_si_nombran_el_mismo_privilegio(self):
        d = con_cambio(BASE, ["otros_privilegios"], {"prvReadUserSettings": "organizacion"})
        cliente = armar(ClienteSimulado(), d, existe=False, otros={"prvReadUserSettings": {"privilegeid": pid("prvReadUserSettings"), "name": "prvReadUserSettings",
                                                                                         "canbebasic": True, "canbelocal": True, "canbedeep": True, "canbeglobal": True}})
        estado, _, detalle = self.con_cliente(cliente, d)
        self.assertEqual(estado, "creado", detalle)
        agregar = [l for l in cliente.llamadas if l["ruta"].endswith("AddPrivilegesRole")][0]
        self.assertEqual({p["PrivilegeId"]: p["Depth"] for p in agregar["cuerpo"]["Privileges"]}[pid("prvReadUserSettings")], "Global")

    def test_ya_existia_no_escribe(self):
        cliente = armar(ClienteSimulado(), BASE)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn(ID_ROL, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_sin_rol_es_error_y_no_crea(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_creacion_falla(self):
        for ruta, texto in (("roles", "la creación falló"), (f"roles({ID_ROL})/Microsoft.Dynamics.CRM.AddPrivilegesRole", "--completar")):
            with self.subTest(ruta):
                cliente = ClienteSimulado()
                cliente.responder("POST", ruta, (400, {"error": "boom"}, {}))
                armar(cliente, BASE, existe=False)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error")
                self.assertIn("HTTP 400", detalle)
                self.assertIn(texto, detalle)

    def test_dos_roles_con_el_mismo_nombre_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", lambda r: r.startswith("roles?") and "Ejecutivo" in r, (200, {"value": [fila_rol(BASE), fila_rol(BASE, roleid="otro")]}, {}))
        armar(cliente, BASE)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("2", detalle)

    def test_un_nombre_con_apostrofo_se_escapa_en_la_consulta(self):
        d = dict(BASE, nombre="SR - MPPP - Ejecutivo d'Or")
        cliente = armar(ClienteSimulado(), d)
        self.con_cliente(cliente, d)
        self.assertTrue([l for l in cliente.llamadas if "d''Or" in l["ruta"]])


class Diferencias(Base):
    def test_cada_diferencia(self):
        e = esperados(BASE)
        completos = [rp(n, x) for n, x in e.items()]
        sin_uno = [p for p in completos if p["PrivilegeName"] != f"prvWrite{T2}"]
        otro_alcance = [rp(n, "Basic" if n == f"prvRead{T1}" else x) for n, x in e.items()]
        casos = [(f"falta prvWrite{T2}", dict(privilegios=sin_uno)),
                 (f"prvRead{T1}: entorno='Basic' playbook='Global'", dict(privilegios=otro_alcance)),
                 (f"sobra prvDelete{T1}", dict(privilegios=completos + [rp(f"prvDelete{T1}", "Global")])),
                 ("sobra prvCreateAccount", dict(privilegios=completos + [rp("prvCreateAccount", "Basic")])),
                 ("description", dict(rol=fila_rol(BASE, description="Otra"))),
                 ("ismanaged", dict(rol=fila_rol(BASE, ismanaged=True))),
                 ("pertenencia a la solución", dict(componentes=[]))]
        for esperado, kw in casos:
            with self.subTest(esperado):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "difiere", detalle)
                self.assertIn(esperado, detalle)
                self.assertFalse(cliente.hubo_escritura())


class Completar(Base):
    def setUp(self):
        e = esperados(BASE)
        self.sin_uno = [rp(n, x) for n, x in e.items() if n != f"prvWrite{T2}"]

    def test_agrega_solo_lo_que_falta(self):
        cliente = armar(ClienteSimulado(), BASE, privilegios=self.sin_uno)
        estado, _, detalle = self.con_cliente(cliente, BASE, completar=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("se agregaron", detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["cuerpo"], {"Privileges": [{"PrivilegeId": pid(f"prvWrite{T2}"), "Depth": "Global"}]})

    def test_no_toca_nada_si_ademas_hay_otra_diferencia(self):
        for extra in ([rp("prvCreateAccount", "Basic")], None):
            privs = self.sin_uno + (extra or [])
            if extra is None:
                privs = [rp(p["PrivilegeName"], "Basic" if p["PrivilegeName"] == f"prvRead{T1}" else p["Depth"]) for p in privs]
            cliente = armar(ClienteSimulado(), BASE, privilegios=privs)
            estado, _, detalle = self.con_cliente(cliente, BASE, completar=True)
            self.assertEqual(estado, "difiere", detalle)
            self.assertFalse(cliente.hubo_escritura())

    def test_con_solo_verificar_no_escribe(self):
        cliente = armar(ClienteSimulado(), BASE, privilegios=self.sin_uno)
        estado, _, _ = self.con_cliente(cliente, BASE, completar=True, solo_verificar=True)
        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())


class RenombrarDesde(Base):
    """Un rol no tiene nombre lógico: se busca por su nombre visible. Para
    cambiárselo hay que decir cómo se llamaba. Ensayado el 2026-09-21: PATCH roles(<id>)."""
    VIEJO = "SR - MPPP - Ejecutivo viéjo"

    def armar(self, viejo_existe=True, nuevo_existe=False, privilegios=None):
        st = {"renombrado": nuevo_existe}
        cliente = ClienteSimulado()
        cliente.responder("GET", lambda r: r.startswith("roles?") and "vi" in r and "jo'" in r,
                          lambda *_: (200, {"value": [fila_rol(BASE, name=self.VIEJO)] if viejo_existe and not st["renombrado"] else []}, {}))
        cliente.responder("GET", lambda r: r.startswith("roles?") and f"'{BASE['nombre']}'" in r, lambda *_: (200, {"value": [fila_rol(BASE)] if st["renombrado"] else []}, {}))

        def al_renombrar(ruta, cuerpo, solucion):
            st["renombrado"] = True
            return (204, None, {})

        cliente.responder("PATCH", f"roles({ID_ROL})", al_renombrar)
        return armar(cliente, BASE, privilegios=privilegios)

    def test_renombra_si_el_viejo_coincide_en_todo_lo_demas(self):
        cliente = self.armar()
        estado, _, detalle = self.con_cliente(cliente, BASE, renombrar_desde=self.VIEJO)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("se renombró", detalle)
        escrituras = [l for l in cliente.llamadas if l["metodo"] != "GET"]
        self.assertEqual([(l["metodo"], l["ruta"], l["cuerpo"], l["solucion"]) for l in escrituras], [("PATCH", f"roles({ID_ROL})", {"name": BASE["nombre"]}, IDENT["solucion"])])

    def test_no_renombra_si_el_viejo_difiere_en_algo_mas(self):
        sin_uno = [rp(n, x) for n, x in esperados(BASE).items() if n != f"prvWrite{T2}"]
        cliente = self.armar(privilegios=sin_uno)
        estado, _, detalle = self.con_cliente(cliente, BASE, renombrar_desde=self.VIEJO)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn(f"falta prvWrite{T2}", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_si_el_nuevo_ya_existe_no_toca_nada(self):
        cliente = self.armar(nuevo_existe=True)
        estado, _, detalle = self.con_cliente(cliente, BASE, renombrar_desde=self.VIEJO)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_si_no_existe_ninguno_de_los_dos_es_bloqueado_y_no_crea(self):
        cliente = self.armar(viejo_existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE, renombrar_desde=self.VIEJO)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn(self.VIEJO, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_con_solo_verificar_no_renombra(self):
        cliente = self.armar()
        estado, _, _ = self.con_cliente(cliente, BASE, renombrar_desde=self.VIEJO, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertFalse(cliente.hubo_escritura())


class FormaYHttpInesperados(Base):
    def test_http_inesperado_es_error_y_nombra_la_consulta(self):
        for matcher, nombre in [(lambda r: r.startswith("businessunits?"), "businessunits"), (lambda r: r.startswith("roles?") and "App Opener" in r, "rol base"),
                                (lambda r: r.startswith("roles?") and "Ejecutivo" in r, "GET roles"), (lambda r: ID_BASE in r, "privilegios del rol base"),
                                (lambda r: ID_ROL in r, "privilegios del rol"), (lambda r: r.startswith("EntityDefinitions("), "EntityDefinitions"),
                                (lambda r: r.startswith("privileges?"), "privileges"), (es_ruta_solutioncomponents, "solutioncomponents"), (es_ruta_solutions, "solutions")]:
            with self.subTest(nombre):
                cliente = ClienteSimulado()
                cliente.responder("GET", matcher, (500, {"error": "boom"}, {}))
                armar(cliente, BASE)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("HTTP 500", detalle)
                self.assertIn(nombre, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_forma_inesperada_es_error_y_nombra_el_campo(self):
        completos = [rp(n, x) for n, x in esperados(BASE).items()]
        casos = [("value[0].businessunitid", dict(bus=[{"businessunitid": None}])),
                 ("value[0].roleid", dict(bases=[{"roleid": 5}])),
                 ("value[0].roleid", dict(rol=fila_rol(BASE, roleid=None))),
                 ("value[0].ismanaged", dict(rol=fila_rol(BASE, ismanaged="no"))),
                 ("RolePrivileges[0].Depth", dict(privilegios=[con_cambio(completos[0], ["Depth"], 3)] + completos[1:])),
                 ("RolePrivileges[0].PrivilegeName", dict(privilegios=[con_cambio(completos[0], ["PrivilegeName"], None)] + completos[1:])),
                 ("Privileges[1].PrivilegeId", dict(tablas={T1: {"LogicalName": T1, "Privileges": [con_cambio(p, ["PrivilegeId"], None) if i == 1 else p for i, p in enumerate(privilegios_de_tabla(T1))]}})),
                 ("Privileges[1].CanBeGlobal", dict(tablas={T1: {"LogicalName": T1, "Privileges": [con_cambio(p, ["CanBeGlobal"], "si") if i == 1 else p for i, p in enumerate(privilegios_de_tabla(T1))]}})),
                 ("value[0].canbeglobal", dict(otros={"prvBulkDelete": {"privilegeid": pid("prvBulkDelete"), "name": "prvBulkDelete", "canbebasic": False, "canbelocal": False, "canbedeep": False, "canbeglobal": 1}}))]
        for campo, kw in casos:
            with self.subTest(campo + str(list(kw))):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("forma inesperada", detalle)
                self.assertIn(f"'{campo}'", detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())


if __name__ == "__main__":
    unittest.main()
