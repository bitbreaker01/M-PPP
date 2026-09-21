"""Pruebas de `_comun.py`: parseo de los dos bloques ```json``` del playbook
(Identidad y Qué se crea) y sus validaciones de forma. Ninguna toca el
entorno ni la red."""
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_CONSTRUIR = os.path.dirname(_AQUI)
if _CONSTRUIR not in sys.path:
    sys.path.insert(0, _CONSTRUIR)

import _comun as c  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, COMPONENTE_VALIDO, identidad, componente, playbook_md  # noqa: E402


class DividirSecciones(unittest.TestCase):
    def test_separa_secciones_por_encabezado_de_nivel_2(self):
        texto = playbook_md()
        secciones = c.dividir_secciones(texto)
        self.assertIn("1", secciones)
        self.assertIn("2", secciones)
        self.assertIn("Identidad", secciones["1"]["titulo"])
        self.assertIn("Qué se crea", secciones["2"]["titulo"])

    def test_no_encuentra_seccion_que_no_existe(self):
        secciones = c.dividir_secciones(playbook_md(con_seccion_1=False))
        self.assertNotIn("1", secciones)


class ObtenerBloqueJson(unittest.TestCase):
    def test_seccion_ausente_es_error(self):
        secciones = c.dividir_secciones(playbook_md(con_seccion_2=False))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_bloque_json(secciones, "2", "Qué se crea")

    def test_sin_bloques_json_es_error(self):
        texto = playbook_md() + "\n## 4. Vacía\n\nsin bloque json acá\n"
        secciones = c.dividir_secciones(texto)
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_bloque_json(secciones, "4", "Vacía")

    def test_dos_bloques_json_en_la_misma_seccion_es_error(self):
        texto = playbook_md(bloques_extra_seccion_2=1)
        secciones = c.dividir_secciones(texto)
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_bloque_json(secciones, "2", "Qué se crea")

    def test_json_invalido_es_error(self):
        texto = playbook_md().replace('"tipo": "choice-global"', '"tipo" "choice-global"')  # sin ':' -> JSON roto
        secciones = c.dividir_secciones(texto)
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_bloque_json(secciones, "2", "Qué se crea")

    def test_bloque_que_no_es_objeto_es_error(self):
        texto = playbook_md()
        # reemplaza el bloque de la sección 2 por una lista, no un objeto
        secciones = c.dividir_secciones(texto)
        secciones["2"]["cuerpo"] = "```json\n[1, 2, 3]\n```\n"
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_bloque_json(secciones, "2", "Qué se crea")


class ObtenerIdentidad(unittest.TestCase):
    def secciones_con(self, identidad_dict):
        return c.dividir_secciones(playbook_md(identidad_dict=identidad_dict))

    def test_identidad_valida_se_lee_completa(self):
        secciones = self.secciones_con(IDENTIDAD_VALIDA)
        resultado = c.obtener_identidad(secciones)
        self.assertEqual(resultado, IDENTIDAD_VALIDA)

    def test_falta_una_clave_es_error(self):
        rota = {k: v for k, v in IDENTIDAD_VALIDA.items() if k != "abrev"}
        secciones = self.secciones_con(rota)
        with self.assertRaises(c.ErrorPlaybook) as ctx:
            c.obtener_identidad(secciones)
        self.assertIn("abrev", str(ctx.exception))

    def test_clave_de_mas_es_error(self):
        con_extra = identidad(algo_inventado="x")
        secciones = self.secciones_con(con_extra)
        with self.assertRaises(c.ErrorPlaybook) as ctx:
            c.obtener_identidad(secciones)
        self.assertIn("algo_inventado", str(ctx.exception))

    def test_fase_no_entero_es_error(self):
        secciones = self.secciones_con(identidad(fase="1"))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_identidad(secciones)

    def test_lcid_no_entero_es_error(self):
        secciones = self.secciones_con(identidad(lcid="1033"))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_identidad(secciones)

    def test_lcid_booleano_es_error(self):
        # bool es subclase de int en Python: True/False no valen como lcid.
        secciones = self.secciones_con(identidad(lcid=True))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_identidad(secciones)

    def test_prefijo_vacio_es_error(self):
        secciones = self.secciones_con(identidad(prefijo=""))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_identidad(secciones)

    def test_publisher_no_texto_es_error(self):
        secciones = self.secciones_con(identidad(publisher=123))
        with self.assertRaises(c.ErrorPlaybook):
            c.obtener_identidad(secciones)


