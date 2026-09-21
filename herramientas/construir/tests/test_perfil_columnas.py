"""Herramienta `perfil_columnas.py`: un column security profile con sus
permisos, desde un playbook. Ninguna prueba toca la red."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import perfil_columnas as pc  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents, es_ruta_solutions, playbook_md  # noqa: E402

BORRAR = object()
IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="perfil-columnas", inventario="6.1")
ID_PERFIL, T = "d" * 8 + "-0000-0000-0000-000000000004", "sanic_mppp_tbl_fila"
BASE = {"tipo": "perfil-columnas", "nombre": "CSP - MPPP - Datos sensibles", "descripcion": "Lectura de cuenta e identificación.",
        "permisos": [{"tabla": T, "columna": "sanic_numerocuenta", "leer": True, "crear": False, "actualizar": False},
                     {"tabla": T, "columna": "sanic_numeroidentificacion", "leer": True, "crear": True, "actualizar": False}]}
COLUMNAS = [{"LogicalName": "sanic_numerocuenta", "IsSecured": True}, {"LogicalName": "sanic_numeroidentificacion", "IsSecured": True}, {"LogicalName": "sanic_estado", "IsSecured": False}]


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


def fp(p, **cambios):
    si = lambda b: 4 if b else 0  # noqa: E731
    return dict({"fieldpermissionid": "fp-" + p["columna"], "entityname": p["tabla"], "attributelogicalname": p["columna"],
                 "canread": si(p["leer"]), "cancreate": si(p["crear"]), "canupdate": si(p["actualizar"]), "canreadunmasked": 0}, **cambios)


def fila_perfil(d, **cambios):
    return dict({"fieldsecurityprofileid": ID_PERFIL, "name": d["nombre"], "description": d["descripcion"], "ismanaged": False}, **cambios)


def armar(cliente, d, existe=True, perfil=None, permisos=None, componentes=None, columnas=None, tabla_existe=True):
    """Configura TODAS las rutas del camino feliz."""
    armar_cliente_precondiciones_ok(cliente, IDENT)
    st = {"existe": existe, "permisos": None if permisos is None else list(permisos)}
    cliente.responder("GET", lambda r: r.startswith("EntityDefinitions(") and "/Attributes?" in r,
                      (200, {"value": columnas if columnas is not None else COLUMNAS}, {}) if tabla_existe else (404, {"error": "x"}, {}))
    cliente.responder("GET", lambda r: r.startswith("fieldsecurityprofiles?"), lambda *_: (200, {"value": [perfil or fila_perfil(d)] if st["existe"] else []}, {}))
    cliente.responder("GET", lambda r: r.startswith("fieldpermissions?"),
                      lambda *_: (200, {"value": st["permisos"] if st["permisos"] is not None else [fp(p) for p in d["permisos"]]}, {}))
    cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": componentes if componentes is not None else [{"solutioncomponentid": "x"}]}, {}))

    def al_crear(*_):
        st["existe"] = True
        if st["permisos"] is None:
            st["permisos"] = []
        return (204, None, {})

    def al_permitir(ruta, cuerpo, solucion):
        st["permisos"].append({"fieldpermissionid": "nuevo", "entityname": cuerpo["entityname"], "attributelogicalname": cuerpo["attributelogicalname"],
                               "canread": cuerpo["canread"], "cancreate": cuerpo["cancreate"], "canupdate": cuerpo["canupdate"], "canreadunmasked": cuerpo["canreadunmasked"]})
        return (204, None, {})

    cliente.responder("POST", "fieldsecurityprofiles", al_crear)
    cliente.responder("POST", "fieldpermissions", al_permitir)
    return cliente


class Base(unittest.TestCase):
    def correr(self, fabrica, datos, **kw):
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "playbook.md")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(playbook_md(IDENT, datos))
            return pc.construir(ruta, kw.pop("solo_verificar", False), fabrica, **kw)

    def con_cliente(self, cliente, datos, **kw):
        return self.correr(lambda: cliente, datos, **kw)


class ValidacionSinRed(Base):
    CASOS = [
        (["tipo"], "rol", "tipo"),
        (["nombre"], "Datos sensibles", "CSP - MPPP - "),
        (["descripcion"], "", "descripcion"),
        (["permisos"], [], "permisos"),
        (["permisos"], {}, "permisos"),
        (["permisos", 0], "sanic_numerocuenta", "permisos[0]"),
        (["permisos", 0, "tabla"], "fila", "permisos[0].tabla"),
        (["permisos", 0, "columna"], "sanic_NumeroCuenta", "permisos[0].columna"),
        (["permisos", 0, "leer"], 4, "permisos[0].leer"),
        (["permisos", 0, "leer"], False, "ningún permiso"),
        (["permisos", 0, "sobra"], 1, "sobra"),
        (["permisos", 0, "crear"], BORRAR, "crear"),
        (["permisos", 1, "columna"], "sanic_numerocuenta", "repetida"),
        (["sobra"], 1, "sobra"),
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


class Precondiciones(Base):
    def bloquea(self, esperado, datos=BASE, **kw):
        cliente = armar(ClienteSimulado(), datos, existe=False, **kw)
        estado, _, detalle = self.con_cliente(cliente, datos)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn(esperado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_tabla_no_existe(self):
        self.bloquea(T, tabla_existe=False)

    def test_la_columna_no_existe(self):
        self.bloquea("sanic_inexistente", datos=con_cambio(BASE, ["permisos", 0, "columna"], "sanic_inexistente"))

    def test_la_columna_no_tiene_seguridad_de_columna(self):
        """Visto el 2026-09-21: la plataforma responde 400 si la columna no está protegida."""
        self.bloquea("sanic_estado", datos=con_cambio(BASE, ["permisos", 0, "columna"], "sanic_estado"))


class Caminos(Base):
    def test_se_crea_el_perfil_y_despues_un_permiso_por_columna(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, comp, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual(comp, BASE["nombre"])
        self.assertIn(ID_PERFIL, detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["ruta"] for p in posts], ["fieldsecurityprofiles", "fieldpermissions", "fieldpermissions"])
        self.assertEqual([p["solucion"] for p in posts], [IDENT["solucion"]] * 3)
        self.assertEqual(posts[0]["cuerpo"], {"name": BASE["nombre"], "description": BASE["descripcion"]})
        self.assertEqual(posts[2]["cuerpo"], {"entityname": T, "attributelogicalname": "sanic_numeroidentificacion", "canread": 4, "cancreate": 4, "canupdate": 0,
                                              "canreadunmasked": 0, "fieldsecurityprofileid@odata.bind": f"/fieldsecurityprofiles({ID_PERFIL})"})

    def test_ya_existia_no_escribe(self):
        cliente = armar(ClienteSimulado(), BASE)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_sin_perfil_es_error_y_no_crea(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_creacion_falla(self):
        for ruta, texto in (("fieldsecurityprofiles", "la creación falló"), ("fieldpermissions", "--completar")):
            with self.subTest(ruta):
                cliente = ClienteSimulado()
                cliente.responder("POST", ruta, (400, {"error": "boom"}, {}))
                armar(cliente, BASE, existe=False)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error")
                self.assertIn("HTTP 400", detalle)
                self.assertIn(texto, detalle)

    def test_dos_perfiles_con_el_mismo_nombre_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", lambda r: r.startswith("fieldsecurityprofiles?"), (200, {"value": [fila_perfil(BASE), fila_perfil(BASE, fieldsecurityprofileid="otro")]}, {}))
        armar(cliente, BASE)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("2", detalle)


class Diferencias(Base):
    def test_cada_diferencia(self):
        p0, p1 = BASE["permisos"]
        casos = [("falta el permiso sobre sanic_mppp_tbl_fila.sanic_numeroidentificacion", dict(permisos=[fp(p0)])),
                 ("sanic_numerocuenta.canupdate: entorno=4 playbook=0", dict(permisos=[fp(p0, canupdate=4), fp(p1)])),
                 ("sanic_numerocuenta.canreadunmasked: entorno=3 playbook=0", dict(permisos=[fp(p0, canreadunmasked=3), fp(p1)])),
                 ("sobra el permiso sobre sanic_mppp_tbl_fila.sanic_otra", dict(permisos=[fp(p0), fp(p1), fp(dict(p0, columna="sanic_otra"))])),
                 ("description", dict(perfil=fila_perfil(BASE, description="Otra"))),
                 ("ismanaged", dict(perfil=fila_perfil(BASE, ismanaged=True))),
                 ("pertenencia a la solución", dict(componentes=[]))]
        for esperado, kw in casos:
            with self.subTest(esperado):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "difiere", detalle)
                self.assertIn(esperado, detalle)
                self.assertFalse(cliente.hubo_escritura())


class Completar(Base):
    def test_agrega_solo_el_permiso_que_falta(self):
        cliente = armar(ClienteSimulado(), BASE, permisos=[fp(BASE["permisos"][0])])
        estado, _, detalle = self.con_cliente(cliente, BASE, completar=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("se agregaron", detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["cuerpo"]["attributelogicalname"] for p in posts], ["sanic_numeroidentificacion"])

    def test_no_toca_nada_si_ademas_hay_otra_diferencia_ni_con_solo_verificar(self):
        p0 = BASE["permisos"][0]
        for kw_armar, kw_correr in ((dict(permisos=[fp(p0, canupdate=4)]), dict(completar=True)), (dict(permisos=[fp(p0)]), dict(completar=True, solo_verificar=True))):
            cliente = armar(ClienteSimulado(), BASE, **kw_armar)
            estado, _, detalle = self.con_cliente(cliente, BASE, **kw_correr)
            self.assertEqual(estado, "difiere", detalle)
            self.assertFalse(cliente.hubo_escritura())


class FormaYHttpInesperados(Base):
    def test_http_inesperado_es_error_y_nombra_la_consulta(self):
        for matcher, nombre in [(lambda r: r.startswith("EntityDefinitions("), "Attributes"), (lambda r: r.startswith("fieldsecurityprofiles?"), "fieldsecurityprofiles"),
                                (lambda r: r.startswith("fieldpermissions?"), "fieldpermissions"), (es_ruta_solutioncomponents, "solutioncomponents"), (es_ruta_solutions, "solutions")]:
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
        p0, p1 = BASE["permisos"]
        casos = [("value[0].IsSecured", dict(columnas=[con_cambio(COLUMNAS[0], ["IsSecured"], None)] + COLUMNAS[1:])),
                 ("value[0].fieldsecurityprofileid", dict(perfil=fila_perfil(BASE, fieldsecurityprofileid=None))),
                 ("value[0].ismanaged", dict(perfil=fila_perfil(BASE, ismanaged="no"))),
                 ("value[0].canread", dict(permisos=[fp(p0, canread="4"), fp(p1)])),
                 ("value[1].attributelogicalname", dict(permisos=[fp(p0), fp(p1, attributelogicalname=None)]))]
        for campo, kw in casos:
            with self.subTest(campo):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("forma inesperada", detalle)
                self.assertIn(f"'{campo}'", detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())


if __name__ == "__main__":
    unittest.main()
