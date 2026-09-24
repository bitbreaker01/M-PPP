"""Pruebas de `herramientas/construir/formulario.py`. Nunca tocan la red.

Lo que más importa acá: que los GUID del XML sean DETERMINISTAS (si no, cada
corrida genera un XML distinto y la herramienta nunca converge) y que el
`classid` de cada control salga del TIPO REAL de la columna. La plataforma no
normaliza el classid: guarda el que se le manda, y uno equivocado se ve roto
recién en la app.
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

import formulario as fo  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="formulario", inventario="12.3")

TABLA = "sanic_mppp_tbl_fila"
METADATA_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
FORM_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
VISTA_ID = "11112222-3333-4444-5555-666677778888"

TIPOS = {
    "sanic_estado": "PicklistType", "sanic_solicitudid": "LookupType", "sanic_numerofila": "IntegerType",
    "sanic_gestion": "PicklistType", "sanic_nombrebeneficiario": "StringType", "sanic_mensaje": "MemoType",
    "sanic_fechavalidada": "DateTimeType", "sanic_documentofirmado": "FileType",
    "sanic_requiererevision": "BooleanType",
}
ETIQUETAS = {c: c.replace("sanic_", "").capitalize() for c in TIPOS}

COMPONENTE = {
    "tipo": "formulario",
    "nombre": "Fila",
    "tabla": TABLA,
    "descripcion": "Formulario principal de Fila. Todo de solo lectura: el estado se cambia con los botones.",
    "pestana": "General",
    "solo_lectura": True,
    "encabezado": ["sanic_estado", "sanic_solicitudid", "sanic_numerofila"],
    "secciones": [
        {"titulo": "Gestion", "campos": ["sanic_gestion", "sanic_nombrebeneficiario"]},
        {"titulo": "Resultado", "campos": ["sanic_mensaje"]},
        {"titulo": "Filas", "subgrilla": {"tabla": "sanic_mppp_tbl_fila", "lookup": "sanic_solicitudid",
                                          "vista": "Por aprobar"}},
    ],
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: formulario · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def xml_de(datos=None):
    datos = COMPONENTE if datos is None else datos
    controles = {c: fo.CONTROL_POR_TIPO[TIPOS[c]] for c in TIPOS}
    subgrillas = {i: {"vista_id": "{" + VISTA_ID.upper() + "}", "relacion": "sanic_mppp_solicitud_fila"}
                  for i, s in enumerate(datos["secciones"]) if "subgrilla" in s}
    return fo.formxml(datos, ETIQUETAS, controles, subgrillas)


def fila_form(datos=None, **cambios):
    datos = COMPONENTE if datos is None else datos
    fila = {"formid": FORM_ID, "name": datos["nombre"], "description": datos["descripcion"],
            "formxml": xml_de(datos), "type": 2, "formactivationstate": 1, "ismanaged": False}
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

    def armar(self, cliente, form=None, en_solucion=True, comportamiento=0, tipos=None):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.form = form
        tipos = TIPOS if tipos is None else tipos

        def definiciones(ruta, cuerpo, solucion):
            if "/Attributes" in ruta:
                return (200, {"value": [{"LogicalName": c, "AttributeTypeName": {"Value": t},
                                         "DisplayName": {"UserLocalizedLabel": {"Label": ETIQUETAS.get(c, c)}}}
                                        for c, t in tipos.items()]}, {})
            if "OneToManyRelationships" in ruta:
                return (200, {"value": [{"SchemaName": "sanic_mppp_solicitud_fila",
                                         "ReferencingEntity": "sanic_mppp_tbl_fila",
                                         "ReferencingAttribute": "sanic_solicitudid"}]}, {})
            return (200, {"MetadataId": METADATA_ID}, {})

        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions("), definiciones)
        cliente.responder("GET", lambda r: r.startswith("savedqueries?"),
                          (200, {"value": [{"savedqueryid": VISTA_ID}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("systemforms?"),
                          lambda r, c, s: (200, {"value": [] if self.form is None else [self.form]}, {}))
        fila_tabla = [{"componenttype": 1, "rootcomponentbehavior": comportamiento, "objectid": METADATA_ID}]
        cliente.responder("GET", es_ruta_solutioncomponents,
                          (200, {"value": fila_tabla if en_solucion else []}, {}))
        return cliente


# ---------------------------------------------------------------------------
# El XML generado
# ---------------------------------------------------------------------------
class XmlGenerado(unittest.TestCase):
    def test_los_guid_son_deterministas(self):
        # Si fueran aleatorios, cada corrida daria un XML distinto y la
        # herramienta diria "difiere" para siempre.
        self.assertEqual(xml_de(), xml_de())
        self.assertEqual(fo.guid("a", "b"), fo.guid("a", "b"))
        self.assertNotEqual(fo.guid("a", "b"), fo.guid("a", "c"))

    def test_cada_control_usa_el_classid_de_su_tipo_real(self):
        x = xml_de()
        self.assertIn(f'datafieldname="sanic_gestion" ', x)
        self.assertIn(fo.CONTROL_POR_TIPO["PicklistType"], x)
        self.assertIn(fo.CONTROL_POR_TIPO["MemoType"], x)      # sanic_mensaje
        self.assertIn(fo.CONTROL_POR_TIPO["IntegerType"], x)   # sanic_numerofila
        self.assertIn(fo.CONTROL_POR_TIPO["LookupType"], x)    # sanic_solicitudid

    def test_un_formulario_de_solo_lectura_deshabilita_todos_sus_controles(self):
        self.assertNotIn('disabled="false"', xml_de())
        self.assertIn('disabled="true"', xml_de())

    def test_un_formulario_editable_no_deshabilita_nada(self):
        x = xml_de(comp(solo_lectura=False))
        self.assertNotIn('disabled="true"', x)

    def test_el_encabezado_siempre_tiene_tres_huecos(self):
        x = xml_de(comp(encabezado=["sanic_estado"]))
        header = x[x.index("<header"):]
        self.assertEqual(3, header.count("<cell "))
        self.assertIn('datafieldname="sanic_estado"', header)

    def test_la_subgrilla_lleva_su_vista_y_su_relacion(self):
        x = xml_de()
        self.assertIn('indicationOfSubgrid="true"', x)
        self.assertIn(fo.CONTROL_SUBGRILLA, x)
        self.assertIn("<TargetEntityType>sanic_mppp_tbl_fila</TargetEntityType>", x)
        self.assertIn("<RelationshipName>sanic_mppp_solicitud_fila</RelationshipName>", x)
        self.assertIn("{" + VISTA_ID.upper() + "}", x)

    def test_las_etiquetas_salen_de_la_metadata_no_del_playbook(self):
        # El playbook no declara etiquetas: si alguien renombra la columna, la
        # etiqueta del formulario lo sigue.
        self.assertIn('description="Gestion"', xml_de())


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class WebResourceEnElFormulario(Base):
    """Un web resource en una sección: es como se muestra el correo que se le
    envió al cliente, renderizado tal cual (12.9)."""

    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = fo.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def seccion(self, **cambios):
        s = {"titulo": "Comunicacion enviada",
             "webresource": {"nombre": "sanic_mppp_wr_html_comunicacion", "alto": 12}}
        s.update(cambios)
        return s

    def test_el_control_lleva_el_classid_de_web_resource(self):
        x = fo._celda_webresource({"nombre": "F"}, "sec0.wr", "WebResource_0", "Comunicacion",
                                  "sanic_mppp_wr_html_comunicacion", 12)
        self.assertIn(fo.CONTROL_WEBRESOURCE, x)
        self.assertIn("<Url>sanic_mppp_wr_html_comunicacion</Url>", x)

    def test_pasa_los_parametros_del_registro(self):
        # Sin PassParameters la página no recibe el `id` y no sabe qué mostrar.
        x = fo._celda_webresource({"nombre": "F"}, "sec0.wr", "WebResource_0", "C",
                                  "sanic_mppp_wr_html_comunicacion", 12)
        self.assertIn("<PassParameters>true</PassParameters>", x)

    def test_el_alto_va_en_el_rowspan(self):
        x = fo._celda_webresource({"nombre": "F"}, "sec0.wr", "WebResource_0", "C",
                                  "sanic_mppp_wr_html_comunicacion", 12)
        self.assertIn('rowspan="12"', x)

    def test_una_seccion_no_puede_llevar_campos_y_webresource(self):
        mala = self.seccion(campos=["sanic_nombre"])
        self.rechaza(comp(secciones=[mala]), "exactamente uno")

    def test_un_alto_fuera_de_rango_se_rechaza(self):
        self.rechaza(comp(secciones=[self.seccion(
            webresource={"nombre": "sanic_mppp_wr_html_comunicacion", "alto": 40})]),
            "entre 1 y 20")

    def test_un_webresource_sin_alto_se_rechaza(self):
        self.rechaza(comp(secciones=[self.seccion(
            webresource={"nombre": "sanic_mppp_wr_html_comunicacion"})]), "faltan ['alto']")


class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = fo.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza({k: v for k, v in COMPONENTE.items() if k != "secciones"}, "faltan ['secciones']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_una_seccion_lleva_campos_o_subgrilla_nunca_las_dos(self):
        self.rechaza(comp(secciones=[{"titulo": "X", "campos": ["a"], "subgrilla": {}}]), "exactamente uno")
        self.rechaza(comp(secciones=[{"titulo": "X"}]), "exactamente uno")

    def test_una_columna_repetida_en_el_formulario_se_rechaza(self):
        malo = comp(secciones=[{"titulo": "A", "campos": ["sanic_gestion"]},
                               {"titulo": "B", "campos": ["sanic_gestion"]}])
        self.rechaza(malo, "ya está en el formulario")

    def test_una_columna_del_encabezado_no_se_repite_en_una_seccion(self):
        malo = comp(secciones=[{"titulo": "A", "campos": ["sanic_estado"]}])
        self.rechaza(malo, "ya está en el formulario")

    def test_mas_de_tres_columnas_en_el_encabezado_se_rechaza(self):
        self.rechaza(comp(encabezado=["a", "b", "c", "d"]), "solo entran 3")

    def test_dos_subgrillas_sobre_la_misma_relacion_se_rechazan(self):
        sg = {"tabla": "t", "lookup": "l", "vista": "v"}
        self.rechaza(comp(secciones=[{"titulo": "A", "subgrilla": dict(sg)},
                                     {"titulo": "B", "subgrilla": dict(sg)}]), "ya hay otra subgrilla")

    def test_los_titulos_van_sin_tildes(self):
        self.rechaza(comp(secciones=[{"titulo": "Gestión", "campos": ["sanic_gestion"]}]), "fuera de ASCII")


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_una_columna_que_la_tabla_no_tiene_queda_bloqueada(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form())
        malo = comp(secciones=[{"titulo": "X", "campos": ["sanic_inventada"]}])
        estado, _, detalle = fo.construir(self.escribir(malo), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("sanic_inventada", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_tipo_de_columna_sin_control_conocido_queda_bloqueado_y_no_inventa(self):
        # La plataforma guarda el classid tal cual: adivinar se ve roto en la app.
        tipos = dict(TIPOS, sanic_gestion="MultiSelectPicklist")
        cliente = self.armar(ClienteSimulado(), form=fila_form(), tipos=tipos)
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("MultiSelectPicklist", detalle)
        self.assertIn("No se inventa un classid", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_vista_de_subgrilla_que_no_existe_queda_bloqueada(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form())
        cliente._reglas.insert(0, ("GET", lambda r: r.startswith("savedqueries?"), (200, {"value": []}, {})))
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("hay que crearla primero", detalle)

    def test_si_ya_esta_bien_no_se_escribe_nada(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form())
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_se_ACTUALIZA_el_principal_que_ya_existe_en_vez_de_crear_otro(self):
        # Dos Main compitiendo es el mismo problema que dos vistas por defecto.
        viejo = fila_form(name="Information", formxml="<form/>")
        cliente = self.armar(ClienteSimulado(), form=viejo)

        def corregir(ruta, cuerpo, solucion):
            self.form = fila_form()
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("systemforms("), corregir)
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        self.assertNotIn("systemforms", [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"])
        patch = next(l for l in cliente.llamadas if l["metodo"] == "PATCH")
        self.assertEqual(f"systemforms({FORM_ID})", patch["ruta"])
        self.assertEqual("Fila", patch["cuerpo"]["name"])
        self.assertIn("formxml", patch["cuerpo"])

    def test_despues_de_corregir_se_publica(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form(formxml="<form/>"))

        def corregir(ruta, cuerpo, solucion):
            self.form = fila_form()
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("systemforms("), corregir)
        cliente.responder("POST", "PublishXml", (204, {}, {}))
        fo.construir(self.escribir(), False, lambda: cliente)
        publicacion = next(l for l in cliente.llamadas if l["ruta"] == "PublishXml")
        self.assertIn(f"<entity>{TABLA}</entity>", publicacion["cuerpo"]["ParameterXml"])

    def test_un_formulario_inactivo_se_reactiva(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form(formactivationstate=0))

        def corregir(ruta, cuerpo, solucion):
            self.form = fila_form()
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith("systemforms("), corregir)
        cliente.responder("POST", "PublishXml", (204, {}, {}))
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("creado", estado, detalle)
        patch = next(l for l in cliente.llamadas if l["metodo"] == "PATCH")
        self.assertEqual(1, patch["cuerpo"]["formactivationstate"])

    def test_dos_formularios_principales_es_forma_inesperada(self):
        cliente = ClienteSimulado()
        self.armar(cliente, form=fila_form())
        cliente._reglas.insert(0, ("GET", lambda r: r.startswith("systemforms?"),
                                   (200, {"value": [fila_form(), fila_form()]}, {})))
        estado, _, detalle = fo.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("el playbook deja de mandar", detalle)

    def test_un_formulario_managed_no_se_toca(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form(ismanaged=True, name="otro"))
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_si_la_tabla_no_esta_en_la_solucion_el_formulario_no_viajaria(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form(), en_solucion=False)
        estado, _, detalle = fo.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no viajaría", detalle)

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado(), form=fila_form(formxml="<form/>"))
        estado, _, detalle = fo.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("formxml", detalle)
        self.assertFalse(cliente.hubo_escritura())


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = fo.salida
        try:
            sys.argv = ["formulario.py", self.escribir(), "--forzar"]
            fo.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            fo.main()
        finally:
            sys.argv, fo.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
