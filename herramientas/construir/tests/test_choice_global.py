"""Pruebas de `choice_global.py`. Nada acá toca el entorno real: la parte
offline se prueba con `FabricaCentinela` (demuestra que ni se intenta
construir un cliente), y la parte contra "el entorno" con `ClienteSimulado`
(demuestra qué se pidió y, sobre todo, que nunca se llegó a escribir nada
salvo en el único camino feliz de creación)."""
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_CONSTRUIR = os.path.dirname(_AQUI)
if _CONSTRUIR not in sys.path:
    sys.path.insert(0, _CONSTRUIR)

import choice_global as cg  # noqa: E402
from _comun import ErrorPlaybook, Bloqueado  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaFalla, FabricaCentinela  # noqa: E402
from fixtures import (  # noqa: E402
    IDENTIDAD_VALIDA,
    COMPONENTE_VALIDO,
    identidad,
    componente,
    escribir_playbook,
    cuerpo_choice_conforme,
    respuesta_solucion_ok,
    respuesta_idioma_ok,
    respuesta_idiomas_provisionados_ok,
    armar_cliente_precondiciones_ok,
    ruta_choice,
    es_ruta_solutions,
    es_ruta_solutioncomponents,
)


class Base(unittest.TestCase):
    def construir(self, fabrica_cliente, identidad_dict=None, componente_dict=None, solo_verificar=False):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            escribir_playbook(ruta, identidad_dict, componente_dict)
            return cg.construir(ruta, solo_verificar, fabrica_cliente)

    def construir_offline(self, identidad_dict=None, componente_dict=None):
        centinela = FabricaCentinela()
        resultado = self.construir(centinela, identidad_dict, componente_dict)
        return resultado, centinela

    def construir_con_cliente(self, cliente, identidad_dict=None, componente_dict=None, solo_verificar=False):
        return self.construir(lambda: cliente, identidad_dict, componente_dict, solo_verificar)


