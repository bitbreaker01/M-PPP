"""BP-PP-197: ningún nombre visible lleva tildes, ñ ni otro carácter fuera de
ASCII. Cada herramienta lo exige SIN tocar la red. Las descripciones son prosa
y sí pueden llevarlos."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import _comun  # noqa: E402
import choice_global  # noqa: E402
import clave  # noqa: E402
import perfil_columnas  # noqa: E402
import relacion  # noqa: E402
import rol  # noqa: E402
import tabla  # noqa: E402
import test_clave  # noqa: E402
import test_perfil_columnas  # noqa: E402
import test_relacion  # noqa: E402
import test_rol  # noqa: E402
import test_tabla  # noqa: E402
from cliente_simulado import FabricaCentinela  # noqa: E402
from fixtures import COMPONENTE_VALIDO, IDENTIDAD_VALIDA, playbook_md  # noqa: E402

# herramienta, identidad, playbook válido, rutas de CADA nombre visible del formato
CASOS = [
    (choice_global, IDENTIDAD_VALIDA, COMPONENTE_VALIDO, [["displayname"], ["opciones", 0, "etiqueta"]]),
    (tabla, test_tabla.IDENT, test_tabla.COMPLETO, [["displayname"], ["displayname_plural"], ["primaria", "displayname"], ["columnas", 0, "displayname"]]),
    (relacion, test_relacion.IDENT, test_relacion.BASE, [["lookup", "displayname"]]),
    (clave, test_clave.IDENT, test_clave.BASE, [["displayname"]]),
    (rol, test_rol.IDENT, test_rol.BASE, [["nombre"]]),
    (perfil_columnas, test_perfil_columnas.IDENT, test_perfil_columnas.BASE, [["nombre"]]),
]


def con_sufijo(obj, ruta, sufijo):
    n = copy.deepcopy(obj)
    nodo = n
    for p in ruta[:-1]:
        nodo = nodo[p]
    nodo[ruta[-1]] = nodo[ruta[-1]] + sufijo
    return n


def correr(herramienta, ident, datos):
    centinela = FabricaCentinela()
    with tempfile.TemporaryDirectory() as dd:
        ruta = os.path.join(dd, "playbook.md")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(playbook_md(ident, datos))
        return herramienta.construir(ruta, False, centinela) + (centinela.llamada,)


class Validador(unittest.TestCase):
    def test_acepta_ascii_y_rechaza_lo_demas_nombrando_los_caracteres(self):
        _comun.exigir_sin_tildes("KEY - MPPP - Plan - Codigo (v2) #1", "'displayname'")
        for texto, malo in (("Código", "ó"), ("Año", "ñ"), ("Ü", "Ü"), ("Fila – numero", "–"), ("«Plan»", "«")):
            with self.subTest(texto):
                with self.assertRaises(_comun.ErrorPlaybook) as e:
                    _comun.exigir_sin_tildes(texto, "'displayname'")
                self.assertIn("BP-PP-197", str(e.exception))
                self.assertIn(malo, str(e.exception))
                self.assertIn("'displayname'", str(e.exception))


class CadaHerramienta(unittest.TestCase):
    def test_un_nombre_visible_con_tilde_o_enie_es_error_sin_tocar_la_red(self):
        for herramienta, ident, base, rutas in CASOS:
            for ruta in rutas:
                for sufijo in (" técnico", " año"):
                    with self.subTest(f"{herramienta.__name__} {ruta} {sufijo}"):
                        estado, _, detalle, toco_la_red = correr(herramienta, ident, con_sufijo(base, ruta, sufijo))
                        self.assertEqual(estado, "error", detalle)
                        self.assertIn("BP-PP-197", detalle)
                        self.assertFalse(toco_la_red)

    def test_los_playbooks_validos_de_las_pruebas_no_llevan_tildes_en_sus_nombres(self):
        """Si esta prueba falla, las demás pruebas de esa herramienta están usando un playbook que la regla rechaza."""
        for herramienta, ident, base, rutas in CASOS:
            for ruta in rutas:
                nodo = base
                for p in ruta:
                    nodo = nodo[p]
                with self.subTest(f"{herramienta.__name__} {ruta}"):
                    _comun.exigir_sin_tildes(nodo, str(ruta))

    def test_la_descripcion_si_puede_llevar_tildes(self):
        for herramienta, ident, base, _ in CASOS:
            clave_desc = "descripcion" if "descripcion" in base else None
            if clave_desc is None:
                continue
            with self.subTest(herramienta.__name__):
                estado, _, detalle, _ = correr(herramienta, ident, dict(base, descripcion=base["descripcion"] + " Descripción con ñ."))
                self.assertNotIn("BP-PP-197", detalle)

    def test_las_etiquetas_de_un_si_no_tampoco_llevan_tilde(self):
        i = next(i for i, c in enumerate(test_tabla.COMPLETO["columnas"]) if c["tipo"] == "sino")
        datos = copy.deepcopy(test_tabla.COMPLETO)
        datos["columnas"][i]["etiqueta_si"] = "Sí"
        estado, _, detalle, toco_la_red = correr(tabla, test_tabla.IDENT, datos)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("BP-PP-197", detalle)
        self.assertFalse(toco_la_red)


class ExcepcionesAprobadas(unittest.TestCase):
    """D-10 (aprobador, 2026-09-21): siete nombres ya construidos que el Web API no
    deja cambiar quedan como excepción. La lista está FIJADA acá a propósito: una
    excepción nueva no se agrega editando un JSON, hay que cambiar esta prueba,
    y eso obliga a pasar por el aprobador."""
    CLAVES = ["KEY - MPPP - Autorización - Autorizado y plan", "KEY - MPPP - Fila - Solicitud y número de fila", "KEY - MPPP - Parámetro - Nombre y versión",
              "KEY - MPPP - Plan - Código", "KEY - MPPP - Regla - Código", "KEY - MPPP - Resultado de regla - Solicitud y código de regla"]
    SI_NO = {"sanic_mppp_tbl_solicitud.sanic_requiererevision": "Requiere revisión"}

    def test_la_lista_es_exactamente_la_de_d10(self):
        self.assertEqual(sorted(_comun.EXCEPCIONES_NOMBRES["nombres_visibles"]), self.CLAVES)
        self.assertEqual(_comun.EXCEPCIONES_NOMBRES["optionset_si_no"], self.SI_NO)

    def test_un_nombre_exceptuado_pasa_y_uno_parecido_no(self):
        for nombre in self.CLAVES:
            _comun.exigir_sin_tildes(nombre, "'displayname'")
        for parecido in ("KEY - MPPP - Plan - Códigos", "key - mppp - plan - código", "KEY - MPPP - Cliente - Código"):
            with self.assertRaises(_comun.ErrorPlaybook):
                _comun.exigir_sin_tildes(parecido, "'displayname'")

    def test_la_herramienta_de_claves_acepta_el_nombre_exceptuado(self):
        datos = dict(test_clave.BASE, nombre="sanic_mppp_key_autorizado_codigo", displayname="KEY - MPPP - Plan - Código")
        estado, _, detalle, _ = correr(clave, test_clave.IDENT, datos)
        self.assertNotIn("BP-PP-197", detalle)


if __name__ == "__main__":
    unittest.main()
