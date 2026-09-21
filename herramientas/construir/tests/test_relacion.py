"""Herramienta `relacion.py`: una relación 1:N con su columna lookup, desde un
playbook. Ninguna prueba toca la red."""
import copy
import os
import sys
import tempfile
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import relacion as rl  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok, es_ruta_solutioncomponents, es_ruta_solutions, label, playbook_md  # noqa: E402

BORRAR = object()
IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="relacion", inventario="4.1")
META_REL = "66666666-6666-6666-6666-666666666666"
PADRE, HIJA, REL, LOOKUP = "sanic_mppp_tbl_cliente", "sanic_mppp_tbl_plan", "sanic_mppp_cliente_plan", "sanic_clienteid"

BASE = {
    "tipo": "relacion",
    "nombre": REL,
    "tabla_padre": PADRE,
    "tabla_hija": HIJA,
    "comportamiento": "restringido",
    "lookup": {"nombre": LOOKUP, "displayname": "Cliente", "descripcion": "Empresa a la que pertenece el plan.",
               "requerida": True, "auditoria": True},
}
PARENTAL = dict(copy.deepcopy(BASE), nombre="sanic_mppp_solicitud_fila", tabla_padre="sanic_mppp_tbl_solicitud",
                tabla_hija="sanic_mppp_tbl_fila", comportamiento="parental",
                lookup={"nombre": "sanic_solicitudid", "displayname": "Solicitud", "descripcion": "Solicitud de la fila.", "requerida": True, "auditoria": False})
DE_SISTEMA = dict(copy.deepcopy(BASE), nombre="sanic_mppp_systemuser_fila_digitadapor", tabla_padre="systemuser",
                  tabla_hija="sanic_mppp_tbl_fila", comportamiento="restringido",
                  lookup={"nombre": "sanic_digitadapor", "displayname": "Digitada por", "descripcion": "Quién la digitó.", "requerida": False, "auditoria": False})

CASCADAS = {
    "parental": {"Assign": "Cascade", "Delete": "Cascade", "Merge": "NoCascade", "Reparent": "Cascade", "Share": "Cascade", "Unshare": "Cascade", "RollupView": "NoCascade"},
    "restringido": {"Assign": "NoCascade", "Delete": "Restrict", "Merge": "NoCascade", "Reparent": "NoCascade", "Share": "NoCascade", "Unshare": "NoCascade", "RollupView": "NoCascade"},
    "quitar_vinculo": {"Assign": "NoCascade", "Delete": "RemoveLink", "Merge": "NoCascade", "Reparent": "NoCascade", "Share": "NoCascade", "Unshare": "NoCascade", "RollupView": "NoCascade"},
}


def con_cambio(obj, ruta, valor):
    nuevo = copy.deepcopy(obj)
    nodo = nuevo
    for paso in ruta[:-1]:
        nodo = nodo[paso]
    if valor is BORRAR:
        del nodo[ruta[-1]]
    else:
        nodo[ruta[-1]] = valor
    return nuevo


