#!/usr/bin/env python3
"""Construye EL formulario de una tabla desde un playbook de tipo `formulario`:
el principal (`systemform` de tipo Main) o el de creación rápida (tipo Quick
Create), según la clave opcional `clase`. Contrato: `power-platform-construir`.

    python3 herramientas/construir/formulario.py <playbook.md> [--solo-verificar] [--completar]

Tres decisiones que valen la pena:

1. **ACTUALIZA el formulario principal que ya existe, no crea uno nuevo.** Cada
   tabla nace con un Main llamado "Information". Crear un segundo Main deja dos
   formularios compitiendo, que es el mismo problema que ya nos mordió con las
   vistas por defecto. Se busca el Main de la tabla y se le cambia el nombre y
   el `formxml`.

2. **El playbook no lleva XML, ni `classid`, ni etiquetas.** Declara secciones y
   columnas; la herramienta resuelve el tipo de cada columna contra la metadata
   y de ahí saca su control, y toma la etiqueta del `DisplayName` de la columna.
   Una etiqueta escrita a mano en el playbook se despega de la tabla el día que
   alguien renombra la columna.

3. **Los GUID del XML son deterministas** (derivados del nombre del formulario
   y de la posición del elemento). Si fueran aleatorios, cada corrida generaría
   un XML distinto, la herramienta diría "difiere" para siempre y nunca
   convergería.

Los `classid` NO son de memoria: se derivaron leyendo formularios reales del
entorno y cruzándolos contra el tipo de cada columna. La plataforma **no
normaliza** el `classid` (se probó con una sonda): guarda el que se le manda,
así que uno equivocado no falla al guardar y se ve roto recién en la app.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
import sys
import uuid
from xml.sax.saxutils import quoteattr

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

from _comun import (  # noqa: E402
    Bloqueado,
    ErrorEntorno,
    ErrorPlaybook,
    Rastro,
    comprobar_solucion_e_idioma,
    dividir_secciones,
    escribir_metadatos,
    exigir_forma,
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "formulario"
FORMULARIO_PRINCIPAL = 2  # Learn, systemform.type: 2 = Main
# Learn, systemform.type: 7 = Quick Create. Es el diálogo chico que abre
# `Xrm.Navigation.openForm({useQuickCreateForm: true})`: sin barra de comandos, sin
# pestañas y sin encabezado de registro — solo los campos y "Guardar y cerrar".
# La tabla tiene que tener `IsQuickCreateEnabled` en `true` o el formulario no se muestra.
FORMULARIO_CREACION_RAPIDA = 7
ACTIVO = 1

# Derivados empíricamente de formularios reales del entorno (2026-09-22), no de
# memoria: se leyeron los Main de account/contact/systemuser/task y se cruzó
# cada `classid` contra el `AttributeType` de su columna. El de File lo enseñó
# un formulario que armó el aprobador a mano, porque ninguna tabla del entorno
# tenía una columna de archivo en un formulario.
# La clave es `AttributeTypeName`, NO `AttributeType`: una columna de ARCHIVO
# reporta `AttributeType = "Virtual"`, igual que las columnas `*name` que
# acompañan a cada choice. Lo que las distingue es `AttributeTypeName`:
# `FileType` contra `VirtualType` (verificado en Dev el 2026-09-22).
CONTROL_POR_TIPO = {
    "StringType": "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}",
    "MemoType": "{E0DECE4B-6FC8-4a8f-A065-082708572369}",
    "PicklistType": "{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}",
    "StateType": "{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}",
    "StatusType": "{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}",
    "BooleanType": "{67FAC785-CD58-4f9f-ABB3-4B7DDC6ED5ED}",
    "LookupType": "{270BD3DB-D9AF-4782-9025-509E298DEC0A}",
    "OwnerType": "{270BD3DB-D9AF-4782-9025-509E298DEC0A}",
    "CustomerType": "{270BD3DB-D9AF-4782-9025-509E298DEC0A}",
    "DateTimeType": "{5B773807-9FB2-42db-97C3-7A91EFF8ADFF}",
    "IntegerType": "{C6D124CA-7EDA-4a60-AEA9-7FB8D318B68F}",
    "MoneyType": "{533B9E00-756B-4312-95A0-DC888637AC78}",
    "FileType": "{0A7FF475-B016-4687-9CE5-042BFDBD6519}",
}
CONTROL_SUBGRILLA = "{E7A81278-8635-4D9E-8D4D-59480B391C5B}"

# Espacio de nombres propio para los GUID deterministas del XML.
SEMILLA = uuid.UUID("7d1f6a52-0c34-4a8e-9f21-5e0a9c3b7d40")

LARGO_NOMBRE = 200

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "tabla": str, "descripcion": str, "pestana": str,
          "solo_lectura": bool, "encabezado": list, "secciones": list}

# `clase` es OPCIONAL y por omisión vale "principal": así los ocho playbooks que ya
# existían siguen valiendo sin tocarlos.
CLAVES_OPCIONALES = {"clase": str}
CLASES = {"principal": FORMULARIO_PRINCIPAL, "creacion_rapida": FORMULARIO_CREACION_RAPIDA}
CLASE_POR_DEFECTO = "principal"

C_FORM = "la consulta del formulario (GET systemforms)"
C_TABLA = "la consulta de la definición de la tabla (GET EntityDefinitions)"
C_COLUMNAS = "la consulta de las columnas de la tabla (GET EntityDefinitions/Attributes)"
# `classid` del control de web resource en un formulario. Sacado de formularios
# REALES del entorno (`mspp_webform`, `mspp_entityformmetadata`), no de memoria.
# Ojo con el casing mixto: la plataforma lo escribe así.
CONTROL_WEBRESOURCE = "{9FDF5F91-88B1-47f4-AD53-C11EFC01A01D}"
TIPO_HTML = 1            # webresourceset.webresourcetype: 1 = HTML

C_WEBRESOURCE = "la consulta del web resource del formulario (GET webresourceset)"

C_VISTA = "la consulta de la vista de la subgrilla (GET savedqueries)"
C_RELACION = "la consulta de la relación de la subgrilla (GET OneToManyRelationships)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"

COMPONENTE_TABLA = 1
INCLUYE_SUBCOMPONENTES = 0


def guid(*partes):
    """GUID determinista: la misma entrada da siempre el mismo valor, así el
    XML generado es estable entre corridas."""
    return "{" + str(uuid.uuid5(SEMILLA, "|".join(str(p) for p in partes))).upper() + "}"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def clase_de(datos):
    """El nombre de clase del playbook, con su valor por omisión."""
    return datos.get("clase", CLASE_POR_DEFECTO)


def tipo_de_formulario(datos):
    """El `systemform.type` que le corresponde. Es lo que separa un formulario
    principal de uno de creación rápida en TODAS las consultas y escrituras: leer el
    que no es hace que la herramienta crea que el formulario no existe y lo duplique."""
    return CLASES[clase_de(datos)]


def _validar_estructura(datos):
    faltan = sorted(set(CLAVES) - set(datos))
    sobran = sorted(set(datos) - set(CLAVES) - set(CLAVES_OPCIONALES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque del formulario no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque del formulario", clave, no_vacio=(tipo is str))
    for clave, tipo in CLAVES_OPCIONALES.items():
        if clave in datos:
            exigir_forma(datos[clave], tipo, "el bloque del formulario", clave, no_vacio=True)
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    clase = clase_de(datos)
    if clase not in CLASES:
        raise ErrorPlaybook(
            f"el bloque dice clase = {clase!r}; las que existen son {sorted(CLASES)}")

    if clase == "creacion_rapida":
        # Un formulario de creación rápida no tiene encabezado de registro, ni subgrillas, ni
        # controles de web resource: la plataforma los ignora. Se rechaza en vez de generarlos y
        # dejar que el usuario descubra en pantalla que la mitad del playbook no hizo nada.
        if datos["encabezado"]:
            raise ErrorPlaybook(
                "un formulario de creación rápida no lleva encabezado: 'encabezado' tiene que ir vacío")
        for i, s in enumerate(datos["secciones"]):
            if "campos" not in s:
                raise ErrorPlaybook(
                    f"la sección {i} no es de campos; un formulario de creación rápida solo admite campos")

    exigir_sin_tildes(datos["nombre"], "nombre")
    if len(datos["nombre"]) > LARGO_NOMBRE:
        raise ErrorPlaybook(f"nombre tiene {len(datos['nombre'])} caracteres; el máximo es {LARGO_NOMBRE}")
    exigir_sin_tildes(datos["pestana"], "pestana")

    encabezado = exigir_forma(datos["encabezado"], [str], "el bloque del formulario", "encabezado")
    if len(encabezado) > 3:
        # El header de un formulario principal tiene exactamente tres huecos.
        raise ErrorPlaybook(f"el encabezado trae {len(encabezado)} columnas y solo entran 3")

    vistas, secciones = set(), exigir_forma(datos["secciones"], list, "el bloque del formulario", "secciones",
                                            no_vacio=True)
    columnas_vistas = set(encabezado)
    for i, s in enumerate(secciones):
        aqui = f"la sección [{i}]"
        exigir_forma(s, dict, aqui, "seccion")
        sobran = sorted(set(s) - {"titulo", "campos", "subgrilla", "webresource"})
        if sobran or "titulo" not in s:
            raise ErrorPlaybook(f"{aqui}: se admite {{titulo, campos, subgrilla, webresource}}; falta 'titulo' o sobra {sobran}")
        exigir_forma(s["titulo"], str, aqui, "titulo", no_vacio=True)
        exigir_sin_tildes(s["titulo"], f"{aqui}.titulo")
        cuantos = sum(1 for c in ("campos", "subgrilla", "webresource") if c in s)
        if cuantos != 1:
            raise ErrorPlaybook(
                f"{aqui}: una sección lleva 'campos', 'subgrilla' O 'webresource', exactamente uno")
        if "webresource" in s:
            wr = exigir_forma(s["webresource"], dict, aqui, "webresource")
            faltan_wr = sorted({"nombre", "alto"} - set(wr))
            sobran_wr = sorted(set(wr) - {"nombre", "alto"})
            if faltan_wr or sobran_wr:
                raise ErrorPlaybook(f"{aqui}.webresource: faltan {faltan_wr}, sobran {sobran_wr}")
            exigir_forma(wr["nombre"], str, f"{aqui}.webresource", "nombre", no_vacio=True)
            exigir_forma(wr["alto"], int, f"{aqui}.webresource", "alto")
            if not 1 <= wr["alto"] <= 20:
                raise ErrorPlaybook(f"{aqui}.webresource: 'alto' va en filas, entre 1 y 20")

        if "campos" in s:
            for columna in exigir_forma(s["campos"], [str], aqui, "campos", no_vacio=True):
                if columna in columnas_vistas:
                    raise ErrorPlaybook(f"{aqui}: la columna '{columna}' ya está en el formulario")
                columnas_vistas.add(columna)
        elif "webresource" in s:
            pass   # ya quedó validado arriba
        else:
            sg = exigir_forma(s["subgrilla"], dict, aqui, "subgrilla")
            faltan_sg = sorted({"tabla", "lookup", "vista"} - set(sg))
            sobran_sg = sorted(set(sg) - {"tabla", "lookup", "vista"})
            if faltan_sg or sobran_sg:
                raise ErrorPlaybook(f"{aqui}.subgrilla: faltan {faltan_sg}, sobran {sobran_sg}")
            for campo in ("tabla", "lookup", "vista"):
                exigir_forma(sg[campo], str, f"{aqui}.subgrilla", campo, no_vacio=True)
            huella = (sg["tabla"], sg["lookup"])
            if huella in vistas:
                raise ErrorPlaybook(f"{aqui}: ya hay otra subgrilla sobre {sg['tabla']} por '{sg['lookup']}'")
            vistas.add(huella)


def validar_playbook(datos):
    _validar_estructura(datos)


# ---------------------------------------------------------------------------
# Generación del formxml
# ---------------------------------------------------------------------------
def _celda(datos, ruta, columna, etiqueta, classid, deshabilitado):
    return (
        f'<cell id="{guid(datos["nombre"], ruta, "cell")}" locklevel="0" colspan="1" rowspan="1" '
        f'labelid="{guid(datos["nombre"], ruta, "label")}">'
        f'<labels><label description={quoteattr(etiqueta)} languagecode="1033" /></labels>'
        f'<control id={quoteattr(columna)} classid="{classid}" datafieldname={quoteattr(columna)} '
        f'disabled="{str(bool(deshabilitado)).lower()}" /></cell>')


def _celda_subgrilla(datos, ruta, nombre, etiqueta, tabla_destino, vista_id, relacion):
    return (
        f'<cell id="{guid(datos["nombre"], ruta, "cell")}" locklevel="0" colspan="1" rowspan="6" auto="false" '
        f'labelid="{guid(datos["nombre"], ruta, "label")}">'
        f'<labels><label description={quoteattr(etiqueta)} languagecode="1033" /></labels>'
        f'<control indicationOfSubgrid="true" id={quoteattr(nombre)} classid="{CONTROL_SUBGRILLA}"><parameters>'
        "<RecordsPerPage>10</RecordsPerPage><AutoExpand>Fixed</AutoExpand>"
        "<EnableQuickFind>false</EnableQuickFind><EnableViewPicker>false</EnableViewPicker>"
        "<EnableChartPicker>false</EnableChartPicker><ChartGridMode>Grid</ChartGridMode>"
        f"<TargetEntityType>{tabla_destino}</TargetEntityType>"
        f"<ViewId>{vista_id}</ViewId><ViewIds>{vista_id}</ViewIds>"
        f"<RelationshipName>{relacion}</RelationshipName>"
        "</parameters></control></cell>")


def _celda_webresource(datos, ruta, nombre_control, etiqueta, web_resource, alto):
    """El control de web resource. `PassParameters` en true es lo que hace que
    la página reciba `id` y `typename` del registro en la cadena de consulta:
    sin eso no sabe qué Solicitud mostrar."""
    return (
        f'<cell id="{guid(datos["nombre"], ruta, "cell")}" locklevel="0" colspan="1" rowspan="{alto}" '
        f'auto="false" showlabel="false" labelid="{guid(datos["nombre"], ruta, "label")}">'
        f'<labels><label description={quoteattr(etiqueta)} languagecode="1033" /></labels>'
        f'<control id={quoteattr(nombre_control)} classid="{CONTROL_WEBRESOURCE}"><parameters>'
        f"<Url>{web_resource}</Url>"
        "<PassParameters>true</PassParameters>"
        "<Security>false</Security><Scrolling>auto</Scrolling><Border>false</Border>"
        "</parameters></control></cell>")


def formxml(datos, etiquetas, controles, subgrillas):
    """El `formxml` completo. `etiquetas` y `controles` vienen de la metadata;
    `subgrillas` trae, por sección, el id de vista y el nombre de relación ya
    resueltos contra el entorno."""
    solo_lectura = datos["solo_lectura"]
    partes = ['<form headerdensity="HighWithControls"><tabs>',
              f'<tab verticallayout="true" id="{guid(datos["nombre"], "tab")}" IsUserDefined="1" '
              f'labelid="{guid(datos["nombre"], "tab", "label")}">',
              f'<labels><label description={quoteattr(datos["pestana"])} languagecode="1033" /></labels>',
              '<columns><column width="100%"><sections>']

    for i, s in enumerate(datos["secciones"]):
        ruta_sec = f"sec{i}"
        partes.append(
            f'<section showlabel="true" showbar="false" IsUserDefined="0" '
            f'id="{guid(datos["nombre"], ruta_sec)}" labelid="{guid(datos["nombre"], ruta_sec, "label")}" '
            f'columns="1" labelwidth="115" celllabelalignment="Left" celllabelposition="Left">'
            f'<labels><label description={quoteattr(s["titulo"])} languagecode="1033" /></labels><rows>')
        if "campos" in s:
            for j, columna in enumerate(s["campos"]):
                partes.append("<row>" + _celda(datos, f"{ruta_sec}.{j}", columna, etiquetas[columna],
                                               controles[columna], solo_lectura) + "</row>")
        elif "webresource" in s:
            wr = s["webresource"]
            partes.append("<row>" + _celda_webresource(
                datos, f"{ruta_sec}.wr", f"WebResource_{i}", s["titulo"],
                wr["nombre"], wr["alto"]) + "</row>")
        else:
            sg = s["subgrilla"]
            resuelta = subgrillas[i]
            partes.append("<row>" + _celda_subgrilla(
                datos, f"{ruta_sec}.grid", f"Subgrid_{i}", s["titulo"], sg["tabla"],
                resuelta["vista_id"], resuelta["relacion"]) + "</row>")
        partes.append("</rows></section>")

    partes.append("</sections></column></columns></tab></tabs>")

    if clase_de(datos) == "creacion_rapida":
        # Sin `<header>`: un formulario de creación rápida no muestra encabezado de registro.
        # Es justamente lo que lo hace chico.
        partes.append("</form>")
        return "".join(partes)

    # El header tiene exactamente tres huecos; los que no se usan van vacíos.
    partes.append(f'<header id="{guid(datos["nombre"], "header")}" celllabelposition="Top" columns="111" '
                  'labelwidth="115" celllabelalignment="Left"><rows><row>')
    for k in range(3):
        if k < len(datos["encabezado"]):
            columna = datos["encabezado"][k]
            partes.append(_celda(datos, f"hdr{k}", columna, etiquetas[columna], controles[columna], solo_lectura))
        else:
            partes.append(f'<cell id="{guid(datos["nombre"], f"hdr{k}")}" showlabel="false" '
                          f'labelid="{guid(datos["nombre"], f"hdr{k}", "label")}">'
                          '<labels><label description="" languagecode="1033" /></labels></cell>')
    partes.append("</row></rows></header></form>")
    return "".join(partes)


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _columnas_de(dv, tabla):
    """Tipo y etiqueta de cada columna, desde la metadata. La etiqueta sale del
    `DisplayName`: una escrita a mano en el playbook se despega de la tabla."""
    ruta = (f"EntityDefinitions(LogicalName='{tabla}')/Attributes"
            "?$select=LogicalName,AttributeTypeName,DisplayName")
    cuerpo = leer_entorno(dv, ruta, C_COLUMNAS, admite_404=True)
    if cuerpo is None:
        raise Bloqueado(f"la tabla '{tabla}' no existe en el entorno")
    tipos, etiquetas = {}, {}
    for a in exigir_forma(cuerpo.get("value"), [dict], C_COLUMNAS, "value", no_vacio=True):
        nombre = exigir_forma(a.get("LogicalName"), str, C_COLUMNAS, "LogicalName", no_vacio=True)
        tipos[nombre] = (a.get("AttributeTypeName") or {}).get("Value")
        visible = ((a.get("DisplayName") or {}).get("UserLocalizedLabel") or {}).get("Label")
        etiquetas[nombre] = visible or nombre
    return tipos, etiquetas


def _vista_id(dv, tabla, nombre_vista):
    ruta = f"savedqueries?$select=savedqueryid&$filter=name eq '{nombre_vista}' and returnedtypecode eq '{tabla}'"
    cuerpo = leer_entorno(dv, ruta, C_VISTA)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_VISTA, "value")
    if len(filas) != 1:
        raise Bloqueado(
            f"la subgrilla pide la vista '{nombre_vista}' sobre '{tabla}' y hay {len(filas)}; hay que crearla primero")
    return "{" + exigir_forma(filas[0].get("savedqueryid"), str, C_VISTA, "savedqueryid", no_vacio=True).upper() + "}"


def _relacion(dv, tabla_padre, tabla_hija, lookup):
    ruta = (f"EntityDefinitions(LogicalName='{tabla_padre}')/OneToManyRelationships"
            f"?$select=SchemaName,ReferencingEntity,ReferencingAttribute")
    cuerpo = leer_entorno(dv, ruta, C_RELACION)
    for r in exigir_forma(cuerpo.get("value"), [dict], C_RELACION, "value"):
        if r.get("ReferencingEntity") == tabla_hija and r.get("ReferencingAttribute") == lookup:
            return exigir_forma(r.get("SchemaName"), str, C_RELACION, "SchemaName", no_vacio=True)
    raise Bloqueado(
        f"no hay relación de '{tabla_padre}' a '{tabla_hija}' por el lookup '{lookup}'; la subgrilla no se puede armar")


def _exigir_webresource(dv, nombre):
    ruta = f"webresourceset?$select=name,webresourcetype&$filter=name eq '{nombre}'"
    filas = exigir_forma(leer_entorno(dv, ruta, C_WEBRESOURCE).get("value"), [dict], C_WEBRESOURCE, "value")
    if len(filas) != 1:
        raise Bloqueado(
            f"el formulario referencia el web resource '{nombre}' y en el entorno hay {len(filas)}; "
            "hay que crearlo primero (`web_resource.py`)")
    if filas[0].get("webresourcetype") != TIPO_HTML:
        raise Bloqueado(
            f"el web resource '{nombre}' no es HTML (webresourcetype "
            f"{filas[0].get('webresourcetype')}): un control de formulario solo muestra HTML")


def _leer_formulario(dv, tabla, tipo):
    # El filtro por `type` es obligatorio: una tabla puede tener un formulario principal Y uno
    # de creación rápida, y leer el que no es haría que la herramienta crea que el suyo no
    # existe y lo duplique.
    ruta = ("systemforms?$select=formid,name,description,formxml,type,formactivationstate,ismanaged"
            f"&$filter=objecttypecode eq '{tabla}' and type eq {tipo}")
    cuerpo = leer_entorno(dv, ruta, C_FORM)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_FORM, "value")
    if len(filas) > 1:
        raise ErrorEntorno(
            f"{C_FORM} devolvió {len(filas)} formularios principales de '{tabla}'; se esperaba uno solo. "
            "Con dos Main compitiendo, la plataforma elige uno y el playbook deja de mandar")
    return filas[0] if filas else None


def _normalizar_xml(texto):
    return "".join((texto or "").split())


def _tabla_en_la_solucion(dv, solution_id, metadata_id):
    """Un formulario no tiene fila propia en `solutioncomponents`: viaja dentro
    de su tabla, igual que una vista o una clave alternativa."""
    ruta = ("solutioncomponents?$select=componenttype,rootcomponentbehavior,objectid"
            f"&$filter=_solutionid_value eq {solution_id} and objectid eq {metadata_id} "
            f"and componenttype eq {COMPONENTE_TABLA}")
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _publicar(dv, tabla, dormir):
    cuerpo = {"ParameterXml": f"<importexportxml><entities><entity>{tabla}</entity></entities></importexportxml>"}
    return escribir_metadatos(dv, "POST", "PublishXml", cuerpo, dormir=dormir)


def _diferencias(datos, form, xml):
    difs, corregibles = [], {}
    for campo, valor in (("name", datos["nombre"]), ("description", datos["descripcion"])):
        if form.get(campo) != valor:
            difs.append(f"{campo} es {form.get(campo)!r} y el playbook dice {valor!r}")
            corregibles[campo] = valor
    if _normalizar_xml(form.get("formxml")) != _normalizar_xml(xml):
        difs.append("el formxml no coincide con el que genera el playbook")
        corregibles["formxml"] = xml
    if form.get("formactivationstate") != ACTIVO:
        difs.append(f"el formulario está inactivo (formactivationstate {form.get('formactivationstate')!r})")
        corregibles["formactivationstate"] = ACTIVO
    if form.get("ismanaged"):
        difs.append("el formulario está managed en este entorno; no se toca desde acá")
        corregibles.clear()
    return difs, corregibles


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)

    ruta_tabla = f"EntityDefinitions(LogicalName='{datos['tabla']}')?$select=MetadataId"
    cuerpo = leer_entorno(dv, ruta_tabla, C_TABLA, admite_404=True)
    if cuerpo is None:
        raise Bloqueado(f"la tabla '{datos['tabla']}' no existe en el entorno")
    metadata_id = exigir_forma(cuerpo.get("MetadataId"), str, C_TABLA, "MetadataId", no_vacio=True)

    tipos, etiquetas = _columnas_de(dv, datos["tabla"])
    declaradas = list(datos["encabezado"]) + [c for s in datos["secciones"] for c in s.get("campos", [])]
    faltantes = [c for c in declaradas if c not in tipos]
    if faltantes:
        raise Bloqueado(f"el formulario declara columnas que la tabla no tiene: {faltantes}")
    sin_control = sorted({tipos[c] for c in declaradas if tipos[c] not in CONTROL_POR_TIPO})
    if sin_control:
        raise Bloqueado(
            f"no se sabe qué control usa un tipo de columna {sin_control}; los conocidos son "
            f"{sorted(CONTROL_POR_TIPO)}. No se inventa un classid: la plataforma lo guarda tal cual y se ve roto en la app")
    controles = {c: CONTROL_POR_TIPO[tipos[c]] for c in declaradas}

    subgrillas = {}
    for i, s in enumerate(datos["secciones"]):
        if "subgrilla" in s:
            sg = s["subgrilla"]
            subgrillas[i] = {"vista_id": _vista_id(dv, sg["tabla"], sg["vista"]),
                             "relacion": _relacion(dv, datos["tabla"], sg["tabla"], sg["lookup"])}
        elif "webresource" in s:
            # Un `<Url>` que no existe no da error al guardar: el formulario
            # abre con un recuadro vacío y nadie se entera hasta que alguien
            # lo mira. Se comprueba antes.
            _exigir_webresource(dv, s["webresource"]["nombre"])

    xml = formxml(datos, etiquetas, controles, subgrillas)
    form = _leer_formulario(dv, datos["tabla"], tipo_de_formulario(datos))
    hubo_escritura = False

    if form is None:
        if solo_verificar:
            return "difiere", componente, f"la tabla '{datos['tabla']}' no tiene formulario principal"
        cuerpo = {"name": datos["nombre"], "description": datos["descripcion"],
                  "objecttypecode": datos["tabla"], "type": tipo_de_formulario(datos),
                  "formxml": xml, "formactivationstate": ACTIVO}
        est, resp, _ = escribir_metadatos(dv, "POST", "systemforms", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta devolvió HTTP {est} (se esperaba 204): {resp}"
        form = _leer_formulario(dv, datos["tabla"], tipo_de_formulario(datos))
        if form is None:
            return "error", componente, "el alta no dio error pero el formulario no aparece al releer"
        hubo_escritura = True
    else:
        difs, corregibles = _diferencias(datos, form, xml)
        if corregibles and not solo_verificar:
            id_form = exigir_forma(form.get("formid"), str, C_FORM, "formid", no_vacio=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"systemforms({id_form})", corregibles, dormir=dormir, solucion=solucion)
            if est not in (200, 204):
                return "error", componente, f"la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
            est, resp, _ = _publicar(dv, datos["tabla"], dormir)
            if est not in (200, 204):
                return "error", componente, f"se corrigió pero la publicación devolvió HTTP {est}: {resp}"
            form = _leer_formulario(dv, datos["tabla"], tipo_de_formulario(datos))
            hubo_escritura = True

    id_form = exigir_forma(form.get("formid"), str, C_FORM, "formid", no_vacio=True)
    difs, _ = _diferencias(datos, form, xml)
    fila = _tabla_en_la_solucion(dv, solution_id, metadata_id)
    if fila is None:
        difs.append(f"la tabla '{datos['tabla']}' no figura en la solución (solutionid {solution_id}), "
                    "así que el formulario no viajaría con ella")
    elif fila.get("rootcomponentbehavior") != INCLUYE_SUBCOMPONENTES:
        difs.append(f"la tabla está en la solución con rootcomponentbehavior {fila.get('rootcomponentbehavior')!r} "
                    f"y no {INCLUYE_SUBCOMPONENTES}: el formulario no viajaría con ella")

    if difs:
        estado = "error" if hubo_escritura else "difiere"
        prefijo = "se escribió pero no quedó bien: " if hubo_escritura else ""
        return estado, componente, prefijo + "; ".join(difs)

    cuantas = sum(len(s.get("campos", [])) for s in datos["secciones"])
    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"formid {id_form}, {len(datos['secciones'])} secciones, {cuantas} campos, "
        f"{len(subgrillas)} subgrillas, {len(datos['encabezado'])} en el encabezado"
        f"{', todo de solo lectura' if datos['solo_lectura'] else ''}; viaja dentro de la tabla")


def construir(ruta_playbook, solo_verificar, fabrica_cliente, completar=False, dormir=None):
    """Nunca lanza: siempre devuelve `(estado, componente, detalle)`."""
    if dormir is None:
        import time

        dormir = time.sleep
    componente = os.path.basename(ruta_playbook)
    paso = "leer el playbook"
    try:
        secciones = dividir_secciones(leer_texto(ruta_playbook))
        paso = "leer el bloque '## 2. Qué se crea'"
        datos = obtener_componente(secciones, TIPO)
        if isinstance(datos.get("nombre"), str):
            componente = datos["nombre"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque del formulario"
        validar_playbook(datos)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} nombre={componente}")
    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, completar, componente, dormir)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except ErrorEntorno as e:
        return "error", componente, str(e)
    except Exception as e:
        return "error", componente, f"fallo inesperado hablando con Dataverse, durante {rastro.en_curso}: {type(e).__name__}: {e}"


def main():
    argv = sys.argv[1:]
    rutas = [a for a in argv if not a.startswith("--")]
    banderas = {a for a in argv if a.startswith("--")}
    desconocidas = sorted(banderas - {"--solo-verificar", "--completar"})
    if len(rutas) != 1 or desconocidas:
        return salida(
            "error", "desconocido",
            "uso incorrecto: formulario.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
