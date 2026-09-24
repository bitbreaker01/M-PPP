"""Pruebas de `herramientas/construir/flujo.py`. Nunca tocan la red.

Lo que más importa: que NUNCA se suba una definición con una marca `@@...@@`
sin resolver (el flujo reventaría recién en ejecución), que un flujo hijo no
quede activado, y que la comparación no mire los identificadores que el
diseñador regenera solo.
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

import flujo as fl  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="flujo", inventario="11.1")

FLUJO_ID = "aaaa1111-2222-3333-4444-555566667777"
HIJO_ID = "bbbb1111-2222-3333-4444-555566667777"
HIJO = "Cloud Flow - MPPP - ING - Ingerir y validar correo"
NOMBRE = "Cloud Flow - MPPP - REC - Recibir correo nuevo"
EV = "sanic_mppp_ev_buzoningesta"
CLAVE_EV = "EV - MPPP - Buzon de ingesta (sanic_mppp_ev_buzoningesta)"

DEFINICION = {
    "triggers": {
        "Cuando_llega_un_correo": {
            "type": "OpenApiConnection",
            "splitOn": "@triggerOutputs()?['body/value']",
            "recurrence": {"interval": 1, "frequency": "Minute"},
            "inputs": {
                "host": {"connectionName": "@@conr:outlook@@", "operationId": "SharedMailboxOnNewEmailV2",
                         "apiId": "/providers/Microsoft.PowerApps/apis/shared_office365"},
                "parameters": {"mailboxAddress": "@parameters('@@ev:sanic_mppp_ev_buzoningesta@@')",
                               "folderId": "Inbox", "includeAttachments": False},
                "authentication": "@parameters('$authentication')",
            },
        }
    },
    "actions": {
        "Ingerir": {
            "runAfter": {},
            "type": "Workflow",
            "inputs": {"host": {"workflowReferenceName": "@@flujo:" + HIJO + "@@"},
                       "body": {"text": "@triggerOutputs()?['body/id']", "text_1": "MPPP-REC"}},
        }
    },
}

COMPONENTE = {
    "tipo": "flujo",
    "nombre": NOMBRE,
    "descripcion": "Llama a MPPP-ING por cada correo nuevo.",
    "archivo": "recursos/flujos/mppp-rec.json",
    "conexiones": {"outlook": {"referencia": "sanic_mppp_conr_outlook", "api": "shared_office365"}},
    "variables": [EV],
    "hijos": [HIJO],
    "activar": True,
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: flujo · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.raiz = self.dir.name
        self.ruta = os.path.join(self.raiz, "playbook.md")

    def escribir(self, componente=None, definicion=None, texto_definicion=None):
        componente = COMPONENTE if componente is None else componente
        destino = os.path.join(self.raiz, componente["archivo"])
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto_definicion if texto_definicion is not None
                    else json.dumps(DEFINICION if definicion is None else definicion, ensure_ascii=False))
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def construir(self, componente=None, solo_verificar=False, completar=False, cliente=None, **kw):
        cliente = cliente if cliente is not None else self.armar(ClienteSimulado())
        return fl.construir(self.escribir(componente, **kw), solo_verificar,
                            lambda: cliente, completar=completar, raiz=self.raiz)

    def armar(self, cliente, flujo=None, conectada=True, estado=(1, 2), hay_hijo=True):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.flujo, self.estado = flujo, estado
        cliente.responder("GET", lambda r: r.startswith("connectionreferences?"),
                          (200, {"value": [{"connectionreferencelogicalname": "sanic_mppp_conr_outlook",
                                            "connectionid": "c-1" if conectada else None,
                                            "statuscode": 1}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("environmentvariabledefinitions?"),
                          (200, {"value": [{"schemaname": EV, "displayname": "EV - MPPP - Buzon de ingesta",
                                            "defaultvalue": "mppp@ejemplo.com", "type": 100000000}]}, {}))

        def workflows(ruta, cuerpo, solucion):
            # El doble distingue la consulta del HIJO de la del flujo propio;
            # si no, un flujo que se llama igual que el hijo se lee mal.
            if f"name eq '{HIJO}'" in ruta and self.hay_hijo:
                return (200, {"value": [{"workflowid": HIJO_ID, "name": HIJO}]}, {})
            return (200, {"value": [] if self.flujo is None else [self.flujo]}, {})

        self.hay_hijo = hay_hijo

        cliente.responder("GET", lambda r: r.startswith("workflows?"), workflows)
        return cliente

    def fila(self, cuerpo=None, estado=(1, 2)):
        return {"workflowid": FLUJO_ID, "name": NOMBRE, "description": COMPONENTE["descripcion"],
                "clientdata": cuerpo, "statecode": estado[0], "statuscode": estado[1], "ismanaged": False}


class ValidacionOffline(Base):
    def rechaza(self, fragmento, **kw):
        centinela = FabricaCentinela()
        estado, _, detalle = fl.construir(self.escribir(**kw), False, centinela, raiz=self.raiz)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_marca_de_conexion_sin_declarar_se_rechaza(self):
        # Si pasara, se subiria una definicion con '@@conr:...@@' crudo y el
        # flujo reventaria recien al ejecutarse.
        mala = copy.deepcopy(DEFINICION)
        mala["triggers"]["Cuando_llega_un_correo"]["inputs"]["host"]["connectionName"] = "@@conr:teams@@"
        self.rechaza("el playbook no lo declara en 'conexiones'", definicion=mala)

    def test_una_conexion_declarada_que_nadie_usa_se_rechaza(self):
        malo = comp(conexiones=dict(COMPONENTE["conexiones"],
                                    dataverse={"referencia": "sanic_mppp_conr_dataverse",
                                               "api": "shared_commondataserviceforapps"}))
        self.rechaza("la definición no los usa", componente=malo)

    def test_un_hijo_sin_declarar_se_rechaza(self):
        self.rechaza("el playbook no lo declara en 'hijos'", componente=comp(hijos=[]))

    def test_una_variable_sin_declarar_se_rechaza(self):
        self.rechaza("el playbook no lo declara en 'variables'", componente=comp(variables=[]))

    def test_una_marca_sin_cerrar_se_rechaza(self):
        mala = copy.deepcopy(DEFINICION)
        mala["actions"]["Ingerir"]["inputs"]["body"]["text_1"] = "@@ev:sin_cerrar"
        self.rechaza("sin cerrar", definicion=mala)

    def test_dos_disparadores_se_rechazan(self):
        mala = copy.deepcopy(DEFINICION)
        mala["triggers"]["Otro"] = {"type": "Recurrence"}
        self.rechaza("un cloud flow tiene exactamente uno", definicion=mala)

    def test_un_nombre_fuera_de_convencion_se_rechaza(self):
        self.rechaza("no empieza con", componente=comp(nombre="Mi flujo"))

    def test_un_flujo_que_se_declara_hijo_de_si_mismo_se_rechaza(self):
        self.rechaza("hijo de sí mismo", componente=comp(hijos=[NOMBRE]))

    def test_un_json_invalido_se_rechaza_sin_tocar_la_red(self):
        self.rechaza("no es JSON válido", texto_definicion="{esto no es json}")

    def test_una_funcion_que_no_existe_se_rechaza(self):
        # `filter` NO es una función: filtrar una colección es una ACCIÓN. La
        # plataforma acepta la definición igual y falla recién AL EJECUTAR,
        # con "The template function 'filter' is not defined or not valid".
        # Pasó en Dev el 2026-09-22 con MPPP-VIG, en la primera corrida.
        mala = copy.deepcopy(DEFINICION)
        mala["actions"]["Ingerir"]["inputs"]["body"]["text_1"] = (
            "@filter(outputs('x'), equals(item(), 1))")
        self.rechaza("no es una función del lenguaje de expresiones", definicion=mala)

    def test_las_funciones_del_lenguaje_se_aceptan(self):
        buena = copy.deepcopy(DEFINICION)
        buena["actions"]["Ingerir"]["inputs"]["body"]["text_1"] = (
            "@int(coalesce(first(outputs('x')?['body/value'])?['v'], '3'))")
        self.escribir(COMPONENTE, definicion=buena)
        fl.validar_playbook(COMPONENTE, IDENT, self.raiz)   # no lanza

    def test_un_flujo_hijo_sin_accion_Response_se_rechaza(self):
        # La plataforma deja CREARLO y despues rechaza ACTIVAR AL PADRE con
        # ChildFlowMissingResponseOperation: el error aparece lejos del archivo
        # que lo causa. Verificado en Dev el 2026-09-22.
        hijo = comp(nombre=HIJO, activar=False, hijos=[], conexiones={}, variables=[])
        definicion = {
            "triggers": {"manual": {"type": "Request", "kind": "Button",
                                    "inputs": {"schema": {"type": "object", "properties": {}}}}},
            "actions": {"Componer": {"runAfter": {}, "type": "Compose", "inputs": "x"}},
        }
        self.rechaza("ChildFlowMissingResponseOperation", componente=hijo, definicion=definicion)

    def test_un_flujo_hijo_con_Response_se_acepta(self):
        hijo = comp(nombre=HIJO, activar=False, hijos=[], conexiones={}, variables=[])
        definicion = {
            "triggers": {"manual": {"type": "Request", "kind": "Button",
                                    "inputs": {"schema": {"type": "object", "properties": {}}}}},
            "actions": {"Responder": {"runAfter": {}, "type": "Response",
                                      "kind": "PowerApp", "inputs": {"statusCode": 200}}},
        }
        self.escribir(hijo, definicion=definicion)
        # No lanza: la validación offline pasa entera.
        fl.validar_playbook(hijo, IDENT, self.raiz)


class ArmadoDelClientdata(Base):
    def armado(self, componente=None, definicion=None):
        componente = COMPONENTE if componente is None else componente
        return fl.clientdata(copy.deepcopy(DEFINICION if definicion is None else definicion), componente,
                             {HIJO: HIJO_ID}, {EV: CLAVE_EV},
                             {CLAVE_EV: {"defaultValue": "x", "type": "String",
                                         "metadata": {"schemaName": EV}}})

    def test_no_queda_ninguna_marca_sin_resolver(self):
        self.assertNotIn("@@", self.armado())

    def test_el_hijo_se_resuelve_a_su_workflowid(self):
        self.assertIn(f'"workflowReferenceName": "{HIJO_ID}"', self.armado())

    def test_la_variable_se_resuelve_a_su_clave_de_parametro(self):
        d = json.loads(self.armado())
        self.assertIn(CLAVE_EV, d["properties"]["definition"]["parameters"])
        self.assertIn(f"@parameters('{CLAVE_EV}')", self.armado())

    def test_la_connection_reference_viaja_por_su_nombre_logico(self):
        d = json.loads(self.armado())
        ref = d["properties"]["connectionReferences"]["outlook"]
        self.assertEqual("sanic_mppp_conr_outlook", ref["connection"]["connectionReferenceLogicalName"])
        self.assertEqual("shared_office365", ref["api"]["name"])

    def test_siempre_lleva_los_dos_parametros_de_sistema(self):
        d = json.loads(self.armado())
        for p in ("$connections", "$authentication"):
            self.assertIn(p, d["properties"]["definition"]["parameters"])

    def test_la_comparacion_ignora_los_identificadores_del_disenador(self):
        # `operationMetadataId` lo regenera el diseñador y no cambia nada.
        con = copy.deepcopy(DEFINICION)
        con["actions"]["Ingerir"]["metadata"] = {"operationMetadataId": "cualquiera"}
        self.assertEqual(fl._normalizar(self.armado()),
                         fl._normalizar(self.armado(definicion=con)))


class ContraElEntorno(Base):
    def test_el_alta_crea_el_flujo_y_lo_activa(self):
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.flujo = self.fila(cuerpo["clientdata"], estado=(0, 1))
            return (204, {}, {})

        cliente.responder("POST", "workflows", crear)

        def parchear(ruta, cuerpo, solucion):
            if "statecode" in cuerpo:
                self.flujo = dict(self.flujo, statecode=cuerpo["statecode"], statuscode=cuerpo["statuscode"])
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("workflows("), parchear)

        estado, _, detalle = self.construir(cliente=cliente)
        self.assertEqual("creado", estado, detalle)
        alta = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "workflows")
        self.assertEqual(fl.CATEGORIA_MODERNA, alta["category"])
        self.assertNotIn("@@", alta["clientdata"])
        self.assertIn("activado", detalle)

    def test_un_flujo_hijo_no_se_activa(self):
        cliente = self.armar(ClienteSimulado(), hay_hijo=False)
        hijo = comp(nombre=HIJO, activar=False, hijos=[])
        definicion = copy.deepcopy(DEFINICION)
        definicion["actions"]["Ingerir"] = {"runAfter": {}, "type": "Compose", "inputs": "x"}

        def crear(ruta, cuerpo, solucion):
            self.flujo = dict(self.fila(cuerpo["clientdata"], estado=(0, 1)), name=HIJO)
            return (204, {}, {})

        cliente.responder("POST", "workflows", crear)
        cliente.responder("PATCH", lambda r: r.startswith("workflows("), (204, {}, {}))

        estado, _, detalle = self.construir(componente=hijo, definicion=definicion, cliente=cliente)
        self.assertEqual("creado", estado, detalle)
        self.assertIn("flujo hijo", detalle)
        estados = [l["cuerpo"] for l in cliente.llamadas if l["metodo"] == "PATCH" and "statecode" in (l["cuerpo"] or {})]
        self.assertTrue(all(e["statecode"] == 0 for e in estados), estados)

    def test_una_connection_reference_sin_conexion_queda_bloqueada_sin_escribir(self):
        cliente = self.armar(ClienteSimulado(), conectada=False)
        estado, _, detalle = self.construir(cliente=cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("una persona tiene que conectarla", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_hijo_que_no_existe_queda_bloqueado_sin_escribir(self):
        cliente = self.armar(ClienteSimulado(), hay_hijo=False)
        estado, _, detalle = self.construir(cliente=cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("hay que construirlo antes", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_no_crea_nada(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = self.construir(solo_verificar=True, cliente=cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_definicion_distinta_se_informa_y_no_se_pisa_sin_completar(self):
        cliente = self.armar(ClienteSimulado(), flujo=self.fila('{"properties":{"otra":1}}'))
        estado, _, detalle = self.construir(cliente=cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no es la del archivo del repositorio", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_con_completar_un_flujo_activo_se_apaga_antes_de_corregirlo(self):
        # Un flujo ACTIVO no acepta que le cambien la definición.
        cliente = self.armar(ClienteSimulado(), flujo=self.fila('{"properties":{"otra":1}}', estado=(1, 2)))

        def parchear(ruta, cuerpo, solucion):
            if "clientdata" in cuerpo:
                self.flujo = dict(self.flujo, clientdata=cuerpo["clientdata"])
            if "statecode" in cuerpo:
                self.flujo = dict(self.flujo, statecode=cuerpo["statecode"], statuscode=cuerpo["statuscode"])
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("workflows("), parchear)
        estado, _, detalle = self.construir(completar=True, cliente=cliente)
        self.assertEqual("creado", estado, detalle)
        cuerpos = [l["cuerpo"] for l in cliente.llamadas if l["metodo"] == "PATCH"]
        self.assertEqual(0, cuerpos[0].get("statecode"), "lo primero es apagarlo")
        self.assertIn("clientdata", cuerpos[1])
        self.assertEqual(1, cuerpos[-1].get("statecode"), "y al final se vuelve a encender")

    def test_si_ya_esta_igual_no_se_escribe_nada(self):
        cliente = self.armar(ClienteSimulado())
        esperado = fl.clientdata(copy.deepcopy(DEFINICION), COMPONENTE, {HIJO: HIJO_ID}, {EV: CLAVE_EV},
                                 {CLAVE_EV: {"defaultValue": "mppp@ejemplo.com", "type": "String",
                                             "metadata": {"schemaName": EV}}})
        self.flujo = self.fila(esperado)
        cliente.responder("GET", lambda r: r.startswith("workflows?"),
                          lambda r, c, s: (200, {"value": [self.fila(esperado)]}, {})
                          if f"name eq '{HIJO}'" not in r
                          else (200, {"value": [{"workflowid": HIJO_ID, "name": HIJO}]}, {}))
        estado, _, detalle = self.construir(cliente=cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())


if __name__ == "__main__":
    unittest.main()
