"""Herramienta `tabla.py`: una tabla con sus columnas propias, desde un
playbook. Ninguna prueba toca la red."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import tabla as tb  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import (  # noqa: E402
    IDENTIDAD_VALIDA,
    SOLUTION_ID,
    armar_cliente_precondiciones_ok,
    es_ruta_solutioncomponents,
    es_ruta_solutions,
    label,
    playbook_md,
)

BORRAR = object()
TABLA = "sanic_mppp_tbl_zzdemo"
META_TABLA = "44444444-4444-4444-4444-444444444444"
META_CHOICE = "55555555-5555-5555-5555-555555555555"
IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="tabla", inventario="3.1")


def col(nombre, tipo, **kw):
    base = {"nombre": nombre, "displayname": nombre.split("_")[1].title(), "descripcion": f"Descripción de {nombre}.",
            "tipo": tipo, "requerida": False, "protegida": False, "auditoria": False}
    base.update(kw)
    return base


# Un playbook con TODOS los tipos que admite el formato.
COMPLETO = {
    "tipo": "tabla",
    "nombre": TABLA,
    "displayname": "Demo",
    "displayname_plural": "Demos",
    "descripcion": "Tabla de demostración.",
    "propiedad": "usuario",
    "notas": False,
    "actividades": False,
    "auditoria": False,
    "primaria": {"nombre": "sanic_nombre", "displayname": "Nombre", "descripcion": "Nombre del registro.",
                 "largo": 200, "requerida": True, "autonumerico": ""},
    "columnas": [
        col("sanic_codigo", "texto", largo=9, requerida=True),
        col("sanic_detalle", "memo", largo=2000),
        col("sanic_orden", "entero", minimo=0, maximo=9999),
        col("sanic_moneda", "choice", choice="sanic_mppp_ch_moneda"),
        col("sanic_activado", "sino", etiqueta_si="Sí", etiqueta_no="No", defecto=False),
        col("sanic_fechadocumento", "fecha"),
        col("sanic_fechaevento", "fechahora"),
        col("sanic_documento", "archivo", tamano_kb=10240),
        col("sanic_folio", "autonumerico", largo=100, formato="ZZ-{SEQNUM:8}"),
    ],
}
# El mínimo: solo texto (lo único verificado contra la plataforma al nacer la herramienta).
SIMPLE = dict(copy.deepcopy(COMPLETO), columnas=[col("sanic_codigo", "texto", largo=9, requerida=True)])

TODO_VERIFICADO = frozenset(tb.CARACTERISTICAS)


def con_cambio(obj, ruta, valor):
    nuevo = copy.deepcopy(obj)
    if not ruta:
        return valor
    nodo = nuevo
    for paso in ruta[:-1]:
        nodo = nodo[paso]
    if valor is BORRAR:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    return nuevo


# ---------------------------------------------------------------------------
# Respuestas simuladas del entorno, derivadas del playbook
# ---------------------------------------------------------------------------
def rl(valor):
    return {"Value": valor, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"}


def aud(valor):
    return {"Value": valor, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyauditsettings"}


TIPO_PLATAFORMA = {"texto": "StringType", "autonumerico": "StringType", "memo": "MemoType", "entero": "IntegerType",
                   "choice": "PicklistType", "sino": "BooleanType", "fecha": "DateTimeType", "fechahora": "DateTimeType",
                   "archivo": "FileType"}


def cuerpo_tabla(datos):
    return {"MetadataId": META_TABLA, "LogicalName": datos["nombre"], "SchemaName": datos["nombre"],
            "OwnershipType": "UserOwned", "HasNotes": datos["notas"], "HasActivities": datos["actividades"],
            "IsAuditEnabled": aud(datos["auditoria"]), "IsManaged": False, "IsCustomEntity": True,
            "PrimaryNameAttribute": datos["primaria"]["nombre"], "DisplayName": label(datos["displayname"]),
            "DisplayCollectionName": label(datos["displayname_plural"]), "Description": label(datos["descripcion"])}


def fila_generica(c, primaria=False):
    return {"LogicalName": c["nombre"], "SchemaName": c["nombre"], "AttributeOf": None, "IsCustomAttribute": True,
            "IsPrimaryName": primaria, "AttributeTypeName": {"Value": TIPO_PLATAFORMA[c.get("tipo", "texto")]},
            "RequiredLevel": rl("ApplicationRequired" if c["requerida"] else "None"),
            "IsSecured": c.get("protegida", False), "IsAuditEnabled": aud(c.get("auditoria", False)),
            "DisplayName": label(c["displayname"]), "Description": label(c["descripcion"])}


def filas_por_tipo(datos):
    p = datos["primaria"]
    por = {"String": [{"LogicalName": p["nombre"], "MaxLength": p["largo"], "FormatName": {"Value": "Text"},
                       "AutoNumberFormat": p["autonumerico"] or None}]}
    for c in datos["columnas"]:
        n, t = c["nombre"], c["tipo"]
        if t in ("texto", "autonumerico"):
            por.setdefault("String", []).append({"LogicalName": n, "MaxLength": c["largo"], "FormatName": {"Value": "Text"},
                                                 "AutoNumberFormat": c.get("formato") or None})
        elif t == "memo":
            por.setdefault("Memo", []).append({"LogicalName": n, "MaxLength": c["largo"]})
        elif t == "entero":
            por.setdefault("Integer", []).append({"LogicalName": n, "MinValue": c["minimo"], "MaxValue": c["maximo"]})
        elif t == "choice":
            por.setdefault("Picklist", []).append({"LogicalName": n, "GlobalOptionSet": {"Name": c["choice"], "IsGlobal": True}})
        elif t == "sino":
            por.setdefault("Boolean", []).append({"LogicalName": n, "DefaultValue": c["defecto"], "OptionSet": {
                "TrueOption": {"Value": 1, "Label": label(c["etiqueta_si"])},
                "FalseOption": {"Value": 0, "Label": label(c["etiqueta_no"])}}})
        elif t in ("fecha", "fechahora"):
            por.setdefault("DateTime", []).append({"LogicalName": n, "Format": "DateOnly" if t == "fecha" else "DateAndTime",
                                                   "DateTimeBehavior": {"Value": "DateOnly" if t == "fecha" else "UserLocal"}})
        elif t == "archivo":
            por.setdefault("File", []).append({"LogicalName": n, "MaxSizeInKB": c["tamano_kb"]})
    return por


SISTEMA = [
    {"LogicalName": "createdon", "SchemaName": "CreatedOn", "AttributeOf": None, "IsCustomAttribute": False, "IsPrimaryName": False,
     "AttributeTypeName": {"Value": "DateTimeType"}, "RequiredLevel": rl("None"), "IsSecured": False, "IsAuditEnabled": aud(False),
     "DisplayName": label("Created On"), "Description": label("")},
    {"LogicalName": TABLA + "id", "SchemaName": TABLA + "Id", "AttributeOf": None, "IsCustomAttribute": True, "IsPrimaryName": False,
     "AttributeTypeName": {"Value": "UniqueidentifierType"}, "RequiredLevel": rl("SystemRequired"), "IsSecured": False,
     "IsAuditEnabled": aud(False), "DisplayName": label("Demo"), "Description": label("")},
]


def armar(cliente, datos, existe=True, genericas=None, por_tipo=None, tabla=None, componentes=None):
    """Configura TODAS las rutas del camino feliz (si no, el error del doble
    por 'ruta sin regla' haría pasar en falso las pruebas que esperan error)."""
    armar_cliente_precondiciones_ok(cliente, IDENT)
    cliente.responder("GET", lambda r: r.startswith("GlobalOptionSetDefinitions(Name="),
                      (200, {"MetadataId": META_CHOICE, "Name": "sanic_mppp_ch_moneda", "IsGlobal": True}, {}))
    estado = {"existe": existe}
    cliente.responder("GET", lambda r: r.startswith(f"EntityDefinitions(LogicalName='{datos['nombre']}')?"),
                      lambda *_: (200, tabla if tabla is not None else cuerpo_tabla(datos), {}) if estado["existe"] else (404, {"error": {"message": "no existe"}}, {}))
    gen = genericas if genericas is not None else ([fila_generica(datos["primaria"], True)] + [fila_generica(c) for c in datos["columnas"]] + SISTEMA)
    cliente.responder("GET", lambda r: "/Attributes?" in r, (200, {"value": gen}, {}))
    pt = por_tipo if por_tipo is not None else filas_por_tipo(datos)
    for t in ("String", "Memo", "Integer", "Picklist", "Boolean", "DateTime", "File"):
        cliente.responder("GET", lambda r, t=t: f"/Attributes/Microsoft.Dynamics.CRM.{t}AttributeMetadata" in r, (200, {"value": pt.get(t, [])}, {}))
    cliente.responder("GET", es_ruta_solutioncomponents, (200, {"value": componentes if componentes is not None else [{"solutioncomponentid": "x"}]}, {}))

    def al_crear(ruta, cuerpo, solucion):
        estado["existe"] = True
        return (204, None, {})

    cliente.responder("POST", "EntityDefinitions", al_crear)
    cliente.responder("POST", f"EntityDefinitions(LogicalName='{datos['nombre']}')/Attributes", (204, None, {}))
    ruta_prim = f"EntityDefinitions(LogicalName='{datos['nombre']}')/Attributes(LogicalName='{datos['primaria']['nombre']}')"
    # La plataforma crea la primaria con SUS valores (850, opcional, auditada) y devuelve el cast sin '@odata.type'.
    cliente.responder("GET", ruta_prim + "/Microsoft.Dynamics.CRM.StringAttributeMetadata",
                      (200, {"LogicalName": datos["primaria"]["nombre"], "SchemaName": datos["primaria"]["nombre"], "MaxLength": 850,
                             "RequiredLevel": rl("None"), "FormatName": {"Value": "Text"}, "IsAuditEnabled": aud(True),
                             "DisplayName": label(datos["primaria"]["displayname"])}, {}))
    cliente.responder("PUT", ruta_prim, (204, None, {}))
    cliente.responder("POST", "PublishXml", (204, None, {}))
    return cliente


class Base(unittest.TestCase):
    def correr(self, fabrica, datos, solo_verificar=False, verificadas=TODO_VERIFICADO, permitir=False, corregir_primaria=False, publicar=False):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "playbook.md")
            open(ruta, "w", encoding="utf-8").write(playbook_md(IDENT, datos))
            return tb.construir(ruta, solo_verificar, fabrica, verificadas=verificadas, permitir_no_verificadas=permitir,
                                corregir_primaria=corregir_primaria, publicar=publicar)

    def con_cliente(self, cliente, datos, **kw):
        return self.correr(lambda: cliente, datos, **kw)


# ---------------------------------------------------------------------------
class ValidacionSinRed(Base):
    CASOS = [
        (["tipo"], "choice-global", "tipo"),
        (["nombre"], "sanic_mppp_ch_zzdemo", "nombre"),
        (["nombre"], "Sanic_mppp_tbl_Demo", "nombre"),
        (["nombre"], "sanic_mppp_tbl_" + "a" * 90, "95"),
        (["displayname"], "", "displayname"),
        (["displayname_plural"], BORRAR, "displayname_plural"),
        (["descripcion"], "  ", "descripcion"),
        (["propiedad"], "organizacional", "propiedad"),
        (["notas"], "no", "notas"),
        (["auditoria"], 1, "auditoria"),
        (["sobra"], True, "sobra"),
        (["primaria", "nombre"], "sanic_Nombre", "primaria.nombre"),
        (["primaria", "largo"], 0, "primaria.largo"),
        (["primaria", "largo"], "200", "primaria.largo"),
        (["primaria", "largo"], True, "primaria.largo"),
        (["primaria", "requerida"], "si", "primaria.requerida"),
        (["primaria", "autonumerico"], None, "primaria.autonumerico"),
        (["primaria", "autonumerico"], "sin marcador", "primaria.autonumerico"),
        (["columnas"], {}, "columnas"),
        (["columnas", 0], "texto", "columnas[0]"),
        (["columnas", 0, "nombre"], "otro_codigo", "columnas[0].nombre"),
        (["columnas", 0, "nombre"], "sanic_nombre", "repetid"),
        (["columnas", 0, "tipo"], "lookup", "columnas[0].tipo"),
        (["columnas", 0, "largo"], 4001, "columnas[0].largo"),
        (["columnas", 0, "largo"], BORRAR, "columnas[0]"),
        (["columnas", 0, "minimo"], 1, "columnas[0]"),
        (["columnas", 0, "requerida"], None, "columnas[0].requerida"),
        (["columnas", 0, "protegida"], "no", "columnas[0].protegida"),
        (["columnas", 2, "minimo"], 10000, "columnas[2]"),
        (["columnas", 2, "maximo"], 2147483648, "columnas[2].maximo"),
        (["columnas", 3, "choice"], "sanic_otro", "columnas[3].choice"),
        (["columnas", 4, "defecto"], "false", "columnas[4].defecto"),
        (["columnas", 4, "etiqueta_si"], "", "columnas[4].etiqueta_si"),
        (["columnas", 7, "tamano_kb"], 0, "columnas[7].tamano_kb"),
        (["columnas", 7, "requerida"], True, "columnas[7]"),
        (["columnas", 8, "formato"], "ZZ-SEQNUM", "columnas[8].formato"),
    ]

    def test_cada_dato_invalido_es_error_nombra_la_clave_y_no_toca_la_red(self):
        for ruta, valor, esperado in self.CASOS:
            with self.subTest(f"{ruta} <- {'BORRAR' if valor is BORRAR else repr(valor)}"):
                centinela = FabricaCentinela()
                estado, _, detalle = self.correr(centinela, con_cambio(COMPLETO, ruta, valor))
                self.assertEqual(estado, "error", detalle)
                self.assertIn(esperado, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(centinela.llamada)

    def test_el_playbook_completo_es_valido(self):
        cliente = armar(ClienteSimulado(), COMPLETO)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "ya_existia", detalle)


class CaracteristicasNoVerificadas(Base):
    def test_usar_algo_no_verificado_contra_la_plataforma_bloquea_sin_red(self):
        centinela = FabricaCentinela()
        estado, _, detalle = self.correr(centinela, COMPLETO, verificadas=frozenset({"tipo:texto"}))
        self.assertEqual(estado, "bloqueado", detalle)
        for c in ("tipo:memo", "tipo:archivo", "tipo:fecha"):
            self.assertIn(c, detalle)
        self.assertFalse(centinela.llamada)

    def test_solo_texto_pasa_con_lo_minimo_verificado(self):
        cliente = armar(ClienteSimulado(), SIMPLE)
        estado, _, detalle = self.con_cliente(cliente, SIMPLE, verificadas=frozenset({"tipo:texto"}))
        self.assertEqual(estado, "ya_existia", detalle)

    def test_el_ensayo_solo_se_permite_sobre_una_tabla_descartable(self):
        real = dict(copy.deepcopy(COMPLETO), nombre="sanic_mppp_tbl_cliente")
        estado, _, detalle = self.correr(FabricaCentinela(), real, verificadas=frozenset(), permitir=True)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn("_tbl_zz", detalle)
        cliente = armar(ClienteSimulado(), COMPLETO)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO, verificadas=frozenset(), permitir=True)
        self.assertEqual(estado, "ya_existia", detalle)

    def test_las_caracteristicas_que_usa_un_playbook(self):
        usadas = tb.caracteristicas_usadas(dict(copy.deepcopy(COMPLETO), auditoria=True))
        self.assertIn("tabla:auditoria", usadas)
        self.assertIn("tipo:autonumerico", usadas)
        self.assertNotIn("columna:protegida", usadas)
        prot = con_cambio(COMPLETO, ["columnas", 0, "protegida"], True)
        self.assertIn("columna:protegida", tb.caracteristicas_usadas(prot))
        auto = con_cambio(COMPLETO, ["primaria", "autonumerico"], "ZZ-{SEQNUM:8}")
        self.assertIn("primaria:autonumerica", tb.caracteristicas_usadas(auto))


class Payload(unittest.TestCase):
    def setUp(self):
        self.p = tb.construir_payload(COMPLETO, IDENT, {"sanic_mppp_ch_moneda": META_CHOICE})
        self.cols = {a["SchemaName"]: a for a in self.p["Attributes"]}

    def test_tabla(self):
        p = self.p
        self.assertEqual(p["@odata.type"], "Microsoft.Dynamics.CRM.EntityMetadata")
        self.assertEqual(p["SchemaName"], TABLA)
        self.assertEqual(p["OwnershipType"], "UserOwned")
        self.assertIs(p["HasNotes"], False)
        self.assertIs(p["HasActivities"], False)
        self.assertIs(p["IsActivity"], False)
        self.assertEqual(p["IsAuditEnabled"]["Value"], False)
        self.assertEqual(p["DisplayCollectionName"]["LocalizedLabels"][0], {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": "Demos", "LanguageCode": 1033})
        self.assertEqual(len(p["Attributes"]), 10)

    def test_primaria(self):
        a = self.p["Attributes"][0]
        self.assertEqual(a["SchemaName"], "sanic_nombre")
        self.assertIs(a["IsPrimaryName"], True)
        self.assertEqual(a["@odata.type"], "Microsoft.Dynamics.CRM.StringAttributeMetadata")
        self.assertEqual(a["MaxLength"], 200)
        self.assertEqual(a["FormatName"], {"Value": "Text"})
        self.assertEqual(a["RequiredLevel"]["Value"], "ApplicationRequired")
        self.assertNotIn("AutoNumberFormat", a)

    def test_cada_tipo(self):
        c = self.cols
        self.assertEqual((c["sanic_codigo"]["@odata.type"], c["sanic_codigo"]["MaxLength"]), ("Microsoft.Dynamics.CRM.StringAttributeMetadata", 9))
        self.assertEqual((c["sanic_detalle"]["@odata.type"], c["sanic_detalle"]["Format"], c["sanic_detalle"]["MaxLength"]), ("Microsoft.Dynamics.CRM.MemoAttributeMetadata", "TextArea", 2000))
        self.assertEqual((c["sanic_orden"]["MinValue"], c["sanic_orden"]["MaxValue"], c["sanic_orden"]["Format"]), (0, 9999, "None"))
        self.assertEqual(c["sanic_moneda"]["GlobalOptionSet@odata.bind"], f"/GlobalOptionSetDefinitions({META_CHOICE})")
        self.assertNotIn("OptionSet", c["sanic_moneda"])
        b = c["sanic_activado"]
        self.assertIs(b["DefaultValue"], False)
        self.assertEqual(b["OptionSet"]["TrueOption"]["Label"]["LocalizedLabels"][0]["Label"], "Sí")
        self.assertEqual(b["OptionSet"]["FalseOption"]["Value"], 0)
        self.assertEqual((c["sanic_fechadocumento"]["Format"], c["sanic_fechadocumento"]["DateTimeBehavior"]), ("DateOnly", {"Value": "DateOnly"}))
        self.assertEqual((c["sanic_fechaevento"]["Format"], c["sanic_fechaevento"]["DateTimeBehavior"]), ("DateAndTime", {"Value": "UserLocal"}))
        self.assertEqual((c["sanic_documento"]["@odata.type"], c["sanic_documento"]["MaxSizeInKB"]), ("Microsoft.Dynamics.CRM.FileAttributeMetadata", 10240))
        self.assertEqual(c["sanic_folio"]["AutoNumberFormat"], "ZZ-{SEQNUM:8}")

    def test_comunes(self):
        for a in self.p["Attributes"]:
            self.assertIn("RequiredLevel", a)
            self.assertIn("DisplayName", a)
            self.assertIn("Description", a)
            self.assertEqual(a["IsAuditEnabled"]["Value"], False)
            self.assertIs(a["IsSecured"], False)
        prot = con_cambio(COMPLETO, ["columnas", 0, "protegida"], True)
        p = tb.construir_payload(prot, IDENT, {"sanic_mppp_ch_moneda": META_CHOICE})
        self.assertNotIn("sanic_codigo", [a["SchemaName"] for a in p["Attributes"]])
        despues = tb.columnas_protegidas_payload(prot, IDENT, {"sanic_mppp_ch_moneda": META_CHOICE})
        self.assertEqual([a["SchemaName"] for a in despues], ["sanic_codigo"])
        self.assertIs(despues[0]["IsSecured"], True)


class Caminos(Base):
    def test_no_existe_se_crea_con_un_solo_post_y_se_verifica(self):
        cliente = armar(ClienteSimulado(), COMPLETO, existe=False)
        estado, comp, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual(comp, TABLA)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["ruta"] for p in posts], ["EntityDefinitions", "PublishXml"])
        self.assertEqual(posts[0]["solucion"], IDENT["solucion"])
        self.assertEqual(len(posts[0]["cuerpo"]["Attributes"]), 10)
        self.assertIn(META_TABLA, detalle)

    def test_las_columnas_protegidas_se_agregan_despues_de_crear_la_tabla(self):
        """La plataforma rechaza (400) una columna con IsSecured=true dentro del
        POST que crea la tabla; sí la acepta agregada después (verificado)."""
        prot = con_cambio(con_cambio(COMPLETO, ["columnas", 0, "protegida"], True), ["columnas", 2, "protegida"], True)
        cliente = armar(ClienteSimulado(), prot, existe=False)
        estado, _, detalle = self.con_cliente(cliente, prot)
        self.assertEqual(estado, "creado", detalle)
        posts = [l for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual([p["ruta"] for p in posts], ["EntityDefinitions", f"EntityDefinitions(LogicalName='{TABLA}')/Attributes",
                                                      f"EntityDefinitions(LogicalName='{TABLA}')/Attributes", "PublishXml"])
        en_tabla = [a["SchemaName"] for a in posts[0]["cuerpo"]["Attributes"]]
        self.assertNotIn("sanic_codigo", en_tabla)
        self.assertNotIn("sanic_orden", en_tabla)
        self.assertEqual(len(en_tabla), 8)
        self.assertEqual([p["cuerpo"]["SchemaName"] for p in posts[1:3]], ["sanic_codigo", "sanic_orden"])
        for p in posts[:3]:
            self.assertEqual(p["solucion"], IDENT["solucion"])
        self.assertIs(posts[1]["cuerpo"]["IsSecured"], True)

    def test_si_falla_agregar_una_protegida_dice_que_la_tabla_quedo_incompleta(self):
        prot = con_cambio(COMPLETO, ["columnas", 0, "protegida"], True)
        cliente = ClienteSimulado()
        cliente.responder("POST", f"EntityDefinitions(LogicalName='{TABLA}')/Attributes", (400, {"error": "boom"}, {}))
        armar(cliente, prot, existe=False)
        estado, _, detalle = self.con_cliente(cliente, prot)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("sanic_codigo", detalle)
        self.assertIn("HTTP 400", detalle)
        self.assertIn("incompleta", detalle)

    def test_la_primaria_se_ajusta_despues_de_crear_porque_la_plataforma_ignora_su_largo_y_su_requerida(self):
        """Verificado el 2026-09-20: al crear la tabla la plataforma deja la
        primaria en 850 y opcional, diga lo que diga el POST (salvo que sea
        autonumérica). Hay que reenviar su definición completa con PUT."""
        cliente = armar(ClienteSimulado(), COMPLETO, existe=False)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "creado", detalle)
        puts = [l for l in cliente.llamadas if l["metodo"] == "PUT"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0]["ruta"], f"EntityDefinitions(LogicalName='{TABLA}')/Attributes(LogicalName='sanic_nombre')")
        c = puts[0]["cuerpo"]
        self.assertEqual(c["@odata.type"], "Microsoft.Dynamics.CRM.StringAttributeMetadata")
        self.assertEqual(c["MaxLength"], 200)
        self.assertEqual(c["RequiredLevel"]["Value"], "ApplicationRequired")
        # Visto el 2026-09-20: la plataforma también ignora IsAuditEnabled=false de la primaria y la deja auditada.
        self.assertEqual(c["IsAuditEnabled"], aud(COMPLETO["auditoria"]))
        self.assertFalse(COMPLETO["auditoria"])
        self.assertEqual(c["DisplayName"]["LocalizedLabels"][0]["Label"], "Nombre")
        self.assertEqual(c["FormatName"], {"Value": "Text"})  # el resto de la definición se conserva
        self.assertEqual(puts[0]["cabeceras"], {"MSCRM.MergeLabels": "true"})
        self.assertEqual(puts[0]["solucion"], IDENT["solucion"])
        orden = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] in ("POST", "PUT")]
        self.assertEqual(orden[-1][1], "PublishXml")
        self.assertIn(TABLA, [l for l in cliente.llamadas if l["ruta"] == "PublishXml"][0]["cuerpo"]["ParameterXml"])

    def test_una_primaria_autonumerica_no_se_ajusta(self):
        auto = con_cambio(COMPLETO, ["primaria", "autonumerico"], "ZZ-{SEQNUM:8}")
        cliente = armar(ClienteSimulado(), auto, existe=False)
        estado, _, detalle = self.con_cliente(cliente, auto)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual([l for l in cliente.llamadas if l["metodo"] == "PUT"], [])

    def test_si_falla_el_ajuste_de_la_primaria_dice_que_quedo_incompleta(self):
        cliente = ClienteSimulado()
        cliente.responder("PUT", lambda r: True, (400, {"error": "boom"}, {}))
        armar(cliente, COMPLETO, existe=False)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("incompleta", detalle)
        self.assertIn("sanic_nombre", detalle)
        self.assertIn("HTTP 400", detalle)

    def test_corregir_primaria_repara_solo_ese_caso(self):
        pt = filas_por_tipo(COMPLETO)
        pt["String"][0]["MaxLength"] = 850
        gen = [fila_generica(dict(COMPLETO["primaria"], requerida=False), True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        # sin el flag: difiere y no escribe
        cliente = armar(ClienteSimulado(), COMPLETO, por_tipo=pt, genericas=gen)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())
        # con el flag: hace el PUT y publica (la relectura simulada sigue difiriendo: acá importa que lo intentó)
        cliente = armar(ClienteSimulado(), COMPLETO, por_tipo=pt, genericas=gen)
        self.con_cliente(cliente, COMPLETO, corregir_primaria=True)
        self.assertEqual([l["metodo"] for l in cliente.llamadas if l["metodo"] in ("PUT", "POST")], ["PUT", "POST"])
        # con el flag pero con OTRA diferencia además: no toca nada
        otra = con_cambio(pt, ["Integer", 0, "MaxValue"], 5)
        cliente = armar(ClienteSimulado(), COMPLETO, por_tipo=otra, genericas=gen)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO, corregir_primaria=True)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_corregir_primaria_tambien_le_quita_la_auditoria_que_puso_la_plataforma(self):
        """Visto el 2026-09-20: la plataforma deja auditada la primaria de una tabla sin auditoría."""
        gen = [dict(fila_generica(COMPLETO["primaria"], True), IsAuditEnabled=aud(True))] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        cliente = armar(ClienteSimulado(), COMPLETO, genericas=gen)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn("sanic_nombre.IsAuditEnabled", detalle)
        self.assertFalse(cliente.hubo_escritura())
        cliente = armar(ClienteSimulado(), COMPLETO, genericas=gen)
        self.con_cliente(cliente, COMPLETO, corregir_primaria=True)
        puts = [l for l in cliente.llamadas if l["metodo"] == "PUT"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0]["cuerpo"]["IsAuditEnabled"], aud(False))

    def test_publicar_vuelve_a_publicar_una_tabla_que_coincide_y_nada_mas(self):
        cliente = armar(ClienteSimulado(), COMPLETO)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO, publicar=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn("publicó", detalle)
        escrituras = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"]
        self.assertEqual(escrituras, [("POST", "PublishXml")])
        # si difiere, no publica ni toca nada
        pt = con_cambio(filas_por_tipo(COMPLETO), ["Integer", 0, "MaxValue"], 5)
        cliente = armar(ClienteSimulado(), COMPLETO, por_tipo=pt)
        estado, _, _ = self.con_cliente(cliente, COMPLETO, publicar=True)
        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())

    def test_corregir_primaria_tambien_la_vuelve_autonumerica(self):
        """Decisión del aprobador (2026-09-20): la primaria de una tabla que ya
        existe pasa de texto a autonumérica y opcional. Es el mismo PUT."""
        auto = con_cambio(con_cambio(COMPLETO, ["primaria", "autonumerico"], "REG-{SEQNUM:4}"), ["primaria", "requerida"], False)
        # el entorno todavía la tiene como texto común, requerida
        pt = filas_por_tipo(COMPLETO)
        gen = [fila_generica(COMPLETO["primaria"], True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        cliente = armar(ClienteSimulado(), auto, por_tipo=pt, genericas=gen)
        estado, _, detalle = self.con_cliente(cliente, auto)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn("sanic_nombre.AutoNumberFormat", detalle)
        self.assertIn("sanic_nombre.RequiredLevel", detalle)
        self.assertFalse(cliente.hubo_escritura())
        cliente = armar(ClienteSimulado(), auto, por_tipo=pt, genericas=gen)
        self.con_cliente(cliente, auto, corregir_primaria=True)
        puts = [l for l in cliente.llamadas if l["metodo"] == "PUT"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0]["cuerpo"]["AutoNumberFormat"], "REG-{SEQNUM:4}")
        self.assertEqual(puts[0]["cuerpo"]["RequiredLevel"]["Value"], "None")
        self.assertEqual(puts[0]["cuerpo"]["MaxLength"], 200)
        # y al revés no: quitarle el formato a una autonumérica NO lo hace la herramienta
        entorno_auto = con_cambio(pt, ["String", 0, "AutoNumberFormat"], "X-{SEQNUM:4}")
        cliente = armar(ClienteSimulado(), COMPLETO, por_tipo=entorno_auto)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO, corregir_primaria=True)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_corregir_primaria_tambien_cambia_su_nombre_visible_y_su_descripcion(self):
        """Al volverla autonumérica cambia su papel (de nombre a número): el
        nombre visible y la descripción van en el mismo PUT. Lo detectó el
        constructor el 2026-09-20: sin esto la reparación no alcanzaba."""
        nuevo = con_cambio(con_cambio(con_cambio(COMPLETO, ["primaria", "autonumerico"], "REG-{SEQNUM:4}"), ["primaria", "displayname"], "Número"),
                           ["primaria", "descripcion"], "Número que la plataforma asigna sola.")
        gen = [fila_generica(COMPLETO["primaria"], True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        cliente = armar(ClienteSimulado(), nuevo, por_tipo=filas_por_tipo(COMPLETO), genericas=gen)
        self.con_cliente(cliente, nuevo, corregir_primaria=True)
        puts = [l for l in cliente.llamadas if l["metodo"] == "PUT"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0]["cuerpo"]["DisplayName"], tb.etiqueta_web_api("Número", 1033))
        self.assertEqual(puts[0]["cuerpo"]["Description"], tb.etiqueta_web_api("Número que la plataforma asigna sola.", 1033))
        # pero el nombre visible de OTRA columna no lo repara
        otra = con_cambio(gen, [1, "DisplayName"], label("Otro"))
        cliente = armar(ClienteSimulado(), nuevo, por_tipo=filas_por_tipo(COMPLETO), genericas=otra)
        estado, _, _ = self.con_cliente(cliente, nuevo, corregir_primaria=True)
        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())

    def test_ya_existia_no_escribe(self):
        cliente = armar(ClienteSimulado(), COMPLETO)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertIn(META_TABLA, detalle)  # quien verifica necesita el identificador para cruzar contra el entorno
        self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_sin_tabla_es_error_y_no_crea(self):
        cliente = armar(ClienteSimulado(), COMPLETO, existe=False)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_el_choice_de_una_columna_no_existe_bloquea_sin_crear(self):
        cliente = ClienteSimulado()
        cliente.responder("GET", lambda r: r.startswith("GlobalOptionSetDefinitions(Name="), (404, {"error": {}}, {}))
        armar(cliente, COMPLETO, existe=False)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "bloqueado", detalle)
        self.assertIn("sanic_mppp_ch_moneda", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_la_creacion_falla(self):
        cliente = ClienteSimulado()
        cliente.responder("POST", "EntityDefinitions", (400, {"error": {"message": "nombre inválido"}}, {}))
        armar(cliente, COMPLETO, existe=False)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 400", detalle)


class Diferencias(Base):
    def difiere(self, esperado, **kw):
        cliente = armar(ClienteSimulado(), COMPLETO, **kw)
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "difiere", detalle)
        self.assertIn(esperado, detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_de_la_tabla(self):
        for clave, valor, esperado in [("OwnershipType", "OrganizationOwned", "OwnershipType"), ("HasNotes", True, "HasNotes"),
                                       ("IsManaged", True, "IsManaged"), ("PrimaryNameAttribute", "sanic_otro", "PrimaryNameAttribute"),
                                       ("DisplayCollectionName", label("Otros"), "DisplayCollectionName"),
                                       ("IsAuditEnabled", aud(True), "IsAuditEnabled"),
                                       ("DisplayName", label("Demo", otros_idiomas=[(3082, "Demo")]), "otro idioma")]:
            with self.subTest(clave):
                self.difiere(esperado, tabla=con_cambio(cuerpo_tabla(COMPLETO), [clave], valor))

    def test_de_las_columnas(self):
        gen = [fila_generica(COMPLETO["primaria"], True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        pt = filas_por_tipo(COMPLETO)
        casos = [
            ("falta la columna sanic_orden", dict(genericas=[g for g in gen if g["LogicalName"] != "sanic_orden"])),
            ("sanic_codigo.RequiredLevel", dict(genericas=con_cambio(gen, [1, "RequiredLevel"], rl("None")))),
            ("sanic_codigo.IsSecured", dict(genericas=con_cambio(gen, [1, "IsSecured"], True))),
            ("sanic_codigo.tipo", dict(genericas=con_cambio(gen, [1, "AttributeTypeName"], {"Value": "MemoType"}))),
            ("sanic_codigo.DisplayName", dict(genericas=con_cambio(gen, [1, "DisplayName"], label("Otro")))),
            ("sanic_codigo.MaxLength", dict(por_tipo=con_cambio(pt, ["String", 1, "MaxLength"], 10))),
            ("sanic_nombre.MaxLength", dict(por_tipo=con_cambio(pt, ["String", 0, "MaxLength"], 100))),
            ("sanic_folio.AutoNumberFormat", dict(por_tipo=con_cambio(pt, ["String", 2, "AutoNumberFormat"], None))),
            ("sanic_orden.MaxValue", dict(por_tipo=con_cambio(pt, ["Integer", 0, "MaxValue"], 5))),
            ("sanic_moneda.choice", dict(por_tipo=con_cambio(pt, ["Picklist", 0, "GlobalOptionSet", "Name"], "sanic_mppp_ch_otro"))),
            ("sanic_activado.DefaultValue", dict(por_tipo=con_cambio(pt, ["Boolean", 0, "DefaultValue"], True))),
            ("sanic_activado.etiqueta_si", dict(por_tipo=con_cambio(pt, ["Boolean", 0, "OptionSet", "TrueOption", "Label"], label("Yes")))),
            ("sanic_fechadocumento.DateTimeBehavior", dict(por_tipo=con_cambio(pt, ["DateTime", 0, "DateTimeBehavior"], {"Value": "UserLocal"}))),
            ("sanic_fechaevento.Format", dict(por_tipo=con_cambio(pt, ["DateTime", 1, "Format"], "DateOnly"))),
            ("sanic_documento.MaxSizeInKB", dict(por_tipo=con_cambio(pt, ["File", 0, "MaxSizeInKB"], 32768))),
            ("pertenencia a la solución", dict(componentes=[])),
        ]
        for esperado, kw in casos:
            with self.subTest(esperado):
                self.difiere(esperado, **kw)

    def test_una_columna_propia_de_mas_difiere_pero_un_lookup_no(self):
        gen = [fila_generica(COMPLETO["primaria"], True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        intrusa = fila_generica(col("sanic_intrusa", "texto", largo=5))
        self.difiere("sanic_intrusa", genericas=gen + [intrusa])
        lookup = dict(fila_generica(col("sanic_clienteid", "texto", largo=5)), AttributeTypeName={"Value": "LookupType"})
        sombra = dict(fila_generica(col("sanic_monedaname", "texto", largo=5)), AttributeOf="sanic_moneda", AttributeTypeName={"Value": "VirtualType"})
        cliente = armar(ClienteSimulado(), COMPLETO, genericas=gen + [lookup, sombra])
        estado, _, detalle = self.con_cliente(cliente, COMPLETO)
        self.assertEqual(estado, "ya_existia", detalle)


class FormaYHttpInesperados(Base):
    def test_http_inesperado_es_error_y_nombra_la_consulta(self):
        for matcher, nombre in [(lambda r: r.startswith("GlobalOptionSetDefinitions(Name="), "GlobalOptionSetDefinitions"),
                                (lambda r: r.startswith("EntityDefinitions(LogicalName=") and "/Attributes" not in r, "EntityDefinitions"),
                                (lambda r: "/Attributes?" in r, "Attributes"),
                                (lambda r: "StringAttributeMetadata" in r, "StringAttributeMetadata"),
                                (es_ruta_solutioncomponents, "solutioncomponents"),
                                (es_ruta_solutions, "solutions")]:
            with self.subTest(nombre):
                cliente = ClienteSimulado()
                cliente.responder("GET", matcher, (500, {"error": {"message": "boom"}}, {}))
                armar(cliente, COMPLETO)
                estado, _, detalle = self.con_cliente(cliente, COMPLETO)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("HTTP 500", detalle)
                self.assertIn(nombre, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_forma_inesperada_es_error_y_nombra_el_campo(self):
        gen = [fila_generica(COMPLETO["primaria"], True)] + [fila_generica(c) for c in COMPLETO["columnas"]] + SISTEMA
        pt = filas_por_tipo(COMPLETO)
        t = cuerpo_tabla(COMPLETO)
        casos = [
            ("MetadataId", dict(tabla=con_cambio(t, ["MetadataId"], None))),
            ("OwnershipType", dict(tabla=con_cambio(t, ["OwnershipType"], 1))),
            ("HasNotes", dict(tabla=con_cambio(t, ["HasNotes"], "false"))),
            ("IsAuditEnabled.Value", dict(tabla=con_cambio(t, ["IsAuditEnabled", "Value"], "false"))),
            ("DisplayName", dict(tabla=con_cambio(t, ["DisplayName"], None))),
            ("value[1].LogicalName", dict(genericas=con_cambio(gen, [1, "LogicalName"], None))),
            ("value[1].RequiredLevel.Value", dict(genericas=con_cambio(gen, [1, "RequiredLevel", "Value"], 0))),
            ("value[1].IsSecured", dict(genericas=con_cambio(gen, [1, "IsSecured"], None))),
            ("value[2]", dict(genericas=con_cambio(gen, [2], "texto"))),
            ("value[1].MaxLength", dict(por_tipo=con_cambio(pt, ["String", 1, "MaxLength"], "9"))),
            ("value[0].MaxValue", dict(por_tipo=con_cambio(pt, ["Integer", 0, "MaxValue"], None))),
            ("value[0].GlobalOptionSet", dict(por_tipo=con_cambio(pt, ["Picklist", 0, "GlobalOptionSet"], None))),
            ("value[0].DateTimeBehavior.Value", dict(por_tipo=con_cambio(pt, ["DateTime", 0, "DateTimeBehavior", "Value"], None))),
            ("value[0].MaxSizeInKB", dict(por_tipo=con_cambio(pt, ["File", 0, "MaxSizeInKB"], True))),
            ("value[0].DefaultValue", dict(por_tipo=con_cambio(pt, ["Boolean", 0, "DefaultValue"], 0))),
        ]
        for campo, kw in casos:
            with self.subTest(campo):
                cliente = armar(ClienteSimulado(), COMPLETO, **kw)
                estado, _, detalle = self.con_cliente(cliente, COMPLETO)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("forma inesperada", detalle)
                self.assertIn(f"'{campo}'", detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())


if __name__ == "__main__":
    unittest.main()
