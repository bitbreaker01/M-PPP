"""Pruebas de `herramientas/construir/importar_solucion.py`. Nunca tocan la red.

Lo que más importa: que NO se importe nada cuando no hace falta (reimportar la
solución entera es la operación más pesada del proyecto), que el resto del
`customizations.xml` salga byte por byte igual al que entró, y que el éxito se
mida releyendo el entorno y no contando lo que pedía el playbook.
"""
import base64
import copy
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

import importar_solucion as imp  # noqa: E402
from cliente_simulado import ClienteSimulado, FabricaCentinela  # noqa: E402
from fixtures import IDENTIDAD_VALIDA, armar_cliente_precondiciones_ok  # noqa: E402

IDENT = dict(IDENTIDAD_VALIDA, tipo_playbook="importacion", inventario="12.8")

APP_ID = "aaaa1111-2222-3333-4444-555566667777"
APP = "sanic_mppp_mda_mantenimientoppp"
SITEMAP = "sanic_mppp_sm_mantenimientoppp"
TABLAS = ["sanic_mppp_tbl_fila", "sanic_mppp_tbl_solicitud"]

COMPONENTE = {
    "tipo": "importacion",
    "idiomas": [1033, 3082],
    "cambios": [{"clase": "app_componentes", "app": APP, "sitemap": SITEMAP, "tablas": TABLAS}],
}

# Un customizations.xml chico pero con la misma forma que el real: dos apps,
# para que quede probado que se toca SOLO la que nombra el playbook.
CUSTOMIZATIONS = """<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml>
  <Entities />
  <AppModules>
    <AppModule>
      <UniqueName>sanic_otra_app</UniqueName>
      <AppModuleComponents>
        <AppModuleComponent type="1" schemaName="entity" />
      </AppModuleComponents>
    </AppModule>
    <AppModule>
      <UniqueName>{app}</UniqueName>
      <ClientType>2</ClientType>
      <AppModuleComponents>
        <AppModuleComponent type="1" schemaName="entity" />
        <AppModuleComponent type="62" schemaName="{sitemap}" />
      </AppModuleComponents>
      <AppModuleRoleMaps />
    </AppModule>
  </AppModules>
  <Languages />
</ImportExportXml>
""".format(app=APP, sitemap=SITEMAP)


TABLA = TABLAS[0]
BOTON = {"id": "digitada", "funcion": "Sanic.Mppp.Comandos.digitada",
         "icono": "sanic_mppp_wr_svg_cmd_digitada",
         "etiqueta": {"1033": "Mark as entered", "3082": "Digitada"},
         "tooltip": {"1033": "Marks the selected rows as entered.",
                     "3082": "Marca como digitadas las filas seleccionadas."},
         "ubicaciones": ["HomepageGrid", "SubGrid"], "secuencia": 50}
CAMBIO_RIBBON = {"clase": "ribbon", "tabla": TABLA, "biblioteca": "sanic_mppp_wr_js_comandos",
                 "botones": [BOTON], "ocultar": [".Delete", ".Assign"]}

# Ribbon como lo devuelve `RetrieveEntityRibbon`: `.Assign` existe, `.Delete`
# solo en la pestaña de gráficos (que no se toca) y uno de otra tabla.
RIBBON = f"""<RibbonDefinitions>
  <Button Id="Mscrm.HomepageGrid.{TABLA}.Assign" Command="Mscrm.AssignSelectedRecord" />
  <Button Id="Mscrm.HomepageGrid.{TABLA}.Chart.Delete" Command="Mscrm.DeleteSelectedRecord" />
  <Button Id="Mscrm.HomepageGrid.{TABLAS[1]}.Assign" Command="Mscrm.AssignSelectedRecord" />
  <Button Id="Mscrm.HomepageGrid.{TABLA}.Edit" Command="Mscrm.EditSelectedRecord" />
</RibbonDefinitions>"""

RIBBON_VACIO = ("<RibbonDiffXml><CustomActions /><Templates>"
                '<RibbonTemplates Id="Mscrm.Templates"></RibbonTemplates></Templates>'
                "<CommandDefinitions /><RuleDefinitions><TabDisplayRules /><DisplayRules />"
                "<EnableRules /></RuleDefinitions><LocLabels /></RibbonDiffXml>")

