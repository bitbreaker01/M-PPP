"""Pruebas de `herramientas/construir/variable_entorno.py`. Nunca tocan la red.

Lo que más importa acá es la separación entre la DEFINICION (viaja en la
solucion) y el VALOR (es de este entorno y no viaja): si el valor viajara, al
importar en otro entorno pisaria el de alla.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

import variable_entorno as ve  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, SOLUTION_ID, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="variable-entorno", inventario="10.1")

DEF_ID = "88888888-8888-8888-8888-888888888888"
VAL_ID = "99999999-9999-9999-9999-999999999999"

COMPONENTE = {
    "tipo": "variable-entorno",
    "nombre": "sanic_mppp_ev_buzoningesta",
    "displayname": "EV - MPPP - Buzon de ingesta",
    "descripcion": "Buzon compartido del que MPPP-REC lee los correos entrantes.",
    "tipovalor": "Texto",
    "obligatoria": True,
    "valor": "mppp@55xljh.onmicrosoft.com",
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: variable-entorno · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def fila_definicion(datos=None, **cambios):
    datos = COMPONENTE if datos is None else datos
    fila = {
        "environmentvariabledefinitionid": DEF_ID,
        "schemaname": datos["nombre"],
        "displayname": datos["displayname"],
        "description": datos["descripcion"],
        "type": ve.TIPOS_DE_VALOR[datos["tipovalor"]],
        "isrequired": datos["obligatoria"],
        "ismanaged": False,
    }
    fila.update(cambios)
    return fila


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, definicion=None, valor=None, en_solucion=True):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.definicion = definicion
        self.valor = valor

        cliente.responder("GET", lambda r: r.startswith("environmentvariabledefinitions?"),
                          lambda r, c, s: (200, {"value": [] if self.definicion is None else [self.definicion]}, {}))
        cliente.responder("GET", lambda r: r.startswith("environmentvariablevalues?"),
                          lambda r, c, s: (200, {"value": [] if self.valor is None else [self.valor]}, {}))
        cliente.responder("GET", es_ruta_solutioncomponents,
                          (200, {"value": [{"componenttype": 380, "objectid": DEF_ID}] if en_solucion else []}, {}))
        return cliente


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = ve.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza({k: v for k, v in COMPONENTE.items() if k != "valor"}, "faltan ['valor']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_el_nombre_sigue_la_convencion(self):
        self.rechaza(comp(nombre="buzoningesta"), "no sigue el patrón sanic_mppp_ev_")
        self.rechaza(comp(nombre="sanic_mppp_ev_buzon-ingesta"), "letras y dígitos ASCII y guión bajo")

    def test_un_tipo_de_valor_invalido_se_rechaza_avisando_que_es_inmutable(self):
        self.rechaza(comp(tipovalor="String"), "se puede cambiar una vez creada")

    def test_una_variable_obligatoria_sin_valor_se_rechaza(self):
        # Obligatoria y vacía rompe los flujos que la leen.
        self.rechaza(comp(obligatoria=True, valor=None), "o no es obligatoria")

    def test_una_variable_opcional_sin_valor_se_acepta(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(comp(obligatoria=False, valor=None)))
        estado, _, detalle = ve.construir(self.escribir(comp(obligatoria=False, valor=None)), True, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertIn("SIN VALOR", detalle)

    def test_el_nombre_visible_va_sin_tildes(self):
        self.rechaza(comp(displayname="EV - MPPP - Buzón de ingesta"), "fuera de ASCII")


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_el_alta_crea_la_definicion_en_la_solucion_y_el_valor_fuera(self):
        cliente = self.armar(ClienteSimulado())

        def crear_def(ruta, cuerpo, solucion):
            self.definicion = fila_definicion()
            return (204, {}, {})

        def crear_val(ruta, cuerpo, solucion):
            self.valor = {"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]}
            return (204, {}, {})

        cliente.responder("POST", "environmentvariabledefinitions", crear_def)
        cliente.responder("POST", "environmentvariablevalues", crear_val)

        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        posts = {l["ruta"]: l for l in cliente.llamadas if l["metodo"] == "POST"}
        # La DEFINICION va a la solucion...
        self.assertEqual(IDENT["solucion"], posts["environmentvariabledefinitions"]["solucion"])
        # ...y el VALOR no, porque es de este entorno.
        self.assertIsNone(posts["environmentvariablevalues"]["solucion"])
        self.assertEqual(100000000, posts["environmentvariabledefinitions"]["cuerpo"]["type"])
        self.assertEqual(f"/environmentvariabledefinitions({DEF_ID})",
                         posts["environmentvariablevalues"]["cuerpo"]["EnvironmentVariableDefinitionId@odata.bind"])

    def test_sin_valor_declarado_no_se_crea_ninguna_fila_de_valor(self):
        datos = comp(obligatoria=False, valor=None)
        cliente = self.armar(ClienteSimulado())

        def crear_def(ruta, cuerpo, solucion):
            self.definicion = fila_definicion(datos)
            return (204, {}, {})

        cliente.responder("POST", "environmentvariabledefinitions", crear_def)

        estado, _, detalle = ve.construir(self.escribir(datos), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        self.assertNotIn("environmentvariablevalues", [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"])
        self.assertIn("SIN VALOR", detalle)

    def test_si_ya_esta_todo_bien_no_se_escribe_nada(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(),
                             valor={"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]})
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_tipo_distinto_dice_que_hay_que_borrar_y_rehacer(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(type=100000001),
                             valor={"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]})
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("INMUTABLE", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_valor_distinto_se_denuncia_y_solo_se_pisa_con_completar(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(),
                             valor={"environmentvariablevalueid": VAL_ID, "value": "otro@dominio.com"})
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("otro@dominio.com", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_corrige_el_valor_de_este_entorno(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(),
                             valor={"environmentvariablevalueid": VAL_ID, "value": "otro@dominio.com"})

        def corregir(ruta, cuerpo, solucion):
            self.valor = {"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]}
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("environmentvariablevalues("), corregir)

        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        patch = next(l for l in cliente.llamadas if l["metodo"] == "PATCH")
        self.assertEqual({"value": COMPONENTE["valor"]}, patch["cuerpo"])
        self.assertIsNone(patch["solucion"])  # el valor nunca viaja en la solucion

    def test_una_definicion_fuera_de_la_solucion_es_difiere(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(),
                             valor={"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]},
                             en_solucion=False)
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn(SOLUTION_ID, detalle)

    def test_una_definicion_managed_no_se_toca(self):
        cliente = self.armar(ClienteSimulado(), definicion=fila_definicion(ismanaged=True, displayname="otro"),
                             valor={"environmentvariablevalueid": VAL_ID, "value": COMPONENTE["valor"]})
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = ve.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no existe en el entorno", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_http_inesperado_en_el_alta_no_se_confunde_con_exito(self):
        cliente = self.armar(ClienteSimulado())
        cliente.responder("POST", "environmentvariabledefinitions", (400, {"error": "schemaname en uso"}, {}))
        estado, _, detalle = ve.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("HTTP 400", detalle)

    def test_dos_definiciones_con_el_mismo_schemaname_es_forma_inesperada(self):
        cliente = ClienteSimulado()
        armar_cliente_precondiciones_ok(cliente, IDENT)
        cliente.responder("GET", lambda r: r.startswith("environmentvariabledefinitions?"),
                          (200, {"value": [fila_definicion(), fila_definicion()]}, {}))
        estado, _, detalle = ve.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("se esperaba a lo sumo una", detalle)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = ve.salida
        try:
            sys.argv = ["variable_entorno.py", self.escribir(), "--forzar"]
            ve.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            ve.main()
        finally:
            sys.argv, ve.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
