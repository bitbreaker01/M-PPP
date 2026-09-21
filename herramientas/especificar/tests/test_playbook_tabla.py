"""El generador de playbooks de tabla: lo que dice la sección 5 (valores
esperados) tiene que salir de la sección 2, sin contradecirla."""
import copy
import glob
import json
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "construir"))

import playbook_tabla as pt  # noqa: E402
import tabla as tb  # noqa: E402
from _comun import dividir_secciones, obtener_componente, obtener_identidad  # noqa: E402

ESPECIFICACIONES = sorted(glob.glob(os.path.join(os.path.dirname(_AQUI), "tablas", "*.json")))


def fila3(md):
    return next(l for l in md.split("\n") if l.startswith("| 3 | Columnas"))


class Generador(unittest.TestCase):
    def setUp(self):
        self.esp = json.load(open(next(r for r in ESPECIFICACIONES if r.endswith("autorizado.json")), encoding="utf-8"))

    def test_la_primaria_cuenta_para_la_auditoria_esperada(self):
        """Autorizado no tiene más columna que la primaria, que hereda la
        auditoría de la tabla: la verificación no puede decir 'ninguna auditada'."""
        self.assertIs(self.esp["componente"]["auditoria"], True)
        self.assertEqual(self.esp["componente"]["columnas"], [])
        f = fila3(pt.generar(self.esp))
        self.assertIn("todas auditadas", f)
        self.assertNotIn("ninguna auditada", f)

    def test_tabla_sin_auditoria(self):
        e = copy.deepcopy(self.esp)
        e["componente"]["auditoria"] = False
        self.assertIn("ninguna auditada", fila3(pt.generar(e)))

    def test_auditoria_mixta_nombra_las_auditadas_incluida_la_primaria(self):
        e = copy.deepcopy(self.esp)
        e["componente"]["columnas"] = [{"nombre": "sanic_x", "displayname": "X", "descripcion": "x.", "tipo": "texto", "largo": 5,
                                        "requerida": False, "protegida": False, "auditoria": False}]
        f = fila3(pt.generar(e))
        self.assertIn("auditadas: `sanic_nombre`", f)
        self.assertNotIn("`sanic_x`", f.split("auditadas:")[1])

    def test_todo_playbook_generado_es_valido_para_la_herramienta_y_no_se_contradice(self):
        for ruta in ESPECIFICACIONES:
            with self.subTest(os.path.basename(ruta)):
                esp = json.load(open(ruta, encoding="utf-8"))
                md = pt.generar(esp)
                sec = dividir_secciones(md)
                datos = obtener_componente(sec, "tabla")
                tb.validar_playbook(datos, obtener_identidad(sec))
                self.assertEqual(datos, esp["componente"])
                f = fila3(md)
                self.assertIn(f"Columnas ({1 + len(datos['columnas'])})", f)
                for c in [datos["primaria"]] + datos["columnas"]:
                    self.assertIn(f"`{c['nombre']}`", f)
                auditadas = [datos["auditoria"]] + [c["auditoria"] for c in datos["columnas"]]
                esperado = "todas auditadas" if all(auditadas) else "ninguna auditada" if not any(auditadas) else "auditadas:"
                self.assertIn(esperado, f)


if __name__ == "__main__":
    unittest.main()
