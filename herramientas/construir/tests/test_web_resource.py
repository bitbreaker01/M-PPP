"""Pruebas de `herramientas/construir/web_resource.py`. Nunca tocan la red.

Dos cosas importan acá: que el contenido salga del ARCHIVO del repositorio y no
de una tira de base64 metida en el playbook, y que se publique al actualizar
(Learn: al crear no hace falta, al actualizar sí).
"""
import base64
import copy
import json
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

import web_resource as wr  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, SOLUTION_ID, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="web-resource", inventario="12.1")

RECURSO_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/></svg>'

COMPONENTE = {
    "tipo": "web-resource",
    "nombre": "sanic_mppp_wr_svg_pordigitar",
    "displayname": "WR - MPPP - SVG - Por digitar",
    "descripcion": "Icono de la entrada de sitemap Por digitar.",
    "recurso": "SVG",
    "archivo": "recursos/svg/pordigitar.svg",
}


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: web-resource · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def fila_recurso(datos=None, contenido=None, **cambios):
    datos = COMPONENTE if datos is None else datos
    fila = {
        "webresourceid": RECURSO_ID,
        "name": datos["nombre"],
        "displayname": datos["displayname"],
        "description": datos["descripcion"],
        "webresourcetype": wr.TIPOS_DE_RECURSO[datos["recurso"]],
        "content": base64.b64encode(SVG).decode("ascii") if contenido is None else contenido,
        "ismanaged": False,
    }
    fila.update(cambios)
    return fila


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.raiz_original = wr._RAIZ
        wr._RAIZ = self.dir.name
        self.addCleanup(lambda: setattr(wr, "_RAIZ", self.raiz_original))
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def escribir_archivo(self, contenido=SVG, relativa=None):
        relativa = COMPONENTE["archivo"] if relativa is None else relativa
        destino = os.path.join(self.dir.name, relativa)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(contenido)

    def armar(self, cliente, recurso=None, en_solucion=True):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.recurso = recurso
        cliente.responder("GET", lambda r: r.startswith(wr.CONJUNTO + "?"),
                          lambda r, c, s: (200, {"value": [] if self.recurso is None else [self.recurso]}, {}))
        cliente.responder("GET", es_ruta_solutioncomponents,
                          (200, {"value": [{"componenttype": 61, "objectid": RECURSO_ID}] if en_solucion else []}, {}))
        return cliente


class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = wr.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza({k: v for k, v in COMPONENTE.items() if k != "archivo"}, "faltan ['archivo']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_el_nombre_sigue_la_convencion_con_el_tipo_adentro(self):
        self.rechaza(comp(nombre="sanic_mppp_wr_pordigitar"), "no sigue el patrón sanic_mppp_wr_svg_")
        self.rechaza(comp(nombre="sanic_mppp_wr_svg_por digitar"), "solo admite letras y dígitos")

    def test_un_tipo_de_recurso_que_no_existe_se_rechaza(self):
        self.rechaza(comp(recurso="VECTOR"), "no es válido")

    def test_la_extension_del_archivo_tiene_que_calzar_con_el_tipo(self):
        # Un SVG guardado como .png se sube igual y se ve roto recien en la app.
        self.rechaza(comp(archivo="recursos/svg/pordigitar.png"), "no termina en '.svg'")

    def test_la_ruta_del_archivo_es_relativa_y_sin_saltos(self):
        self.rechaza(comp(archivo="/etc/passwd.svg"), "ruta relativa a la raíz")
        self.rechaza(comp(archivo="../fuera/x.svg"), "ruta relativa a la raíz")

    def test_el_nombre_visible_va_sin_tildes(self):
        self.rechaza(comp(displayname="WR - MPPP - SVG - Por digitación"), "fuera de ASCII")


class ContraElEntorno(Base):
    def test_sin_el_archivo_en_el_repo_queda_bloqueado_sin_escribir(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("no existe el archivo", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_archivo_vacio_queda_bloqueado(self):
        self.escribir_archivo(b"")
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("vacío", detalle)

    def test_el_alta_sube_el_archivo_en_base64_y_va_a_la_solucion(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.recurso = fila_recurso()
            return (204, {}, {})

        cliente.responder("POST", wr.CONJUNTO, crear)

        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        post = next(l for l in cliente.llamadas if l["metodo"] == "POST")
        self.assertEqual(wr.CONJUNTO, post["ruta"])  # webresourceset, NO webresources
        self.assertEqual(base64.b64encode(SVG).decode("ascii"), post["cuerpo"]["content"])
        self.assertEqual(11, post["cuerpo"]["webresourcetype"])  # SVG
        self.assertEqual(IDENT["solucion"], post["solucion"])

    def test_al_crear_no_se_publica(self):
        # Learn: "It is not necessary to publish Web resources when they are created."
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.recurso = fila_recurso()
            return (204, {}, {})

        cliente.responder("POST", wr.CONJUNTO, crear)
        wr.construir(self.escribir(), False, lambda: cliente)
        self.assertNotIn("PublishXml", [l["ruta"] for l in cliente.llamadas])

    def test_si_ya_esta_bien_no_se_escribe_nada(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso())
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_contenido_distinto_se_denuncia_y_no_se_pisa_sin_permiso(self):
        self.escribir_archivo(b"<svg>otro</svg>")
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso())
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no es el del archivo del repositorio", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_sube_el_contenido_nuevo_y_DESPUES_publica(self):
        # Learn: "It is necessary to publish them when they are updated."
        nuevo = b"<svg>nuevo</svg>"
        self.escribir_archivo(nuevo)
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso())

        def corregir(ruta, cuerpo, solucion):
            self.recurso = fila_recurso(contenido=base64.b64encode(nuevo).decode("ascii"))
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith(wr.CONJUNTO + "("), corregir)
        cliente.responder("POST", "PublishXml", (204, {}, {}))

        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        orden = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] in ("PATCH", "POST")]
        self.assertEqual([("PATCH", f"{wr.CONJUNTO}({RECURSO_ID})"), ("POST", "PublishXml")], orden)
        publicacion = next(l for l in cliente.llamadas if l["ruta"] == "PublishXml")
        self.assertIn(f"<webresource>{RECURSO_ID}</webresource>", publicacion["cuerpo"]["ParameterXml"])

    def test_un_tipo_distinto_dice_que_hay_que_rehacerlo(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso(webresourcetype=5))
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("INMUTABLE", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_recurso_managed_no_se_toca(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso(ismanaged=True, displayname="otro"))
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("managed", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_recurso_fuera_de_la_solucion_es_difiere(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado(), recurso=fila_recurso(), en_solucion=False)
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn(SOLUTION_ID, detalle)

    def test_solo_verificar_nunca_escribe(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = wr.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no existe en el entorno", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_http_inesperado_en_el_alta_no_se_confunde_con_exito(self):
        self.escribir_archivo()
        cliente = self.armar(ClienteSimulado())
        cliente.responder("POST", wr.CONJUNTO, (400, {"error": "nombre en uso"}, {}))
        estado, _, detalle = wr.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("HTTP 400", detalle)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = wr.salida
        try:
            sys.argv = ["web_resource.py", self.escribir(), "--forzar"]
            wr.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            wr.main()
        finally:
            sys.argv, wr.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
