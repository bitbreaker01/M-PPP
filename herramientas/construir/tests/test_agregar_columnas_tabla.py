"""`tabla.py --agregar-columnas`: agrega a una tabla YA construida las columnas
que el playbook declara y el entorno no tiene, y solo si esa es la ÚNICA
diferencia (D-15, 2026-09-21: `sanic_cantidadexcel` nace después que su tabla).
Nunca borra, nunca cambia una columna que ya existe."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import tabla as tb  # noqa: E402
import test_tabla as tt  # noqa: E402
from cliente_simulado import ClienteSimulado  # noqa: E402
from fixtures import label  # noqa: E402

D, T = tt.COMPLETO, tt.COMPLETO["nombre"]
ENTERO = next(c for c in D["columnas"] if c["tipo"] == "entero")
SINO = next(c for c in D["columnas"] if c["tipo"] == "sino")
RUTA_ATRIBUTOS = f"EntityDefinitions(LogicalName='{T}')/Attributes"


def entorno_sin(faltan, otra=False, tabla_vieja=False, falla_en=None):
    """Un entorno al que le faltan columnas, y que las gana a medida que se agregan."""
    agregadas = set()
    visibles = lambda n: n not in faltan or n in agregadas  # noqa: E731
    gen = [tt.fila_generica(D["primaria"], True)] + [tt.fila_generica(c) for c in D["columnas"]] + tt.SISTEMA
    pt = copy.deepcopy(tt.filas_por_tipo(D))
    if otra:
        otra_col = next(c for c in D["columnas"] if c["tipo"] == "texto")
        next(f for f in pt["String"] if f["LogicalName"] == otra_col["nombre"])["MaxLength"] = 7
    cliente = ClienteSimulado()
    cliente.responder("GET", lambda r: "/Attributes?" in r, lambda *_: (200, {"value": [g for g in gen if visibles(g["LogicalName"])]}, {}))
    for t in ("String", "Memo", "Integer", "Picklist", "Boolean", "DateTime", "File"):
        cliente.responder("GET", lambda r, t=t: f"/Attributes/Microsoft.Dynamics.CRM.{t}AttributeMetadata" in r,
                          lambda *_, t=t: (200, {"value": [f for f in pt.get(t, []) if visibles(f["LogicalName"])]}, {}))

    def al_agregar(ruta, cuerpo, solucion):
        if falla_en == cuerpo["SchemaName"]:
            return (400, {"error": "boom"}, {})
        agregadas.add(cuerpo["SchemaName"])
        return (204, None, {})

    cliente.responder("POST", RUTA_ATRIBUTOS, al_agregar)
    tabla = tt.cuerpo_tabla(D)
    if tabla_vieja:
        tabla["DisplayName"] = label("Otro nombre")
    return tt.armar(cliente, D, tabla=tabla)


class AgregarColumnas(tt.Base):
    def escrituras(self, cliente):
        return [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"]

    def test_sin_el_flag_difiere_y_no_escribe(self):
        cliente = entorno_sin({ENTERO["nombre"]})
        estado, _, detalle = self.con_cliente(cliente, D)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn(f"falta la columna {ENTERO['nombre']}", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_agrega_las_que_faltan_en_el_orden_del_playbook_publica_una_vez_y_relee(self):
        cliente = entorno_sin({SINO["nombre"], ENTERO["nombre"]})
        estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("se agregaron 2 columnas", detalle)
        for c in (ENTERO, SINO):
            self.assertIn(c["nombre"], detalle)
        orden = [c["nombre"] for c in D["columnas"] if c["nombre"] in (ENTERO["nombre"], SINO["nombre"])]
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST" and l["ruta"] == RUTA_ATRIBUTOS]
        self.assertEqual([p["cuerpo"]["SchemaName"] for p in posts], orden)
        self.assertEqual(self.escrituras(cliente), [("POST", RUTA_ATRIBUTOS)] * 2 + [("POST", "PublishXml")])
        for p in posts:
            self.assertEqual(p["solucion"], tt.IDENT["solucion"])
        # El cuerpo es EL MISMO que usaría la creación de la tabla: una sola receta por tipo de columna.
        esperado = {c["nombre"]: tb._columna_payload(c, tt.IDENT["lcid"], {}) for c in (ENTERO, SINO)}
        for p in posts:
            self.assertEqual(p["cuerpo"], esperado[p["cuerpo"]["SchemaName"]])

    def test_con_cualquier_otra_diferencia_ademas_no_toca_nada(self):
        for kw in (dict(otra=True), dict(tabla_vieja=True)):
            with self.subTest(kw):
                cliente = entorno_sin({ENTERO["nombre"]}, **kw)
                estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
                self.assertEqual(estado, "difiere", detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_si_falta_la_primaria_no_es_algo_que_se_agregue(self):
        cliente = entorno_sin({D["primaria"]["nombre"]})
        estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_con_solo_verificar_o_si_no_falta_nada_no_escribe(self):
        for faltan, kw, esperado in (({ENTERO["nombre"]}, dict(agregar_columnas=True, solo_verificar=True), "difiere"), (set(), dict(agregar_columnas=True), "ya_existia")):
            cliente = entorno_sin(faltan)
            estado, _, detalle = self.con_cliente(cliente, D, **kw)
            self.assertEqual(estado, esperado, detalle)
            self.assertFalse(cliente.hubo_escritura())

    def test_si_la_tabla_no_existe_el_flag_no_cambia_nada_se_crea_como_siempre(self):
        cliente = tt.armar(ClienteSimulado(), D, existe=False)
        estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
        self.assertEqual(estado, "creado", detalle)

    def test_si_una_alta_falla_es_error_dice_cual_y_cuales_ya_quedaron(self):
        orden = [c["nombre"] for c in D["columnas"] if c["nombre"] in (ENTERO["nombre"], SINO["nombre"])]
        cliente = entorno_sin(set(orden), falla_en=orden[1])
        estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("HTTP 400", detalle)
        self.assertIn(orden[1], detalle)
        self.assertIn(f"ya se agregaron: {orden[0]}", detalle)
        self.assertNotIn(("POST", "PublishXml"), self.escrituras(cliente))

    def test_si_al_releer_sigue_difiriendo_es_error_no_ya_existia(self):
        cliente = ClienteSimulado()
        # La alta "sale bien" pero la columna nunca aparece: el entorno manda, no el 204.
        cliente.responder("POST", RUTA_ATRIBUTOS, (204, None, {}))
        gen = [tt.fila_generica(D["primaria"], True)] + [tt.fila_generica(c) for c in D["columnas"] if c["nombre"] != ENTERO["nombre"]] + tt.SISTEMA
        pt = copy.deepcopy(tt.filas_por_tipo(D))
        pt["Integer"] = [f for f in pt["Integer"] if f["LogicalName"] != ENTERO["nombre"]]
        tt.armar(cliente, D, genericas=gen, por_tipo=pt)
        estado, _, detalle = self.con_cliente(cliente, D, agregar_columnas=True)
        self.assertEqual(estado, "error", detalle)
        self.assertIn(f"falta la columna {ENTERO['nombre']}", detalle)

    def test_el_flag_pasa_por_la_linea_de_comandos(self):
        fuente = open(tb.__file__, encoding="utf-8").read()
        self.assertIn('"--agregar-columnas" in argv', fuente)
        self.assertIn("[--agregar-columnas]", fuente)


if __name__ == "__main__":
    unittest.main()