def rl_(valor):
    return {"Value": valor, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"}


def aud(valor):
    return {"Value": valor, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyauditsettings"}


def id_de(tabla):
    return "systemuserid" if tabla == "systemuser" else tabla + "id"


def cuerpo_relacion(d):
    return {"MetadataId": META_REL, "SchemaName": d["nombre"], "ReferencedEntity": d["tabla_padre"], "ReferencedAttribute": id_de(d["tabla_padre"]),
            "ReferencingEntity": d["tabla_hija"], "ReferencingAttribute": d["lookup"]["nombre"], "IsCustomRelationship": True, "IsManaged": False,
            "RelationshipType": "OneToManyRelationship", "CascadeConfiguration": dict(CASCADAS[d["comportamiento"]], Archive="NoCascade")}


def cuerpo_lookup(d):
    k = d["lookup"]
    return {"LogicalName": k["nombre"], "SchemaName": k["nombre"], "AttributeTypeName": {"Value": "LookupType"}, "Targets": [d["tabla_padre"]],
            "RequiredLevel": rl_("ApplicationRequired" if k["requerida"] else "None"), "IsAuditEnabled": aud(k["auditoria"]), "IsSecured": False,
            "DisplayName": label(k["displayname"]), "Description": label(k["descripcion"])}


def armar(cliente, d, existe=True, relacion=None, lookup=None, componentes=None, tablas=None):
    """Configura TODAS las rutas del camino feliz."""
    armar_cliente_precondiciones_ok(cliente, IDENT)
    estado = {"existe": existe}
    tablas = tablas if tablas is not None else {d["tabla_padre"]: {"PrimaryIdAttribute": id_de(d["tabla_padre"]), "IsCustomEntity": d["tabla_padre"] != "systemuser"},
                                                d["tabla_hija"]: {"PrimaryIdAttribute": id_de(d["tabla_hija"]), "IsCustomEntity": True}}

    def tabla(ruta, *_):
        nombre = ruta.split("'")[1]
        if nombre in tablas:
            return (200, dict(tablas[nombre], LogicalName=nombre, MetadataId="t-" + nombre), {})
        return (404, {"error": "no existe"}, {})

    cliente.responder("GET", lambda r: r.startswith("EntityDefinitions(LogicalName=") and "/Attributes" not in r, tabla)
    cliente.responder("GET", lambda r: r.startswith("RelationshipDefinitions(SchemaName="),
                      lambda *_: (200, relacion if relacion is not None else cuerpo_relacion(d), {}) if estado["existe"] else (404, {"error": "no existe"}, {}))
    def leer_lookup(*_):
        if not estado["existe"]:
            return (404, {"error": "no existe"}, {})
        if lookup is not None:
            return (200, lookup, {})
        c = cuerpo_lookup(d)
        if estado.get("recien_creada") and not estado.get("auditoria_ajustada"):
            c["IsAuditEnabled"] = aud(False)  # verificado: la plataforma ignora la auditoría del lookup al crear
        return (200, c, {})

    cliente.responder("GET", lambda r: "/Attributes(LogicalName=" in r, leer_lookup)
    # Una relación NO tiene fila propia en solutioncomponents: viaja dentro de la tabla hija (componenttype 1, con todos sus subcomponentes).
    cliente.responder("GET", es_ruta_solutioncomponents,
                      (200, {"value": componentes if componentes is not None else [{"solutioncomponentid": "x", "rootcomponentbehavior": 0}]}, {}))

    def al_crear(*_):
        estado["existe"] = True
        estado["recien_creada"] = True
        return (204, None, {})

    def al_ajustar(*_):
        estado["auditoria_ajustada"] = True
        return (204, None, {})

    cliente.responder("PUT", lambda r: "/Attributes(LogicalName=" in r, al_ajustar)

    cliente.responder("POST", "RelationshipDefinitions", al_crear)
    cliente.responder("POST", "PublishXml", (204, None, {}))
    return cliente


class Base(unittest.TestCase):
    def correr(self, fabrica, datos, solo_verificar=False):
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "playbook.md")
            open(ruta, "w", encoding="utf-8").write(playbook_md(IDENT, datos))
            return rl.construir(ruta, solo_verificar, fabrica)

    def con_cliente(self, cliente, datos, **kw):
        return self.correr(lambda: cliente, datos, **kw)


class ValidacionSinRed(Base):
    CASOS = [
        (["tipo"], "tabla", "tipo"),
        (["nombre"], "sanic_mppp_rel_Cliente", "nombre"),
        (["nombre"], "sanic_cliente_plan", "nombre"),
        (["nombre"], "sanic_mppp_cliente_plan_" + "a" * 90, "100"),
        (["tabla_padre"], "cliente", "tabla_padre"),
        (["tabla_hija"], "systemuser", "tabla_hija"),
        (["tabla_hija"], BORRAR, "tabla_hija"),
        (["comportamiento"], "cascada", "comportamiento"),
        (["sobra"], 1, "sobra"),
        (["lookup"], "sanic_clienteid", "lookup"),
        (["lookup", "nombre"], "sanic_ClienteId", "lookup.nombre"),
        (["lookup", "nombre"], "otro_clienteid", "lookup.nombre"),
        (["lookup", "displayname"], "", "lookup.displayname"),
        (["lookup", "requerida"], "si", "lookup.requerida"),
        (["lookup", "auditoria"], None, "lookup.auditoria"),
        (["lookup", "largo"], 10, "largo"),
    ]

    def test_cada_dato_invalido_es_error_nombra_la_clave_y_no_toca_la_red(self):
        for ruta, valor, esperado in self.CASOS:
            with self.subTest(f"{ruta} <- {'BORRAR' if valor is BORRAR else repr(valor)}"):
                centinela = FabricaCentinela()
                estado, _, detalle = self.correr(centinela, con_cambio(BASE, ruta, valor))
                self.assertEqual(estado, "error", detalle)
                self.assertIn(esperado, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(centinela.llamada)

    def test_el_nombre_tiene_que_nombrar_a_las_dos_tablas(self):
        """BP-PP-188: `<prefijo>_<abrev>_<padre>_<hijo>`, con un sufijo libre
        cuando hay más de una relación entre el mismo par de tablas."""
        estado, _, detalle = self.correr(FabricaCentinela(), con_cambio(BASE, ["nombre"], "sanic_mppp_plan_cliente"))
        self.assertEqual(estado, "error", detalle)
        self.assertIn("sanic_mppp_cliente_plan", detalle)
        cliente = armar(ClienteSimulado(), DE_SISTEMA)
        estado, _, detalle = self.con_cliente(cliente, DE_SISTEMA)
        self.assertEqual(estado, "ya_existia", detalle)


class Payload(unittest.TestCase):
    def test_restringido(self):
        p = rl.construir_payload(BASE, IDENT, id_de(PADRE))
        self.assertEqual(p["@odata.type"], "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata")
        self.assertEqual((p["SchemaName"], p["ReferencedEntity"], p["ReferencedAttribute"], p["ReferencingEntity"]), (REL, PADRE, PADRE + "id", HIJA))
        self.assertEqual(p["CascadeConfiguration"], CASCADAS["restringido"])
        k = p["Lookup"]
        self.assertEqual(k["@odata.type"], "Microsoft.Dynamics.CRM.LookupAttributeMetadata")
        self.assertEqual((k["SchemaName"], k["AttributeType"], k["AttributeTypeName"]), (LOOKUP, "Lookup", {"Value": "LookupType"}))
        self.assertEqual(k["RequiredLevel"]["Value"], "ApplicationRequired")
        self.assertEqual(k["IsAuditEnabled"]["Value"], True)
        self.assertEqual(k["DisplayName"]["LocalizedLabels"][0]["Label"], "Cliente")
        self.assertEqual(p["AssociatedMenuConfiguration"]["Behavior"], "UseCollectionName")

    def test_cada_comportamiento(self):
        for c, esperado in CASCADAS.items():
            with self.subTest(c):
                self.assertEqual(rl.construir_payload(con_cambio(BASE, ["comportamiento"], c), IDENT, "x")["CascadeConfiguration"], esperado)


class Caminos(Base):
    def test_no_existe_se_crea_se_publica_y_se_verifica(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, comp, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual(comp, REL)
        self.assertIn(META_REL, detalle)
        escrituras = [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"]
        ruta_lookup = f"EntityDefinitions(LogicalName='{HIJA}')/Attributes(LogicalName='{LOOKUP}')"
        self.assertEqual(escrituras, [("POST", "RelationshipDefinitions"), ("PUT", ruta_lookup), ("POST", "PublishXml")])
        put = [l for l in cliente.llamadas if l["metodo"] == "PUT"][0]
        self.assertEqual(put["cuerpo"]["@odata.type"], "Microsoft.Dynamics.CRM.LookupAttributeMetadata")
        self.assertEqual(put["cuerpo"]["IsAuditEnabled"]["Value"], True)
        self.assertEqual(put["cuerpo"]["Targets"], [PADRE])  # el resto de la definición se conserva
        self.assertEqual(put["cabeceras"], {"MSCRM.MergeLabels": "true"})
        self.assertEqual(put["solucion"], IDENT["solucion"])
        post = [l for l in cliente.llamadas if l["ruta"] == "RelationshipDefinitions"][0]
        self.assertEqual(post["solucion"], IDENT["solucion"])
        self.assertEqual(post["cuerpo"]["ReferencedAttribute"], PADRE + "id")
        xml = [l for l in cliente.llamadas if l["ruta"] == "PublishXml"][0]["cuerpo"]["ParameterXml"]
        self.assertIn(f"<entity>{PADRE}</entity>", xml)
        self.assertIn(f"<entity>{HIJA}</entity>", xml)

    def test_un_lookup_sin_auditoria_no_necesita_ajuste(self):
        cliente = armar(ClienteSimulado(), PARENTAL, existe=False)
        estado, _, detalle = self.con_cliente(cliente, PARENTAL)
        self.assertEqual(estado, "creado", detalle)
        self.assertEqual([l for l in cliente.llamadas if l["metodo"] == "PUT"], [])

    def test_si_falla_el_ajuste_de_la_auditoria_dice_que_quedo_incompleta(self):
        cliente = ClienteSimulado()
        cliente.responder("PUT", lambda r: True, (400, {"error": "boom"}, {}))
        armar(cliente, BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("incompleta", detalle)
        self.assertIn("--corregir-lookup", detalle)

    def test_corregir_lookup_repara_solo_la_auditoria(self):
        sin_aud = con_cambio(cuerpo_lookup(BASE), ["IsAuditEnabled"], aud(False))
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "p.md")
            open(ruta, "w", encoding="utf-8").write(playbook_md(IDENT, BASE))
            cliente = armar(ClienteSimulado(), BASE, lookup=sin_aud)
            rl.construir(ruta, False, lambda: cliente, corregir_lookup=True)
            self.assertEqual([l["metodo"] for l in cliente.llamadas if l["metodo"] != "GET"], ["PUT", "POST"])
            otra = con_cambio(sin_aud, ["RequiredLevel"], rl_("None"))
            cliente = armar(ClienteSimulado(), BASE, lookup=otra)
            estado, _, _ = rl.construir(ruta, False, lambda: cliente, corregir_lookup=True)
        self.assertEqual(estado, "difiere")
        self.assertFalse(cliente.hubo_escritura())

    def test_hacia_una_tabla_del_sistema_solo_publica_la_hija(self):
        cliente = armar(ClienteSimulado(), DE_SISTEMA, existe=False)
        estado, _, detalle = self.con_cliente(cliente, DE_SISTEMA)
        self.assertEqual(estado, "creado", detalle)
        xml = [l for l in cliente.llamadas if l["ruta"] == "PublishXml"][0]["cuerpo"]["ParameterXml"]
        self.assertNotIn("systemuser", xml)
        self.assertEqual([l for l in cliente.llamadas if l["ruta"] == "RelationshipDefinitions"][0]["cuerpo"]["ReferencedAttribute"], "systemuserid")

    def test_ya_existia_no_escribe(self):
        for d in (BASE, PARENTAL, DE_SISTEMA):
            with self.subTest(d["nombre"]):
                cliente = armar(ClienteSimulado(), d)
                estado, _, detalle = self.con_cliente(cliente, d)
                self.assertEqual(estado, "ya_existia", detalle)
                self.assertIn(META_REL, detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_solo_verificar_sin_relacion_es_error_y_no_crea(self):
        cliente = armar(ClienteSimulado(), BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE, solo_verificar=True)
        self.assertEqual(estado, "error")
        self.assertIn("no existe", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_falta_una_de_las_tablas_bloquea_sin_crear(self):
        for falta in (PADRE, HIJA):
            with self.subTest(falta):
                tablas = {t: {"PrimaryIdAttribute": t + "id", "IsCustomEntity": True} for t in (PADRE, HIJA) if t != falta}
                cliente = armar(ClienteSimulado(), BASE, existe=False, tablas=tablas)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "bloqueado", detalle)
                self.assertIn(falta, detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_la_creacion_falla(self):
        cliente = ClienteSimulado()
        cliente.responder("POST", "RelationshipDefinitions", (400, {"error": "ya hay una relación parental"}, {}))
        armar(cliente, PARENTAL, existe=False)
        estado, _, detalle = self.con_cliente(cliente, PARENTAL)
        self.assertEqual(estado, "error")
        self.assertIn("HTTP 400", detalle)

    def test_si_falla_publicar_lo_dice(self):
        cliente = ClienteSimulado()
        cliente.responder("POST", "PublishXml", (500, {"error": "boom"}, {}))
        armar(cliente, BASE, existe=False)
        estado, _, detalle = self.con_cliente(cliente, BASE)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("publicar", detalle)
        self.assertIn("--publicar", detalle)

    def test_publicar_republica_una_relacion_que_coincide_y_nada_mas(self):
        with tempfile.TemporaryDirectory() as dd:
            ruta = os.path.join(dd, "p.md")
            open(ruta, "w", encoding="utf-8").write(playbook_md(IDENT, BASE))
            cliente = armar(ClienteSimulado(), BASE)
            estado, _, detalle = rl.construir(ruta, False, lambda: cliente, publicar=True)
        self.assertEqual(estado, "ya_existia", detalle)
        self.assertEqual([(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"], [("POST", "PublishXml")])


class Diferencias(Base):
    def test_cada_diferencia(self):
        r, k = cuerpo_relacion(BASE), cuerpo_lookup(BASE)
        casos = [
            ("ReferencedEntity", dict(relacion=con_cambio(r, ["ReferencedEntity"], "sanic_mppp_tbl_otra"))),
            ("ReferencingEntity", dict(relacion=con_cambio(r, ["ReferencingEntity"], "sanic_mppp_tbl_otra"))),
            ("ReferencingAttribute", dict(relacion=con_cambio(r, ["ReferencingAttribute"], "sanic_otroid"))),
            ("IsManaged", dict(relacion=con_cambio(r, ["IsManaged"], True))),
            ("CascadeConfiguration.Delete", dict(relacion=con_cambio(r, ["CascadeConfiguration", "Delete"], "RemoveLink"))),
            ("CascadeConfiguration.Assign", dict(relacion=con_cambio(r, ["CascadeConfiguration", "Assign"], "Cascade"))),
            (f"{LOOKUP}.RequiredLevel", dict(lookup=con_cambio(k, ["RequiredLevel"], rl_("None")))),
            (f"{LOOKUP}.IsAuditEnabled", dict(lookup=con_cambio(k, ["IsAuditEnabled"], aud(False)))),
            (f"{LOOKUP}.DisplayName", dict(lookup=con_cambio(k, ["DisplayName"], label("Otro")))),
            (f"{LOOKUP}.Targets", dict(lookup=con_cambio(k, ["Targets"], ["account"]))),
            (f"{LOOKUP}.tipo", dict(lookup=con_cambio(k, ["AttributeTypeName"], {"Value": "StringType"}))),
            ("pertenencia a la solución", dict(componentes=[])),
            ("no incluye todos sus subcomponentes", dict(componentes=[{"solutioncomponentid": "x", "rootcomponentbehavior": 1}])),
        ]
        for esperado, kw in casos:
            with self.subTest(esperado):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "difiere", detalle)
                self.assertIn(esperado, detalle)
                self.assertFalse(cliente.hubo_escritura())


class FormaYHttpInesperados(Base):
    def test_http_inesperado_es_error_y_nombra_la_consulta(self):
        for matcher, nombre in [(lambda r: r.startswith("EntityDefinitions(LogicalName=") and "/Attributes" not in r, "EntityDefinitions"),
                                (lambda r: r.startswith("RelationshipDefinitions(SchemaName="), "RelationshipDefinitions"),
                                (lambda r: "/Attributes(LogicalName=" in r, "LookupAttributeMetadata"),
                                (es_ruta_solutioncomponents, "solutioncomponents"), (es_ruta_solutions, "solutions")]:
            with self.subTest(nombre):
                cliente = ClienteSimulado()
                cliente.responder("GET", matcher, (500, {"error": "boom"}, {}))
                armar(cliente, BASE)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("HTTP 500", detalle)
                self.assertIn(nombre, detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())

    def test_forma_inesperada_es_error_y_nombra_el_campo(self):
        r, k = cuerpo_relacion(BASE), cuerpo_lookup(BASE)
        casos = [
            ("MetadataId", dict(relacion=con_cambio(r, ["MetadataId"], None))),
            ("ReferencedEntity", dict(relacion=con_cambio(r, ["ReferencedEntity"], 5))),
            ("IsManaged", dict(relacion=con_cambio(r, ["IsManaged"], "false"))),
            ("CascadeConfiguration", dict(relacion=con_cambio(r, ["CascadeConfiguration"], None))),
            ("CascadeConfiguration.Delete", dict(relacion=con_cambio(r, ["CascadeConfiguration", "Delete"], None))),
            ("RequiredLevel.Value", dict(lookup=con_cambio(k, ["RequiredLevel", "Value"], 0))),
            ("IsAuditEnabled", dict(lookup=con_cambio(k, ["IsAuditEnabled"], True))),
            ("Targets", dict(lookup=con_cambio(k, ["Targets"], "sanic_mppp_tbl_cliente"))),
            ("Targets[0]", dict(lookup=con_cambio(k, ["Targets"], [None]))),
            ("DisplayName", dict(lookup=con_cambio(k, ["DisplayName"], None))),
            ("value[0].rootcomponentbehavior", dict(componentes=[{"solutioncomponentid": "x", "rootcomponentbehavior": None}])),
            ("PrimaryIdAttribute", dict(tablas={PADRE: {"PrimaryIdAttribute": None, "IsCustomEntity": True}, HIJA: {"PrimaryIdAttribute": HIJA + "id", "IsCustomEntity": True}})),
        ]
        for campo, kw in casos:
            with self.subTest(campo):
                cliente = armar(ClienteSimulado(), BASE, **kw)
                estado, _, detalle = self.con_cliente(cliente, BASE)
                self.assertEqual(estado, "error", detalle)
                self.assertIn("forma inesperada", detalle)
                self.assertIn(f"'{campo}'", detalle)
                self.assertNotIn("fallo inesperado", detalle)
                self.assertFalse(cliente.hubo_escritura())


if __name__ == "__main__":
    unittest.main()
