"""`tabla.py --corregir-nombres`: corrige SOLO nombres visibles (tabla, plural,
columnas, etiquetas de un sí/no) y solo si esa es la ÚNICA diferencia.
Ensayado contra la plataforma el 2026-09-21 con todos los tipos de columna."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import test_tabla as tt  # noqa: E402
from cliente_simulado import ClienteSimulado  # noqa: E402
from fixtures import label  # noqa: E402

D, T = tt.COMPLETO, tt.COMPLETO["nombre"]
SINO = next(c for c in D["columnas"] if c["tipo"] == "sino")
ENTERO = next(c for c in D["columnas"] if c["tipo"] == "entero")
CAST = {"texto": "String", "memo": "Memo", "entero": "Integer", "choice": "Picklist", "sino": "Boolean", "fecha": "DateTime", "fechahora": "DateTime", "archivo": "File", "autonumerico": "String"}


def entorno_viejo(tabla=False, columnas=(), primaria=False, sino=False, otra=False):
    """Argumentos de `tt.armar` para un entorno con nombres viejos."""
    t = tt.cuerpo_tabla(D)
    if tabla:
        t["DisplayName"], t["DisplayCollectionName"] = label("Démo"), label("Démos")
    gen = [tt.fila_generica(D["primaria"], True)] + [tt.fila_generica(c) for c in D["columnas"]] + tt.SISTEMA
    for g in gen:
        if g["LogicalName"] in columnas or (primaria and g["LogicalName"] == D["primaria"]["nombre"]):
            g["DisplayName"] = label("Nombre viéjo")
    pt = copy.deepcopy(tt.filas_por_tipo(D))
    if sino:
        fila = next(f for f in pt["Boolean"] if f["LogicalName"] == SINO["nombre"])
        fila["OptionSet"]["TrueOption"]["Label"] = label("Sí")
    if otra:
        next(f for f in pt["Integer"] if f["LogicalName"] == ENTERO["nombre"])["MaxValue"] = 5
    return dict(tabla=t, genericas=gen, por_tipo=pt)


def con_rutas_de_correccion(cliente):
    cliente.responder("GET", f"EntityDefinitions(LogicalName='{T}')", (200, {"LogicalName": T, "SchemaName": T, "OwnershipType": "UserOwned", "DisplayName": label("Démo")}, {}))
    cliente.responder("PUT", f"EntityDefinitions(LogicalName='{T}')", (204, None, {}))
    for c in D["columnas"]:
        ruta = f"EntityDefinitions(LogicalName='{T}')/Attributes(LogicalName='{c['nombre']}')"
        cliente.responder("GET", f"{ruta}/Microsoft.Dynamics.CRM.{CAST[c['tipo']]}AttributeMetadata", (200, {"LogicalName": c["nombre"], "SchemaName": c["nombre"], "DisplayName": label("Nombre viéjo"), "Conservado": 7}, {}))
        cliente.responder("PUT", ruta, (204, None, {}))
    cliente.responder("POST", "UpdateOptionValue", (204, None, {}))
    return cliente


class CorregirNombres(tt.Base):
    def escrituras(self, cliente):
        return [(l["metodo"], l["ruta"]) for l in cliente.llamadas if l["metodo"] != "GET"]

    def test_sin_el_flag_difiere_y_no_escribe(self):
        cliente = tt.armar(con_rutas_de_correccion(ClienteSimulado()), D, **entorno_viejo(tabla=True))
        estado, _, detalle = self.con_cliente(cliente, D)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_corrige_tabla_columnas_primaria_y_si_no_y_publica_una_vez(self):
        kw = entorno_viejo(tabla=True, columnas=(ENTERO["nombre"], SINO["nombre"]), primaria=True, sino=True)
        cliente = tt.armar(con_rutas_de_correccion(ClienteSimulado()), D, **kw)
        self.con_cliente(cliente, D, corregir_nombres=True)  # la relectura simulada sigue difiriendo: importa qué escribió
        prim = f"EntityDefinitions(LogicalName='{T}')/Attributes(LogicalName='{D['primaria']['nombre']}')"
        col = lambda c: f"EntityDefinitions(LogicalName='{T}')/Attributes(LogicalName='{c['nombre']}')"  # noqa: E731
        self.assertEqual(self.escrituras(cliente), [("PUT", f"EntityDefinitions(LogicalName='{T}')"), ("PUT", prim), ("PUT", col(ENTERO)), ("PUT", col(SINO)),
                                                    ("POST", "UpdateOptionValue"), ("POST", "PublishXml")])
        puts = {l["ruta"]: l for l in cliente.llamadas if l["metodo"] == "PUT"}
        tabla = puts[f"EntityDefinitions(LogicalName='{T}')"]
        self.assertEqual(tabla["cuerpo"]["@odata.type"], "Microsoft.Dynamics.CRM.EntityMetadata")
        self.assertEqual(tabla["cuerpo"]["DisplayName"]["LocalizedLabels"][0]["Label"], D["displayname"])
        self.assertEqual(tabla["cuerpo"]["DisplayCollectionName"]["LocalizedLabels"][0]["Label"], D["displayname_plural"])
        self.assertEqual(tabla["cuerpo"]["OwnershipType"], "UserOwned")  # el resto se conserva
        self.assertEqual((tabla["cabeceras"], tabla["solucion"]), ({"MSCRM.MergeLabels": "true"}, tt.IDENT["solucion"]))
        entero = puts[col(ENTERO)]["cuerpo"]
        self.assertEqual((entero["@odata.type"], entero["DisplayName"]["LocalizedLabels"][0]["Label"], entero["Conservado"]),
                         ("Microsoft.Dynamics.CRM.IntegerAttributeMetadata", ENTERO["displayname"], 7))
        op = next(l for l in cliente.llamadas if l["ruta"] == "UpdateOptionValue")["cuerpo"]
        self.assertEqual((op["EntityLogicalName"], op["AttributeLogicalName"], op["Value"], op["MergeLabels"], op["SolutionUniqueName"]), (T, SINO["nombre"], 1, True, tt.IDENT["solucion"]))
        self.assertEqual(op["Label"]["LocalizedLabels"][0]["Label"], SINO["etiqueta_si"])

    def test_con_otra_diferencia_ademas_no_toca_nada(self):
        cliente = tt.armar(con_rutas_de_correccion(ClienteSimulado()), D, **entorno_viejo(tabla=True, otra=True))
        estado, _, detalle = self.con_cliente(cliente, D, corregir_nombres=True)
        self.assertEqual(estado, "difiere", detalle)
        self.assertFalse(cliente.hubo_escritura())

    def test_con_solo_verificar_o_si_ya_coincide_no_escribe(self):
        for kw_armar, kw, esperado in ((entorno_viejo(tabla=True), dict(corregir_nombres=True, solo_verificar=True), "difiere"), ({}, dict(corregir_nombres=True), "ya_existia")):
            cliente = tt.armar(con_rutas_de_correccion(ClienteSimulado()), D, **kw_armar)
            estado, _, detalle = self.con_cliente(cliente, D, **kw)
            self.assertEqual(estado, esperado, detalle)
            self.assertFalse(cliente.hubo_escritura())

    def test_si_una_escritura_falla_es_error_y_dice_cual(self):
        cliente = ClienteSimulado()
        cliente.responder("PUT", f"EntityDefinitions(LogicalName='{T}')/Attributes(LogicalName='{ENTERO['nombre']}')", (400, {"error": "boom"}, {}))
        tt.armar(con_rutas_de_correccion(cliente), D, **entorno_viejo(columnas=(ENTERO["nombre"],)))
        estado, _, detalle = self.con_cliente(cliente, D, corregir_nombres=True)
        self.assertEqual(estado, "error", detalle)
        self.assertIn("HTTP 400", detalle)
        self.assertIn(ENTERO["nombre"], detalle)


if __name__ == "__main__":
    unittest.main()
