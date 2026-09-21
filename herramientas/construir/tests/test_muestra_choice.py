"""Comparación de un choice contra el XML de la solución exportada: la
comprobación independiente del ciclo (otro camino que el Web API)."""
import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)

import muestra_choice as mc  # noqa: E402

DATOS = {
    "nombre": "sanic_x_ch_demo",
    "displayname": "CH - X - Demo",
    "descripcion": "Una descripción.",
    "opciones": [
        {"valor": 159460001, "etiqueta": "Uno", "descripcion": "Primera"},
        {"valor": 159460002, "etiqueta": "Dos", "descripcion": ""},
    ],
}


def xml(opciones=None, display="CH - X - Demo", idioma_extra=False, is_global="1"):
    opciones = opciones if opciones is not None else [(159460001, "Uno", "Primera"), (159460002, "Dos", None)]
    partes = []
    for valor, etiqueta, desc in opciones:
        d = f'<Descriptions><Description description="{desc}" languagecode="1033" /></Descriptions>' if desc is not None else ""
        partes.append(f'<option value="{valor}" ExternalValue="" IsHidden="0"><labels><label description="{etiqueta}" languagecode="1033" /></labels>{d}</option>')
    extra = '<displayname description="Demo" languagecode="3082" />' if idioma_extra else ""
    return (
        f'<ImportExportXml><optionsets><optionset Name="sanic_x_ch_demo" localizedName="{display}" description="Una descripción.">'
        f"<OptionSetType>picklist</OptionSetType><IsGlobal>{is_global}</IsGlobal>"
        f'<displaynames><displayname description="{display}" languagecode="1033" />{extra}</displaynames>'
        '<Descriptions><Description description="Una descripción." languagecode="1033" /></Descriptions>'
        f"<options>{''.join(partes)}</options></optionset></optionsets></ImportExportXml>"
    )


class CompararContraXml(unittest.TestCase):
    def test_coincide(self):
        self.assertEqual(mc.comparar_con_xml(xml(), DATOS, 1033), [])

    def test_una_descripcion_de_opcion_vacia_puede_faltar_en_el_xml(self):
        self.assertEqual(mc.comparar_con_xml(xml(), DATOS, 1033), [])

    def test_no_esta_en_la_solucion(self):
        difs = mc.comparar_con_xml("<ImportExportXml><optionsets /></ImportExportXml>", DATOS, 1033)
        self.assertEqual(len(difs), 1)
        self.assertIn("no está en la solución exportada", difs[0])

    def test_detecta_cada_diferencia(self):
        casos = {
            "displayname": xml(display="Otro nombre"),
            "opciones[1].etiqueta": xml(opciones=[(159460001, "Uno", "Primera"), (159460002, "DOS", None)]),
            "opciones[0].valor": xml(opciones=[(159460009, "Uno", "Primera"), (159460002, "Dos", None)]),
            "cantidad de opciones": xml(opciones=[(159460001, "Uno", "Primera")]),
            "orden": xml(opciones=[(159460002, "Dos", None), (159460001, "Uno", "Primera")]),
            "otro idioma": xml(idioma_extra=True),
            "IsGlobal": xml(is_global="0"),
        }
        for esperado, x in casos.items():
            with self.subTest(esperado):
                difs = mc.comparar_con_xml(x, DATOS, 1033)
                self.assertTrue(difs, "no detectó la diferencia")
                if esperado != "orden":
                    self.assertTrue(any(esperado in d for d in difs), difs)


if __name__ == "__main__":
    unittest.main()
