"""Comparación de un perfil de seguridad de columna contra el XML de la
solución exportada. Usa la muestra REAL de `playbooks/perfil-columnas/muestras/`."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_perfil_columnas as mp  # noqa: E402

XML = "<ImportExportXml>" + open(os.path.join(_RAIZ, "playbooks", "perfil-columnas", "muestras", "zzensayo.perfil.solucion.xml"), encoding="utf-8").read() + "</ImportExportXml>"
F = "sanic_mppp_tbl_fila"
# Lo que tenía el perfil descartable del que salió la muestra: lectura sola sobre las dos columnas.
MUESTRA = {"tipo": "perfil-columnas", "nombre": "CSP - MPPP - ZZ Ensayo", "descripcion": "Perfil descartable de ensayo.",
           "permisos": [{"tabla": F, "columna": "sanic_numerocuenta", "leer": True, "crear": False, "actualizar": False},
                        {"tabla": F, "columna": "sanic_numeroidentificacion", "leer": True, "crear": False, "actualizar": False}]}


def cambiar(d, ruta, valor):
    n = copy.deepcopy(d)
    nodo = n
    for p in ruta[:-1]:
        nodo = nodo[p]
    nodo[ruta[-1]] = valor
    return n


class ContraLaMuestraReal(unittest.TestCase):
    def test_coincide(self):
        self.assertEqual(mp.comparar_con_xml(XML, MUESTRA), [])

    def test_no_esta(self):
        difs = mp.comparar_con_xml(XML, cambiar(MUESTRA, ["nombre"], "CSP - MPPP - ZZ Inexistente"))
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        casos = [("descripcion", cambiar(MUESTRA, ["descripcion"], "Otra.")),
                 (f"{F}.sanic_numerocuenta.CanUpdate: xml='0' playbook='4'", cambiar(MUESTRA, ["permisos", 0, "actualizar"], True)),
                 (f"falta el permiso sobre {F}.sanic_otra", cambiar(MUESTRA, ["permisos", 1, "columna"], "sanic_otra")),
                 (f"sobra el permiso sobre {F}.sanic_numeroidentificacion", cambiar(MUESTRA, ["permisos"], MUESTRA["permisos"][:1]))]
        for esperado, datos in casos:
            with self.subTest(esperado):
                difs = mp.comparar_con_xml(XML, datos)
                self.assertTrue(any(esperado in d for d in difs), difs)

    def test_leer_sin_enmascarar_distinto_de_cero_es_una_diferencia(self):
        xml = XML.replace("<CanReadUnmasked>0</CanReadUnmasked>", "<CanReadUnmasked>3</CanReadUnmasked>", 1)
        self.assertNotEqual(xml, XML)
        self.assertTrue(any("CanReadUnmasked" in d for d in mp.comparar_con_xml(xml, MUESTRA)))


if __name__ == "__main__":
    unittest.main()
