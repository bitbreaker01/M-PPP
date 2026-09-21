"""El generador de enums de C#: nombres válidos, valores exactos del playbook, y el archivo del repo al día."""
import os
import re
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))

import generar_enums as ge  # noqa: E402


class Enums(unittest.TestCase):
    def test_pascal(self):
        casos = {"Rechazada en AS400": "RechazadaEnAS400", "No es correo nuevo": "NoEsCorreoNuevo", "En proceso": "EnProceso", "USD": "USD", "Envia a revision": "EnviaARevision"}
        for texto, esperado in casos.items():
            self.assertEqual(ge.pascal(texto), esperado)

    def test_el_archivo_del_repo_esta_al_dia(self):
        self.assertEqual(open(ge.DESTINO, encoding="utf-8").read(), ge.generar(), "correr herramientas/codigo/generar_enums.py")

    def test_lo_generado_trae_los_valores_exactos_y_nombres_validos_de_csharp(self):
        texto = ge.generar()
        self.assertIn("public enum EstadoDeLaFila", texto)
        self.assertIn("Validada = 159460003,", texto)
        self.assertIn("RechazadaEnAS400 = 159460006,", texto)
        for nombre in re.findall(r"^\s+(\w+) = \d+,$", texto, re.M):
            self.assertRegex(nombre, r"^[A-Za-z_][A-Za-z0-9_]*$")
        self.assertEqual(len(re.findall(r"public enum ", texto)), 14)


if __name__ == "__main__":
    unittest.main()
