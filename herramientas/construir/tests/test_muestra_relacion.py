"""Comparación de una relación contra el XML de la solución exportada. Usa las
muestras REALES de `playbooks/relacion/muestras/`."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_relacion as mr  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente  # noqa: E402

M = os.path.join(_RAIZ, "playbooks", "relacion", "muestras")
XML = ("<ImportExportXml><Entities><Entity><Name>sanic_mppp_tbl_zzhija</Name><EntityInfo><entity Name=\"sanic_mppp_tbl_zzhija\"><attributes>"
       + open(os.path.join(M, "zzensayo.lookup.solucion.xml"), encoding="utf-8").read() + "</attributes></entity></EntityInfo></Entity></Entities>"
       + open(os.path.join(M, "zzensayo.relaciones.solucion.xml"), encoding="utf-8").read() + "</ImportExportXml>")
TERCERA = obtener_componente(dividir_secciones(leer_texto(os.path.join(_RAIZ, "playbooks", "relacion", "ensayos", "sanic_mppp_zzotro_zzhija_tercera.md"))), "relacion")


def cambiar(d, ruta, valor):
    n = copy.deepcopy(d)
    nodo = n
    for p in ruta[:-1]:
        nodo = nodo[p]
    nodo[ruta[-1]] = valor
    return n


class ContraLaMuestraReal(unittest.TestCase):
    def test_coincide(self):
        self.assertEqual(mr.comparar_con_xml(XML, TERCERA, 1033), [])

    def test_una_tabla_del_sistema_viene_con_su_nombre_de_esquema(self):
        """El XML exportado nombra las tablas por su nombre de esquema (`SystemUser`);
        el playbook, por el lógico (`systemuser`). No es una diferencia."""
        ruta = os.path.join(_RAIZ, "playbooks", "relacion", "ensayos", "sanic_mppp_systemuser_zzhija_digitadapor.md")
        datos = obtener_componente(dividir_secciones(leer_texto(ruta)), "relacion")
        difs = mr.comparar_con_xml(XML, datos, 1033)
        self.assertFalse([d for d in difs if d.startswith("tabla_padre")], difs)
        otra = mr.comparar_con_xml(XML, cambiar(datos, ["tabla_padre"], "team"), 1033)
        self.assertTrue([d for d in otra if d.startswith("tabla_padre")], otra)

    def test_no_esta(self):
        difs = mr.comparar_con_xml(XML, cambiar(TERCERA, ["nombre"], "sanic_mppp_zzotro_zzhija_inexistente"), 1033)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        casos = [("tabla_padre", cambiar(TERCERA, ["tabla_padre"], "sanic_mppp_tbl_zzpadre")),
                 ("comportamiento", cambiar(TERCERA, ["comportamiento"], "parental")),
                 ("comportamiento", cambiar(TERCERA, ["comportamiento"], "quitar_vinculo")),
                 ("lookup.requerida", cambiar(TERCERA, ["lookup", "requerida"], False)),
                 ("lookup.auditoria", cambiar(TERCERA, ["lookup", "auditoria"], False)),
                 ("lookup.displayname", cambiar(TERCERA, ["lookup", "displayname"], "Otro")),
                 ("lookup.descripcion", cambiar(TERCERA, ["lookup", "descripcion"], "Otra.")),
                 ("falta la columna lookup", cambiar(TERCERA, ["lookup", "nombre"], "sanic_inexistenteid"))]
        for esperado, datos in casos:
            with self.subTest(esperado):
                difs = mr.comparar_con_xml(XML, datos, 1033)
                self.assertTrue(any(esperado in d for d in difs), difs)


if __name__ == "__main__":
    unittest.main()
