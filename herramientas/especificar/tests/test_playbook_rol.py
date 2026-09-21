"""El generador de playbooks de rol: lo generado es válido para la herramienta,
la sección 5 sale de la sección 2, y cada rol coincide CELDA POR CELDA con la
matriz de privilegios del diseño (`diseno/04-matriz-privilegios.md`)."""
import glob
import json
import os
import re
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "construir"))

import playbook_rol as pr  # noqa: E402
import rol as rl  # noqa: E402
from _comun import dividir_secciones, obtener_componente, obtener_identidad  # noqa: E402

ESPECIFICACIONES = sorted(glob.glob(os.path.join(os.path.dirname(_AQUI), "roles", "*.json")))
CODIGOS = {"C": "crear", "R": "leer", "W": "escribir", "D": "borrar", "Ap": "anexar", "At": "anexar_a", "As": "asignar"}
ALCANCE = {"O": "organizacion", "U": "usuario"}


def leer_matriz():
    """{rol: {tabla lógica: {acción: alcance}}}, de las tablas de `04` §2 y §3."""
    texto = open(os.path.join(_RAIZ, "diseno", "04-matriz-privilegios.md"), encoding="utf-8").read()
    matriz = {}
    for seccion in re.split(r"\n## ", texto):
        if not seccion.startswith(("2. Roles humanos", "3. Identidades de aplicación")):
            continue
        filas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in seccion.split("\n") if l.startswith("|")]
        roles = [re.match(r"SR - MPPP - [^(]+", c).group(0).strip() for c in filas[0][1:]]
        for fila in filas[2:]:
            if not re.fullmatch(r"[A-Za-z, ]+", fila[0]):
                continue  # "**Borrado** en cualquier tabla", "CorridaHistorico (fase 3)", "Privilegios varios", "Custom API"
            for nombre_tabla in [t.strip() for t in fila[0].split(",")]:
                tabla = "sanic_mppp_tbl_" + nombre_tabla.lower()
                if not os.path.exists(os.path.join(_RAIZ, "playbooks", "tabla", tabla + ".md")):
                    continue  # "Custom API", "Privilegios varios": no son tablas
                for rol_, celda in zip(roles, fila[1:]):
                    celda = re.sub(r"\(.*?\)", "", celda).replace("*", "").strip()
                    if celda == "—":
                        continue
                    codigos, alcance = [x.strip() for x in celda.split(":")]
                    matriz.setdefault(rol_, {})[tabla] = {CODIGOS[c]: ALCANCE[alcance] for c in codigos.split()}
    return matriz


class ContraLaMatriz(unittest.TestCase):
    def test_el_lector_de_la_matriz_entiende_el_documento(self):
        m = leer_matriz()
        self.assertEqual(m["SR - MPPP - Ejecutivo"]["sanic_mppp_tbl_solicitud"], {"leer": "organizacion", "escribir": "organizacion", "anexar_a": "organizacion"})
        self.assertEqual(m["SR - MPPP - Supervisor"]["sanic_mppp_tbl_solicitud"], {"leer": "organizacion", "anexar_a": "organizacion"})
        self.assertEqual(set(m["SR - MPPP - Administrador tecnico"]), {"sanic_mppp_tbl_parametro", "sanic_mppp_tbl_regla"})
        self.assertIn("asignar", m["SR - MPPP - Administrador de planes"]["sanic_mppp_tbl_cliente"])
        self.assertNotIn("sanic_mppp_tbl_fila", m["SR - MPPP - Administrador de planes"])

    def test_cada_rol_coincide_celda_por_celda_con_la_matriz(self):
        m = leer_matriz()
        self.assertTrue(ESPECIFICACIONES)
        for ruta in ESPECIFICACIONES:
            comp = json.load(open(ruta, encoding="utf-8"))["componente"]
            with self.subTest(comp["nombre"]):
                self.assertEqual(comp["tablas"], m[comp["nombre"]])

    def test_ningun_rol_humano_borra(self):
        for ruta in ESPECIFICACIONES:
            comp = json.load(open(ruta, encoding="utf-8"))["componente"]
            self.assertFalse([t for t, a in comp["tablas"].items() if "borrar" in a], comp["nombre"])


class Generador(unittest.TestCase):
    def test_todo_playbook_generado_es_valido_y_no_se_contradice(self):
        for ruta in ESPECIFICACIONES:
            with self.subTest(os.path.basename(ruta)):
                esp = json.load(open(ruta, encoding="utf-8"))
                md = pr.generar(esp)
                sec = dividir_secciones(md)
                datos = obtener_componente(sec, "rol")
                rl.validar_playbook(datos, obtener_identidad(sec))
                self.assertEqual(datos, esp["componente"])
                for tabla, acciones in datos["tablas"].items():
                    fila = next(l for l in md.split("\n") if l.startswith(f"| `{tabla}` |"))
                    for accion, alcance in acciones.items():
                        self.assertIn(f"`prv{rl.ACCIONES[accion]}{tabla}` = {rl.ALCANCES[alcance]}", fila)
                    self.assertEqual(fila.count("`prv"), len(acciones))

    def test_ningun_nombre_choca(self):
        nombres = [json.load(open(r, encoding="utf-8"))["componente"]["nombre"] for r in ESPECIFICACIONES]
        self.assertEqual(len(nombres), len(set(nombres)))


if __name__ == "__main__":
    unittest.main()
