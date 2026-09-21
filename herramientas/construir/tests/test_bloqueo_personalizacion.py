"""Dataverse admite una sola personalización de metadatos a la vez. Si otra
está corriendo, una escritura de metadatos devuelve 429 con
`CustomizationLockException`: es pasajero, se espera y se reintenta. Cualquier
otro 429 o error NO se reintenta."""
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import _comun as c  # noqa: E402

BLOQUEO = (429, {"error": "Failed to create entity … Microsoft.Crm.ObjectModel.CustomizationLockException: Cannot start another "
                          "[EntityCustomization] because there is a previous [EntityCustomization] running at this moment."}, {})


BLOQUEO_PUBLICAR = (429, {"error": "Cannot start the requested operation [Publish] because there is another [Import] running at this moment. "
                                   "Use Solution History for more details."}, {})


class ClienteEnSecuencia:
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = list(respuestas), []

    def call(self, metodo, ruta, cuerpo=None, **kw):
        self.llamadas.append((metodo, ruta, cuerpo, kw))
        return self.respuestas.pop(0)


class EscribirMetadatos(unittest.TestCase):
    def setUp(self):
        self.esperas = []

    def escribir(self, cliente, **kw):
        return c.escribir_metadatos(cliente, "POST", "EntityDefinitions", {"a": 1}, dormir=self.esperas.append, solucion="sol", **kw)

    def test_sin_bloqueo_no_espera(self):
        cli = ClienteEnSecuencia([(204, None, {})])
        self.assertEqual(self.escribir(cli)[0], 204)
        self.assertEqual(self.esperas, [])
        self.assertEqual(cli.llamadas[0][3], {"solucion": "sol"})

    def test_espera_y_reintenta_mientras_dure_el_bloqueo(self):
        cli = ClienteEnSecuencia([BLOQUEO, BLOQUEO, (204, None, {})])
        self.assertEqual(self.escribir(cli)[0], 204)
        self.assertEqual(len(cli.llamadas), 3)
        self.assertEqual(self.esperas, [c.ESPERA_BLOQUEO_SEGUNDOS] * 2)
        self.assertTrue(all(l[2] == {"a": 1} and l[3] == {"solucion": "sol"} for l in cli.llamadas))

    def test_tambien_espera_cuando_la_plataforma_esta_instalando_algo(self):
        """Visto el 2026-09-20: Microsoft instaló sola una actualización
        (CustomControlsCore) y el PublishXml dio 429 con OTRO mensaje."""
        cli = ClienteEnSecuencia([BLOQUEO_PUBLICAR, (204, None, {})])
        self.assertEqual(self.escribir(cli)[0], 204)
        self.assertEqual(self.esperas, [c.ESPERA_BLOQUEO_SEGUNDOS])

    def test_se_rinde_despues_del_maximo_y_devuelve_el_429(self):
        cli = ClienteEnSecuencia([BLOQUEO] * (c.REINTENTOS_BLOQUEO + 1))
        est, cuerpo, _ = self.escribir(cli)
        self.assertEqual(est, 429)
        self.assertIn("CustomizationLockException", str(cuerpo))
        self.assertEqual(len(cli.llamadas), c.REINTENTOS_BLOQUEO + 1)
        self.assertEqual(len(self.esperas), c.REINTENTOS_BLOQUEO)

    def test_otro_429_o_cualquier_otro_error_no_se_reintenta(self):
        for resp in [(429, {"error": "Rate limit exceeded"}, {}), (400, {"error": "An unexpected error occurred."}, {}), (500, None, {})]:
            with self.subTest(resp[0]):
                cli = ClienteEnSecuencia([resp, (204, None, {})])
                self.assertEqual(self.escribir(cli)[0], resp[0])
                self.assertEqual(len(cli.llamadas), 1)
        self.assertEqual(self.esperas, [])


class LasHerramientasLaUsan(unittest.TestCase):
    def test_ninguna_herramienta_escribe_metadatos_por_fuera(self):
        """Toda escritura (POST, PUT) de las herramientas pasa por `escribir_metadatos`."""
        import re
        for archivo in ("tabla.py", "choice_global.py", "relacion.py", "clave.py", "rol.py"):
            with self.subTest(archivo):
                fuente = open(os.path.join(os.path.dirname(_AQUI), archivo), encoding="utf-8").read()
                self.assertEqual(re.findall(r'dv\.call\(\s*"(?:POST|PUT|PATCH|DELETE)"', fuente), [])
                self.assertIn("escribir_metadatos(", fuente)


if __name__ == "__main__":
    unittest.main()