CUST_CON_ENTIDADES = """<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml>
  <Entities>
    <Entity>
      <Name LocalizedName="Otra" OriginalName="Otra">{otra}</Name>
      {ribbon}
    </Entity>
    <Entity>
      <Name LocalizedName="Fila" OriginalName="Fila">{tabla}</Name>
      <SavedQueries />
      {ribbon}
    </Entity>
  </Entities>
  <Languages />
</ImportExportXml>
""".format(tabla=TABLA, otra=TABLAS[1], ribbon=RIBBON_VACIO)


def zip_ribbon(xml=RIBBON):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("RibbonXml.xml", xml)
        z.writestr("[Content_Types].xml", "<Types />")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def zip_de(cust=CUSTOMIZATIONS):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("customizations.xml", cust)
        z.writestr("solution.xml", "<ImportExportXml />")
        z.writestr("[Content_Types].xml", "<Types />")
    return buf.getvalue()


def comp(**cambios):
    d = copy.deepcopy(COMPONENTE)
    d.update(cambios)
    return d


def playbook(componente=None):
    componente = COMPONENTE if componente is None else componente
    return (
        "# Playbook: importacion · prueba\n\n"
        "## 1. Identidad\n\n```json\n" + json.dumps(IDENT, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 2. Qué se crea\n\n```json\n" + json.dumps(componente, ensure_ascii=False, indent=2) + "\n```\n\n"
        "## 3. Precondiciones\n\n(no hace falta para las pruebas)\n"
    )


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = os.path.join(self.dir.name, "playbook.md")

    def escribir(self, componente=None):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(playbook(componente))
        return self.ruta

    def armar(self, cliente, puestas_antes=(), puestas_despues=None, cust=CUSTOMIZATIONS, data="",
              steps_apagados_despues=(), falla_al_reencender=False):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.puestas = list(puestas_antes)
        self.despues = TABLAS if puestas_despues is None else list(puestas_despues)
        self.importado = False

        cliente.responder("GET", lambda r: r.startswith("appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple"),
                          (200, {"value": [{"appmoduleid": APP_ID, "uniquename": APP}]}, {}))
        cliente.responder("GET", lambda r: r.startswith("RetrieveAppComponents("),
                          lambda r, c, s: (200, {"value": [{"componenttype": 1, "objectid": "md-" + t}
                                                           for t in (self.despues if self.importado
                                                                     else self.puestas)]}, {}))
        cliente.responder("GET", lambda r: r.startswith("EntityDefinitions(md-"),
                          lambda r, c, s: (200, {"LogicalName": r.split("(md-")[1].split(")")[0]}, {}))
        cliente.responder("POST", "ExportSolution",
                          (200, {"ExportSolutionFile": base64.b64encode(zip_de(cust)).decode("ascii")}, {}))

        def importar(ruta, cuerpo, solucion):
            self.importado = True
            self.enviado = base64.b64decode(cuerpo["CustomizationFile"])
            return (204, {}, {})

        cliente.responder("POST", "ImportSolution", importar)
        cliente.responder("GET", lambda r: r.startswith("importjobs("),
                          (200, {"progress": 100.0, "data": data}, {}))
        cliente.responder("POST", "PublishXml", (204, {}, {}))
        self.steps_apagados_despues = list(steps_apagados_despues)
        # El doble devuelve el ID además del nombre, como la plataforma: la
        # herramienta lo necesita para volver a encender el step, no solo para
        # nombrarlo en un mensaje.
        cliente.responder("GET", lambda r: r.startswith("sdkmessageprocessingsteps?"),
                          lambda r, c, s: (200, {"value": [
                              {"name": n, "statecode": 1, "sdkmessageprocessingstepid": "id-" + n}
                              for n in (self.steps_apagados_despues if self.importado else [])]}, {}))
        cliente.responder("PATCH", lambda r: r.startswith("sdkmessageprocessingsteps("),
                          (400, {"error": "no se pudo"}, {}) if falla_al_reencender else (204, {}, {}))
        return cliente

    def cust_enviado(self):
        return zipfile.ZipFile(io.BytesIO(self.enviado)).read("customizations.xml").decode("utf-8")


class EdicionDelXml(unittest.TestCase):
    def test_se_reemplaza_solo_la_app_que_nombra_el_playbook(self):
        nuevo, hubo = imp.reemplazar_componentes(CUSTOMIZATIONS, APP, SITEMAP, TABLAS)
        self.assertTrue(hubo)
        otra = nuevo[nuevo.index("sanic_otra_app"):nuevo.index(APP)]
        self.assertIn('type="1" schemaName="entity"', otra)
        self.assertNotIn("sanic_mppp_tbl_fila", otra)

    def test_el_resto_del_archivo_no_se_toca(self):
        nuevo, _ = imp.reemplazar_componentes(CUSTOMIZATIONS, APP, SITEMAP, TABLAS)
        # Todo lo que no es el bloque de componentes de esa app sigue igual.
        for trozo in ('<?xml version="1.0" encoding="utf-8"?>', "<Entities />", "<Languages />",
                      "<ClientType>2</ClientType>", "<AppModuleRoleMaps />"):
            self.assertIn(trozo, nuevo)

    def test_la_basura_entity_desaparece_de_esa_app(self):
        nuevo, _ = imp.reemplazar_componentes(CUSTOMIZATIONS, APP, SITEMAP, TABLAS)
        mia = nuevo[nuevo.index(APP):]
        self.assertNotIn('schemaName="entity"', mia)
        for t in TABLAS:
            self.assertIn(f'type="1" schemaName="{t}"', mia)
        self.assertIn(f'type="62" schemaName="{SITEMAP}"', mia)

    def test_aplicar_dos_veces_no_cambia_nada(self):
        # Idempotencia: es lo que evita reimportar la solución al pedo.
        una, hubo1 = imp.reemplazar_componentes(CUSTOMIZATIONS, APP, SITEMAP, TABLAS)
        dos, hubo2 = imp.reemplazar_componentes(una, APP, SITEMAP, TABLAS)
        self.assertTrue(hubo1)
        self.assertFalse(hubo2)
        self.assertEqual(una, dos)

    def test_una_app_que_no_esta_en_el_xml_queda_bloqueada(self):
        with self.assertRaises(imp.Bloqueado) as ctx:
            imp.reemplazar_componentes(CUSTOMIZATIONS, "sanic_mppp_mda_fantasma", SITEMAP, TABLAS)
        self.assertIn("no contiene ninguna app", str(ctx.exception))

    def test_el_zip_conserva_los_demas_archivos(self):
        datos = imp.rearmar_zip(zip_de(), "<nuevo />")
        z = zipfile.ZipFile(io.BytesIO(datos))
        self.assertEqual(["customizations.xml", "solution.xml", "[Content_Types].xml"], z.namelist())
        self.assertEqual("<nuevo />", z.read("customizations.xml").decode("utf-8"))
        self.assertEqual("<ImportExportXml />", z.read("solution.xml").decode("utf-8"))


class RibbonGenerado(unittest.TestCase):
    def xml(self, cambio=None, ocultables=None):
        cambio = CAMBIO_RIBBON if cambio is None else cambio
        presentes = imp.botones_a_ocultar(RIBBON, TABLA, cambio["ocultar"]) if ocultables is None else ocultables
        return imp.ribbondiffxml(IDENT, cambio, COMPONENTE["idiomas"], presentes)

    def test_un_boton_va_en_cada_ubicacion_que_declara(self):
        x = self.xml()
        self.assertIn(f'Location="Mscrm.HomepageGrid.{TABLA}.MainTab.Management.Controls._children"', x)
        self.assertIn(f'Location="Mscrm.SubGrid.{TABLA}.MainTab.Management.Controls._children"', x)
        self.assertNotIn("Mscrm.Form.", x)

    def test_las_dos_ubicaciones_comparten_un_solo_CommandDefinition(self):
        x = self.xml()
        self.assertEqual(1, x.count("<CommandDefinition "))
        self.assertEqual(2, x.count("<CustomAction "))

    def test_el_comando_llama_al_javascript_con_las_filas_seleccionadas(self):
        x = self.xml()
        self.assertIn('FunctionName="Sanic.Mppp.Comandos.digitada"', x)
        self.assertIn('Library="$webresource:sanic_mppp_wr_js_comandos"', x)
        self.assertIn('<CrmParameter Value="SelectedControlSelectedItemIds" />', x)

    def test_cada_etiqueta_lleva_un_texto_por_idioma(self):
        # En el XML del ribbon la plataforma NO sustituye.
        x = self.xml()
        self.assertEqual(x.count('languagecode="1033"'), x.count('languagecode="3082"'))
        self.assertIn('description="Digitada" languagecode="3082"', x)
        self.assertIn('description="Mark as entered" languagecode="1033"', x)

    def test_solo_se_oculta_lo_que_existe_y_nunca_la_pestana_de_graficos(self):
        x = self.xml()
        self.assertIn(f'Location="Mscrm.HomepageGrid.{TABLA}.Assign"', x)
        # `.Delete` solo existe bajo `.Chart.`, que no se toca.
        self.assertNotIn(".Chart.", x)
        # Y nunca un botón de OTRA tabla.
        self.assertNotIn(TABLAS[1], x)

    def test_nunca_se_sobrescribe_un_CommandDefinition_de_la_plataforma(self):
        # Los comandos OOB son GLOBALES: tocarlos apagaría ese botón en TODAS
        # las tablas del entorno. Se oculta por el id del BOTÓN.
        x = self.xml()
        self.assertNotIn('<CommandDefinition Id="Mscrm.', x)
        self.assertNotIn("Mscrm.AssignSelectedRecord", x)

    def test_generar_dos_veces_da_el_mismo_texto(self):
        self.assertEqual(self.xml(), self.xml())

    def test_un_hide_ya_declarado_no_se_pierde_cuando_el_boton_ya_no_se_ve(self):
        # La trampa: los ocultables salen del ribbon REAL, y un botón ya oculto
        # NO aparece ahí. Sin esto, la segunda corrida lo des-oculta. Pasó de
        # verdad en Dev el 2026-09-22: importar las 10 tablas revirtió la que
        # ya estaba hecha.
        primero, _ = imp.reemplazar_ribbon(CUST_CON_ENTIDADES, TABLA, self.xml())
        # Ahora el ribbon real ya no muestra `.Assign`: está oculto.
        ribbon_sin_assign = RIBBON.replace(f'<Button Id="Mscrm.HomepageGrid.{TABLA}.Assign" '
                                           'Command="Mscrm.AssignSelectedRecord" />', "")
        ocultables = imp.ocultables_de_la_tabla(primero, ribbon_sin_assign, TABLA, CAMBIO_RIBBON["ocultar"])
        self.assertIn(f"Mscrm.HomepageGrid.{TABLA}.Assign", ocultables)
        _, hubo = imp.reemplazar_ribbon(primero, TABLA, self.xml(ocultables=ocultables))
        self.assertFalse(hubo, "la segunda corrida no tiene que cambiar nada")

    def test_un_hide_que_el_playbook_ya_no_pide_se_suelta(self):
        primero, _ = imp.reemplazar_ribbon(CUST_CON_ENTIDADES, TABLA, self.xml())
        ocultables = imp.ocultables_de_la_tabla(primero, RIBBON, TABLA, [".Delete"])
        self.assertEqual([], ocultables)

    def test_se_reemplaza_solo_el_ribbon_de_la_tabla_nombrada(self):
        nuevo, hubo = imp.reemplazar_ribbon(CUST_CON_ENTIDADES, TABLA, self.xml())
        self.assertTrue(hubo)
        otra = nuevo[:nuevo.index(TABLA)]
        self.assertIn("<CustomActions />", otra)
        self.assertNotIn("Sanic.Mppp.Comandos", otra)

    def test_reemplazar_dos_veces_no_cambia_nada(self):
        una, hubo1 = imp.reemplazar_ribbon(CUST_CON_ENTIDADES, TABLA, self.xml())
        dos, hubo2 = imp.reemplazar_ribbon(una, TABLA, self.xml())
        self.assertTrue(hubo1)
        self.assertFalse(hubo2)

    def test_una_tabla_que_no_esta_en_la_solucion_queda_bloqueada(self):
        with self.assertRaises(imp.Bloqueado) as ctx:
            imp.reemplazar_ribbon(CUST_CON_ENTIDADES, "sanic_mppp_tbl_fantasma", self.xml())
        self.assertIn("no contiene la tabla", str(ctx.exception))

    def test_un_texto_con_comillas_no_rompe_el_atributo(self):
        import copy as _copy
        cambio = _copy.deepcopy(CAMBIO_RIBBON)
        cambio["botones"][0]["etiqueta"]["3082"] = 'Marcar "ya"'
        x = self.xml(cambio)
        self.assertIn("&quot;ya&quot;", x)
        self.assertNotIn('description="Marcar "ya""', x)


class ValidacionOffline(Base):
    def rechaza(self, componente, fragmento):
        centinela = FabricaCentinela()
        estado, _, detalle = imp.construir(self.escribir(componente), False, centinela)
        self.assertEqual("error", estado, detalle)
        self.assertIn(fragmento, detalle)
        self.assertFalse(centinela.llamada)

    def test_una_clase_desconocida_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["cambios"][0]["clase"] = "lo_que_sea"
        self.rechaza(malo, "las clases admitidas son")

    def test_una_tabla_sin_el_prefijo_del_publisher_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["cambios"][0]["tablas"] = ["account"]
        self.rechaza(malo, "no llevan el prefijo del publisher")

    def test_tablas_repetidas_se_rechazan(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["cambios"][0]["tablas"] = TABLAS + [TABLAS[0]]
        self.rechaza(malo, "tiene repetidos")

    def test_la_misma_app_en_dos_cambios_se_rechaza(self):
        malo = copy.deepcopy(COMPONENTE)
        malo["cambios"] = malo["cambios"] + copy.deepcopy(malo["cambios"])
        self.rechaza(malo, "aparece en más de un cambio")


class ContraElEntorno(Base):
    def test_si_ya_estan_las_tablas_no_se_importa_nada(self):
        # Reimportar la solución entera al pedo es lo más caro que puede hacer
        # esta herramienta.
        cliente = self.armar(ClienteSimulado(), puestas_antes=TABLAS)
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("ya_existia", estado, detalle)
        rutas = [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertNotIn("ImportSolution", rutas)
        self.assertNotIn("ExportSolution", rutas)

    def test_solo_verificar_nunca_importa(self):
        cliente = self.armar(ClienteSimulado(), puestas_antes=[])
        estado, _, detalle = imp.construir(self.escribir(), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertIn("le faltan", detalle)
        rutas = [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertNotIn("ImportSolution", rutas)

    def test_el_ciclo_completo_exporta_edita_importa_publica_y_verifica(self):
        cliente = self.armar(ClienteSimulado(), puestas_antes=[])
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("creado", estado, detalle)
        rutas = [l["ruta"] for l in cliente.llamadas if l["metodo"] == "POST"]
        self.assertEqual(["ExportSolution", "ImportSolution", "PublishXml"],
                         [r for r in rutas if r in ("ExportSolution", "ImportSolution", "PublishXml")])
        enviado = self.cust_enviado()
        for t in TABLAS:
            self.assertIn(f'type="1" schemaName="{t}"', enviado)

    def test_si_despues_de_importar_falta_una_tabla_no_se_informa_exito(self):
        # Un 204 de ImportSolution no prueba nada: se relee el entorno.
        cliente = self.armar(ClienteSimulado(), puestas_antes=[], puestas_despues=[TABLAS[0]])
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("le siguen faltando", detalle)
        self.assertIn(TABLAS[1], detalle)

    def test_si_el_import_deshabilita_un_step_la_herramienta_lo_vuelve_a_encender(self):
        # Pasó de verdad: el ImportSolution del 2026-09-22 dejó apagados los 20
        # steps del proyecto y nadie se enteró hasta el día siguiente. Un step
        # apagado NO da error: simplemente deja de correr.
        #
        # Detectarlo no alcanzaba. El 2026-09-23 la herramienta lo detectó TRES
        # veces en una hora y las tres hubo que reactivar a mano, leyendo el
        # mensaje y corriendo un script aparte. Un paso manual después de una
        # operación que ya falló es un paso que alguien va a saltear, y el costo
        # de saltearlo es la lógica de servidor muerta sin que nada avise.
        # La herramienta sabe EXACTAMENTE cuáles apagó: los reenciende ella.
        cliente = self.armar(ClienteSimulado(), puestas_antes=[],
                             steps_apagados_despues=["MPPP - Transicion de Fila - Update"])
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("creado", estado, detalle)
        self.assertIn("volvió a encender", detalle)
        self.assertIn("Transicion de Fila", detalle)

    def test_si_un_step_no_se_puede_reencender_eso_si_es_un_error(self):
        # Reparar puede fallar. Si falla, NO se informa éxito: quedaría lógica de
        # servidor apagada y el mensaje diciendo que todo salió bien.
        cliente = self.armar(ClienteSimulado(), puestas_antes=[],
                             steps_apagados_despues=["MPPP - Transicion de Fila - Update"],
                             falla_al_reencender=True)
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("NO SE PUDO VOLVER A ENCENDER", detalle)

    def test_un_componente_con_failure_en_el_importjob_no_se_informa_exito(self):
        cliente = self.armar(ClienteSimulado(), puestas_antes=[],
                             data='<result result="failure" errorcode="0x80040265" />')
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("result=\"failure\"", detalle)

    def armar_ribbon(self, cliente, despues_ok=True, cust=CUST_CON_ENTIDADES):
        armar_cliente_precondiciones_ok(cliente, IDENT)
        self.importado = False
        base = f"{IDENT['prefijo']}.{IDENT['abrev']}.{TABLA.split('_')[-1]}.digitada"
        # Después de importar, el ribbon trae los botones propios y ya no el genérico.
        despues = ("<RibbonDefinitions>"
                   # El botón sale con `ModernImage`, que es el icono que mira Unified
                   # Interface: sin él la verificación tiene que fallar, y este doble
                   # representa el ribbon TAL COMO QUEDA después de importar.
                   + "".join(f'<Button Id="{base}.{u}.Button" Command="{base}.Command" '
                             f'ModernImage="$webresource:{BOTON["icono"]}" />'
                             for u in BOTON["ubicaciones"])
                   + (f'<Button Id="Mscrm.HomepageGrid.{TABLA}.Edit" Command="Mscrm.EditSelectedRecord" />'
                      if despues_ok
                      else f'<Button Id="Mscrm.HomepageGrid.{TABLA}.Assign" Command="Mscrm.Assign" />')
                   + "</RibbonDefinitions>")
        cliente.responder("GET", lambda r: r.startswith("RetrieveEntityRibbon("),
                          lambda r, c, s: (200, {"CompressedEntityXml":
                                                 zip_ribbon(despues if self.importado else RIBBON)}, {}))
        cliente.responder("POST", "ExportSolution",
                          (200, {"ExportSolutionFile": base64.b64encode(zip_de(cust)).decode("ascii")}, {}))

        def importar(ruta, cuerpo, solucion):
            self.importado = True
            self.enviado = base64.b64decode(cuerpo["CustomizationFile"])
            return (204, {}, {})

        cliente.responder("POST", "ImportSolution", importar)
        cliente.responder("GET", lambda r: r.startswith("importjobs("),
                          (200, {"progress": 100.0, "data": ""}, {}))
        cliente.responder("POST", "PublishXml", (204, {}, {}))
        cliente.responder("GET", lambda r: r.startswith("sdkmessageprocessingsteps?"),
                          (200, {"value": []}, {}))
        cliente.responder("PATCH", lambda r: r.startswith("sdkmessageprocessingsteps("), (204, {}, {}))
        return cliente

    def test_el_ciclo_de_ribbon_importa_publica_la_tabla_y_verifica(self):
        cliente = self.armar_ribbon(ClienteSimulado())
        estado, _, detalle = imp.construir(self.escribir(comp(cambios=[CAMBIO_RIBBON])), False, lambda: cliente)
        self.assertEqual("creado", estado, detalle)
        # Un cambio de ribbon no se ve hasta publicar la TABLA.
        publicaciones = [l["cuerpo"]["ParameterXml"] for l in cliente.llamadas if l["ruta"] == "PublishXml"]
        self.assertTrue(any(f"<entity>{TABLA}</entity>" in p for p in publicaciones), publicaciones)
        self.assertIn("Sanic.Mppp.Comandos.digitada", self.cust_enviado())

    def test_si_el_generico_sigue_a_la_vista_despues_de_importar_no_se_informa_exito(self):
        cliente = self.armar_ribbon(ClienteSimulado(), despues_ok=False)
        estado, _, detalle = imp.construir(self.escribir(comp(cambios=[CAMBIO_RIBBON])), False, lambda: cliente)
        self.assertEqual("error", estado, detalle)
        self.assertIn("siguen a la vista", detalle)

    def test_solo_verificar_con_ribbon_nunca_importa(self):
        cliente = self.armar_ribbon(ClienteSimulado())
        estado, _, detalle = imp.construir(self.escribir(comp(cambios=[CAMBIO_RIBBON])), True, lambda: cliente)
        self.assertEqual("difiere", estado, detalle)
        self.assertNotIn("ImportSolution", [l["ruta"] for l in cliente.llamadas])

    def test_una_app_que_no_existe_en_el_entorno_queda_bloqueada_sin_exportar(self):
        cliente = ClienteSimulado()
        armar_cliente_precondiciones_ok(cliente, IDENT)
        cliente.responder("GET", lambda r: r.startswith("appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple"),
                          (200, {"value": []}, {}))
        estado, _, detalle = imp.construir(self.escribir(), False, lambda: cliente)
        self.assertEqual("bloqueado", estado, detalle)
        self.assertIn("hay que crearla primero", detalle)
        self.assertFalse(any(l["ruta"] == "ExportSolution" for l in cliente.llamadas))


if __name__ == "__main__":
    unittest.main()
