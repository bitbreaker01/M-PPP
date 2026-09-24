"""Pruebas de `herramientas/construir/app.py`. Nunca tocan la red.

Lo que más importa: que cada título lleve UNA etiqueta POR IDIOMA (ahí la
plataforma no sustituye), y que una entrada que nombra una vista NO se arme con
`Entity=` — con cuatro entradas sobre la misma tabla, las cuatro abrirían la
vista por defecto y la navegación del diseño se cae.
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

import app as ap  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="app", inventario="12.7+12.8")

APP_ID = "aaaa1111-2222-3333-4444-555566667777"
SITEMAP_ID = "bbbb1111-2222-3333-4444-555566667777"
VISTA_ID = "cccc1111-2222-3333-4444-555566667777"

def t(texto):
    return {"1033": texto, "3082": texto}

COMPONENTE = {
    "tipo": "app",
    "nombre": "MDA - MPPP - Mantenimiento PPP",
    "uniquename": "sanic_mppp_mda_mantenimientoppp",
    "descripcion": "Una sola app para los cuatro perfiles (D-12).",
    "icono": "sanic_mppp_wr_svg_app",
    "sitemap": "sanic_mppp_sm_mantenimientoppp",
    "idiomas": [1033, 3082],
    "roles": ["SR - MPPP - Ejecutivo"],
    "tablas": ["sanic_mppp_tbl_fila", "sanic_mppp_tbl_solicitud"],
    "areas": [
        {"titulo": t("Trabajo"), "grupos": [
            {"titulo": t("Trabajo"), "entradas": [
                {"id": "subarea_pordigitar", "titulo": t("Por digitar"), "tabla": "sanic_mppp_tbl_fila",
                 "vista": "Mis clientes - por digitar", "icono": "sanic_mppp_wr_svg_pordigitar"},
                {"id": "subarea_solicitudes", "titulo": t("Solicitudes"), "tabla": "sanic_mppp_tbl_solicitud",
                 "icono": "sanic_mppp_wr_svg_solicitudes"},
            ]},
        ]},
    ],
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: app · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def xml_de(datos=None):
    datos = COMPONENTE if datos is None else datos
    iconos = {}
    for a in datos["areas"]:
        for g in a["grupos"]:
            for e in g["entradas"]:
                iconos[e["icono"]] = "/WebResources/" + e["icono"]
    iconos[datos["icono"]] = "/WebResources/" + datos["icono"]
    vistas = {(e["tabla"], e["vista"]): VISTA_ID
              for a in datos["areas"] for g in a["grupos"] for e in g["entradas"] if "vista" in e}
    return ap.sitemapxml(datos, iconos, vistas)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, sitemap=None, app=None, sin_icono=False, problemas=None, puestas=None):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.sitemap, self.app = sitemap, app
        cliente.responder("GET", lambda r: r.startswith("webresourceset?"),
                          (200, {"value": [] if sin_icono else [{"name": "x", "webresourceid": "wr-1"}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("savedqueries?"),
                          (200, {"value": [{"savedqueryid": VISTA_ID}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("roles?"),
                          (200, {"value": [{"roleid": "rol-1", "name": "SR - MPPP - Ejecutivo"}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("sitemaps?"),
                          lambda r, c, s: (200, {"value": [] if self.sitemap is None else [self.sitemap]}, {}))
        # La plataforma tiene DOS capas. `GET appmodules?` devuelve solo la
        # publicada; `RetrieveUnpublishedMultiple` devuelve las dos. El doble
        # respeta esa diferencia: si no, una app sin publicar se ve igual que
        # una publicada y la prueba no distingue nada.
        cliente.responder("GET", lambda r: r.startswith("appmodules?"),
                          lambda r, c, s: (200, {"value": [] if self.app is None
                                                 or self.app.get("componentstate") == 1 else [self.app]}, {}))
        cliente.responder("GET", lambda r: r.startswith("appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple"),
                          lambda r, c, s: (200, {"value": [] if self.app is None else [self.app]}, {}))
        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions(LogicalName="),
                          lambda r, c, s: (200, {"MetadataId": "md-" + r.split("'")[1]}, {}))
        # `AddAppComponents` devuelve 204 aunque no agregue nada: la herramienta
        # tiene que releer lo que QUEDÓ, no contar lo que pidió el playbook.
        self.puestas = list(COMPONENTE["tablas"]) if puestas is None else puestas
        cliente.responder("GET", lambda r: r.startswith("RetrieveAppComponents("),
                          lambda r, c, s: (200, {"value": [{"componenttype": 1, "objectid": "md-" + t}
                                                           for t in self.puestas]}, {}))
        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions(md-"),
                          lambda r, c, s: (200, {"LogicalName": r.split("(md-")[1].split(")")[0]}, {}))
        lista = problemas or []
        cliente.responder("GET", lambda r: r.startswith("ValidateApp("),
                          (200, {"AppValidationResponse": {"ValidationIssueList": lista}}, {}))
        return cliente


class XmlGenerado(unittest.TestCase):
    def test_cada_titulo_lleva_una_etiqueta_por_idioma(self):
        # `01-convenciones.md`: en el XML del sitemap no hay sustitucion.
        x = xml_de()
        self.assertIn('<Title LCID="1033" Title="Por digitar" />', x)
        self.assertIn('<Title LCID="3082" Title="Por digitar" />', x)
        self.assertEqual(x.count('LCID="1033"'), x.count('LCID="3082"'))

    def test_una_entrada_con_vista_no_usa_Entity(self):
        # Con Entity=, cuatro entradas sobre la misma tabla abren lo mismo.
        x = xml_de()
        pordigitar = x[x.index("subarea_pordigitar"):x.index("</SubArea>")]
        self.assertNotIn("Entity=", pordigitar)
        self.assertIn("pagetype=entitylist", pordigitar)
        self.assertIn(f"viewid=%7b{VISTA_ID}%7d", pordigitar)
        self.assertIn(f"viewtype={ap.VISTA_LISTA}", pordigitar)

    def test_una_entrada_sin_vista_usa_Entity(self):
        x = xml_de()
        i = x.index("subarea_solicitudes")
        solicitudes = x[i:x.index("</SubArea>", i)]
        self.assertIn('Entity="sanic_mppp_tbl_solicitud"', solicitudes)
        self.assertNotIn("Url=", solicitudes)

    def test_el_amp_de_la_url_va_escapado(self):
        # Una URL con & crudo rompe el XML del sitemap entero.
        x = xml_de()
        self.assertIn("&amp;pagetype", x)
        self.assertNotIn("?etn=sanic_mppp_tbl_fila&pagetype", x)

    def test_el_icono_se_referencia_como_webresources(self):
        self.assertIn('VectorIcon="/WebResources/sanic_mppp_wr_svg_pordigitar"', xml_de())


class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = ap.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_un_titulo_sin_todos_los_idiomas_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["areas"][0]["titulo"] = {"1033": "Trabajo"}
        self.rechaza(malo, "un texto por cada idioma")

    def test_un_titulo_con_un_idioma_de_mas_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["areas"][0]["titulo"] = {"1033": "T", "3082": "T", "1034": "T"}
        self.rechaza(malo, "sobran")

    def test_una_entrada_sobre_una_tabla_que_la_app_no_incluye_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["areas"][0]["grupos"][0]["entradas"][0]["tabla"] = "sanic_mppp_tbl_regla"
        self.rechaza(malo, "no está en la lista de tablas de la app")

    def test_dos_entradas_con_el_mismo_id_se_rechazan(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["areas"][0]["grupos"][0]["entradas"][1]["id"] = "subarea_pordigitar"
        self.rechaza(malo, "está repetido")

    def test_los_nombres_siguen_la_convencion(self):
        self.rechaza(comp(uniquename="mantenimientoppp"), "no sigue el patrón sanic_mppp_mda_")
        self.rechaza(comp(sitemap="mapa"), "no sigue el patrón sanic_mppp_sm_")


class ContraElEntorno(Base):
    def test_un_icono_que_no_existe_queda_bloqueado_sin_escribir(self):
        cliente = self.armar(ClienteSimulado(), sin_icono=True)
        estado, _, detalle = ap.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("hay que crearlo primero", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_alta_crea_sitemap_y_app_y_asocia_todo(self):
        cliente = self.armar(ClienteSimulado())

        def crear_sitemap(ruta, cuerpo, solucion):
            self.sitemap = {"sitemapid": SITEMAP_ID, "sitemapnameunique": COMPONENTE["sitemap"],
                            "sitemapxml": xml_de(), "isappaware": True}
            return (204, {}, {})

        def crear_app(ruta, cuerpo, solucion):
            self.app = {"appmoduleid": APP_ID, "uniquename": COMPONENTE["uniquename"],
                        "name": COMPONENTE["nombre"], "description": COMPONENTE["descripcion"],
                        "ismanaged": False}
            return (204, {}, {})

        cliente.responder("POST", "sitemaps", crear_sitemap)
        cliente.responder("POST", "appmodules", crear_app)
        cliente.responder("POST", "AddAppComponents", (204, {}, {}))
        cliente.responder("POST", lambda r: "appmoduleroles_association" in r, (204, {}, {}))
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = ap.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        rutas = [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertIn("sitemaps", rutas)
        self.assertIn("appmodules", rutas)
        # Sin `clienttype` la plataforma lo pone en 2 y la app abre con el cartel
        # "designed for the legacy web client" (visto en Dev el 2026-09-23).
        alta = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "appmodules")
        self.assertEqual(4, alta["clienttype"], "4 = Unified Interface")
        # Un AddAppComponents por el sitemap y uno por cada tabla.
        self.assertEqual(1 + len(COMPONENTE["tablas"]), rutas.count("AddAppComponents"))
        self.assertTrue(any("appmoduleroles_association" in r for r in rutas))
        self.assertIn("PublishXml", rutas)
        # OData exige un URI ABSOLUTO en el `@odata.id` de un `$ref`.
        rol = next(l["cuerpo"] for l in cliente.llamadas if "appmoduleroles_association" in l["ruta"])
        self.assertTrue(rol["@odata.id"].startswith("https://"), rol["@odata.id"])
        self.assertTrue(rol["@odata.id"].endswith("roles(rol-1)"), rol["@odata.id"])
        sm = next(l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "sitemaps")
        self.assertIs(True, sm["isappaware"])
        # El tipo `entity` lleva `entityid`, no `MetadataId`: con `MetadataId`
        # la plataforma responde 400 (verificado en Dev el 2026-09-22).
        tablas = [l["cuerpo"] for l in cliente.llamadas if l["ruta"] == "AddAppComponents"
                  and l["cuerpo"]["Components"][0]["@odata.type"].endswith(".entity")]
        self.assertEqual(len(COMPONENTE["tablas"]), len(tablas))
        self.assertEqual(["md-" + t for t in COMPONENTE["tablas"]],
                         [c["Components"][0]["entityid"] for c in tablas])
        for cuerpo in tablas:
            self.assertNotIn("MetadataId", cuerpo["Components"][0])

    def test_una_app_sin_publicar_se_encuentra_y_no_se_intenta_crear(self):
        # `componentstate = 1` (sin publicar): un `GET appmodules?` NO la
        # devuelve. Si la herramienta no la ve, la intenta crear y la
        # plataforma responde 400 con `-2147155681` (unique name duplicado),
        # que no dice "duplicado" por ningún lado. Verificado en Dev el
        # 2026-09-22: el primer alta había funcionado y quedó invisible.
        sitemap = {"sitemapid": SITEMAP_ID, "sitemapnameunique": COMPONENTE["sitemap"],
                   "sitemapxml": xml_de(), "isappaware": True}
        app = {"appmoduleid": APP_ID, "uniquename": COMPONENTE["uniquename"],
               "name": COMPONENTE["nombre"], "description": COMPONENTE["descripcion"],
               "ismanaged": False, "componentstate": 1}
        cliente = self.armar(ClienteSimulado(), sitemap=sitemap, app=app)
        cliente.responder("POST", "AddAppComponents", (204, {}, {}))
        cliente.responder("POST", lambda r: "appmoduleroles_association" in r, (204, {}, {}))
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = ap.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        rutas = [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertNotIn("appmodules", rutas)
        self.assertIn("PublishXml", rutas)

    def test_una_tabla_que_no_quedo_en_la_app_no_se_informa_como_puesta(self):
        # `AddAppComponents` responde 204 aunque no agregue nada, y
        # `ValidateApp` tampoco se queja (verificado en Dev el 2026-09-22:
        # diez altas, diez 204, cero tablas). Si la herramienta cuenta lo que
        # pidió el playbook en vez de lo que quedó, informa un éxito falso.
        sitemap = {"sitemapid": SITEMAP_ID, "sitemapnameunique": COMPONENTE["sitemap"],
                   "sitemapxml": xml_de(), "isappaware": True}
        app = {"appmoduleid": APP_ID, "uniquename": COMPONENTE["uniquename"],
               "name": COMPONENTE["nombre"], "description": COMPONENTE["descripcion"], "ismanaged": False}
        cliente = self.armar(ClienteSimulado(), sitemap=sitemap, app=app,
                             puestas=[COMPONENTE["tablas"][0]])
        cliente.responder("POST", "AddAppComponents", (204, {}, {}))
        cliente.responder("POST", lambda r: "appmoduleroles_association" in r, (204, {}, {}))
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = ap.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("error", estado, detalle)
        self.assertIn("no incluye 1 de las 2 tablas", detalle)
        self.assertIn(COMPONENTE["tablas"][1], detalle)

    def test_si_ValidateApp_devuelve_errores_no_se_informa_exito(self):
        cliente = self.armar(ClienteSimulado(), problemas=[{"ErrorType": "Error", "Message": "falta una vista"}],
                             sitemap={"sitemapid": SITEMAP_ID, "sitemapxml": xml_de(), "isappaware": True},
                             app={"appmoduleid": APP_ID, "ismanaged": False})
        estado, _, detalle = ap.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("falta una vista", detalle)

    def test_un_aviso_de_ValidateApp_no_frena(self):
        cliente = self.armar(ClienteSimulado(), problemas=[{"ErrorType": "Warning", "Message": "aviso"}],
                             sitemap={"sitemapid": SITEMAP_ID, "sitemapxml": xml_de(), "isappaware": True},
                             app={"appmoduleid": APP_ID, "ismanaged": False})
        estado, _, detalle = ap.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)

    def test_un_sitemap_sin_isappaware_se_denuncia(self):
        cliente = self.armar(ClienteSimulado(),
                             sitemap={"sitemapid": SITEMAP_ID, "sitemapxml": xml_de(), "isappaware": False},
                             app={"appmoduleid": APP_ID, "ismanaged": False})
        estado, _, detalle = ap.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("isappaware", detalle)

    def test_una_app_managed_no_se_toca(self):
        cliente = self.armar(ClienteSimulado(),
                             sitemap={"sitemapid": SITEMAP_ID, "sitemapxml": xml_de(), "isappaware": True},
                             app={"appmoduleid": APP_ID, "ismanaged": True})
        estado, _, detalle = ap.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = ap.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = ap.salida
        try:
            sys.argv = ["app.py", self.escribir(), "--forzar"]
            ap.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            ap.main()
        finally:
            sys.argv, ap.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
