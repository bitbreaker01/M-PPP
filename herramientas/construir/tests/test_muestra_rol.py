"""Comparación de un rol contra el XML de la solución exportada. Usa la
muestra REAL de `playbooks/rol/muestras/`."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_rol as mr  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente, obtener_identidad  # noqa: E402

XML = "<ImportExportXml>" + open(os.path.join(_RAIZ, "playbooks", "rol", "muestras", "zzensayo.rol.solucion.xml"), encoding="utf-8").read() + "</ImportExportXml>"
_SEC = dividir_secciones(leer_texto(os.path.join(_RAIZ, "playbooks", "rol", "ensayos", "zz_nuevo_mas.md")))
NUEVO, IDENT = obtener_componente(_SEC, "rol"), obtener_identidad(_SEC)
C, F = "sanic_mppp_tbl_cliente", "sanic_mppp_tbl_fila"


def cambiar(d, ruta, valor, borrar=False):
    n = copy.deepcopy(d)
    nodo = n
    for p in ruta[:-1]:
        nodo = nodo[p]
    if borrar:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    return n


class ContraLaMuestraReal(unittest.TestCase):
    def test_coincide(self):
        self.assertEqual(mr.comparar_con_xml(XML, NUEVO, IDENT), [])

    def test_no_esta(self):
        difs = mr.comparar_con_xml(XML, cambiar(NUEVO, ["nombre"], "SR - MPPP - ZZ Inexistente"), IDENT)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        casos = [(f"falta prvDelete{C}", cambiar(NUEVO, ["tablas", C, "borrar"], "organizacion")),
                 (f"sobra prvAssign{C}", cambiar(NUEVO, ["tablas", C, "asignar"], None, borrar=True)),
                 (f"sobra prvAppend{F}", cambiar(NUEVO, ["tablas", F, "anexar"], None, borrar=True)),
                 (f"prvAppendTo{F}: xml='Local' playbook='Global'", cambiar(NUEVO, ["tablas", F, "anexar_a"], "organizacion")),
                 ("falta prvReadAccount", cambiar(NUEVO, ["otros_privilegios", "prvReadAccount"], "organizacion")),
                 ("prvBulkDelete: xml='Global' playbook='Deep'", cambiar(NUEVO, ["otros_privilegios", "prvBulkDelete"], "unidad_e_hijas")),
                 ("descripcion", cambiar(NUEVO, ["descripcion"], "Otra."))]
        for esperado, datos in casos:
            with self.subTest(esperado):
                difs = mr.comparar_con_xml(XML, datos, IDENT)
                self.assertTrue(any(esperado in d for d in difs), difs)

    def test_los_privilegios_del_rol_base_no_son_sobrantes(self):
        """El XML no sabe cuáles vienen de la base: eso lo comprueba `rol.py` contra el entorno."""
        self.assertFalse([d for d in mr.comparar_con_xml(XML, NUEVO, IDENT) if "prvReadAppModule" in d])

    def test_una_tabla_entera_de_la_solucion_que_el_playbook_no_nombra_es_sobrante(self):
        difs = mr.comparar_con_xml(XML, cambiar(NUEVO, ["tablas", F], None, borrar=True), IDENT)
        self.assertEqual(len([d for d in difs if d.startswith("sobra ") and d.split()[1].endswith(F)]), 4, difs)


if __name__ == "__main__":
    unittest.main()
