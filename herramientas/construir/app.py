#!/usr/bin/env python3
"""Construye la app model-driven y su sitemap, desde un playbook de tipo `app`.
Contrato: `power-platform-construir`; Learn, "Create, manage, and publish
model-driven apps using code".

    python3 herramientas/construir/app.py <playbook.md> [--solo-verificar] [--completar]

Van en UNA herramienta porque son una sola cosa: un sitemap sin app no lo abre
nadie, y una app sin sitemap no navega a ningún lado. La secuencia
(`sitemap` → `appmodule` → `AddAppComponents` → roles → `ValidateApp` →
`PublishXml`) conviene que se ejecute junta y se verifique junta.

El `sitemapxml` se genera del playbook. Su esquema no está publicado en Learn:
se sacó leyendo un sitemap real del entorno (2026-09-22).

Dos cosas que el playbook declara y la herramienta resuelve contra el entorno:
los íconos, que se referencian como `/WebResources/<nombre>.svg`, y las vistas,
que se resuelven a su `savedqueryid`.

**Entradas con vista propia**: un `SubArea` con `Entity=` abre la vista POR
DEFECTO de esa tabla. Como el sitemap tiene cuatro entradas sobre la misma
tabla (Por digitar, Devueltas, Por aprobar, Filas), las que nombran una vista
se arman con `Url` apuntando a su `viewid`. Ese patrón NO se pudo verificar
contra ningún sitemap del entorno: hay que mirarlo en la app una vez.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
import sys
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

TIPO = "app"

# Copiados tal cual de un sitemap real del entorno. `ToolTipResourseId` va con
# esa errata: así está en el esquema de la plataforma.
CLIENTES = "All,Outlook,OutlookLaptopClient,OutlookWorkstationClient,Web"
SKU = "All,OnPremise,Live,SPLA"
RECURSO_AREA = "SitemapDesigner.NewTitle"
RECURSO_GRUPO = "SitemapDesigner.NewGroup"
RECURSO_TOOLTIP = "SitemapDesigner.Unknown"

CLIENTE_UNIFICADO = 4    # appmodule.clienttype: 4 = Unified Interface, 2 = cliente web clásico
FORMFACTOR_TODOS = 1     # el valor que llevan todas las apps del entorno
NAVEGACION_AREAS = 0     # navegación por áreas del sitemap

COMPONENTE_SITEMAP = 62  # Learn, AppModuleComponent
VISTA_LISTA = 1039       # viewtype de una vista de lista en /main.aspx

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "uniquename": str, "descripcion": str, "icono": str,
          "sitemap": str, "idiomas": list, "roles": list, "tablas": list, "areas": list}

C_APP = "la consulta de la app (GET appmodules)"
C_SITEMAP = "la consulta del sitemap (GET sitemaps)"
C_RECURSO = "la consulta del icono (GET webresourceset)"
C_VISTA = "la consulta de una vista del sitemap (GET savedqueries)"
C_ROL = "la consulta de un rol (GET roles)"
C_COMPONENTES = "la consulta de los componentes de la app (GET RetrieveAppComponents)"

COMPONENTE_TABLA = 1  # appmodulecomponent.componenttype


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_titulos(titulos, idiomas, donde):
    exigir_forma(titulos, dict, donde, "titulo")
    faltan = [str(i) for i in idiomas if str(i) not in titulos]
    sobran = sorted(set(titulos) - {str(i) for i in idiomas})
    if faltan or sobran:
        # `01-convenciones.md`: las etiquetas embebidas en el XML del sitemap
        # van UNA POR CADA IDIOMA, porque ahí la plataforma no sustituye.
        raise ErrorPlaybook(
            f"{donde}: el titulo tiene que traer un texto por cada idioma {idiomas}; faltan {faltan}, sobran {sobran}")
    for lcid, texto in titulos.items():
        exigir_forma(texto, str, donde, f"titulo[{lcid}]", no_vacio=True)


def _validar_estructura(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque de la app no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque de la app", clave, no_vacio=True)
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    exigir_sin_tildes(datos["nombre"], "nombre")
    for clave, patron in (("uniquename", f"{identidad['prefijo']}_{identidad['abrev']}_mda_"),
                          ("sitemap", f"{identidad['prefijo']}_{identidad['abrev']}_sm_")):
        if not datos[clave].startswith(patron):
            raise ErrorPlaybook(f"{clave} = {datos[clave]!r} no sigue el patrón {patron}<nombre> (`01-convenciones.md` §2)")

    idiomas = exigir_forma(datos["idiomas"], [int], "el bloque de la app", "idiomas", no_vacio=True)
    exigir_forma(datos["roles"], [str], "el bloque de la app", "roles", no_vacio=True)
    exigir_forma(datos["tablas"], [str], "el bloque de la app", "tablas", no_vacio=True)

    ids, entradas = set(), 0
    for i, area in enumerate(exigir_forma(datos["areas"], list, "el bloque de la app", "areas", no_vacio=True)):
        aqui = f"el area [{i}]"
        exigir_forma(area, dict, aqui, "area")
        if sorted(area) != ["grupos", "titulo"]:
            raise ErrorPlaybook(f"{aqui}: se admite exactamente {{titulo, grupos}}")
        _validar_titulos(area["titulo"], idiomas, aqui)
        for j, grupo in enumerate(exigir_forma(area["grupos"], list, aqui, "grupos", no_vacio=True)):
            donde_g = f"{aqui}.grupo[{j}]"
            exigir_forma(grupo, dict, donde_g, "grupo")
            if sorted(grupo) != ["entradas", "titulo"]:
                raise ErrorPlaybook(f"{donde_g}: se admite exactamente {{titulo, entradas}}")
            _validar_titulos(grupo["titulo"], idiomas, donde_g)
            for k, e in enumerate(exigir_forma(grupo["entradas"], list, donde_g, "entradas", no_vacio=True)):
                donde_e = f"{donde_g}.entrada[{k}]"
                exigir_forma(e, dict, donde_e, "entrada")
                sobran_e = sorted(set(e) - {"id", "titulo", "tabla", "vista", "icono"})
                faltan_e = sorted({"id", "titulo", "tabla", "icono"} - set(e))
                if faltan_e or sobran_e:
                    raise ErrorPlaybook(f"{donde_e}: faltan {faltan_e}, sobran {sobran_e}")
                for campo in ("id", "tabla", "icono"):
                    exigir_forma(e[campo], str, donde_e, campo, no_vacio=True)
                if "vista" in e:
                    exigir_forma(e["vista"], str, donde_e, "vista", no_vacio=True)
                _validar_titulos(e["titulo"], idiomas, donde_e)
                if e["id"] in ids:
                    raise ErrorPlaybook(f"{donde_e}: el id '{e['id']}' está repetido en el sitemap")
                ids.add(e["id"])
                if e["tabla"] not in datos["tablas"]:
                    raise ErrorPlaybook(
                        f"{donde_e}: la entrada abre '{e['tabla']}', que no está en la lista de tablas de la app")
                entradas += 1
    if entradas == 0:
        raise ErrorPlaybook("el sitemap no tiene ninguna entrada")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)


# ---------------------------------------------------------------------------
# Generación del sitemapxml
# ---------------------------------------------------------------------------
def _titulos(titulos, idiomas):
    partes = "".join(f'<Title LCID="{i}" Title={quoteattr(titulos[str(i)])} />' for i in idiomas)
    return f"<Titles>{partes}</Titles>"


def sitemapxml(datos, iconos, vistas):
    """`iconos` mapea nombre de web resource → ruta `/WebResources/...`;
    `vistas` mapea (tabla, nombre de vista) → savedqueryid."""
    idiomas = datos["idiomas"]
    partes = ['<SiteMap IntroducedVersion="7.0.0.0">']
    for i, area in enumerate(datos["areas"]):
        partes.append(
            f'<Area Id="area_{i}" ResourceId="{RECURSO_AREA}" DescriptionResourceId="{RECURSO_AREA}" '
            f'ShowGroups="true" IntroducedVersion="7.0.0.0">' + _titulos(area["titulo"], idiomas))
        for j, grupo in enumerate(area["grupos"]):
            partes.append(
                f'<Group Id="group_{i}_{j}" ResourceId="{RECURSO_GRUPO}" DescriptionResourceId="{RECURSO_GRUPO}" '
                f'IntroducedVersion="7.0.0.0" IsProfile="false" ToolTipResourseId="{RECURSO_TOOLTIP}">'
                + _titulos(grupo["titulo"], idiomas))
            for e in grupo["entradas"]:
                icono = iconos[e["icono"]]
                comun = (f'Id={quoteattr(e["id"])} VectorIcon={quoteattr(icono)} Icon={quoteattr(icono)} '
                         f'Client="{CLIENTES}" AvailableOffline="true" PassParams="false" Sku="{SKU}"')
                if "vista" in e:
                    # `Entity=` abriria la vista POR DEFECTO de la tabla; con
                    # cuatro entradas sobre la misma tabla, las cuatro abririan
                    # lo mismo. Por eso las que nombran una vista van por Url.
                    vista_id = vistas[(e["tabla"], e["vista"])]
                    url = (f"/main.aspx?etn={e['tabla']}&amp;pagetype=entitylist"
                           f"&amp;viewid=%7b{vista_id}%7d&amp;viewtype={VISTA_LISTA}")
                    partes.append(f'<SubArea {comun} Url="{url}">' + _titulos(e["titulo"], idiomas) + "</SubArea>")
                else:
                    partes.append(f'<SubArea {comun} Entity={quoteattr(e["tabla"])}>'
                                  + _titulos(e["titulo"], idiomas) + "</SubArea>")
            partes.append("</Group>")
        partes.append("</Area>")
    partes.append("</SiteMap>")
    return "".join(partes)


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _icono(dv, nombre):
    cuerpo = leer_entorno(dv, f"webresourceset?$select=name&$filter=name eq '{nombre}'", C_RECURSO)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_RECURSO, "value")
    if len(filas) != 1:
        raise Bloqueado(f"el icono '{nombre}' no existe como web resource (hay {len(filas)}); hay que crearlo primero")
    return "/WebResources/" + nombre


def _vista(dv, tabla, nombre):
    ruta = f"savedqueries?$select=savedqueryid&$filter=name eq '{nombre}' and returnedtypecode eq '{tabla}'"
    cuerpo = leer_entorno(dv, ruta, C_VISTA)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_VISTA, "value")
    if len(filas) != 1:
        raise Bloqueado(f"la entrada de sitemap pide la vista '{nombre}' sobre '{tabla}' y hay {len(filas)}")
    return exigir_forma(filas[0].get("savedqueryid"), str, C_VISTA, "savedqueryid", no_vacio=True)


def _rol(dv, nombre):
    cuerpo = leer_entorno(dv, f"roles?$select=roleid,name&$filter=name eq '{nombre}'", C_ROL)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_ROL, "value")
    if not filas:
        raise Bloqueado(f"el rol '{nombre}' no existe; la app no se puede asociar a un rol que no está")
    # Un rol existe una vez por unidad de negocio: alcanza con el de la raíz.
    return exigir_forma(filas[0].get("roleid"), str, C_ROL, "roleid", no_vacio=True)


def _leer_sitemap(dv, unico):
    # OJO: un GET sin filtro devuelve SOLO el sitemap clasico, aunque el
    # entorno tenga varios de apps (verificado en Dev). Siempre con filtro.
    ruta = f"sitemaps?$select=sitemapid,sitemapnameunique,sitemapxml,isappaware&$filter=sitemapnameunique eq '{unico}'"
    cuerpo = leer_entorno(dv, ruta, C_SITEMAP)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_SITEMAP, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_SITEMAP} devolvió {len(filas)} sitemaps llamados '{unico}'; el nombre único es único")
    return filas[0] if filas else None


def _leer_app(dv, unico):
    # OJO: `GET appmodules?` devuelve SOLO la capa PUBLICADA. Una app recién
    # creada nace con `componentstate = 1` (sin publicar) y no aparece ahí,
    # aunque exista. Si la herramienta no la ve, la vuelve a crear y la
    # plataforma responde `HTTP 400 {"error":"-2147155681"}`, que significa
    # "unique name duplicado" y no lo dice por ningún lado (verificado en Dev
    # el 2026-09-22 creando dos veces el mismo unique name). Por eso se lee
    # SIEMPRE por la capa sin publicar, que devuelve las dos.
    ruta = ("appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()"
            "?$select=appmoduleid,name,uniquename,description,webresourceid,ismanaged,componentstate"
            f"&$filter=uniquename eq '{unico}'")
    cuerpo = leer_entorno(dv, ruta, C_APP)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_APP, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_APP} devolvió {len(filas)} apps con unique name '{unico}'")
    return filas[0] if filas else None


def _tablas_de_la_app(dv, id_app):
    """Nombres lógicos de las tablas que la app REALMENTE incluye.
    `RetrieveAppComponents` es la función documentada para esto; el `objectid`
    de un componente de tipo 1 es el `MetadataId` de la tabla."""
    cuerpo = leer_entorno(dv, f"RetrieveAppComponents(AppModuleId={id_app})", C_COMPONENTES)
    nombres = set()
    for fila in exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value"):
        if fila.get("componenttype") != COMPONENTE_TABLA:
            continue
        definicion = leer_entorno(dv, f"EntityDefinitions({fila['objectid']})?$select=LogicalName",
                                  C_COMPONENTES, admite_404=True)
        if definicion and definicion.get("LogicalName"):
            nombres.add(definicion["LogicalName"])
    return nombres


def _normalizar_xml(texto):
    return "".join((texto or "").split())


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    comprobar_solucion_e_idioma(dv, identidad)

    iconos = {}
    for area in datos["areas"]:
        for grupo in area["grupos"]:
            for e in grupo["entradas"]:
                if e["icono"] not in iconos:
                    iconos[e["icono"]] = _icono(dv, e["icono"])
    iconos[datos["icono"]] = _icono(dv, datos["icono"])

    vistas = {}
    for area in datos["areas"]:
        for grupo in area["grupos"]:
            for e in grupo["entradas"]:
                if "vista" in e and (e["tabla"], e["vista"]) not in vistas:
                    vistas[(e["tabla"], e["vista"])] = _vista(dv, e["tabla"], e["vista"])

    xml = sitemapxml(datos, iconos, vistas)
    hubo_escritura = False

    # --- el sitemap ---
    sitemap = _leer_sitemap(dv, datos["sitemap"])
    if sitemap is None:
        if solo_verificar:
            return "difiere", componente, f"el sitemap '{datos['sitemap']}' no existe en el entorno"
        cuerpo = {"sitemapnameunique": datos["sitemap"], "sitemapname": datos["nombre"],
                  "sitemapxml": xml, "isappaware": True}
        est, resp, _ = escribir_metadatos(dv, "POST", "sitemaps", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta del sitemap devolvió HTTP {est} (se esperaba 204): {resp}"
        sitemap = _leer_sitemap(dv, datos["sitemap"])
        if sitemap is None:
            return "error", componente, "el alta del sitemap no dio error pero no aparece al releer"
        hubo_escritura = True
    elif _normalizar_xml(sitemap.get("sitemapxml")) != _normalizar_xml(xml) and not solo_verificar:
        id_sm = exigir_forma(sitemap.get("sitemapid"), str, C_SITEMAP, "sitemapid", no_vacio=True)
        est, resp, _ = escribir_metadatos(
            dv, "PATCH", f"sitemaps({id_sm})", {"sitemapxml": xml}, dormir=dormir, solucion=solucion)
        if est not in (200, 204):
            return "error", componente, f"la corrección del sitemap devolvió HTTP {est}: {resp}"
        sitemap = _leer_sitemap(dv, datos["sitemap"])
        hubo_escritura = True

    id_sitemap = exigir_forma(sitemap.get("sitemapid"), str, C_SITEMAP, "sitemapid", no_vacio=True)

    # --- la app ---
    app = _leer_app(dv, datos["uniquename"])
    if app is None:
        if solo_verificar:
            return "difiere", componente, f"la app '{datos['uniquename']}' no existe en el entorno"
        icono_id = leer_entorno(
            dv, f"webresourceset?$select=webresourceid&$filter=name eq '{datos['icono']}'", C_RECURSO)
        id_icono = exigir_forma(icono_id.get("value"), [dict], C_RECURSO, "value", no_vacio=True)[0]["webresourceid"]
        # `clienttype` NO se puede omitir: la plataforma lo pone en 2 (cliente
        # web clásico) y la app arranca con el cartel "This app is designed for
        # the legacy web client...". Todas las apps del entorno están en 4
        # (Unified Interface); la nuestra nació en 2 por no declararlo
        # (verificado en Dev el 2026-09-23).
        cuerpo = {"name": datos["nombre"], "uniquename": datos["uniquename"],
                  "description": datos["descripcion"], "webresourceid": id_icono,
                  "clienttype": CLIENTE_UNIFICADO, "formfactor": FORMFACTOR_TODOS,
                  "navigationtype": NAVEGACION_AREAS}
        est, resp, _ = escribir_metadatos(dv, "POST", "appmodules", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta de la app devolvió HTTP {est} (se esperaba 204): {resp}"
        app = _leer_app(dv, datos["uniquename"])
        if app is None:
            return "error", componente, "el alta de la app no dio error pero no aparece al releer"
        hubo_escritura = True

    id_app = exigir_forma(app.get("appmoduleid"), str, C_APP, "appmoduleid", no_vacio=True)
    if app.get("ismanaged"):
        return "difiere", componente, "la app está managed en este entorno; no se toca desde acá"

    # --- componentes: sitemap y tablas ---
    if not solo_verificar:
        componentes = [{"sitemapid": id_sitemap, "@odata.type": "Microsoft.Dynamics.CRM.sitemap"}]
        est, resp, _ = escribir_metadatos(
            dv, "POST", "AddAppComponents", {"AppId": id_app, "Components": componentes}, dormir=dormir)
        if est not in (200, 204):
            return "error", componente, f"AddAppComponents del sitemap devolvió HTTP {est}: {resp}"
        hubo_escritura = True

        for tabla in datos["tablas"]:
            definicion = leer_entorno(dv, f"EntityDefinitions(LogicalName='{tabla}')?$select=MetadataId",
                                      "la consulta de la tabla (GET EntityDefinitions)", admite_404=True)
            if definicion is None:
                raise Bloqueado(f"la app incluye la tabla '{tabla}', que no existe en el entorno")
            # La propiedad es `entityid`, NO `MetadataId`: el tipo OData
            # `Microsoft.Dynamics.CRM.entity` no tiene `MetadataId` y devuelve
            # HTTP 400. El VALOR sí es el MetadataId de la tabla.
            est, resp, _ = escribir_metadatos(
                dv, "POST", "AddAppComponents",
                {"AppId": id_app, "Components": [{"entityid": definicion["MetadataId"],
                                                  "@odata.type": "Microsoft.Dynamics.CRM.entity"}]}, dormir=dormir)
            if est not in (200, 204):
                return "error", componente, f"AddAppComponents de la tabla '{tabla}' devolvió HTTP {est}: {resp}"

        # --- roles ---
        for nombre_rol in datos["roles"]:
            id_rol = _rol(dv, nombre_rol)
            # El `@odata.id` de un `$ref` tiene que ser un URI ABSOLUTO: con
            # uno relativo OData responde 400 pidiendo `odata.context`.
            est, resp, _ = escribir_metadatos(
                dv, "POST", f"appmodules({id_app})/appmoduleroles_association/$ref",
                {"@odata.id": dv.api + f"roles({id_rol})"}, dormir=dormir)
            if est not in (200, 204):
                # Que el rol ya esté asociado no es un fallo.
                if est != 400 or "duplicate" not in str(resp).lower():
                    return "error", componente, f"asociar el rol '{nombre_rol}' devolvió HTTP {est}: {resp}"

        est, resp, _ = escribir_metadatos(
            dv, "POST", "PublishXml",
            {"ParameterXml": f"<importexportxml><appmodules><appmodule>{id_app}</appmodule></appmodules>"
                             "</importexportxml>"}, dormir=dormir)
        if est not in (200, 204):
            return "error", componente, f"la publicación de la app devolvió HTTP {est}: {resp}"

    # --- validación de la propia plataforma ---
    est, resp, _ = dv.call("GET", f"ValidateApp(AppModuleId={id_app})")
    problemas = []
    if est == 200:
        for issue in ((resp.get("AppValidationResponse") or {}).get("ValidationIssueList") or []):
            if issue.get("ErrorType") == "Error":
                problemas.append(issue.get("Message") or str(issue))
    else:
        problemas.append(f"ValidateApp devolvió HTTP {est}: {resp}")

    # `AddAppComponents` devuelve 204 aunque no agregue NADA (verificado en Dev
    # el 2026-09-22: diez altas de tabla, diez 204, cero componentes). Y
    # `ValidateApp` tampoco se queja. Contar lo que pide el playbook y darlo
    # por hecho sería mentir: se cuenta lo que quedó.
    tablas_puestas = _tablas_de_la_app(dv, id_app)
    faltan_tablas = [t for t in datos["tablas"] if t not in tablas_puestas]

    difs = list(problemas)
    if faltan_tablas:
        difs.append(
            f"la app no incluye {len(faltan_tablas)} de las {len(datos['tablas'])} tablas del playbook "
            f"(faltan {faltan_tablas}); AddAppComponents devolvió 204 sin agregarlas")
    if _normalizar_xml(sitemap.get("sitemapxml")) != _normalizar_xml(xml):
        difs.append("el sitemapxml no coincide con el que genera el playbook")
    if not sitemap.get("isappaware"):
        difs.append("el sitemap no está marcado como isappaware: no es el de una app moderna")

    if difs:
        estado = "error" if hubo_escritura else "difiere"
        prefijo = "se escribió pero no quedó bien: " if hubo_escritura else ""
        return estado, componente, prefijo + "; ".join(difs)

    entradas = sum(len(g["entradas"]) for a in datos["areas"] for g in a["grupos"])
    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"appmoduleid {id_app}, sitemapid {id_sitemap}, {len(datos['areas'])} areas y {entradas} entradas, "
        f"{len(datos['tablas'])} tablas, {len(datos['roles'])} roles, idiomas {datos['idiomas']}; ValidateApp sin errores")


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
        if isinstance(datos.get("uniquename"), str):
            componente = datos["uniquename"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque de la app"
        validar_playbook(datos, identidad)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} uniquename={componente}")
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
            "uso incorrecto: app.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
