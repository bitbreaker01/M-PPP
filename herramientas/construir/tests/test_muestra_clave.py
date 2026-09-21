"""Comparación de una clave alternativa contra el XML de la solución
exportada. Usa la muestra REAL de `playbooks/clave/muestras/`."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_clave as mc  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente  # noqa: E402

M = os.path.join(_RAIZ, "playbooks", "clave", "muestras")
XML = ("<ImportExportXml><Entities><Entity><Name>sanic_mppp_tbl_zzclave</Name><EntityInfo><entity Name=\"sanic_mppp_tbl_zzclave\">"
       + open(os.path.join(M, "zzensayo.claves.solucion.xml"), encoding="utf-8").read() + "</entity></EntityInfo></Entity></Entities></ImportExportXml>")
COMPUESTA = obtener_componente(dividir_secciones(leer_texto(os.path.join(_RAIZ, "playbooks", "clave", "ensayos", "sanic_mppp_key_zzclave_padre_numero.md"))), "clave")


def cambiar(d, clave, valor):
    n = copy.deepcopy(d)
    n[clave] = valor
    return n


class ContraLaMuestraReal(unittest.TestCase):
    def test_coincide_aunque_el_xml_traiga_las_columnas_en_otro_orden(self):
        self.assertEqual(COMPUESTA["columnas"], ["sanic_zzpadreid", "sanic_numero"])  # el XML las trae al revés
        self.assertEqual(mc.comparar_con_xml(XML, COMPUESTA, 1033), [])

    def test_no_esta(self):
        difs = mc.comparar_con_xml(XML, cambiar(COMPUESTA, "nombre", "sanic_mppp_key_zzclave_inexistente"), 1033)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_esta_pero_en_otra_tabla(self):
        difs = mc.comparar_con_xml(XML, cambiar(COMPUESTA, "tabla", "sanic_mppp_tbl_zzpadre"), 1033)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        casos = [("columnas", cambiar(COMPUESTA, "columnas", ["sanic_numero"])),
                 ("columnas", cambiar(COMPUESTA, "columnas", ["sanic_numero", "sanic_zzpadreid", "sanic_codigo"])),
                 ("displayname", cambiar(COMPUESTA, "displayname", "KEY - MPPP - Otro"))]
        for esperado, datos in casos:
            with self.subTest(esperado + str(datos["columnas"])):
                difs = mc.comparar_con_xml(XML, datos, 1033)
                self.assertTrue(any(d.startswith(esperado) for d in difs), difs)

    def test_una_etiqueta_en_otro_idioma_es_una_diferencia(self):
        xml = XML.replace('<displayname description="KEY - MPPP - ZZ Clave - padre_numero" languagecode="1033" />',
                          '<displayname description="KEY - MPPP - ZZ Clave - padre_numero" languagecode="1033" /><displayname description="x" languagecode="3082" />')
        self.assertNotEqual(xml, XML)
        self.assertTrue(any("otro idioma" in d for d in mc.comparar_con_xml(xml, COMPUESTA, 1033)))


if __name__ == "__main__":
    unittest.main()
