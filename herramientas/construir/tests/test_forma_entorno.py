"""Forma de las respuestas del entorno: todo valor que la herramienta lee de
una respuesta y usa para decidir se valida por TIPO, hasta el último nivel
(no solo el contenedor). Un 200 con un valor ausente o de otro tipo es
`error` ("no se pudo averiguar"), nunca `bloqueado`, `difiere`, `ya_existia`
ni `creado`.

Cada caso parte de una respuesta feliz y le cambia UN solo valor. La prueba
afirma el estado Y que el detalle nombra la consulta y el campo: así solo
puede pasar por el camino correcto, no por una red de contención genérica.
"""
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
from fixtures import (  # noqa: E402
    COMPONENTE_VALIDO,
    cuerpo_choice_conforme,
    es_ruta_solutioncomponents,
    es_ruta_solutions,
    escribir_playbook,
    respuesta_idioma_ok,
    respuesta_idiomas_provisionados_ok,
    respuesta_solucion_ok,
    ruta_choice,
)

BORRAR = object()
RUTA_ORG = "organizations?$select=languagecode"
RUTA_IDIOMAS = "RetrieveProvisionedLanguages"


def con_cambio(cuerpo, ruta, valor):
    """Copia de `cuerpo` con el valor en `ruta` (lista de claves e índices)
    reemplazado por `valor`, o quitado si `valor` es BORRAR. Una ruta vacía
    reemplaza el cuerpo entero."""
    if not ruta:
        return valor
    nuevo = copy.deepcopy(cuerpo)
    nodo = nuevo
    for paso in ruta[:-1]:
        nodo = nodo[paso]
    if valor is BORRAR:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    return nuevo


