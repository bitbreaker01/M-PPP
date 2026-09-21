"""El generador de playbooks de relación: lo generado es válido para la
herramienta, la sección 5 sale de la sección 2, y los nombres no chocan."""
import glob
import json
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "construir"))

import playbook_relacion as pr  # noqa: E402
import relacion as rl  # noqa: E402
from _comun import dividir_secciones, obtener_componente, obtener_identidad  # noqa: E402

ESPECIFICACIONES = sorted(glob.glob(os.path.join(os.path.dirname(_AQUI), "relaciones", "*.json")))


class Generador(unittest.TestCase):
    def test_todo_playbook_generado_es_valido_y_no_se_contradice(self):
        self.assertTrue(ESPECIFICACIONES)
        for ruta in ESPECIFICACIONES:
            with self.subTest(os.path.basename(ruta)):
                esp = json.load(open(ruta, encoding="utf-8"))
                md = pr.generar(esp)
                sec = dividir_secciones(md)
                datos = obtener_componente(sec, "relacion")
                rl.validar_playbook(datos, obtener_identidad(sec))
                self.assertEqual(datos, esp["componente"])
                k = datos["lookup"]
                f3 = next(l for l in md.split("\n") if l.startswith("| 3 | El lookup"))
                self.assertIn(f"requerida = {'true' if k['requerida'] else 'false'}", f3)
                self.assertIn(f"auditoría = {'true' if k['auditoria'] else 'false'}", f3)
                f2 = next(l for l in md.split("\n") if l.startswith("| 2 | Cascadas"))
                for accion, valor in rl.CASCADAS[datos["comportamiento"]].items():
                    self.assertIn(f"`{accion} = {valor}`", f2)

    def test_ningun_nombre_de_relacion_ni_de_lookup_choca(self):
        comps = [json.load(open(r, encoding="utf-8"))["componente"] for r in ESPECIFICACIONES]
        nombres = [c["nombre"] for c in comps]
        self.assertEqual(len(nombres), len(set(nombres)), "dos relaciones con el mismo nombre")
        lookups = [(c["tabla_hija"], c["lookup"]["nombre"]) for c in comps]
        self.assertEqual(len(lookups), len(set(lookups)), "dos lookups con el mismo nombre en la misma tabla")

    def test_una_tabla_hija_tiene_a_lo_sumo_una_relacion_parental(self):
        from collections import Counter
        comps = [json.load(open(r, encoding="utf-8"))["componente"] for r in ESPECIFICACIONES]
        cuenta = Counter(c["tabla_hija"] for c in comps if c["comportamiento"] == "parental")
        self.assertEqual([t for t, n in cuenta.items() if n > 1], [])


if __name__ == "__main__":
    unittest.main()
