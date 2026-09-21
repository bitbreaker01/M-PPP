"""El generador de playbooks de clave alternativa: lo generado es válido para
la herramienta, la sección 5 sale de la sección 2, los nombres no chocan, y
cada columna existe en los playbooks ya aprobados de su tabla o de su relación."""
import glob
import json
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "construir"))

import clave as cv  # noqa: E402
import playbook_clave as pc  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente, obtener_identidad  # noqa: E402

ESPECIFICACIONES = sorted(glob.glob(os.path.join(os.path.dirname(_AQUI), "claves", "*.json")))


def columnas_del_diseno():
    """tabla → {columna: (tipo, requerida, protegida)}, de los playbooks de tabla y de relación."""
    cols = {}
    for p in glob.glob(os.path.join(_RAIZ, "playbooks", "tabla", "sanic_*.md")):
        c = obtener_componente(dividir_secciones(leer_texto(p)), "tabla")
        prim = c["primaria"]
        cols[c["nombre"]] = {prim["nombre"]: ("texto", prim["requerida"], False)}
        for k in c["columnas"]:
            cols[c["nombre"]][k["nombre"]] = (k["tipo"], k["requerida"], k["protegida"])
    for p in glob.glob(os.path.join(_RAIZ, "playbooks", "relacion", "sanic_*.md")):
        c = obtener_componente(dividir_secciones(leer_texto(p)), "relacion")
        cols[c["tabla_hija"]][c["lookup"]["nombre"]] = ("lookup", c["lookup"]["requerida"], False)
    return cols


class Generador(unittest.TestCase):
    def test_todo_playbook_generado_es_valido_y_no_se_contradice(self):
        self.assertTrue(ESPECIFICACIONES)
        for ruta in ESPECIFICACIONES:
            with self.subTest(os.path.basename(ruta)):
                esp = json.load(open(ruta, encoding="utf-8"))
                md = pc.generar(esp)
                sec = dividir_secciones(md)
                datos = obtener_componente(sec, "clave")
                cv.validar_playbook(datos, obtener_identidad(sec))
                self.assertEqual(datos, esp["componente"])
                f1 = next(l for l in md.split("\n") if l.startswith("| 1 | `GET EntityDefinitions"))
                self.assertIn(f"/Keys(LogicalName='{datos['nombre']}')", f1)
                f2 = next(l for l in md.split("\n") if l.startswith("| 2 | Columnas de la clave"))
                for c in datos["columnas"]:
                    self.assertIn(f"`{c}`", f2)

    def test_ningun_nombre_choca_ni_hay_dos_claves_iguales_en_una_tabla(self):
        comps = [json.load(open(r, encoding="utf-8"))["componente"] for r in ESPECIFICACIONES]
        nombres = [c["nombre"] for c in comps]
        self.assertEqual(len(nombres), len(set(nombres)))
        juegos = [(c["tabla"], tuple(sorted(c["columnas"]))) for c in comps]
        self.assertEqual(len(juegos), len(set(juegos)))

    def test_cada_columna_existe_en_el_diseno_admite_clave_y_no_esta_protegida(self):
        cols = columnas_del_diseno()
        for ruta in ESPECIFICACIONES:
            esp = json.load(open(ruta, encoding="utf-8"))
            c = esp["componente"]
            for col in c["columnas"]:
                with self.subTest(f"{c['nombre']} · {col}"):
                    self.assertIn(col, cols[c["tabla"]], "la columna no está en el playbook de la tabla ni en el de una relación")
                    tipo, _, protegida = cols[c["tabla"]][col]
                    self.assertIn(tipo, ("texto", "entero", "lookup", "choice", "fechahora", "fecha", "autonumerico"))
                    self.assertFalse(protegida)

    def test_una_columna_opcional_en_una_clave_se_advierte_en_el_playbook(self):
        """Con un valor nulo en una columna de la clave, la plataforma no exige unicidad."""
        cols = columnas_del_diseno()
        for ruta in ESPECIFICACIONES:
            esp = json.load(open(ruta, encoding="utf-8"))
            c = esp["componente"]
            opcionales = [col for col in c["columnas"] if not cols[c["tabla"]][col][1]]
            with self.subTest(c["nombre"]):
                md = pc.generar(esp)
                self.assertEqual(sorted(esp["columnas_opcionales"]), sorted(opcionales))
                for col in opcionales:
                    self.assertIn(f"`{col}` es opcional", md)
                if not opcionales:
                    self.assertIn("Todas las columnas de la clave son requeridas", md)


if __name__ == "__main__":
    unittest.main()
