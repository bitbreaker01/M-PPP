"""Pruebas de `herramientas/construir/vista.py`. Nunca tocan la red.

Lo que más se prueba: que el `fetchxml` y el `layoutxml` GENERADOS estén de
acuerdo entre sí. Cada `<cell>` del layout necesita su `<attribute>` en el
fetch; si se despegan, la vista sale con una columna en blanco y eso no falla
al crearse, falla cuando alguien la abre.
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

import vista as vi  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, SOLUTION_ID, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="vista", inventario="12.2")

TABLA = "sanic_mppp_tbl_fila"
PRIMARIA = "sanic_mppp_tbl_filaid"
CODIGO_TABLA = 10123
VISTA_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
METADATA_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"

COMPONENTE = {
    "tipo": "vista",
    "nombre": "Mis clientes - por digitar",
    "tabla": TABLA,
    "clase": "Publica",
    "descripcion": "Filas validadas de los clientes del ejecutivo que mira.",
    "pordefecto": True,
    "columnas": [
        {"nombre": "sanic_solicitudid", "ancho": 140},
        {"nombre": "sanic_numerofila", "ancho": 70},
        {"nombre": "sanic_nombrebeneficiario"},
    ],
    "orden": [{"columna": "sanic_solicitudid", "sentido": "asc"},
              {"columna": "sanic_numerofila", "sentido": "asc"}],
    "filtro": {
        "tipo": "and",
        "condiciones": [{"columna": "sanic_estado", "operador": "eq", "valores": [159460003]}],
        "enlaces": [{
            "tabla": "sanic_mppp_tbl_plan", "de": "sanic_mppp_tbl_planid", "a": "sanic_planid", "alias": "plan",
            "enlaces": [{
                "tabla": "sanic_mppp_tbl_cliente", "de": "sanic_mppp_tbl_clienteid", "a": "sanic_clienteid",
                "alias": "cliente",
                "condiciones": [{"columna": "ownerid", "operador": "eq-userid"}],
            }],
        }],
    },
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: vista · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def fila_vista(datos=None, **cambios):
    datos = COMPONENTE if datos is None else datos
    fila = {
        "savedqueryid": VISTA_ID,
        "name": datos["nombre"],
        "description": datos["descripcion"],
        "returnedtypecode": datos["tabla"],
        "querytype": vi.CLASES[datos["clase"]],
        "isdefault": datos["pordefecto"],
        "fetchxml": vi.fetchxml(datos, PRIMARIA),
        "layoutxml": vi.layoutxml(datos, PRIMARIA, CODIGO_TABLA),
        "statecode": 0,
        "ismanaged": False,
    }
    fila.update(cambios)
    return fila


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, vista=None, sin_tabla=False, en_solucion=True, comportamiento=0):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.vista = vista
        self.comportamiento = comportamiento
        cliente.responder(
            "GET", lambda r: r.startswith("EntityDefinitions("),
            (404, {}, {}) if sin_tabla else
            (200, {"PrimaryIdAttribute": PRIMARIA, "ObjectTypeCode": CODIGO_TABLA, "MetadataId": METADATA_ID}, {}))
        cliente.responder("GET", lambda r: r.startswith("savedqueries?"),
                          lambda r, c, s: (200, {"value": [] if self.vista is None else [self.vista]}, {}))
        # La vista NO tiene fila propia en solutioncomponents: viaja dentro de
        # su tabla. Lo que se consulta es la fila de la TABLA.
        fila_tabla = [{"componenttype": 1, "rootcomponentbehavior": self.comportamiento, "objectid": METADATA_ID}]
        cliente.responder("GET", es_ruta_solutioncomponents,
                          (200, {"value": fila_tabla if en_solucion else []}, {}))
        return cliente


# ---------------------------------------------------------------------------
# El XML generado
# ---------------------------------------------------------------------------
class XmlGenerado(unittest.TestCase):
    def test_cada_celda_del_layout_tiene_su_atributo_en_el_fetch(self):
        # Es LA invariante de esta herramienta.
        fetch = vi.fetchxml(COMPONENTE, PRIMARIA)
        layout = vi.layoutxml(COMPONENTE, PRIMARIA, CODIGO_TABLA)
        for columna in [c["nombre"] for c in COMPONENTE["columnas"]]:
            self.assertIn(f'<cell name="{columna}"', layout)
            self.assertIn(f'<attribute name="{columna}" />', fetch)

    def test_la_primaria_va_siempre_en_el_fetch_aunque_no_se_muestre(self):
        # La grilla la necesita para abrir el registro.
        fetch = vi.fetchxml(COMPONENTE, PRIMARIA)
        self.assertIn(f'<attribute name="{PRIMARIA}" />', fetch)
        self.assertNotIn(f'<cell name="{PRIMARIA}"', vi.layoutxml(COMPONENTE, PRIMARIA, CODIGO_TABLA))

    def test_la_primaria_no_se_duplica_si_el_playbook_la_declara(self):
        datos = comp(columnas=[{"nombre": PRIMARIA}, {"nombre": "sanic_numerofila"}],
                     orden=[{"columna": "sanic_numerofila", "sentido": "asc"}])
        fetch = vi.fetchxml(datos, PRIMARIA)
        self.assertEqual(1, fetch.count(f'<attribute name="{PRIMARIA}" />'))

    def test_el_orden_descendente_se_escribe_como_descending_true(self):
        datos = comp(orden=[{"columna": "sanic_numerofila", "sentido": "desc"}])
        self.assertIn('<order attribute="sanic_numerofila" descending="true" />', vi.fetchxml(datos, PRIMARIA))

    def test_los_enlaces_anidados_salen_anidados(self):
        fetch = vi.fetchxml(COMPONENTE, PRIMARIA)
        self.assertIn('<link-entity name="sanic_mppp_tbl_plan"', fetch)
        self.assertIn('<link-entity name="sanic_mppp_tbl_cliente"', fetch)
        self.assertIn('<condition attribute="ownerid" operator="eq-userid" />', fetch)
        # El de cliente está ADENTRO del de plan: dos saltos, no dos hermanos.
        i_plan = fetch.index('name="sanic_mppp_tbl_plan"')
        i_cliente = fetch.index('name="sanic_mppp_tbl_cliente"')
        i_cierre = fetch.index("</link-entity>")
        self.assertLess(i_plan, i_cliente)
        self.assertLess(i_cliente, i_cierre)

    def test_un_operador_de_varios_valores_escribe_un_value_por_cada_uno(self):
        datos = comp(filtro={"tipo": "and", "condiciones": [
            {"columna": "sanic_estado", "operador": "in", "valores": [1, 2, 3]}]})
        fetch = vi.fetchxml(datos, PRIMARIA)
        self.assertIn("<value>1</value><value>2</value><value>3</value>", fetch)

    def test_una_columna_enlazada_sale_dentro_de_su_link_entity(self):
        # El correo del Autorizado en la subgrilla del Plan, el Cliente en
        # "Todos - por digitar": el atributo va ADENTRO del link-entity y la
        # celda se llama alias.columna.
        datos = comp(columnas=[{"nombre": "sanic_numerofila"},
                               {"nombre": "sanic_nombre", "enlace": "cliente", "ancho": 180}],
                     orden=[{"columna": "sanic_numerofila", "sentido": "asc"}])
        fetch = vi.fetchxml(datos, PRIMARIA)
        layout = vi.layoutxml(datos, PRIMARIA, CODIGO_TABLA)
        self.assertIn('<cell name="cliente.sanic_nombre" width="180" />', layout)
        # El atributo NO va suelto en la entidad raíz...
        raiz = fetch[:fetch.index("<link-entity")]
        self.assertNotIn('<attribute name="sanic_nombre" />', raiz)
        # ...sino adentro del link-entity de cliente.
        dentro = fetch[fetch.index('alias="cliente"'):]
        self.assertIn('<attribute name="sanic_nombre" />', dentro)

    def test_una_columna_que_nombra_un_enlace_inexistente_se_rechaza(self):
        datos = comp(columnas=[{"nombre": "sanic_numerofila"},
                               {"nombre": "sanic_nombre", "enlace": "inventado"}],
                     orden=[{"columna": "sanic_numerofila", "sentido": "asc"}])
        with self.assertRaises(vi.ErrorPlaybook) as ctx:
            vi.validar_playbook(datos)
        self.assertIn("que el filtro no declara", str(ctx.exception))

    def test_la_misma_columna_de_dos_enlaces_distintos_no_es_repetida(self):
        datos = comp(columnas=[{"nombre": "sanic_numerofila"},
                               {"nombre": "sanic_nombre", "enlace": "plan"},
                               {"nombre": "sanic_nombre", "enlace": "cliente"}],
                     orden=[{"columna": "sanic_numerofila", "sentido": "asc"}])
        vi.validar_playbook(datos)  # no lanza

    def test_los_valores_se_escapan_para_no_romper_el_xml(self):
        datos = comp(filtro={"tipo": "and", "condiciones": [
            {"columna": "sanic_mensaje", "operador": "like", "valores": ['%<script>&"%']}]})
        fetch = vi.fetchxml(datos, PRIMARIA)
        self.assertNotIn("<script>", fetch)
        self.assertIn("&lt;script&gt;", fetch)


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = vi.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza({k: v for k, v in COMPONENTE.items() if k != "filtro"}, "faltan ['filtro']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_una_clase_que_no_existe_se_rechaza_nombrando_las_validas(self):
        self.rechaza(comp(clase="Grilla"), "no es válida")

    def test_una_vista_sin_columnas_se_rechaza(self):
        self.rechaza(comp(columnas=[]), "columnas")

    def test_columnas_repetidas_se_rechazan(self):
        self.rechaza(comp(columnas=[{"nombre": "sanic_numerofila"}, {"nombre": "sanic_numerofila"}],
                          orden=[{"columna": "sanic_numerofila", "sentido": "asc"}]), "columnas repetidas")

    def test_ordenar_por_una_columna_que_no_se_muestra_se_rechaza(self):
        # El usuario no entendería por qué la grilla está en ese orden.
        self.rechaza(comp(orden=[{"columna": "sanic_fechavalidada", "sentido": "asc"}]), "que la vista no muestra")

    def test_un_operador_que_no_esta_en_la_lista_cerrada_se_rechaza(self):
        self.rechaza(comp(filtro={"condiciones": [{"columna": "x", "operador": "contains", "valores": ["a"]}]}),
                     "no admitido")

    def test_la_cantidad_de_valores_tiene_que_calzar_con_el_operador(self):
        self.rechaza(comp(filtro={"condiciones": [{"columna": "x", "operador": "eq", "valores": [1, 2]}]}),
                     "exactamente un valor")
        self.rechaza(comp(filtro={"condiciones": [{"columna": "x", "operador": "null", "valores": [1]}]}),
                     "no lleva valores")
        self.rechaza(comp(filtro={"condiciones": [{"columna": "x", "operador": "in", "valores": []}]}),
                     "al menos un valor")

    def test_un_ancho_absurdo_se_rechaza(self):
        self.rechaza(comp(columnas=[{"nombre": "sanic_numerofila", "ancho": 5000}],
                          orden=[{"columna": "sanic_numerofila", "sentido": "asc"}]), "fuera de 25..800")

    def test_mas_de_tres_saltos_de_enlace_se_rechaza(self):
        def anidar(n):
            e = {"tabla": "t", "de": "a", "a": "b", "alias": f"x{n}"}
            return e if n == 0 else dict(e, enlaces=[anidar(n - 1)])
        self.rechaza(comp(filtro={"enlaces": [anidar(4)]}), "no es una vista de grilla")

    def test_el_nombre_visible_va_sin_tildes(self):
        self.rechaza(comp(nombre="Mis clientes - por digitación"), "fuera de ASCII")


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_una_tabla_que_no_existe_queda_bloqueada_sin_escribir(self):
        cliente = self.armar(ClienteSimulado(), sin_tabla=True)
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_alta_manda_los_dos_xml_generados_y_va_a_la_solucion(self):
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.vista = fila_vista()
            return (204, {}, {})

        cliente.responder("POST", "savedqueries", crear)

        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        post = next(l for l in cliente.llamadas if l["metodo"] == "POST")
        self.assertEqual(IDENT["solucion"], post["solucion"])
        self.assertEqual(0, post["cuerpo"]["querytype"])
        self.assertIn("<fetch", post["cuerpo"]["fetchxml"])
        self.assertIn("<grid", post["cuerpo"]["layoutxml"])
        self.assertIs(True, post["cuerpo"]["isdefault"])

    def test_al_crear_no_se_publica_porque_la_plataforma_publica_sola(self):
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.vista = fila_vista()
            return (204, {}, {})

        cliente.responder("POST", "savedqueries", crear)
        vi.construir(self.escribir(), False, lambda: cliente)
        self.assertNotIn("PublishXml", [l["ruta"] for l in cliente.llamadas])

    def test_si_ya_esta_bien_no_se_escribe_nada(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista())
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_xml_se_compara_sin_que_los_espacios_cuenten(self):
        apretada = fila_vista(fetchxml=vi.fetchxml(COMPONENTE, PRIMARIA).replace("\n", "").replace("  ", ""))
        cliente = self.armar(ClienteSimulado(), vista=apretada)
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)

    def test_un_fetch_distinto_se_denuncia(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(fetchxml="<fetch><entity name='otra'/></fetch>"))
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("fetchxml", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_corrige_el_xml_y_DESPUES_publica(self):
        # Learn: hay que publicar despues de ACTUALIZAR, no al crear.
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(fetchxml="<fetch/>"))

        def corregir(ruta, cuerpo, solucion):
            self.vista = fila_vista()
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("savedqueries("), corregir)
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        metodos = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] in ("PATCH", "POST")]
        self.assertEqual([("PATCH", f"savedqueries({VISTA_ID})"), ("POST", "PublishXml")], metodos)
        publicacion = next(l for l in cliente.llamadas if l["ruta"] == "PublishXml")
        self.assertIn(f"<entity>{TABLA}</entity>", publicacion["cuerpo"]["ParameterXml"])

    def test_una_clase_distinta_dice_que_conviene_rehacerla(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(querytype=64))
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("INMUTABLE", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_vista_managed_no_se_toca(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(ismanaged=True, description="otra"))
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_si_la_tabla_no_esta_en_la_solucion_la_vista_no_viajaria(self):
        # Una vista no tiene fila propia en solutioncomponents: viaja dentro de
        # su tabla (verificado en Dev el 2026-09-22).
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(), en_solucion=False)
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn(SOLUTION_ID, detalle)
        self.assertIn("no viajaría", detalle)

    def test_si_la_tabla_esta_sin_subcomponentes_la_vista_no_viajaria(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(), comportamiento=1)
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("rootcomponentbehavior", detalle)

    def test_el_savedqueryid_que_inyecta_la_plataforma_no_cuenta_como_diferencia(self):
        # Dataverse le agrega savedqueryid="..." al fetchxml al guardarlo.
        con_id = vi.fetchxml(COMPONENTE, PRIMARIA).replace(
            '<fetch version="1.0"', f'<fetch savedqueryid="{VISTA_ID}" version="1.0"')
        cliente = self.armar(ClienteSimulado(), vista=fila_vista(fetchxml=con_id))
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_dos_vistas_con_el_mismo_nombre_en_la_misma_tabla_es_forma_inesperada(self):
        cliente = ClienteSimulado()
        armar_cliente_precondiciones_ok(cliente, IDENT)
        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions("),
                          (200, {"PrimaryIdAttribute": PRIMARIA, "ObjectTypeCode": CODIGO_TABLA,
                                 "MetadataId": METADATA_ID}, {}))
        cliente.responder("GET", lambda r: r.startswith("savedqueries?"),
                          (200, {"value": [fila_vista(), fila_vista()]}, {}))
        estado, _, detalle = vi.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("el nombre es la clave de negocio", detalle)

    def test_una_vista_por_defecto_desmarca_a_la_otra_que_lo_estaba(self):
        # Dataverse no desmarca sola la anterior: toda tabla nace con una
        # "Active X" de fabrica por defecto. Con dos, la declaracion es mentira.
        cliente = self.armar(ClienteSimulado(), vista=fila_vista())
        self.otras = [{"savedqueryid": "otra-id", "name": "Active Filas"}]

        def responder_savedqueries(ruta, cuerpo, solucion):
            if "isdefault eq true" in ruta:
                return (200, {"value": self.otras + [{"savedqueryid": VISTA_ID, "name": COMPONENTE["nombre"]}]}, {})
            return (200, {"value": [self.vista]}, {})

        cliente._reglas.insert(0, ("GET", lambda r: r.startswith("savedqueries?"), responder_savedqueries))

        def desmarcar(ruta, cuerpo, solucion):
            self.otras = []
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("savedqueries("), desmarcar)
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        patch = next(l for l in cliente.llamadas if l["metodo"] == "PATCH")
        self.assertEqual("savedqueries(otra-id)", patch["ruta"])
        self.assertEqual({"isdefault": False}, patch["cuerpo"])
        self.assertIn("PublishXml", [l["ruta"] for l in cliente.llamadas])

    def test_solo_verificar_denuncia_la_otra_por_defecto_y_no_escribe(self):
        cliente = self.armar(ClienteSimulado(), vista=fila_vista())

        def responder_savedqueries(ruta, cuerpo, solucion):
            if "isdefault eq true" in ruta:
                return (200, {"value": [{"savedqueryid": "otra-id", "name": "Active Filas"}]}, {})
            return (200, {"value": [self.vista]}, {})

        cliente._reglas.insert(0, ("GET", lambda r: r.startswith("savedqueries?"), responder_savedqueries))

        estado, _, detalle = vi.construir(self.escribir(), True, lambda: cliente)

        self.assertEqual("difiere", estado, detalle)
        self.assertIn("Active Filas", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = vi.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_http_inesperado_en_el_alta_no_se_confunde_con_exito(self):
        cliente = self.armar(ClienteSimulado())
        cliente.responder("POST", "savedqueries", (400, {"error": "fetchxml invalido"}, {}))
        estado, _, detalle = vi.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("HTTP 400", detalle)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = vi.salida
        try:
            sys.argv = ["vista.py", self.escribir(), "--forzar"]
            vi.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            vi.main()
        finally:
            sys.argv, vi.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