class ObtenerComponente(unittest.TestCase):
    def test_tipo_correcto_se_lee(self):
        secciones = c.dividir_secciones(playbook_md())
        datos = c.obtener_componente(secciones, "choice-global")
        self.assertEqual(datos, COMPONENTE_VALIDO)

    def test_tipo_distinto_es_error_sin_leer_nada_mas(self):
        secciones = c.dividir_secciones(playbook_md(componente_dict=componente(tipo="tabla-y-columnas")))
        with self.assertRaises(c.ErrorPlaybook) as ctx:
            c.obtener_componente(secciones, "choice-global")
        self.assertIn("tabla-y-columnas", str(ctx.exception))


class Salida(unittest.TestCase):
    def test_creado_y_ya_existia_devuelven_codigo_0(self):
        self.assertEqual(c.salida("creado", "x", "d"), 0)
        self.assertEqual(c.salida("ya_existia", "x", "d"), 0)

    def test_los_demas_estados_devuelven_codigo_distinto_de_0(self):
        for estado in ("difiere", "bloqueado", "error"):
            self.assertNotEqual(c.salida(estado, "x", "d"), 0)

    def test_imprime_una_linea_json_con_las_tres_claves(self):
        import io
        import contextlib
        import json as _json

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            c.salida("creado", "sanic_mppp_ch_moneda", "detalle")
        linea = buf.getvalue().strip().splitlines()[-1]
        obj = _json.loads(linea)
        self.assertEqual(obj, {"estado": "creado", "componente": "sanic_mppp_ch_moneda", "detalle": "detalle"})


class ExigirForma(unittest.TestCase):
    """`exigir_forma` es el único punto donde se valida el tipo de un valor
    leído de una respuesta del entorno."""

    def ok(self, valor, tipo, **kw):
        return c.exigir_forma(valor, tipo, "GET consulta", "campo", **kw)

    def test_devuelve_el_valor_cuando_cumple(self):
        self.assertEqual(self.ok(1033, int), 1033)
        self.assertEqual(self.ok("x", str), "x")
        self.assertIs(self.ok(False, bool), False)
        self.assertEqual(self.ok({"a": 1}, dict), {"a": 1})
        self.assertEqual(self.ok([1, 2], [int]), [1, 2])
        self.assertEqual(self.ok([], [dict]), [])
        self.assertIsNone(self.ok(None, dict, permite_nulo=True))

    def test_rechaza_el_tipo_equivocado(self):
        for valor, tipo in [("1033", int), (None, int), (1.0, int), (5, str), (None, str), ("false", bool),
                            (0, bool), ([], dict), ({}, [int]), ("abc", [str]), (None, [int])]:
            with self.subTest(valor=valor, tipo=tipo):
                with self.assertRaises(c.ErrorEntorno):
                    self.ok(valor, tipo)

    def test_un_booleano_no_es_un_entero(self):
        with self.assertRaises(c.ErrorEntorno):
            self.ok(True, int)
        with self.assertRaises(c.ErrorEntorno):
            self.ok([1033, True], [int])

    def test_lista_valida_cada_elemento_y_dice_cual_fallo(self):
        with self.assertRaises(c.ErrorEntorno) as ctx:
            self.ok([1033, "3082"], [int])
        self.assertIn("'campo[1]'", str(ctx.exception))

    def test_no_vacio_aplica_a_texto_y_a_lista(self):
        for valor, tipo in [("", str), ([], [int])]:
            with self.subTest(valor=valor):
                with self.assertRaises(c.ErrorEntorno):
                    self.ok(valor, tipo, no_vacio=True)

    def test_el_mensaje_es_uniforme_y_acota_lo_que_vuelca(self):
        with self.assertRaises(c.ErrorEntorno) as ctx:
            self.ok("x" * 5000, int)
        msg = str(ctx.exception)
        self.assertIn("GET consulta", msg)
        self.assertIn("forma inesperada", msg)
        self.assertIn("'campo'", msg)
        self.assertIn("un entero", msg)
        self.assertLess(len(msg), 600)


class NombreDeArchivo(unittest.TestCase):
    """Un componente sin nombre lógico (rol, perfil) se guarda con su nombre visible hecho archivo."""

    def test_translitera_tildes_y_enie_en_vez_de_perderlas(self):
        import _comun
        casos = {"SR - MPPP - Administrador técnico": "sr_mppp_administrador_tecnico", "CSP - MPPP - Datos sensibles": "csp_mppp_datos_sensibles",
                 "SR - MPPP - Señor Ñandú (época Ü)": "sr_mppp_senor_nandu_epoca_u", "  --Raro--  ": "raro"}
        for nombre, esperado in casos.items():
            with self.subTest(nombre):
                self.assertEqual(_comun.nombre_de_archivo(nombre), esperado)


if __name__ == "__main__":
    unittest.main()
