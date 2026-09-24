"""Pruebas de `herramientas/construir/custom_api.py`. Nunca tocan la red.

Lo que más se prueba acá es la desconfianza: en una Custom API casi todo es
inmutable, así que la herramienta tiene que rechazar un playbook mal armado
SIN tocar el entorno, y tiene que negarse a "arreglar" lo que no se puede
arreglar con un PATCH.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

import custom_api as ca  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import (  # noqa: E402
    IDENTIDAD_VALIDA,
    SOLUTION_ID,
    armar_cliente_precondiciones_ok,
    es_ruta_solutioncomponents,
)

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="custom-api", inventario="8.1")

API_ID = "55555555-5555-5555-5555-555555555555"
TIPO_ID = "66666666-6666-6666-6666-666666666666"
TYPENAME = "Sanic.Mppp.Plugins.Api.ValidarSolicitudApi"

COMPONENTE = {
    "tipo": "custom-api",
    "nombre": "sanic_mppp_capi_validarsolicitud",
    "displayname": "CAPI - MPPP - Validar solicitud",
    "descripcion": "Valida una Solicitud ingresada y deja sus filas guardadas.",
    "plugintype": TYPENAME,
    "esfuncion": False,
    "esprivada": True,
    "binding": "Global",
    "pasosdeterceros": "None",
    "habilitadaenflujos": False,
    "privilegio": "prvCreatesanic_mppp_tbl_solicitud",
    "entrada": [
        {"nombre": "solicitudid", "displayname": "CAPI_IP - MPPP - Solicitud id",
         "descripcion": "Identificador de la Solicitud a validar.", "tipo": "Guid", "opcional": False},
    ],
    "salida": [
        {"nombre": "estado", "displayname": "CAPI_OP - MPPP - Estado",
         "descripcion": "Valor del choice EstadoSolicitud resultante.", "tipo": "Integer"},
        {"nombre": "yaprocesada", "displayname": "CAPI_OP - MPPP - Ya procesada",
         "descripcion": "Verdadero si no hizo nada porque ya estaba validada.", "tipo": "Boolean"},
    ],
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None, identidad=None):
    componente = COMPONENTE if componente is None else componente
    identidad = IDENT if identidad is None else identidad
    return (
        "# Playbook: custom-api · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(identidad, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def es_ruta_apis(ruta):
    return ruta.startswith("customapis?")


def es_ruta_tipos(ruta):
    return ruta.startswith("plugintypes?")


def fila_parametro(p, es_salida, datos=None):
    datos = COMPONENTE if datos is None else datos
    fila = {
        "uniquename": p["nombre"],
        "name": ca.nombre_largo(datos["nombre"], IDENT, es_salida, p["nombre"]),
        "displayname": p["displayname"],
        "description": p["descripcion"],
        "type": ca.TIPOS_DE_PARAMETRO[p["tipo"]],
    }
    fila["customapiresponsepropertyid" if es_salida else "customapirequestparameterid"] = "p-" + p["nombre"]
    if not es_salida:
        fila["isoptional"] = p["opcional"]
    return fila


def fila_api(datos=None, entrada=None, salida=None, **cambios):
    """La fila que devolvería el entorno si tuviera exactamente lo declarado."""
    datos = COMPONENTE if datos is None else datos
    entrada = datos["entrada"] if entrada is None else entrada
    salida = datos["salida"] if salida is None else salida
    fila = {
        "customapiid": API_ID,
        "uniquename": datos["nombre"],
        "name": datos["nombre"],
        "displayname": datos["displayname"],
        "description": datos["descripcion"],
        "executeprivilegename": datos["privilegio"],
        "isfunction": datos["esfuncion"],
        "isprivate": datos["esprivada"],
        "bindingtype": ca.BINDING[datos["binding"]],
        "allowedcustomprocessingsteptype": ca.PASOS_DE_TERCEROS[datos["pasosdeterceros"]],
        "workflowsdkstepenabled": datos["habilitadaenflujos"],
        "ismanaged": False,
        "PluginTypeId": {"plugintypeid": TIPO_ID, "typename": datos["plugintype"]},
        "CustomAPIRequestParameters": [fila_parametro(p, False, datos) for p in entrada],
        "CustomAPIResponseProperties": [fila_parametro(p, True, datos) for p in salida],
    }
    fila.update(cambios)
    return fila


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None, identidad=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente, identidad))
        return self.ruta

    def armar(self, cliente, apis, tipos=None, componentes=None):
        """`apis` es la SECUENCIA de respuestas de `GET customapis` (una por
        lectura): así se simula el antes y el después de una escritura."""
        armar_cliente_precondiciones_ok(cliente, IDENT)
        if tipos is None:
            tipos = [{"plugintypeid": TIPO_ID, "typename": TYPENAME}]
        cliente.responder("GET", es_ruta_tipos, (200, {"value": tipos}, {}))
        pendientes = list(apis)

        def responder_api(ruta, cuerpo, solucion):
            fila = pendientes.pop(0) if len(pendientes) > 1 else pendientes[0]
            return (200, {"value": [] if fila is None else [fila]}, {})

        cliente.responder("GET", es_ruta_apis, responder_api)
        if componentes is None:
            componentes = [{"componenttype": 10101, "objectid": API_ID}]
        cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": componentes}, {}))
        return cliente


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = ca.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada, "no tenía que intentar construir el cliente de Dataverse")

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        sin_salida = {k: v for k, v in COMPONENTE.items() if k != "salida"}
        self.rechaza(sin_salida, "faltan ['salida']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_el_nombre_sigue_el_patron_de_la_convencion(self):
        self.rechaza(comp(nombre="validarsolicitud"), "no sigue el patrón sanic_mppp_capi_")
        self.rechaza(comp(nombre="sanic_mppp_capi_Validar"), "solo van minúsculas ASCII y dígitos")
        self.rechaza(comp(nombre="sanic_mppp_capi_validar_solicitud"), "solo van minúsculas ASCII y dígitos")

    def test_el_nombre_de_un_parametro_es_inmutable_asi_que_se_valida_duro(self):
        malo = comp(entrada=[dict(COMPONENTE["entrada"][0], nombre="solicitudId")])
        self.rechaza(malo, "solo puede llevar minúsculas ASCII y dígitos")
        malo = comp(entrada=[dict(COMPONENTE["entrada"][0], nombre="solicitud_id")])
        self.rechaza(malo, "solo puede llevar minúsculas ASCII y dígitos")

    def test_un_nombre_repetido_entre_entrada_y_salida_se_rechaza(self):
        # El nombre es el identificador del parámetro al llamar la API.
        malo = comp(salida=[dict(COMPONENTE["salida"][0], nombre="solicitudid")])
        self.rechaza(malo, "está repetido")

    def test_un_tipo_que_no_existe_se_rechaza_nombrando_los_validos(self):
        malo = comp(salida=[dict(COMPONENTE["salida"][0], tipo="Int32")])
        self.rechaza(malo, "no es un tipo de Custom API")

    def test_un_tipo_que_necesita_tabla_se_rechaza_en_vez_de_declararlo_a_medias(self):
        # `logicalentityname` también es inmutable: mejor no crear nada.
        malo = comp(salida=[dict(COMPONENTE["salida"][0], tipo="Entity")])
        self.rechaza(malo, "necesita `logicalentityname`")

    def test_una_api_atada_a_una_tabla_todavia_no_se_sabe_crear(self):
        self.rechaza(comp(binding="Entity"), "solo sabe crear API unbound")
        self.rechaza(comp(binding="Otro"), "no es válido")

    def test_una_function_sin_salidas_se_rechaza(self):
        self.rechaza(comp(esfuncion=True, salida=[]), "una Function tiene que devolver algo")

    def test_los_nombres_visibles_van_sin_tildes(self):
        self.rechaza(comp(displayname="CAPI - MPPP - Validación"), "fuera de ASCII")
        malo = comp(entrada=[dict(COMPONENTE["entrada"][0], displayname="CAPI_IP - MPPP - Solicitud ñ")])
        self.rechaza(malo, "fuera de ASCII")

    def test_pasos_de_terceros_se_nombra_no_se_numera(self):
        self.rechaza(comp(pasosdeterceros="0"), "no es válido")

    def test_el_nombre_largo_del_parametro_se_calcula_no_se_escribe(self):
        self.assertEqual(
            "sanic_mppp_capiip_validarsolicitud_solicitudid",
            ca.nombre_largo("sanic_mppp_capi_validarsolicitud", IDENT, False, "solicitudid"),
        )
        self.assertEqual(
            "sanic_mppp_capiop_validarsolicitud_filasvalidas",
            ca.nombre_largo("sanic_mppp_capi_validarsolicitud", IDENT, True, "filasvalidas"),
        )


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_sin_el_paquete_registrado_queda_bloqueado_y_no_escribe(self):
        cliente = self.armar(ClienteSimulado(), [None], tipos=[])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("paquete_plugins.py", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_alta_crea_la_api_y_un_post_por_parametro(self):
        cliente = self.armar(ClienteSimulado(), [None, fila_api(entrada=[], salida=[]), fila_api()])
        cliente.responder("POST", "customapis", (204, {}, {}))
        cliente.responder("POST", "customapirequestparameters", (204, {}, {}))
        cliente.responder("POST", "customapiresponseproperties", (204, {}, {}))

        estado, componente, detalle = ca.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        self.assertEqual(COMPONENTE["nombre"], componente)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(["customapis", "customapirequestparameters",
                          "customapiresponseproperties", "customapiresponseproperties"],
                         [p["ruta"] for p in posts])
        # Todo entra en la solución en la misma llamada que lo crea.
        for p in posts:
            self.assertEqual(IDENT["solucion"], p["solucion"])

    def test_el_cuerpo_del_alta_lleva_lo_que_fija_el_diseno(self):
        cliente = self.armar(ClienteSimulado(), [None, fila_api(entrada=[], salida=[]), fila_api()])
        for ruta in ("customapis", "customapirequestparameters", "customapiresponseproperties"):
            cliente.responder("POST", ruta, (204, {}, {}))
        ca.construir(self.escribir(), False, lambda: cliente)

        cuerpo = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "customapis")
        self.assertEqual(0, cuerpo["bindingtype"])                      # Global (unbound)
        self.assertEqual(0, cuerpo["allowedcustomprocessingsteptype"])  # None: nadie le cuelga pasos
        self.assertIs(True, cuerpo["isprivate"])
        self.assertIs(False, cuerpo["isfunction"])
        self.assertEqual("prvCreatesanic_mppp_tbl_solicitud", cuerpo["executeprivilegename"])
        self.assertEqual(f"/plugintypes({TIPO_ID})", cuerpo["PluginTypeId@odata.bind"])

        entrada = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "customapirequestparameters")
        self.assertEqual("solicitudid", entrada["uniquename"])
        self.assertEqual("sanic_mppp_capiip_validarsolicitud_solicitudid", entrada["name"])
        self.assertEqual(12, entrada["type"])  # Guid
        self.assertIs(False, entrada["isoptional"])
        self.assertEqual(f"/customapis({API_ID})", entrada["CustomAPIId@odata.bind"])

        salidas = [l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "customapiresponseproperties"]
        self.assertEqual(7, salidas[0]["type"])  # Integer
        self.assertNotIn("isoptional", salidas[0])  # una salida no es opcional ni obligatoria

    def test_si_ya_esta_bien_no_se_escribe_nada(self):
        cliente = self.armar(ClienteSimulado(), [fila_api()])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_componenttype_leido_se_informa_y_la_consulta_no_lo_filtra(self):
        cliente = self.armar(ClienteSimulado(), [fila_api()], componentes=[{"componenttype": 10101, "objectid": API_ID}])
        _, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertIn("componenttype 10101", detalle)
        for l in cliente.llamadas:
            if l["ruta"].startswith("solutioncomponents?"):
                self.assertNotIn("componenttype eq", l["ruta"])

    def test_un_tipo_de_parametro_distinto_dice_que_hay_que_borrar_y_rehacer(self):
        otra = copy.deepcopy(COMPONENTE)
        otra["entrada"][0]["tipo"] = "String"
        cliente = self.armar(ClienteSimulado(), [fila_api(datos=otra)])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("INMUTABLE", detalle)
        self.assertIn("borrar la Custom API entera", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_isoptional_distinto_tambien_es_inmutable(self):
        otra = copy.deepcopy(COMPONENTE)
        otra["entrada"][0]["opcional"] = True
        cliente = self.armar(ClienteSimulado(), [fila_api(datos=otra)])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("isoptional", detalle)
        self.assertIn("INMUTABLE", detalle)

    def test_completar_no_intenta_arreglar_un_campo_inmutable(self):
        # Lo peor que podría hacer: un PATCH que la plataforma acepta callada
        # sin cambiar nada, y quedarnos creyendo que está corregido.
        cliente = self.armar(ClienteSimulado(), [fila_api(isfunction=True)])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("INMUTABLE", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_corrige_lo_que_si_se_puede_y_nada_mas(self):
        viejo = fila_api(displayname="CAPI - MPPP - Viejo", executeprivilegename="prvOtro")
        cliente = self.armar(ClienteSimulado(), [viejo, fila_api()])
        cliente.responder("PATCH", lambda r: r.startswith("customapis("), (204, {}, {}))

        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        patches = [l for l in cliente.llamadas if l["metodo"] == "PATCH"]
        self.assertEqual(1, len(patches))
        self.assertEqual({"displayname", "executeprivilegename"}, set(patches[0]["cuerpo"]))
        self.assertEqual(f"customapis({API_ID})", patches[0]["ruta"])

    def test_completar_agrega_una_salida_que_falta(self):
        sin_una = fila_api(salida=COMPONENTE["salida"][:1])
        cliente = self.armar(ClienteSimulado(), [sin_una, fila_api()])
        cliente.responder("POST", "customapiresponseproperties", (204, {}, {}))

        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(1, len(posts))
        self.assertEqual("yaprocesada", posts[0]["cuerpo"]["uniquename"])

    def test_sin_completar_una_salida_que_falta_solo_se_denuncia(self):
        cliente = self.armar(ClienteSimulado(), [fila_api(salida=COMPONENTE["salida"][:1])])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("falta la salida 'yaprocesada'", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_parametro_de_mas_se_denuncia_y_nunca_se_borra(self):
        extra = dict(COMPONENTE["salida"][0], nombre="colado")
        cliente = self.armar(ClienteSimulado(), [fila_api(salida=COMPONENTE["salida"] + [extra])])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("'colado'", detalle)
        self.assertIn("nunca borra", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_api_managed_no_se_toca(self):
        cliente = self.armar(ClienteSimulado(), [fila_api(ismanaged=True, displayname="otro")])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado(), [None])
        estado, _, detalle = ca.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no existe en el entorno", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_api_fuera_de_la_solucion_es_difiere(self):
        cliente = self.armar(ClienteSimulado(), [fila_api()], componentes=[])
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn(SOLUTION_ID, detalle)

    def test_un_http_inesperado_en_el_alta_no_se_confunde_con_exito(self):
        cliente = self.armar(ClienteSimulado(), [None])
        cliente.responder("POST", "customapis", (400, {"error": "unique name en uso"}, {}))
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("HTTP 400", detalle)

    def test_si_un_parametro_no_se_pudo_crear_no_se_informa_creado(self):
        cliente = self.armar(ClienteSimulado(), [None, fila_api(entrada=[], salida=[])])
        cliente.responder("POST", "customapis", (204, {}, {}))
        cliente.responder("POST", "customapirequestparameters", (400, {"error": "tipo inválido"}, {}))
        estado, _, detalle = ca.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("la Custom API se creó pero", detalle)
        self.assertIn("solicitudid", detalle)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = ca.salida
        try:
            sys.argv = ["custom_api.py", self.escribir(), "--forzar"]
            ca.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            ca.main()
        finally:
            sys.argv, ca.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
