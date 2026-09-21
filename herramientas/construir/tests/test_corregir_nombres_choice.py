"""`choice_global.py --corregir-nombres`: la única modificación que la
herramienta admite sobre un choice que ya existe. Solo nombres visibles (el
del choice y las etiquetas de sus opciones), y solo si esa es la ÚNICA
diferencia. Ensayado contra la plataforma el 2026-09-21."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import choice_global as cg  # noqa: E402
from cliente_simulado import ClienteSimulado  # noqa: E402
from fixtures import COMPONENTE_VALIDO, IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, cuerpo_choice_conforme, es_ruta_solutioncomponents, escribir_playbook, ruta_choice  # noqa: E402

NOMBRE = COMPONENTE_VALIDO["nombre"]
META = "11111111-1111-1111-1111-111111111111"


def armar(cuerpo_viejo):
    """El entorno arranca con `cuerpo_viejo` y refleja cada escritura de nombres."""
    st = {"cuerpo": copy.deepcopy(cuerpo_viejo)}
    cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
    cliente.responder("GET", ruta_choice(NOMBRE), lambda *_: (200, copy.deepcopy(st["cuerpo"]), {}))
    cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

    def al_put(ruta, cuerpo, solucion):
        st["cuerpo"]["DisplayName"] = {"LocalizedLabels": [{"Label": l["Label"], "LanguageCode": l["LanguageCode"]} for l in cuerpo["DisplayName"]["LocalizedLabels"]]}
        return (204, None, {})

    def al_actualizar_opcion(ruta, cuerpo, solucion):
        op = next(o for o in st["cuerpo"]["Options"] if o["Value"] == cuerpo["Value"])
        op["Label"] = {"LocalizedLabels": [{"Label": cuerpo["Label"]["LocalizedLabels"][0]["Label"], "LanguageCode": 1033}]}
        return (204, None, {})

    cliente.responder("PUT", f"GlobalOptionSetDefinitions({META})", al_put)
    cliente.responder("POST", "UpdateOptionValue", al_actualizar_opcion)
    cliente.responder("POST", "PublishXml", (204, None, {}))
    return cliente


def viejo(**cambios):
    c = cuerpo_choice_conforme()
    if "displayname" in cambios:
        c["DisplayName"]["LocalizedLabels"][0]["Label"] = cambios["displayname"]
    for i, texto in cambios.get("etiquetas", {}).items():
        c["Options"][i]["Label"]["LocalizedLabels"][0]["Label"] = texto
    for i, texto in cambios.get("descripciones", {}).items():
        c["Options"][i]["Description"]["LocalizedLabels"][0]["Label"] = texto
    return c


class CorregirNombres(unittest.TestCase):
    def correr(self, cliente, **kw):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            escribir_playbook(ruta, IDENTIDAD_VALIDA, COMPONENTE_VALIDO)
            return cg.construir(ruta, kw.pop("solo_verificar", False), lambda: cliente, **kw)

    def test_sin_el_flag_difiere_y_no_escribe(self):
        cliente = armar(viejo(displayname="CH - MPPP - Monéda"))
        estado, _, detalle = self.correr(cliente)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_renombra_el_choice_y_las_opciones_que_difieren_y_publica(self):
        cliente = armar(viejo(displayname="CH - MPPP - Monéda", etiquetas={1: "USDólar"}))
        estado, _, detalle = self.correr(cliente, corregir_nombres=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("se corrigieron", detalle)
        escrituras = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"]
        self.assertEqual(escrituras, [("PUT", f"GlobalOptionSetDefinitions({META})"), ("POST", "UpdateOptionValue"), ("POST", "PublishXml")])
        put = next(l for l in cliente.llamadas if l["metodo"] == "PUT")
        self.assertEqual(put["cuerpo"]["@odata.type"], "Microsoft.Dynamics.CRM.OptionSetMetadata")
        self.assertEqual(put["cuerpo"]["DisplayName"]["LocalizedLabels"][0]["Label"], COMPONENTE_VALIDO["displayname"])
        self.assertEqual(put["cuerpo"]["Name"], NOMBRE)  # el resto de la definición se conserva
        self.assertEqual(put["cabeceras"], {"MSCRM.MergeLabels": "true"})
        self.assertEqual(put["solucion"], IDENTIDAD_VALIDA["solucion"])
        op = next(l for l in cliente.llamadas if l["ruta"] == "UpdateOptionValue")["cuerpo"]
        self.assertEqual((op["OptionSetName"], op["Value"], op["MergeLabels"], op["SolutionUniqueName"]), (NOMBRE, COMPONENTE_VALIDO["opciones"][1]["valor"], True, IDENTIDAD_VALIDA["solucion"]))
        self.assertEqual(op["Label"]["LocalizedLabels"][0]["Label"], COMPONENTE_VALIDO["opciones"][1]["etiqueta"])
        self.assertIn(NOMBRE, next(l for l in cliente.llamadas if l["ruta"] == "PublishXml")["cuerpo"]["ParameterXml"])

    def test_solo_las_opciones_no_hace_put(self):
        cliente = armar(viejo(etiquetas={0: "CÓR"}))
        estado, _, detalle = self.correr(cliente, corregir_nombres=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertEqual([l["metodo"] for l in cliente.llamadas if l["metodo"] == "PUT"], [])

    def test_con_otra_diferencia_ademas_no_toca_nada(self):
        for otro in (viejo(displayname="CH - MPPP - Monéda", descripciones={0: "Otra descripción"}),):
            cliente = armar(otro)
            estado, _, detalle = self.correr(cliente, corregir_nombres=True)
            self.assertEqual(estado, "difiere", detalle)
            self.assertFalse(cliente.hubo_escritura())

    def test_con_solo_verificar_no_escribe(self):
        cliente = armar(viejo(displayname="CH - MPPP - Monéda"))
        estado, _, _ = self.correr(cliente, corregir_nombres=True, solo_verificar=True)
        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())

    def test_si_coincide_no_escribe(self):
        cliente = armar(viejo())
        estado, _, _ = self.correr(cliente, corregir_nombres=True)
        self.assertEqual(estado, "ya_existia")
        self.assertFalse(cliente.hubo_escritura())

    def test_si_una_escritura_falla_es_error_y_dice_cual(self):
        cliente = ClienteSimulado()
        cliente.responder("POST", "UpdateOptionValue", (400, {"error": "boom"}, {}))
        armado = armar(viejo(etiquetas={0: "CÓR"}))
        cliente._reglas += armado._reglas
        estado, _, detalle = self.correr(cliente, corregir_nombres=True)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("HTTP 400", detalle)
        self.assertIn("opciones[0]", detalle)


if __name__ == "__main__":
    unittest.main()
