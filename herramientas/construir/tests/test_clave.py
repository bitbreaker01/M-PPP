"""Herramienta `clave.py`: una clave alternativa, desde un playbook. Ninguna
prueba toca la red ni espera de verdad."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import clave as cv  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents, es_ruta_solutions, label, playbook_md  # noqa: E402

BORRAR = object()
ID_TABLA = "99999999-9999-9999-9999-999999999999"
IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="clave", inventario="5.4")
TABLA, CLAVE, META = "sanic_mppp_tbl_autorizado", "sanic_mppp_key_autorizado_cliente_nombre", "77777777-7777-7777-7777-777777777777"
BASE = {"tipo": "clave", "nombre": CLAVE, "displayname": "KEY - MPPP - Autorizado - Cliente y correo", "tabla": TABLA,
        "columnas": ["sanic_clienteid", "sanic_nombre"]}


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


def col(nombre, tipo, **kw):
    return dict({"LogicalName": nombre, "AttributeTypeName": {"Value": tipo}, "IsSecured": False, "AttributeOf": None}, **kw)


COLUMNAS = [col("sanic_clienteid", "LookupType"), col("sanic_nombre", "StringType"), col("sanic_secreta", "StringType", IsSecured=True),
            col("sanic_detalle", "MemoType"), col("sanic_larga", "StringType")]
LARGOS = [{"LogicalName": "sanic_nombre", "MaxLength": 320}, {"LogicalName": "sanic_larga", "MaxLength": 500}]


def cuerpo_clave(d, estado="Active"):
    return {"MetadataId": META, "LogicalName": d["nombre"], "SchemaName": d["nombre"], "KeyAttributes": list(d["columnas"]),
            "EntityKeyIndexStatus": estado, "IsManaged": False, "DisplayName": label(d["displayname"]), "AsyncJob": None}


def armar(cliente, d, existe=True, clave=None, estados=None, componentes=None, columnas=None):
    """Configura TODAS las rutas del camino feliz. `estados`: secuencia de
    EntityKeyIndexStatus que devuelve el entorno en lecturas sucesivas."""
    armar_cliente_precondiciones_ok(cliente, IDENT)
    st = {"existe": existe, "estados": list(estados or ["Active"])}
    cliente.responder("GET", lambda r: r.startswith(f"EntityDefinitions(LogicalName='{d['tabla']}')?"), (200, {"LogicalName": d["tabla"], "MetadataId": ID_TABLA}, {}))
    cliente.responder("GET", lambda r: "/Attributes/Microsoft.Dynamics.CRM.StringAttributeMetadata" in r, (200, {"value": LARGOS}, {}))
    cliente.responder("GET", lambda r: "/Attributes?" in r, (200, {"value": columnas if columnas is not None else COLUMNAS}, {}))

    def leer(*_):
        if not st["existe"]:
            return (404, {"error": "no existe"}, {})
        if clave is not None:
            return (200, clave, {})
        e = st["estados"].pop(0) if len(st["estados"]) > 1 else st["estados"][0]
        return (200, cuerpo_clave(d, e), {})

    cliente.responder("GET", lambda r: "/Keys(LogicalName=" in r, leer)
    cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": componentes if componentes is not None else [{"rootcomponentbehavior": 0}]}, {}))

    def al_crear(*_):
        st["existe"] = True
        return (204, None, {})

    cliente.responder("POST", f"EntityDefinitions(LogicalName='{d['tabla']}')/Keys", al_crear)
    return cliente


class Base(unittest.TestCase):
    def setUp(self):
        self.esperas = []

    def correr(self, fabrica, datos, solo_verificar=False):
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "playbook.md")
            open(ruta, "w", encoding="utf-8").write(playbook_md(IDENT, datos))
            return cv.construir(ruta, solo_verificar, fabrica, dormir=self.esperas.append)

    def con_cliente(self, cliente, datos, **kw):
        return self.correr(lambda: cliente, datos, **kw)


class ValidacionSinRed(Base):
    CASOS = [
        (["tipo"], "tabla", "tipo"),
        (["nombre"], "sanic_mppp_key_Autorizado", "nombre"),
        (["nombre"], "sanic_mppp_key_plan_codigo", "sanic_mppp_key_autorizado_"),
        (["nombre"], "sanic_mppp_key_autorizado_" + "a" * 90, "95"),
        (["displayname"], "", "displayname"),
        (["displayname"], "Clave del autorizado", "KEY - MPPP - "),
        (["tabla"], "autorizado", "tabla"),
        (["columnas"], [], "columnas"),
        (["columnas"], "sanic_nombre", "columnas"),
        (["columnas"], ["sanic_nombre", "sanic_nombre"], "repetida"),
        (["columnas"], ["sanic_Nombre"], "columnas[0]"),
        (["columnas"], ["sanic_c%d" % i for i in range(17)], "16"),
        (["columnas", 0], 5, "columnas[0]"),
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


class Payload(unittest.TestCase):
    def test_cuerpo(self):
        p = cv.construir_payload(BASE, IDENT)
        self.assertEqual(p["@odata.type"], "Microsoft.Dynamics.CRM.EntityKeyMetadata")
        self.assertEqual(p["SchemaName"], CLAVE)
        self.assertEqual(p["KeyAttributes"], ["sanic_clienteid", "sanic_nombre"])
        self.assertEqual(p["DisplayName"]["LocalizedLabels"][0], {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": BASE["displayname"], "LanguageCode": 1033})


class Precondiciones(Base):
    def bloquea(self, datos, esperado, **kw):
        cliente = armar(ClienteSimulado(), datos, existe=False, **kw)
        estado, _, detalle = self.con_cliente(cliente, datos)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn(esperado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_columna_no_existe(self):
        self.bloquea(con_cambio(BASE, ["columnas"], ["sanic_clienteid", "sanic_inexistente"]), "sanic_inexistente")

    def test_una_columna_con_seguridad_de_columna_no_puede_ir(self):
        self.bloquea(con_cambio(BASE, ["columnas"], ["sanic_secreta"]), "seguridad de columna")

    def test_un_tipo_que_no_admite_clave(self):
        self.bloquea(con_cambio(BASE, ["columnas"], ["sanic_detalle"]), "MemoType")

    def test_supera_los_900_bytes(self):
        self.bloquea(con_cambio(BASE, ["columnas"], ["sanic_larga"]), "900")

    def test_450_caracteres_es_justo_el_limite(self):
        largos = [{"LogicalName": "sanic_larga", "MaxLength": 450}]
        cliente = ClienteSimulado()
        cliente.responder("GET", lambda r: "/Attributes/Microsoft.Dynamics.CRM.StringAttributeMetadata" in r, (200, {"value": largos}, {}))
        d = con_cambio(BASE, ["columnas"], ["sanic_larga"])
        armar(cliente, d, existe=False)
        estado, _, detalle = self.con_cliente(cliente, d)
        self.assertEqual(estado, "creado", detalle)


class Caminos(Base):
    def test_se_crea_y_espera_a_que_el_indice_este_activo(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False, estados=["Pending", "InProgress", "Active", "Active"])
        estado, comp, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual(comp, CLAVE)
        self.assertIn(META, detalle)
        self.assertEqual(self.esperas, [cv.ESPERA_INDICE_SEGUNDOS] * 2)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["ruta"] for p in posts], [f"EntityDefinitions(LogicalName='{TABLA}')/Keys"])
        self.assertEqual(posts[0]["solucion"], IDENT["solucion"])

    def test_si_el_indice_falla_lo_dice_y_nombra_la_reactivacion(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False, estados=["Pending", "Failed", "Failed"])
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("Failed", detalle)
        self.assertIn("ReactivateEntityKey", detalle)

    def test_si_el_indice_no_termina_a_tiempo_lo_dice(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False, estados=["Pending"])
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("Pending", detalle)
        self.assertEqual(len(self.esperas), cv.INTENTOS_INDICE)

    def test_ya_existia_no_escribe_ni_espera(self):
        cliente = armar(ClienteSimulado(), BASE)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn(META, detalle)
        self.assertFalse(cliente.hubo_escritura())
        self.assertEqual(self.esperas, [])

    def test_existe_pero_el_indice_no_esta_activo(self):
        for e, esperado in (("Failed", "difiere"), ("InProgress", "error")):
            with self.subTest(e):
                cliente = armar(ClienteSimulado(), BASE, estados=[e])
                estado, _, detalle = self.con_cliente(cliente, BASE, solo_verificar=True)
                self.assertEqual(estado, esperado, detalle)
                self.assertIn(e, detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_sin_clave_es_error_y_no_crea(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_creacion_falla(self):
        cliente = ClienteSimulado()
        cliente.responder("POST", f"EntityDefinitions(LogicalName='{TABLA}')/Keys", (400, {"error": "clave duplicada"}, {}))
        armar(cliente, BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 400", detalle)


class Pertenencia(Base):
    def test_se_comprueba_la_de_la_tabla_porque_una_clave_no_es_un_componente_propio(self):
        """Visto el 2026-09-21 en el ensayo: una clave recién creada no tiene fila en
        solutioncomponents (ni tipo 14 ni ningún otro); viaja dentro de su tabla."""
        cliente = armar(ClienteSimulado(), BASE)
        self.con_cliente(cliente, BASE)
        rutas = [l["ruta"] for l in cliente.llamadas if es_ruta_solutioncomponents(l["ruta"])]
        self.assertEqual(len(rutas), 1)
        self.assertIn(f"objectid eq {ID_TABLA}", rutas[0])
        self.assertIn("componenttype eq 1", rutas[0])


class Diferencias(Base):
    def test_el_orden_de_las_columnas_no_es_una_diferencia(self):
        """La plataforma devuelve KeyAttributes en su propio orden (alfabético)."""
        clave = con_cambio(cuerpo_clave(BASE), ["KeyAttributes"], ["sanic_nombre", "sanic_clienteid"])
        estado, _, detalle = self.con_cliente(armar(ClienteSimulado(), BASE, clave=clave), BASE)
        self.assertEqual(estado, "ya_existia", detalle)

    def test_cada_diferencia(self):
        c = cuerpo_clave(BASE)
        casos = [("KeyAttributes", dict(clave=con_cambio(c, ["KeyAttributes"], ["sanic_nombre"]))),
                 ("IsManaged", dict(clave=con_cambio(c, ["IsManaged"], True))),
                 ("DisplayName", dict(clave=con_cambio(c, ["DisplayName"], label("Otro")))),
                 ("pertenencia a la solución", dict(componentes=[])),
                 ("no incluye todos sus subcomponentes", dict(componentes=[{"rootcomponentbehavior": 1}]))]
        for esperado, kw in casos:
            with self.subTest(esperado + str(kw)[:40]):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "difiere", detalle)
                self.assertIn(esperado, detalle)
                self.assertFalse(cliente.hubo_escritura())


class FormaYHttpInesperados(Base):
    def test_http_inesperado_es_error_y_nombra_la_consulta(self):
        for matcher, nombre in [(lambda r: r.startswith("EntityDefinitions(LogicalName=") and "/" not in r.split(")", 1)[1][:2], "EntityDefinitions"),
                                (lambda r: "/Attributes?" in r, "Attributes"), (lambda r: "StringAttributeMetadata" in r, "StringAttributeMetadata"),
                                (lambda r: "/Keys(LogicalName=" in r, "Keys"), (es_ruta_solutioncomponents, "solutioncomponents"), (es_ruta_solutions, "solutions")]:
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
        c = cuerpo_clave(BASE)
        casos = [("MetadataId", dict(clave=con_cambio(c, ["MetadataId"], None))), ("KeyAttributes", dict(clave=con_cambio(c, ["KeyAttributes"], "sanic_nombre"))),
                 ("KeyAttributes[0]", dict(clave=con_cambio(c, ["KeyAttributes"], [None, "sanic_nombre"]))),
                 ("EntityKeyIndexStatus", dict(clave=con_cambio(c, ["EntityKeyIndexStatus"], 2))), ("IsManaged", dict(clave=con_cambio(c, ["IsManaged"], "false"))),
                 ("DisplayName", dict(clave=con_cambio(c, ["DisplayName"], None))),
                 ("value[0].rootcomponentbehavior", dict(componentes=[{"rootcomponentbehavior": "0"}])),
                 ("value[1].IsSecured", dict(columnas=con_cambio(COLUMNAS, [1, "IsSecured"], None))),
                 ("value[0].AttributeTypeName.Value", dict(columnas=con_cambio(COLUMNAS, [0, "AttributeTypeName", "Value"], 5)))]
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
