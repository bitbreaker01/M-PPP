"""Pruebas de `herramientas/construir/datos.py`. Nunca tocan la red.

Acá lo que importa es la IDEMPOTENCIA (la clave de negocio, no el GUID) y que
un valor que el playbook declara de una forma quede en el entorno de esa forma
y no de otra: estas filas son la configuración con la que se validan las
solicitudes de un banco.
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

import datos as dt  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="datos", inventario="9.1")

TABLA = "sanic_mppp_tbl_parametro"
CONJUNTO = "sanic_mppp_tbl_parametros"
PRIMARIA = "sanic_mppp_tbl_parametroid"
CHOICE = "sanic_mppp_ch_tipoparametro"

FILA_A = {"sanic_nombre": "rpa.puedeaprobar", "sanic_version": 1, "sanic_valor": "no",
          "sanic_tipo": {"choice": CHOICE, "etiqueta": "Texto"}}
FILA_B = {"sanic_nombre": "lectura.limites", "sanic_version": 1,
          "sanic_valor": '{"maximoBytesComprimido":2097152}',
          "sanic_tipo": {"choice": CHOICE, "etiqueta": "JSON"}}

COMPONENTE = {"tipo": "datos", "tabla": TABLA, "clave": ["sanic_nombre", "sanic_version"], "filas": [FILA_A, FILA_B]}

VALORES_CHOICE = {"Texto": 159460001, "JSON": 159460002}


def comp(filas=None, **cambios):
    d = copy.deepcopy(COMPONENTE)
    if filas is not None:
        d["filas"] = filas
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: datos · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


def fila_guardada(fila, **cambios):
    """La fila tal como la devolvería el entorno: el choice ya como número."""
    guardada = {PRIMARIA: "id-" + fila["sanic_nombre"]}
    for columna, valor in fila.items():
        guardada[columna] = VALORES_CHOICE[valor["etiqueta"]] if isinstance(valor, dict) else valor
    guardada.update(cambios)
    return guardada


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, guardadas=None, sin_tabla=False, sin_choice=False, etiquetas=None):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.guardadas = {} if guardadas is None else guardadas

        cliente.responder(
            "GET", lambda r: r.startswith("EntityDefinitions("),
            (404, {}, {}) if sin_tabla else (200, {"EntitySetName": CONJUNTO, "PrimaryIdAttribute": PRIMARIA}, {}),
        )
        etiquetas = VALORES_CHOICE if etiquetas is None else etiquetas
        opciones = [{"Value": v, "Label": {"LocalizedLabels": [{"Label": k, "LanguageCode": 1033}]}}
                    for k, v in etiquetas.items()]
        cliente.responder(
            "GET", lambda r: r.startswith("GlobalOptionSetDefinitions("),
            (404, {}, {}) if sin_choice else (200, {"Options": opciones}, {}),
        )

        def responder_filas(ruta, cuerpo, solucion):
            for nombre, fila in self.guardadas.items():
                if f"'{nombre}'" in ruta:
                    return (200, {"value": [fila]}, {})
            return (200, {"value": []}, {})

        cliente.responder("GET", lambda r: r.startswith(CONJUNTO + "?"), responder_filas)
        return cliente


# ---------------------------------------------------------------------------
# Validación offline
# ---------------------------------------------------------------------------
class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = dt.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada, "no tenía que intentar construir el cliente de Dataverse")

    def test_una_clave_de_mas_o_de_menos_se_rechaza(self):
        self.rechaza({k: v for k, v in COMPONENTE.items() if k != "clave"}, "faltan ['clave']")
        self.rechaza(comp(sobrante=1), "sobran ['sobrante']")

    def test_una_fila_sin_la_clave_de_negocio_se_rechaza(self):
        sin_version = {k: v for k, v in FILA_A.items() if k != "sanic_version"}
        self.rechaza(comp(filas=[sin_version]), "no trae las columnas de la clave de negocio")

    def test_dos_filas_con_la_misma_clave_de_negocio_se_rechazan(self):
        # Sin esto, la segunda pisaría a la primera y el playbook mentiría.
        otra = dict(FILA_A, sanic_valor="si")
        self.rechaza(comp(filas=[FILA_A, otra]), "misma clave de negocio")

    def test_un_choice_mal_declarado_se_rechaza(self):
        self.rechaza(comp(filas=[dict(FILA_A, sanic_tipo={"choice": CHOICE})]), "solo se admite {choice, etiqueta}")
        self.rechaza(comp(filas=[dict(FILA_A, sanic_tipo={"choice": CHOICE, "valor": 1})]), "solo se admite {choice, etiqueta}")

    def test_un_valor_que_no_es_escalar_ni_choice_se_rechaza(self):
        self.rechaza(comp(filas=[dict(FILA_A, sanic_valor=["a", "b"])]), "solo se admiten escalares")

    def test_la_clave_no_puede_tener_columnas_repetidas(self):
        self.rechaza(comp(clave=["sanic_nombre", "sanic_nombre"]), "columnas repetidas")

    def test_un_apostrofo_se_duplica_en_el_filtro_odata(self):
        # Sin esto, un nombre con apóstrofo rompe la consulta.
        self.assertEqual("'O''Brien'", dt.literal_odata("O'Brien"))
        self.assertEqual("'texto'", dt.literal_odata("texto"))
        self.assertEqual("7", dt.literal_odata(7))
        self.assertEqual("true", dt.literal_odata(True))
        self.assertEqual("false", dt.literal_odata(False))
        self.assertEqual("null", dt.literal_odata(None))


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class ContraElEntorno(Base):
    def test_una_tabla_que_no_existe_queda_bloqueada_sin_escribir(self):
        cliente = self.armar(ClienteSimulado(), sin_tabla=True)
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("no existe en el entorno", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_una_etiqueta_de_choice_que_no_existe_queda_bloqueada_y_lista_las_que_hay(self):
        cliente = self.armar(ClienteSimulado(), etiquetas={"Texto": 159460001})
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("no tiene la opción 'JSON'", detalle)
        self.assertIn("['Texto']", detalle)
        # Y el entorno queda INTACTO: la primera fila era válida, pero nada se
        # escribe hasta haber resuelto todos los choice de todas las filas.
        self.assertFalse(cliente.hubo_escritura())

    def test_el_alta_traduce_la_etiqueta_del_choice_a_su_numero(self):
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            self.guardadas[cuerpo["sanic_nombre"]] = fila_guardada(
                FILA_A if cuerpo["sanic_nombre"] == FILA_A["sanic_nombre"] else FILA_B)
            return (204, {}, {})

        cliente.responder("POST", CONJUNTO, crear)

        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        posts = [l["cuerpo"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(2, len(posts))
        self.assertEqual(159460001, posts[0]["sanic_tipo"])
        self.assertEqual(159460002, posts[1]["sanic_tipo"])
        # Un dato NO es componente de solución: no va la cabecera.
        for l in cliente.llamadas:
            if l["metodo"] == "POST":
                self.assertIsNone(l["solucion"])

    def test_correr_dos_veces_no_duplica_nada(self):
        cliente = self.armar(ClienteSimulado(), guardadas={
            FILA_A["sanic_nombre"]: fila_guardada(FILA_A),
            FILA_B["sanic_nombre"]: fila_guardada(FILA_B),
        })
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertIn("2 que ya estaban", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_valor_distinto_se_denuncia_y_no_se_pisa_sin_permiso(self):
        cliente = self.armar(ClienteSimulado(), guardadas={
            FILA_A["sanic_nombre"]: fila_guardada(FILA_A, sanic_valor="si"),
            FILA_B["sanic_nombre"]: fila_guardada(FILA_B),
        })
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("sanic_valor es 'si' y el playbook dice 'no'", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_completar_corrige_solo_las_columnas_que_difieren(self):
        cliente = self.armar(ClienteSimulado(), guardadas={
            FILA_A["sanic_nombre"]: fila_guardada(FILA_A, sanic_valor="si"),
            FILA_B["sanic_nombre"]: fila_guardada(FILA_B),
        })

        def corregir(ruta, cuerpo, solucion):
            self.guardadas[FILA_A["sanic_nombre"]] = fila_guardada(FILA_A)
            return (204, {}, {})

        cliente.responder("PATCH", lambda r: r.startswith(CONJUNTO + "("), corregir)

        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente, completar=True)

        self.assertEqual("creado", estado, detalle)
        patches = [l for l in cliente.llamadas if l["metodo"] == "PATCH"]
        self.assertEqual(1, len(patches))
        self.assertEqual({"sanic_valor": "no"}, patches[0]["cuerpo"])
        self.assertEqual(f"{CONJUNTO}(id-rpa.puedeaprobar)", patches[0]["ruta"])

    def test_solo_verificar_nunca_escribe(self):
        cliente = self.armar(ClienteSimulado())
        estado, _, detalle = dt.construir(self.escribir(), True, lambda: cliente, completar=True)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("no existe en el entorno", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_plugin_que_rechaza_el_valor_se_informa_con_su_mensaje(self):
        # El caso real: `NormalizarYValidarStep` rechazando un nombre mal formado.
        cliente = self.armar(ClienteSimulado())
        cliente.responder("POST", CONJUNTO, (400, {"error": "La columna 'sanic_nombre' no tiene un valor válido"}, {}))
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente, dormir=lambda s: None)
        self.assertEqual("error", estado, detalle)
        self.assertIn("no tiene un valor válido", detalle)

    def test_si_un_plugin_normaliza_el_valor_al_guardarlo_se_denuncia_en_vez_de_callarlo(self):
        # Si la fila queda distinta de lo que pide el playbook, no es "creado".
        cliente = self.armar(ClienteSimulado())

        def crear(ruta, cuerpo, solucion):
            fila = FILA_A if cuerpo["sanic_nombre"] == FILA_A["sanic_nombre"] else FILA_B
            self.guardadas[cuerpo["sanic_nombre"]] = fila_guardada(fila, sanic_valor="NO")
            return (204, {}, {})

        cliente.responder("POST", CONJUNTO, crear)
        estado, _, detalle = dt.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("se creó pero no quedó como el playbook", detalle)

    def test_dos_filas_con_la_misma_clave_en_el_entorno_es_forma_inesperada(self):
        cliente = ClienteSimulado()
        armar_cliente_precondiciones_ok(cliente, IDENT)
        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions("),
                          (200, {"EntitySetName": CONJUNTO, "PrimaryIdAttribute": PRIMARIA}, {}))
        cliente.responder("GET", lambda r: r.startswith("GlobalOptionSetDefinitions("),
                          (200, {"Options": [{"Value": v, "Label": {"LocalizedLabels": [{"Label": k, "LanguageCode": 1033}]}}
                                             for k, v in VALORES_CHOICE.items()]}, {}))
        cliente.responder("GET", lambda r: r.startswith(CONJUNTO + "?"),
                          (200, {"value": [fila_guardada(FILA_A), fila_guardada(FILA_A)]}, {}))
        estado, _, detalle = dt.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("clave alternativa", detalle)


TABLA_HIJA = "sanic_mppp_tbl_plan"
CONJUNTO_HIJA = "sanic_mppp_tbl_plans"
PRIMARIA_HIJA = "sanic_mppp_tbl_planid"
TABLA_PADRE = "sanic_mppp_tbl_cliente"
CONJUNTO_PADRE = "sanic_mppp_tbl_clientes"
PRIMARIA_PADRE = "sanic_mppp_tbl_clienteid"
ID_PADRE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

LOOKUP = {"lookup": {"tabla": TABLA_PADRE, "clave": {"sanic_nombre": "ACME"}}}
PLAN_A = {"sanic_codigo": "0042", "sanic_clienteid": LOOKUP}
PLAN_B = {"sanic_codigo": "0043", "sanic_clienteid": LOOKUP}
CON_LOOKUP = {"tipo": "datos", "tabla": TABLA_HIJA, "clave": ["sanic_codigo"], "filas": [PLAN_A, PLAN_B]}


class Lookups(Base):
    """Un lookup se declara por la clave de negocio de la fila apuntada, nunca
    por GUID: un playbook con GUID adentro solo sirve en el entorno donde se
    escribió."""

    def armar_lookup(self, cliente, padre_existe=True, hijas=None):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.hijas = {} if hijas is None else hijas

        def definiciones(ruta, cuerpo, solucion):
            if f"'{TABLA_PADRE}'" in ruta:
                return (200, {"EntitySetName": CONJUNTO_PADRE, "PrimaryIdAttribute": PRIMARIA_PADRE}, {})
            return (200, {"EntitySetName": CONJUNTO_HIJA, "PrimaryIdAttribute": PRIMARIA_HIJA}, {})

        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions("), definiciones)
        cliente.responder("GET", lambda r: r.startswith(CONJUNTO_PADRE + "?"),
                          (200, {"value": [{PRIMARIA_PADRE: ID_PADRE}] if padre_existe else []}, {}))

        def hijas_resp(ruta, cuerpo, solucion):
            for codigo, fila in self.hijas.items():
                if f"'{codigo}'" in ruta:
                    return (200, {"value": [fila]}, {})
            return (200, {"value": []}, {})

        cliente.responder("GET", lambda r: r.startswith(CONJUNTO_HIJA + "?"), hijas_resp)
        return cliente

    def test_un_lookup_se_escribe_con_odata_bind_y_el_guid_resuelto(self):
        cliente = self.armar_lookup(ClienteSimulado())
        creadas = []

        def crear(ruta, cuerpo, solucion):
            creadas.append(cuerpo)
            self.hijas[cuerpo["sanic_codigo"]] = {
                PRIMARIA_HIJA: "id-" + cuerpo["sanic_codigo"],
                "sanic_codigo": cuerpo["sanic_codigo"],
                "_sanic_clienteid_value": ID_PADRE,
            }
            return (204, {}, {})

        cliente.responder("POST", CONJUNTO_HIJA, crear)

        estado, _, detalle = dt.construir(self.escribir(CON_LOOKUP), False, lambda: cliente)

        self.assertEqual("creado", estado, detalle)
        self.assertEqual(f"/{CONJUNTO_PADRE}({ID_PADRE})", creadas[0]["sanic_clienteid@odata.bind"])
        self.assertNotIn("sanic_clienteid", creadas[0])

    def test_un_lookup_se_compara_contra_la_columna_de_lectura(self):
        # Se ESCRIBE `col@odata.bind` y se LEE `_col_value`. Sin esa traducción
        # una fila correcta daría "difiere" para siempre.
        hijas = {
            "0042": {PRIMARIA_HIJA: "id-0042", "sanic_codigo": "0042", "_sanic_clienteid_value": ID_PADRE},
            "0043": {PRIMARIA_HIJA: "id-0043", "sanic_codigo": "0043", "_sanic_clienteid_value": ID_PADRE},
        }
        cliente = self.armar_lookup(ClienteSimulado(), hijas=hijas)
        estado, _, detalle = dt.construir(self.escribir(CON_LOOKUP), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_lookup_que_apunta_a_otra_fila_se_denuncia(self):
        hijas = {
            "0042": {PRIMARIA_HIJA: "id-0042", "sanic_codigo": "0042", "_sanic_clienteid_value": "otro-guid"},
            "0043": {PRIMARIA_HIJA: "id-0043", "sanic_codigo": "0043", "_sanic_clienteid_value": ID_PADRE},
        }
        cliente = self.armar_lookup(ClienteSimulado(), hijas=hijas)
        estado, _, detalle = dt.construir(self.escribir(CON_LOOKUP), False, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("_sanic_clienteid_value", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_un_padre_que_no_existe_queda_bloqueado_sin_escribir_nada(self):
        cliente = self.armar_lookup(ClienteSimulado(), padre_existe=False)
        estado, _, detalle = dt.construir(self.escribir(CON_LOOKUP), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("sembrar primero la tabla apuntada", detalle)
        # Ni siquiera la primera fila: todos los lookups se resuelven antes de escribir.
        self.assertFalse(cliente.hubo_escritura())

    def test_el_mismo_padre_se_resuelve_una_sola_vez(self):
        cliente = self.armar_lookup(ClienteSimulado())
        cliente.responder("POST", CONJUNTO_HIJA, (204, {}, {}))
        dt.construir(self.escribir(CON_LOOKUP), True, lambda: cliente)
        consultas = [l for l in cliente.llamadas if l["ruta"].startswith(CONJUNTO_PADRE + "?")]
        self.assertEqual(1, len(consultas), "las dos filas apuntan al mismo Cliente")

    def test_un_lookup_mal_declarado_se_rechaza_sin_red(self):
        for malo, fragmento in [
            ({"lookup": {"tabla": TABLA_PADRE}}, "solo se admite {tabla, clave}"),
            ({"lookup": {"tabla": TABLA_PADRE, "clave": {}}}, "ninguna columna en su clave"),
            ({"lookup": {"tabla": TABLA_PADRE, "clave": {"sanic_nombre": None}}}, "escalares no nulos"),
            ({"lookup": {"tabla": TABLA_PADRE, "clave": {"sanic_nombre": "ACME"}}, "choice": "x"}, "declara 'lookup'"),
        ]:
            centinela = FabricaCentinela()
            datos = dict(CON_LOOKUP, filas=[{"sanic_codigo": "0042", "sanic_clienteid": malo}])
            estado, _, detalle = dt.construir(self.escribir(datos), False, centinela)
            self.assertEqual("error", estado, detalle)
            self.assertIn(fragmento, detalle)
            self.assertFalse(centinela.llamada)


class Uso(Base):
    def test_una_bandera_desconocida_no_se_ignora_en_silencio(self):
        original, capturado = sys.argv, []
        real = dt.salida
        try:
            sys.argv = ["datos.py", self.escribir(), "--forzar"]
            dt.salida = lambda e, c, d: capturado.append((e, c, d)) or 1
            dt.main()
        finally:
            sys.argv, dt.salida = original, real
        self.assertEqual("error", capturado[0][0])
        self.assertIn("--forzar", capturado[0][2])


if __name__ == "__main__":
    unittest.main()
