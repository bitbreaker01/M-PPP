"""Comparación de una tabla contra el XML de la solución exportada. Usa como
datos las muestras REALES guardadas en `playbooks/tabla/muestras/`."""
import copy
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_tabla as mt  # noqa: E402
from _comun import dividir_secciones, leer_texto, obtener_componente  # noqa: E402


def datos_de(ruta):
    return obtener_componente(dividir_secciones(leer_texto(os.path.join(_RAIZ, ruta))), "tabla")


def xml_de(nombre):
    return "<ImportExportXml><Entities>" + open(os.path.join(_RAIZ, "playbooks", "tabla", "muestras", nombre), encoding="utf-8").read() + "</Entities></ImportExportXml>"


CLIENTE = datos_de("playbooks/tabla/sanic_mppp_tbl_cliente.md")
ENSAYO = datos_de("playbooks/tabla/ensayos/sanic_mppp_tbl_zzensayo.md")
XML_CLIENTE = xml_de("sanic_mppp_tbl_cliente.solucion.xml")
XML_ENSAYO = xml_de("sanic_mppp_tbl_zzensayo.solucion.xml")


def cambiar(datos, ruta, valor):
    d = copy.deepcopy(datos)
    nodo = d
    for p in ruta[:-1]:
        nodo = nodo[p]
    nodo[ruta[-1]] = valor
    return d


class ContraMuestrasReales(unittest.TestCase):
    def test_las_dos_muestras_reales_coinciden_con_su_playbook(self):
        self.assertEqual(mt.comparar_con_xml(XML_CLIENTE, CLIENTE, 1033), [])
        self.assertEqual(mt.comparar_con_xml(XML_ENSAYO, ENSAYO, 1033), [])

    def test_la_tabla_no_esta(self):
        difs = mt.comparar_con_xml(XML_CLIENTE, ENSAYO, 1033)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        i = {c["nombre"]: n for n, c in enumerate(ENSAYO["columnas"])}
        casos = [
            ("displayname_plural", cambiar(ENSAYO, ["displayname_plural"], "Otros")),
            ("descripcion", cambiar(ENSAYO, ["descripcion"], "Otra.")),
            ("auditoria de la tabla", cambiar(ENSAYO, ["auditoria"], False)),
            ("propiedad", cambiar(ENSAYO, ["propiedad"], "organizacion")),
            ("sanic_nombre.largo", cambiar(ENSAYO, ["primaria", "largo"], 50)),
            ("sanic_nombre.requerida", cambiar(ENSAYO, ["primaria", "requerida"], False)),
            ("sanic_nombre.autonumerico", cambiar(ENSAYO, ["primaria", "autonumerico"], "")),
            ("sanic_codigo.largo", cambiar(ENSAYO, ["columnas", i["sanic_codigo"], "largo"], 10)),
            ("sanic_codigo.requerida", cambiar(ENSAYO, ["columnas", i["sanic_codigo"], "requerida"], False)),
            ("sanic_codigo.displayname", cambiar(ENSAYO, ["columnas", i["sanic_codigo"], "displayname"], "Otro")),
            ("sanic_cuenta.protegida", cambiar(ENSAYO, ["columnas", i["sanic_cuenta"], "protegida"], False)),
            ("sanic_documento.auditoria", cambiar(ENSAYO, ["columnas", i["sanic_documento"], "auditoria"], True)),
            ("sanic_documento.tamano_kb", cambiar(ENSAYO, ["columnas", i["sanic_documento"], "tamano_kb"], 5)),
            ("sanic_orden.maximo", cambiar(ENSAYO, ["columnas", i["sanic_orden"], "maximo"], 5)),
            ("sanic_moneda.choice", cambiar(ENSAYO, ["columnas", i["sanic_moneda"], "choice"], "sanic_mppp_ch_banco")),
            ("sanic_activado.defecto", cambiar(ENSAYO, ["columnas", i["sanic_activado"], "defecto"], True)),
            ("sanic_fechadocumento.tipo", cambiar(ENSAYO, ["columnas", i["sanic_fechadocumento"], "tipo"], "fechahora")),
            ("sanic_folio.formato", cambiar(ENSAYO, ["columnas", i["sanic_folio"], "formato"], "X-{SEQNUM:3}")),
            ("sanic_detalle.tipo", cambiar(cambiar(ENSAYO, ["columnas", i["sanic_detalle"], "tipo"], "texto"), ["columnas", i["sanic_detalle"], "largo"], 2000)),
        ]
        for esperado, datos in casos:
            with self.subTest(esperado):
                difs = mt.comparar_con_xml(XML_ENSAYO, datos, 1033)
                self.assertTrue(any(esperado in d for d in difs), difs)

    def test_columna_que_falta_y_columna_de_mas(self):
        falta = copy.deepcopy(CLIENTE)
        falta["columnas"].append(dict(CLIENTE["columnas"][0], nombre="sanic_inexistente"))
        self.assertTrue(any("falta la columna sanic_inexistente" in d for d in mt.comparar_con_xml(XML_CLIENTE, falta, 1033)))
        sobra = copy.deepcopy(CLIENTE)
        sobra["columnas"].pop()
        self.assertTrue(any("sanic_cifcom" in d and "no declara" in d for d in mt.comparar_con_xml(XML_CLIENTE, sobra, 1033)))


if __name__ == "__main__":
    unittest.main()