# (consulta que se rompe, ruta del valor, valor malo, texto del campo que debe nombrar el detalle)
CASOS = [
    # --- solutions -------------------------------------------------------
    ("solutions", [], None, "cuerpo"),
    ("solutions", ["value"], "texto", "value"),
    ("solutions", ["value"], BORRAR, "value"),
    ("solutions", ["value", 0], "no soy un objeto", "value[0]"),
    ("solutions", ["value", 0, "ismanaged"], None, "ismanaged"),
    ("solutions", ["value", 0, "ismanaged"], "false", "ismanaged"),
    ("solutions", ["value", 0, "solutionid"], None, "solutionid"),
    ("solutions", ["value", 0, "solutionid"], 123, "solutionid"),
    ("solutions", ["value", 0, "solutionid"], "", "solutionid"),
    ("solutions", ["value", 0, "publisherid"], None, "publisherid"),
    ("solutions", ["value", 0, "publisherid", "uniquename"], None, "publisherid.uniquename"),
    ("solutions", ["value", 0, "publisherid", "customizationprefix"], 5, "publisherid.customizationprefix"),
    ("solutions", ["value", 0, "publisherid", "customizationoptionvalueprefix"], "15946", "publisherid.customizationoptionvalueprefix"),
    ("solutions", ["value", 0, "publisherid", "customizationoptionvalueprefix"], True, "publisherid.customizationoptionvalueprefix"),
    # --- organizations ---------------------------------------------------
    ("organizations", [], [], "cuerpo"),
    ("organizations", ["value"], [], "value"),
    ("organizations", ["value", 0], "x", "value[0]"),
    ("organizations", ["value", 0, "languagecode"], None, "languagecode"),
    ("organizations", ["value", 0, "languagecode"], "1033", "languagecode"),
    ("organizations", ["value", 0, "languagecode"], True, "languagecode"),
    ("organizations", ["value", 0, "languagecode"], BORRAR, "languagecode"),
    # --- RetrieveProvisionedLanguages ------------------------------------
    ("idiomas", ["RetrieveProvisionedLanguages"], ["1033", "3082"], "RetrieveProvisionedLanguages[0]"),
    ("idiomas", ["RetrieveProvisionedLanguages"], [1033, None], "RetrieveProvisionedLanguages[1]"),
    ("idiomas", ["RetrieveProvisionedLanguages"], [True], "RetrieveProvisionedLanguages[0]"),
    ("idiomas", ["RetrieveProvisionedLanguages"], [], "RetrieveProvisionedLanguages"),
    ("idiomas", ["RetrieveProvisionedLanguages"], BORRAR, "RetrieveProvisionedLanguages"),
    # --- existencia del choice -------------------------------------------
    ("choice", [], ["lista"], "cuerpo"),
    ("choice", ["MetadataId"], None, "MetadataId"),
    ("choice", ["MetadataId"], 5, "MetadataId"),
    ("choice", ["Name"], None, "Name"),
    ("choice", ["IsGlobal"], None, "IsGlobal"),
    ("choice", ["IsGlobal"], "true", "IsGlobal"),
    ("choice", ["IsManaged"], BORRAR, "IsManaged"),
    ("choice", ["OptionSetType"], None, "OptionSetType"),
    ("choice", ["DisplayName"], None, "DisplayName"),
    ("choice", ["DisplayName"], "texto", "DisplayName"),
    ("choice", ["DisplayName", "LocalizedLabels"], "texto", "DisplayName.LocalizedLabels"),
    ("choice", ["DisplayName", "LocalizedLabels", 0], "texto", "DisplayName.LocalizedLabels[0]"),
    ("choice", ["DisplayName", "LocalizedLabels", 0, "LanguageCode"], "1033", "DisplayName.LocalizedLabels[0].LanguageCode"),
    ("choice", ["DisplayName", "LocalizedLabels", 0, "Label"], 5, "DisplayName.LocalizedLabels[0].Label"),
    ("choice", ["Description"], "texto", "Description"),
    ("choice", ["Options"], BORRAR, "Options"),
    ("choice", ["Options"], {"no": "lista"}, "Options"),
    ("choice", ["Options", 0], "texto", "Options[0]"),
    ("choice", ["Options", 0, "Value"], "159460001", "Options[0].Value"),
    ("choice", ["Options", 0, "Value"], True, "Options[0].Value"),
    ("choice", ["Options", 1, "Label"], None, "Options[1].Label"),
    ("choice", ["Options", 1, "Label", "LocalizedLabels", 0, "LanguageCode"], None, "Options[1].Label.LocalizedLabels[0].LanguageCode"),
    ("choice", ["Options", 0, "Description"], 7, "Options[0].Description"),
    # --- solutioncomponents ----------------------------------------------
    ("solutioncomponents", [], None, "cuerpo"),
    ("solutioncomponents", ["value"], "texto", "value"),
    ("solutioncomponents", ["value"], ["no soy un objeto"], "value[0]"),
]

# Texto con el que el detalle identifica cada consulta.
NOMBRE_CONSULTA = {
    "solutions": "solutions",
    "organizations": "organizations",
    "idiomas": "RetrieveProvisionedLanguages",
    "choice": "GlobalOptionSetDefinitions",
    "solutioncomponents": "solutioncomponents",
}