# ---------------------------------------------------------------------------
# Validación previa (offline): ni una sola llamada de red, ni siquiera para
# construir el cliente.
# ---------------------------------------------------------------------------
class ValidacionPreviaOffline(Base):
    """Cada prueba de acá afirma, además del estado, una parte del `detalle`
    que SOLO puede venir del chequeo específico que la prueba dice ejercitar
    — nunca alcanza con el estado solo: desde que `construir()` tiene un
    `except Exception` genérico al final de esta fase, un chequeo específico
    roto puede terminar en 'error' por otro camino (una excepción imprevista
    más adelante) y la prueba seguiría en verde sin discriminar nada."""

    def test_nombre_no_cumple_el_patron(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            componente_dict=componente(nombre="sanic_mppp_choice_moneda")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("sanic_mppp_choice_moneda", detalle)
        self.assertIn("no cumple", detalle)

    def test_nombre_con_prefijo_equivocado(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            componente_dict=componente(nombre="otroprefijo_mppp_ch_moneda")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("otroprefijo_mppp_ch_moneda", detalle)
        self.assertIn("no cumple", detalle)

    def test_nombre_supera_95_caracteres(self):
        nombre_largo = "sanic_mppp_ch_" + ("x" * 90)
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(nombre=nombre_largo))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("95 caracteres", detalle)

    def test_displayname_no_cumple_el_patron(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            componente_dict=componente(displayname="Moneda")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("displayname", detalle)
        self.assertIn("Moneda", detalle)

    def test_displayname_con_abreviatura_equivocada(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            componente_dict=componente(displayname="CH - OTRA - Moneda")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("CH - OTRA - Moneda", detalle)

    def test_valor_fuera_del_rango_declarado_en_identidad(self):
        opciones = [{"valor": 100000001, "etiqueta": "X", "descripcion": ""}]
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(opciones=opciones))
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(centinela.llamada)
        self.assertIn("100000001", detalle)

    def test_etiquetas_repetidas(self):
        opciones = [
            {"valor": 159460001, "etiqueta": "COR", "descripcion": ""},
            {"valor": 159460002, "etiqueta": "COR", "descripcion": ""},
        ]
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(opciones=opciones))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("etiquetas repetidas", detalle)

    def test_valores_repetidos(self):
        opciones = [
            {"valor": 159460001, "etiqueta": "COR", "descripcion": ""},
            {"valor": 159460001, "etiqueta": "USD", "descripcion": ""},
        ]
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(opciones=opciones))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("valores repetidos", detalle)

    def test_opciones_vacias_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(opciones=[]))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("opciones", detalle)
        self.assertIn("no vacía", detalle)

    def test_clave_de_mas_en_el_bloque_del_componente(self):
        malo = dict(COMPONENTE_VALIDO)
        malo["lcid"] = 1033  # ya no va acá: ahora vive en Identidad
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=malo)
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("lcid", detalle)
        self.assertIn("sobran", detalle)

    def test_clave_faltante_en_el_bloque_del_componente(self):
        malo = {k: v for k, v in COMPONENTE_VALIDO.items() if k != "descripcion"}
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=malo)
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("descripcion", detalle)
        self.assertIn("faltan", detalle)

    def test_descripcion_vacia_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(descripcion="  "))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("descripcion", detalle)
        self.assertIn("obligatoria", detalle)

    def test_valor_de_opcion_no_entero(self):
        opciones = [{"valor": "159460001", "etiqueta": "COR", "descripcion": ""}]
        (estado, comp, detalle), centinela = self.construir_offline(componente_dict=componente(opciones=opciones))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("opciones[0].valor", detalle)
        self.assertIn("entero", detalle)

    def test_tipo_distinto_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            componente_dict=componente(tipo="tabla-y-columnas")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("tabla-y-columnas", detalle)

    def test_identidad_con_clave_de_mas_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(identidad_dict=identidad(extra="x"))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("extra", detalle)
        self.assertIn("sobran", detalle)

    def test_identidad_con_lcid_no_entero_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(identidad_dict=identidad(lcid="1033"))
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("'lcid'", detalle)
        self.assertIn("entero", detalle)

    def test_identidad_con_prefijo_opciones_como_texto_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            identidad_dict=identidad(prefijo_opciones="15946")
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        # Distintivo del mensaje de `_validar_claves_y_tipos` para esta
        # clave puntual: si ese chequeo se rompiera, `validar_rango_offline`
        # también terminaría en 'error' (TypeError al sumarle 1 a un texto),
        # pero por el `except Exception` genérico, sin mencionar
        # 'prefijo_opciones' ni 'entero'. Demostrado por mutación en el
        # reporte final.
        self.assertIn("prefijo_opciones", detalle)
        self.assertIn("entero", detalle)

    def test_identidad_con_prefijo_opciones_float_es_error(self):
        (estado, comp, detalle), centinela = self.construir_offline(
            identidad_dict=identidad(prefijo_opciones=15946.0)
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("prefijo_opciones", detalle)
        self.assertIn("entero", detalle)

    def test_identidad_con_prefijo_opciones_booleano_es_error(self):
        # bool es subclase de int en Python: True/False no valen como prefijo.
        (estado, comp, detalle), centinela = self.construir_offline(
            identidad_dict=identidad(prefijo_opciones=True)
        )
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("prefijo_opciones", detalle)
        self.assertIn("entero", detalle)


class ExcepcionImprevistaEnFaseSinRed(Base):
    """La fase sin red (leer y validar el playbook) tiene que tener su propia
    red de contención: cualquier excepción, no solo ErrorPlaybook/Bloqueado/
    OSError, termina en 'error' y nunca escapa como traza."""

    def test_typeerror_en_validacion_offline_termina_en_error_sin_traza(self):
        import unittest.mock as mock

        with mock.patch.object(cg, "validar_nombres", side_effect=TypeError("forma de dato inesperada")):
            (estado, comp, detalle), centinela = self.construir_offline()
        self.assertEqual(estado, "error")
        self.assertFalse(centinela.llamada)
        self.assertIn("TypeError", detalle)


# ---------------------------------------------------------------------------
# Funciones puras: el cuerpo del POST y la comparación contra el entorno.
# ---------------------------------------------------------------------------
class ConstruirPayload(unittest.TestCase):
    def test_usa_el_lcid_de_identidad_no_del_componente(self):
        payload = cg.construir_payload(COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertEqual(payload["DisplayName"]["LocalizedLabels"][0]["LanguageCode"], IDENTIDAD_VALIDA["lcid"])
        self.assertEqual(payload["Options"][0]["Value"], 159460001)
        self.assertEqual(payload["Name"], COMPONENTE_VALIDO["nombre"])
        self.assertEqual(payload["OptionSetType"], "Picklist")
        self.assertIs(payload["IsGlobal"], True)


class CompararContraPlaybook(unittest.TestCase):
    def test_coincide_exactamente_sin_diferencias(self):
        diffs = cg.comparar_contra_playbook(cuerpo_choice_conforme(), COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertEqual(diffs, [])

    def test_ismanaged_true_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme(is_managed=True)
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("IsManaged" in d for d in diffs), diffs)

    def test_isglobal_falso_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["IsGlobal"] = False
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("IsGlobal" in d for d in diffs), diffs)

    def test_optionsettype_distinto_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["OptionSetType"] = "Boolean"
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("OptionSetType" in d for d in diffs), diffs)

    def test_displayname_distinto_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["DisplayName"]["LocalizedLabels"][0]["Label"] = "CH - MPPP - Otra cosa"
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("DisplayName" in d for d in diffs), diffs)

    def test_descripcion_distinta_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Description"]["LocalizedLabels"][0]["Label"] = "otra cosa"
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("Description" in d for d in diffs), diffs)

    def test_valor_de_opcion_distinto_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Options"][0]["Value"] = 999999999
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("opciones[0].Value" in d for d in diffs), diffs)

    def test_etiqueta_de_opcion_distinta_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Options"][0]["Label"]["LocalizedLabels"][0]["Label"] = "XXX"
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("opciones[0].etiqueta" in d for d in diffs), diffs)

    def test_descripcion_de_opcion_distinta_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Options"][0]["Description"]["LocalizedLabels"][0]["Label"] = "otra descripción"
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("opciones[0].descripcion" in d for d in diffs), diffs)

    def test_cantidad_de_opciones_distinta_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Options"] = cuerpo["Options"][:1]
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("cantidad de opciones" in d for d in diffs), diffs)

    def test_etiqueta_del_choice_en_otro_idioma_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["DisplayName"]["LocalizedLabels"].append({"Label": "Currency", "LanguageCode": 2058})
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("otro idioma" in d for d in diffs), diffs)

    def test_etiqueta_de_opcion_en_otro_idioma_es_diferencia(self):
        cuerpo = cuerpo_choice_conforme()
        cuerpo["Options"][0]["Label"]["LocalizedLabels"].append({"Label": "COR-EN", "LanguageCode": 2058})
        diffs = cg.comparar_contra_playbook(cuerpo, COMPONENTE_VALIDO, IDENTIDAD_VALIDA)
        self.assertTrue(any("otro idioma" in d for d in diffs), diffs)


