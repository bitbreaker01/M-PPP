"""Pruebas de `herramientas/construir/step.py`. Nunca tocan la red.

El foco está en las IMÁGENES y en las combinaciones que Learn prohíbe: un step
mal registrado no falla al registrarse, falla en producción la primera vez que
alguien guarda un registro. Todo eso tiene que quedar frenado sin red.
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

import step as st  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="steps", inventario="8.2")

TIPO_LISTA = "Sanic.Mppp.Plugins.Steps.ListaBlancaStep"
TIPO_TRANSICION = "Sanic.Mppp.Plugins.Steps.TransicionDeFilaStep"
FILA = "sanic_mppp_tbl_fila"

STEP_LISTA = {
    "nombre": "MPPP - Lista blanca - Update de Fila",
    "descripcion": "Una persona solo puede escribir las columnas permitidas.",
    "plugintype": TIPO_LISTA,
    "mensaje": "Update",
    "tabla": FILA,
    "etapa": "PreOperation",
    "modo": "Sincrono",
    "orden": 0,
    "filtro": [],
    "preimagen": None,
}

STEP_TRANSICION = {
    "nombre": "MPPP - Transicion de Fila - Update",
    "descripcion": "Autoriza el cambio de estado de una Fila y escribe quien actuo.",
    "plugintype": TIPO_TRANSICION,
    "mensaje": "Update",
    "tabla": FILA,
    "etapa": "PreOperation",
    "modo": "Sincrono",
    "orden": 1,
    "filtro": ["sanic_estado"],
    "preimagen": {"alias": "PreImagen", "columnas": ["sanic_estado", "sanic_digitadapor", "sanic_solicitudid"]},
}

COMPONENTE = {"tipo": "steps", "paquete": "sanic_mppp_pkg_plugins", "steps": [STEP_LISTA, STEP_TRANSICION]}

IDS = {TIPO_LISTA: "t-lista", TIPO_TRANSICION: "t-transicion"}
MENSAJE_ID = "m-update"
FILTRO_ID = "f-fila-update"


def comp(steps=None, **cambios):
    d = copy.deepcopy(COMPONENTE)
    if steps is not None:
        d["steps"] = steps
    d.update(cambios)
    return d


def un_step(base=STEP_LISTA, **cambios):
    s = copy.deepcopy(base)
    s.update(cambios)
    return s


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: steps · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def step_id_de(s):
    return "step-" + s["plugintype"].rsplit(".", 1)[-1]


def fila_step(s, **cambios):
    fila = {
        "sdkmessageprocessingstepid": step_id_de(s),
        "name": s["nombre"],
        "description": s["descripcion"],
        "stage": st.ETAPAS[s["etapa"]],
        "mode": st.MODOS[s["modo"]],
        "rank": s["orden"],
        "filteringattributes": st.texto_de_filtro(s["filtro"]),
        "statecode": 0,
        "supporteddeployment": 0,
    }
    fila.update(cambios)
    return fila


def fila_imagen(s, **cambios):
    imagen = {
        "sdkmessageprocessingstepimageid": "img-" + step_id_de(s),
        "imagetype": st.IMAGEN_PRE,
        "entityalias": s["preimagen"]["alias"],
        "attributes": ",".join(sorted(s["preimagen"]["columnas"])),
        "messagepropertyname": "Target",
        "name": s["preimagen"]["alias"],
    }
    imagen.update(cambios)
    return imagen


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, steps_en_entorno=None, imagenes=None, en_solucion=True, tipos_faltantes=()):
        """`steps_en_entorno` e `imagenes` son dicts por step_id. Se responde
        siempre lo mismo salvo que la prueba los mute entre llamadas."""
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.steps_en_entorno = {} if steps_en_entorno is None else steps_en_entorno
        self.imagenes = {} if imagenes is None else imagenes

        def responder_tipos(ruta, cuerpo, solucion):
            for typename, tid in IDS.items():
                if f"'{typename}'" in ruta:
                    if typename in tipos_faltantes:
                        return (200, {"value": []}, {})
                    return (200, {"value": [{"plugintypeid": tid, "typename": typename}]}, {})
            return (200, {"value": []}, {})

        cliente.responder("GET", lambda r: r.startswith("plugintypes?"), responder_tipos)
        cliente.responder("GET", lambda r: r.startswith("sdkmessages?"),
                          (200, {"value": [{"sdkmessageid": MENSAJE_ID, "name": "Update"}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("sdkmessagefilters?"),
                          (200, {"value": [{"sdkmessagefilterid": FILTRO_ID, "primaryobjecttypecode": FILA,
                                            "sdkmessageid": {"name": "Update"}}]}, {}))

        def responder_steps(ruta, cuerpo, solucion):
            for typename, tid in IDS.items():
                if f"eq {tid} " in ruta:
                    fila = self.steps_en_entorno.get(typename)
                    return (200, {"value": [] if fila is None else [fila]}, {})
            return (200, {"value": []}, {})

        cliente.responder("GET", lambda r: r.startswith("sdkmessageprocessingsteps?"), responder_steps)

        def responder_imagenes(ruta, cuerpo, solucion):
            for sid, filas in self.imagenes.items():
                if f"eq {sid}" in ruta:
                    return (200, {"value": filas}, {})
            return (200, {"value": []}, {})

        cliente.responder("GET", lambda r: r.startswith("sdkmessageprocessingstepimages?"), responder_imagenes)
        cliente.responder("GET", es_ruta_solutioncomponents,
                          (200, {"value": [{"componenttype": 92, "objectid": "x"}] if en_solucion else []}, {}))
        return cliente


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = st.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada, "no tenía que intentar construir el cliente de Dataverse")

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza(comp(steps=[{k: v for k, v in STEP_LISTA.items() if k != "etapa"}]), "faltan ['etapa']")
        self.rechaza(comp(steps=[un_step(sobrante=1)]), "sobran ['sobrante']")

    def test_una_etapa_o_un_modo_que_no_existen_se_rechazan(self):
        self.rechaza(comp(steps=[un_step(etapa="MainOperation")]), "no es válida")
        self.rechaza(comp(steps=[un_step(modo="Diferido")]), "no es válido")

    def test_un_step_asincrono_fuera_de_postoperation_se_rechaza(self):
        # Learn: async solo se admite en PostOperation.
        self.rechaza(comp(steps=[un_step(modo="Asincrono", etapa="PreOperation")]), "solo se puede registrar en PostOperation")
        self.rechaza(comp(steps=[un_step(modo="Asincrono", etapa="PreValidation")]), "solo se puede registrar en PostOperation")

    def test_un_step_asincrono_en_postoperation_se_acepta(self):
        bueno = comp(steps=[un_step(modo="Asincrono", etapa="PostOperation")])
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = st.construir(self.escribir(bueno), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)  # no existe todavía, pero pasó la validación

    def test_una_preimagen_sobre_create_se_rechaza(self):
        # No hay "antes" de un Create.
        malo = un_step(base=STEP_TRANSICION, mensaje="Create", filtro=[])
        self.rechaza(comp(steps=[malo]), "no puede tener pre-imagen")

    def test_una_preimagen_sobre_un_mensaje_que_no_la_admite_se_rechaza(self):
        malo = un_step(base=STEP_TRANSICION, mensaje="Associate", filtro=[])
        self.rechaza(comp(steps=[malo]), "no admite imágenes")

    def test_una_preimagen_sin_columnas_se_rechaza(self):
        # Vacío significa TODAS las columnas: mala práctica de rendimiento.
        malo = un_step(base=STEP_TRANSICION, preimagen={"alias": "PreImagen", "columnas": []})
        self.rechaza(comp(steps=[malo]), "columnas")

    def test_una_preimagen_con_columnas_repetidas_se_rechaza(self):
        malo = un_step(base=STEP_TRANSICION, preimagen={"alias": "PreImagen", "columnas": ["sanic_estado", "sanic_estado"]})
        self.rechaza(comp(steps=[malo]), "columnas repetidas")

    def test_un_filtro_sobre_create_se_rechaza(self):
        self.rechaza(comp(steps=[un_step(mensaje="Create", filtro=["sanic_estado"])]), "solo tiene sentido en")

    def test_el_filtro_no_puede_llevar_la_clave_primaria(self):
        # Viene siempre en el Target: deja el filtro sin efecto.
        malo = un_step(filtro=["sanic_estado", FILA + "id"])
        self.rechaza(comp(steps=[malo]), "no puede incluir la clave primaria")

    def test_dos_steps_del_mismo_plugin_sobre_el_mismo_mensaje_y_tabla_se_rechazan(self):
        self.rechaza(comp(steps=[STEP_LISTA, un_step(nombre="Otro")]), "ya hay otro step del mismo plugin")

    def test_dos_steps_con_el_mismo_nombre_se_rechazan(self):
        otro = un_step(base=STEP_TRANSICION, nombre=STEP_LISTA["nombre"])
        self.rechaza(comp(steps=[STEP_LISTA, otro]), "el nombre está repetido")

    def test_los_nombres_visibles_van_sin_tildes(self):
        self.rechaza(comp(steps=[un_step(nombre="MPPP - Transición")]), "fuera de ASCII")

    def test_el_filtro_se_ordena_para_que_el_orden_no_produzca_falsas_diferencias(self):
        self.assertEqual("a,b,c", st.texto_de_filtro(["c", "a", "b"]))
        self.assertIsNone(st.texto_de_filtro([]))


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_sin_el_paquete_registrado_queda_bloqueado_y_no_escribe(self):
        cliente = self.armar(ClienteSimulado(), tipos_faltantes=(TIPO_LISTA,))
        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("paquete_plugins.py", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_tabla_que_no_admite_el_mensaje_queda_bloqueada(self):
        cliente = ClienteSimulado()
        armar_cliente_precondiciones_ok(cliente, IDENT)
        cliente.responder("GET", lambda r: r.startswith("plugintypes?"),
                          (200, {"value": [{"plugintypeid": "t-lista", "typename": TIPO_LISTA}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("sdkmessages?"),
                          (200, {"value": [{"sdkmessageid": MENSAJE_ID, "name": "Update"}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("sdkmessagefilters?"), (200, {"value": []}, {}))
        estado, _, detalle = st.construir(self.escribir(comp(steps=[STEP_LISTA])), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("no admite el mensaje", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_alta_manda_el_eventhandler_por_su_propiedad_polimorfica(self):
        # `eventhandler` NO acepta un @odata.bind genérico: hay que usar la
        # propiedad de navegación del destino.
        cliente = self.armar(ClienteSimulado())
        creados = {}

        def crear(ruta, cuerpo, solucion):
            creados["cuerpo"] = cuerpo
            s = STEP_LISTA if cuerpo["plugintypeid@odata.bind"].endswith("(t-lista)") else STEP_TRANSICION
            self.steps_en_entorno[s["plugintype"]] = fila_step(s)
            if s["preimagen"]:
                self.imagenes[step_id_de(s)] = []
            return (204, {}, {})

        cliente.responder("POST", "sdkmessageprocessingsteps", crear)

        def crear_imagen(ruta, cuerpo, solucion):
            self.imagenes[step_id_de(STEP_TRANSICION)] = [fila_imagen(STEP_TRANSICION)]
            return (204, {}, {})

        cliente.responder("POST", "sdkmessageprocessingstepimages", crear_imagen)

        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        cuerpo = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "sdkmessageprocessingsteps")
        self.assertIn("eventhandler_plugintype@odata.bind", cuerpo)
        self.assertNotIn("eventhandler@odata.bind", cuerpo)
        self.assertEqual(cuerpo["plugintypeid@odata.bind"], cuerpo["eventhandler_plugintype@odata.bind"])
        self.assertEqual(20, cuerpo["stage"])   # PreOperation
        self.assertEqual(0, cuerpo["mode"])     # Sincrono
        self.assertEqual(0, cuerpo["supporteddeployment"])
        self.assertEqual(IDENT["solucion"], next(l["solucion"] for l in cliente.llamadas if l["metodo"] == "POST"))

    def test_la_preimagen_se_crea_con_target_y_las_columnas_declaradas(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): []},
        )

        def crear_imagen(ruta, cuerpo, solucion):
            self.imagenes[step_id_de(STEP_TRANSICION)] = [fila_imagen(STEP_TRANSICION)]
            return (204, {}, {})

        cliente.responder("POST", "sdkmessageprocessingstepimages", crear_imagen)

        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        cuerpo = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "sdkmessageprocessingstepimages")
        self.assertEqual(0, cuerpo["imagetype"])  # PreImage
        self.assertEqual("Target", cuerpo["messagepropertyname"])
        self.assertEqual("PreImagen", cuerpo["entityalias"])
        self.assertEqual("sanic_digitadapor,sanic_estado,sanic_solicitudid", cuerpo["attributes"])
        self.assertEqual(f"/sdkmessageprocessingsteps({step_id_de(STEP_TRANSICION)})",
                         cuerpo["sdkmessageprocessingstepid@odata.bind"])

    def test_una_preimagen_que_falta_se_agrega_aunque_no_pidan_completar(self):
        # No es un ajuste de gusto: sin ella el plugin revienta al primer guardado.
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): []},
        )

        def crear_imagen(ruta, cuerpo, solucion):
            self.imagenes[step_id_de(STEP_TRANSICION)] = [fila_imagen(STEP_TRANSICION)]
            return (204, {}, {})

        cliente.responder("POST", "sdkmessageprocessingstepimages", crear_imagen)
        estado, _, _ = st.construir(self.escribir(), False, lambda: cliente, completar=False)
        self.assertEqual("creado", estado)

    def test_solo_verificar_denuncia_la_preimagen_que_falta_y_no_escribe(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): []},
        )
        estado, _, detalle = st.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("le falta la pre-imagen", detalle)
        self.assertIn("revienta al primer guardado", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_si_ya_esta_todo_bien_no_se_escribe_nada(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )
        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertIn("2 que ya estaban", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_orden_distinto_se_denuncia_nombrando_el_step(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA, rank=5), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )
        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn(STEP_LISTA["nombre"], detalle)
        self.assertIn("rank es 5", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_corrige_el_orden_con_un_patch(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA, rank=5), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )

        def corregir(ruta, cuerpo, solucion):
            self.steps_en_entorno[TIPO_LISTA] = fila_step(STEP_LISTA)
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("sdkmessageprocessingsteps("), corregir)

        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        patches = [l for l in cliente.llamadas if l["metodo"] == "PATCH"]
        self.assertEqual(1, len(patches))
        self.assertEqual(0, patches[0]["cuerpo"]["rank"])
        # La clave natural nunca se toca: eso sería otro step, no una corrección.
        for prohibido in ("plugintypeid@odata.bind", "sdkmessageid@odata.bind", "sdkmessagefilterid@odata.bind"):
            self.assertNotIn(prohibido, patches[0]["cuerpo"])

    def test_completar_puede_borrar_un_filtro_que_sobra(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={
                TIPO_LISTA: fila_step(STEP_LISTA, filteringattributes="sanic_estado"),
                TIPO_TRANSICION: fila_step(STEP_TRANSICION),
            },
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )

        def corregir(ruta, cuerpo, solucion):
            self.steps_en_entorno[TIPO_LISTA] = fila_step(STEP_LISTA)
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("sdkmessageprocessingsteps("), corregir)
        st.construir(self.escribir(), False, lambda: cliente, completar=True)
        patch = next(l for l in cliente.llamadas if l["metodo"] == "PATCH")
        self.assertIn("filteringattributes", patch["cuerpo"])
        self.assertIsNone(patch["cuerpo"]["filteringattributes"])

    def test_un_step_deshabilitado_se_denuncia(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA, statecode=1), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )
        estado, _, detalle = st.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("deshabilitado", detalle)

    def test_columnas_de_preimagen_distintas_se_denuncian(self):
        pobre = fila_imagen(STEP_TRANSICION, attributes="sanic_estado")
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [pobre]},
        )
        estado, _, detalle = st.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("columnas de la pre-imagen", detalle)

    def test_el_orden_de_las_columnas_del_filtro_no_produce_una_falsa_diferencia(self):
        al_reves = fila_step(STEP_TRANSICION, filteringattributes="sanic_estado")
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: al_reves},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
        )
        estado, _, detalle = st.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)

    def test_un_step_fuera_de_la_solucion_se_denuncia(self):
        cliente = self.armar(
            ClienteSimulado(),
            steps_en_entorno={TIPO_LISTA: fila_step(STEP_LISTA), TIPO_TRANSICION: fila_step(STEP_TRANSICION)},
            imagenes={step_id_de(STEP_TRANSICION): [fila_imagen(STEP_TRANSICION)]},
            en_solucion=False,
        )
        estado, _, detalle = st.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no figura como componente de la solución", detalle)

    def test_un_http_inesperado_en_el_alta_no_se_confunde_con_exito(self):
        cliente = self.armar(ClienteSimulado())
        cliente.responder("POST", "sdkmessageprocessingsteps", (400, {"error": "rank invalido"}, {}))
        estado, _, detalle = st.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("HTTP 400", detalle)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = st.salida
        try:
            sys.argv = ["step.py", self.escribir(), "--forzar"]
            st.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            st.main()
        finally:
            sys.argv, st.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