class FormaInesperadaEsError(unittest.TestCase):
    def _cliente(self, consulta, ruta, valor):
        _, sol, _ = respuesta_solucion_ok()
        _, org, _ = respuesta_idioma_ok()
        _, idi, _ = respuesta_idiomas_provisionados_ok()
        cuerpos = {
            "solutions": sol,
            "organizations": org,
            "idiomas": idi,
            "choice": cuerpo_choice_conforme(),
            "solutioncomponents": {"value": [{"solutioncomponentid": "33333333-3333-3333-3333-333333333333"}]},
        }
        cuerpos[consulta] = con_cambio(cuerpos[consulta], ruta, valor)
        # Se configuran TODAS las rutas del camino feliz, aunque la ejecución
        # deba cortar antes: si no, el AssertionError del doble ("ruta sin
        # regla") terminaría también en 'error' y la prueba pasaría en falso.
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, (200, cuerpos["solutions"], {}))
        cliente.responder("GET", RUTA_ORG, (200, cuerpos["organizations"], {}))
        cliente.responder("GET", RUTA_IDIOMAS, (200, cuerpos["idiomas"], {}))
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, cuerpos["choice"], {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, cuerpos["solutioncomponents"], {}))
        return cliente

    def _correr(self, cliente, solo_verificar=False):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            escribir_playbook(ruta)
            return cg.construir(ruta, solo_verificar, lambda: cliente)

    def test_un_valor_de_tipo_equivocado_es_error_y_nombra_consulta_y_campo(self):
        for consulta, ruta, valor, campo in CASOS:
            for solo_verificar in (False, True):
                etiqueta = f"{consulta} {ruta} <- {'BORRAR' if valor is BORRAR else repr(valor)} (solo_verificar={solo_verificar})"
                with self.subTest(etiqueta):
                    cliente = self._cliente(consulta, ruta, valor)
                    estado, _, detalle = self._correr(cliente, solo_verificar)
                    self.assertEqual(estado, "error", detalle)
                    self.assertIn("forma inesperada", detalle)
                    self.assertIn(NOMBRE_CONSULTA[consulta], detalle)
                    self.assertIn(f"'{campo}'", detalle)
                    self.assertNotIn("fallo inesperado", detalle)
                    self.assertFalse(cliente.hubo_escritura())

    def test_el_camino_feliz_de_esta_mesa_de_pruebas_da_ya_existia(self):
        """Control: sin ningún cambio, la misma mesa da `ya_existia`. Si esto
        fallara, los casos de arriba podrían estar pasando por otra razón."""
        _, sol, _ = respuesta_solucion_ok()
        cliente = self._cliente("solutions", [], sol)
        estado, _, detalle = self._correr(cliente)
        self.assertEqual(estado, "ya_existia", detalle)

    def test_description_nula_es_legitima(self):
        """La `Description` de una opción puede venir nula (una opción sin
        descripción es legítima en el playbook): no es forma inesperada."""
        datos = copy.deepcopy(COMPONENTE_VALIDO)
        for op in datos["opciones"]:
            op["descripcion"] = ""
        cuerpo = cuerpo_choice_conforme(datos)
        for op in cuerpo["Options"]:
            op["Description"] = None
        cliente = self._cliente("choice", [], cuerpo)
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            escribir_playbook(ruta, None, datos)
            estado, _, detalle = cg.construir(ruta, False, lambda: cliente)
        self.assertEqual(estado, "ya_existia", detalle)

    def test_las_dos_respuestas_de_negocio_vacias_siguen_siendo_de_negocio(self):
        cliente = self._cliente("solutions", ["value"], [])
        estado, _, detalle = self._correr(cliente)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn("no existe", detalle)

        cliente = self._cliente("solutioncomponents", ["value"], [])
        estado, _, detalle = self._correr(cliente)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn("pertenencia a la solución", detalle)


class RedesDeUltimoRecursoDicenDondeEstaban(unittest.TestCase):
    def _correr(self, cliente):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            escribir_playbook(ruta)
            return cg.construir(ruta, False, lambda: cliente)

    def test_excepcion_imprevista_contra_el_entorno_nombra_la_consulta_en_curso(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", RUTA_ORG, TimeoutError("se agotó el tiempo"))
        estado, _, detalle = self._correr(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("fallo inesperado", detalle)
        self.assertIn("TimeoutError", detalle)
        self.assertIn("GET organizations", detalle)

    def test_excepcion_imprevista_antes_de_la_primera_consulta_lo_dice(self):
        class ClienteRoto:
            call = None  # llamar a None lanza TypeError antes de cualquier consulta

        estado, _, detalle = self._correr(ClienteRoto())
        self.assertEqual(estado, "error")
        self.assertIn("fallo inesperado", detalle)
        self.assertIn("GET solutions", detalle)

    def test_excepcion_imprevista_sin_red_nombra_el_paso(self):
        original = cg.validar_nombres
        cg.validar_nombres = lambda *_: (_ for _ in ()).throw(TypeError("dato raro"))
        try:
            estado, _, detalle = self._correr(ClienteSimulado())
        finally:
            cg.validar_nombres = original
        self.assertEqual(estado, "error")
        self.assertIn("fallo inesperado", detalle)
        self.assertIn("TypeError", detalle)
        self.assertIn("validar los nombres", detalle)


if __name__ == "__main__":
    unittest.main()