# ---------------------------------------------------------------------------
# Precondiciones contra "el entorno" (cliente simulado). Ninguna debe llegar
# a escribir nada.
# ---------------------------------------------------------------------------
class PrecondicionesContraEntorno(Base):
    def test_solucion_no_existe(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, (200, {"value": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_solucion_managed(self):
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        cuerpo["value"][0]["ismanaged"] = True
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_publisher_uniquename_distinto(self):
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        cuerpo["value"][0]["publisherid"]["uniquename"] = "sanic"  # el publisher equivocado, "Sanic Corp"
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_prefijo_de_texto_distinto(self):
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        cuerpo["value"][0]["publisherid"]["customizationprefix"] = "otro"
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_prefijo_de_opciones_distinto(self):
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        cuerpo["value"][0]["publisherid"]["customizationoptionvalueprefix"] = 10000
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_idioma_base_distinto_del_lcid_del_playbook(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", (200, {"value": [{"languagecode": 3082}]}, {}))
        cliente.responder("GET", "RetrieveProvisionedLanguages", respuesta_idiomas_provisionados_ok())
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())

    def test_lcid_no_provisionado(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", respuesta_idioma_ok())
        cliente.responder("GET", "RetrieveProvisionedLanguages", (200, {"RetrieveProvisionedLanguages": [2058]}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "bloqueado")
        self.assertFalse(cliente.hubo_escritura())


class PrecondicionesHttpInesperado(Base):
    """Un HTTP inesperado (401, 500, ...) en una consulta de precondición
    nunca es 'una precondición no se cumple' (bloqueado): es 'no se pudo
    averiguar' (error). `bloqueado` queda solo para un 200 cuyo contenido
    dice que la precondición no se cumple."""

    def test_consulta_solucion_401_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, (401, {"error": "no autorizado"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 401", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_solucion_500_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, (500, {"error": "boom"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 500", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_organizations_401_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", (401, {"error": "no autorizado"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 401", detalle)
        self.assertIn("organizations", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_retrieveprovisionedlanguages_500_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", respuesta_idioma_ok())
        cliente.responder("GET", "RetrieveProvisionedLanguages", (500, {"error": "boom"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 500", detalle)
        self.assertIn("RetrieveProvisionedLanguages", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_organizations_200_con_value_vacio_es_error(self):
        """200 sin ninguna fila en 'value' no es una respuesta de negocio
        válida (todo entorno tiene exactamente una organización): es una
        forma inesperada, no una precondición incumplida."""
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", (200, {"value": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("organizations", detalle)
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_organizations_200_sin_languagecode_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", (200, {"value": [{}]}, {}))
        # Se configura igual (aunque no debería llegar a pedirse) para que el
        # test falle por la razón correcta y no por una ruta sin configurar.
        cliente.responder("GET", "RetrieveProvisionedLanguages", respuesta_idiomas_provisionados_ok())
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("organizations", detalle)
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    # -- Segunda vuelta: la misma clase de bug (forma inesperada con 200
    # tratada como negativa de negocio) en el resto de las consultas. --

    def test_consulta_retrieveprovisionedlanguages_200_con_clave_ausente_es_error(self):
        """Reproducido por el revisor: `cuerpo.get("RetrieveProvisionedLanguages", [])`
        infiere `[]` en silencio cuando la clave no está, y eso se leía como
        'no está provisionado' (bloqueado) en vez de 'no pude averiguarlo'
        (error)."""
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", respuesta_idioma_ok())
        cliente.responder("GET", "RetrieveProvisionedLanguages", (200, {"algo_distinto": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("RetrieveProvisionedLanguages", detalle)
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_retrieveprovisionedlanguages_200_tipo_equivocado_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", respuesta_idioma_ok())
        cliente.responder("GET", "RetrieveProvisionedLanguages", (200, {"RetrieveProvisionedLanguages": "1033"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_retrieveprovisionedlanguages_200_vacia_es_error(self):
        """Una lista vacía tampoco es una respuesta de negocio posible: todo
        entorno tiene como mínimo su idioma base provisionado."""
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, respuesta_solucion_ok())
        cliente.responder("GET", "organizations?$select=languagecode", respuesta_idioma_ok())
        cliente.responder("GET", "RetrieveProvisionedLanguages", (200, {"RetrieveProvisionedLanguages": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_solucion_200_sin_value_es_error(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, (200, {"otracosa": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("solución", detalle)
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_solucion_200_sin_publisherid_es_error(self):
        """`fila_sol.get("publisherid") or {}` convertía la ausencia del
        publisher expandido en un diccionario vacío, y de ahí en un
        'publisher equivocado' (bloqueado) en vez de 'no pude averiguarlo'."""
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        del cuerpo["value"][0]["publisherid"]
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("publisherid", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_consulta_solucion_200_sin_solutionid_es_error(self):
        cliente = ClienteSimulado()
        est, cuerpo, cab = respuesta_solucion_ok()
        del cuerpo["value"][0]["solutionid"]
        cliente.responder("GET", es_ruta_solutions, (est, cuerpo, cab))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("solutionid", detalle)
        self.assertFalse(cliente.hubo_escritura())


class VerificacionFormaInesperada(Base):
    """Los campos que cada consulta declara devolver se validan por forma
    (que existan y sean del tipo esperado) antes de usarse: su ausencia o
    forma rara con HTTP 200 es 'error', nunca se infiere un valor por
    defecto silencioso que termine pareciendo una respuesta de negocio."""

    def test_existencia_200_no_es_objeto_es_error(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, ["no", "es", "un", "objeto"], {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_existencia_200_sin_metadataid_es_error(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cuerpo = cuerpo_choice_conforme()
        del cuerpo["MetadataId"]
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, cuerpo, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("MetadataId", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solutioncomponents_200_forma_inesperada_es_error(self):
        """`cuerpo_sc.get("value", [])` convertía la ausencia de 'value' en
        0 filas, que el código ya interpreta como 'no pertenece a la
        solución' (difiere) — una respuesta de negocio legítima que no es lo
        mismo que 'no pude averiguar la pertenencia'."""
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, cuerpo_choice_conforme(), {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"otracosa": []}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("solutioncomponents", detalle)
        self.assertIn("forma inesperada", detalle)
        self.assertFalse(cliente.hubo_escritura())


class ExistenciaAnomala(Base):
    def test_get_existencia_500_no_se_trata_como_no_existe(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (500, {"error": "boom"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 500", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_get_existencia_401_no_se_trata_como_no_existe(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (401, {"error": "no autorizado"}, {}))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 401", detalle)
        self.assertFalse(cliente.hubo_escritura())


# ---------------------------------------------------------------------------
# Los tres caminos de la verificación (creado / ya existía / --solo-verificar)
# ---------------------------------------------------------------------------
class CaminoCreacion(Base):
    def test_creacion_feliz_un_solo_post_con_la_cabecera_de_solucion(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        respuestas = iter([(404, {}, {}), (200, cuerpo_choice_conforme(), {})])
        cliente.responder("GET", ruta_choice(nombre), lambda ruta, cuerpo, sol: next(respuestas))
        cliente.responder(
            "POST",
            "GlobalOptionSetDefinitions",
            (204, {}, {"OData-EntityId": "https://org/api/data/v9.2/GlobalOptionSetDefinitions(1)"}),
        )
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "creado")
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["solucion"], IDENTIDAD_VALIDA["solucion"])
        self.assertEqual(posts[0]["cuerpo"]["Name"], nombre)

    def test_204_con_relectura_que_difiere_no_reintenta_crear_y_es_error(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        respuestas = iter([(404, {}, {}), (200, cuerpo_choice_conforme(is_managed=True), {})])
        cliente.responder("GET", ruta_choice(nombre), lambda ruta, cuerpo, sol: next(respuestas))
        cliente.responder("POST", "GlobalOptionSetDefinitions", (204, {}, {"OData-EntityId": "https://org/x(1)"}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "error")
        self.assertIn("no coincide", detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(len(posts), 1, "no debe reintentar crear ante una relectura que difiere")

    def test_post_que_no_devuelve_204_es_error_sin_reintentar(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        cliente.responder("GET", ruta_choice(nombre), (404, {}, {}))
        cliente.responder("POST", "GlobalOptionSetDefinitions", (400, {"error": "algo salió mal"}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "error")
        self.assertIn("HTTP 400", detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(len(posts), 1)


class CaminoYaExistiaYDifiere(Base):
    def test_ya_existia_coincide_cero_escritura(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        cliente.responder("GET", ruta_choice(nombre), (200, cuerpo_choice_conforme(), {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "ya_existia")
        self.assertFalse(cliente.hubo_escritura())

    def test_existe_pero_difiere_cero_escritura(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        cuerpo = cuerpo_choice_conforme()
        cuerpo["DisplayName"]["LocalizedLabels"][0]["Label"] = "CH - MPPP - Otra cosa"
        cliente.responder("GET", ruta_choice(nombre), (200, cuerpo, {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())

    def test_existe_y_coincide_pero_no_pertenece_a_la_solucion_es_difiere(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        nombre = COMPONENTE_VALIDO["nombre"]
        cliente.responder("GET", ruta_choice(nombre), (200, cuerpo_choice_conforme(), {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": []}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente)

        self.assertEqual(estado, "difiere")
        self.assertIn("pertenencia", detalle)
        self.assertFalse(cliente.hubo_escritura())


class CaminoSoloVerificar(Base):
    def test_no_existe_es_error_y_nunca_hay_post_posible(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (404, {}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente, solo_verificar=True)

        self.assertEqual(estado, "error")
        self.assertIn("no existe en el entorno", detalle)
        self.assertNotIn("POST", cliente.metodos_llamados())
        self.assertFalse(cliente.hubo_escritura())

    def test_coincide_es_ya_existia(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, cuerpo_choice_conforme(), {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente, solo_verificar=True)

        self.assertEqual(estado, "ya_existia")
        self.assertFalse(cliente.hubo_escritura())

    def test_difiere_es_difiere(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cuerpo = cuerpo_choice_conforme(is_managed=True)
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), (200, cuerpo, {}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, comp, detalle = self.construir_con_cliente(cliente, solo_verificar=True)

        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())


class ExcepcionesDelCliente(Base):
    def test_fabrica_cliente_lanza_excepcion_termina_en_error_sin_exponer_el_detalle(self):
        fabrica = FabricaFalla(TimeoutError("timed out talking to login.microsoftonline.com with secret=abc123"))
        estado, comp, detalle = self.construir(fabrica)
        self.assertEqual(estado, "error")
        self.assertEqual(detalle, cg.MENSAJE_FALLO_CLIENTE)
        self.assertNotIn("abc123", detalle)
        self.assertNotIn("secret", detalle.lower())

    def test_llamada_de_red_lanza_excepcion_en_medio_de_las_precondiciones(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", es_ruta_solutions, TimeoutError("se cayó la red"))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("TimeoutError", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_excepcion_durante_la_verificacion_final_no_deja_traza_sin_manejar(self):
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cliente.responder("GET", ruta_choice(COMPONENTE_VALIDO["nombre"]), ConnectionError("se cortó a mitad de camino"))
        estado, comp, detalle = self.construir_con_cliente(cliente)
        self.assertEqual(estado, "error")
        self.assertIn("ConnectionError", detalle)
        self.assertFalse(cliente.hubo_escritura())


# ---------------------------------------------------------------------------
# Reutilización: no atado a "moneda" ni a dos opciones. 18 opciones, etiquetas
# con tildes, paréntesis y barras.
# ---------------------------------------------------------------------------
class Reutilizacion18Opciones(Base):
    def _componente_grande(self):
        opciones = [
            {
                "valor": 159460000 + i,
                "etiqueta": f"Opcion {i} (a/n) - variante",
                "descripcion": f"Descripción larga de la opción {i}, con \"comillas\" y una / barra",
            }
            for i in range(1, 19)
        ]
        return componente(
            nombre="sanic_mppp_ch_pruebagrande",
            displayname="CH - MPPP - Prueba grande",
            opciones=opciones,
        )

    def test_validaciones_offline_pasan_con_18_opciones(self):
        comp = self._componente_grande()
        cg.validar_json_componente(comp)  # no debe lanzar
        cg.validar_nombres(comp, IDENTIDAD_VALIDA)  # no debe lanzar
        cg.validar_rango_offline(comp, IDENTIDAD_VALIDA)  # no debe lanzar

    def test_comparacion_no_marca_diferencias_con_caracteres_especiales(self):
        comp = self._componente_grande()
        cuerpo = cuerpo_choice_conforme(comp)
        diffs = cg.comparar_contra_playbook(cuerpo, comp, IDENTIDAD_VALIDA)
        self.assertEqual(diffs, [])

    def test_creacion_feliz_de_punta_a_punta_con_18_opciones(self):
        comp = self._componente_grande()
        cliente = armar_cliente_precondiciones_ok(ClienteSimulado())
        cuerpo_final = cuerpo_choice_conforme(comp)
        respuestas = iter([(404, {}, {}), (200, cuerpo_final, {})])
        cliente.responder("GET", ruta_choice(comp["nombre"]), lambda ruta, cuerpo, sol: next(respuestas))
        cliente.responder("POST", "GlobalOptionSetDefinitions", (204, {}, {"OData-EntityId": "https://org/x(1)"}))
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": [{"solutioncomponentid": "x"}]}, {}))

        estado, nombre, detalle = self.construir_con_cliente(cliente, componente_dict=comp)

        self.assertEqual(estado, "creado")
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(len(posts[0]["cuerpo"]["Options"]), 18)


if __name__ == "__main__":
    unittest.main()
