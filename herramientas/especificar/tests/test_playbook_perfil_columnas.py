"""El playbook del perfil de seguridad de columna: válido para la herramienta,
fiel a `diseno/04-matriz-privilegios.md` §4, y sin contradecirse."""
import os
import re
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "construir"))

import perfil_columnas as pc  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente, obtener_identidad  # noqa: E402

RUTA = os.path.join(_RAIZ, "playbooks", "perfil-columnas", "csp_mppp_datos_sensibles.md")


class PerfilDeFase1(unittest.TestCase):
    def setUp(self):
        self.md = leer_texto(RUTA)
        sec = dividir_secciones(self.md)
        self.datos, self.ident = obtener_componente(sec, "perfil-columnas"), obtener_identidad(sec)

    def test_es_valido_para_la_herramienta(self):
        pc.validar_playbook(self.datos, self.ident)

    def test_las_columnas_son_las_de_la_matriz_y_el_perfil_es_de_solo_lectura(self):
        matriz = open(os.path.join(_RAIZ, "diseno", "04-matriz-privilegios.md"), encoding="utf-8").read()
        seccion = matriz[matriz.index("## 4. Column security profile"):matriz.index("## 5. ")]
        self.assertIn(f'"{self.datos["nombre"]}"', seccion.split("\n")[0])
        columnas = set(re.findall(r"`(sanic_mppp_tbl_[a-z]+)\.(sanic_[a-z]+)`", seccion.split("\n")[2]))
        self.assertEqual(columnas, {(p["tabla"], p["columna"]) for p in self.datos["permisos"]})
        fila = next(l for l in seccion.split("\n") if l.startswith(f"| `{self.datos['nombre']}` |"))
        self.assertEqual([c.strip() for c in fila.split("|")[2:5]], ["sí", "no", "no"])
        for p in self.datos["permisos"]:
            self.assertEqual((p["leer"], p["crear"], p["actualizar"]), (True, False, False), p["columna"])

    def test_las_columnas_estan_protegidas_en_el_playbook_de_su_tabla(self):
        for p in self.datos["permisos"]:
            tabla = obtener_componente(dividir_secciones(leer_texto(os.path.join(_RAIZ, "playbooks", "tabla", p["tabla"] + ".md"))), "tabla")
            columna = next(c for c in tabla["columnas"] if c["nombre"] == p["columna"])
            self.assertTrue(columna["protegida"], p["columna"])

    def test_la_seccion_5_nombra_cada_permiso_de_la_seccion_2(self):
        fila = next(l for l in self.md.split("\n") if l.startswith("| 2 | `GET fieldpermissions`"))
        for p in self.datos["permisos"]:
            self.assertIn(f"`{p['tabla']}.{p['columna']}`", fila)
        self.assertIn("exactamente dos" if len(self.datos["permisos"]) == 2 else "__", fila)


if __name__ == "__main__":
    unittest.main()
