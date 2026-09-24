#!/usr/bin/env python3
"""Construye UNA vista de Dataverse (`savedquery`) desde un playbook de tipo
`vista`. Contrato: `power-platform-construir`; Learn, "Customize views".

    python3 herramientas/construir/vista.py <playbook.md> [--solo-verificar] [--completar]

El playbook **no lleva XML escrito a mano**: declara columnas, orden y filtro,
y la herramienta genera el `fetchxml` y el `layoutxml`. Es a propósito. Esos
dos XML tienen que estar de acuerdo entre sí (cada `<cell>` del layout necesita
su atributo en el fetch); escribirlos a mano en 17 playbooks es garantía de que
tarde o temprano se despeguen y la vista salga con una columna en blanco.

Una vista existente se reconoce por su `name` + `returnedtypecode`: Dataverse
no tiene clave alternativa para `savedquery`, así que ese par es la clave de
negocio. Dos vistas con el mismo nombre en la misma tabla son forma inesperada.

Learn: una personalización se publica sola al CREARSE; hay que publicar
explícitamente después de ACTUALIZARLA. La herramienta publica solo cuando
escribió un `PATCH`.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
import sys
from xml.sax.saxutils import escape, quoteattr

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

TIPO = "vista"

# Learn, tabla SavedQuery (verificado 2026-09-22). Son los cinco documentados.
CLASES = {"Publica": 0, "BusquedaAvanzada": 1, "Relacionada": 2, "BusquedaRapida": 4, "Lookup": 64}

# Operadores de FetchXML que hacen falta para las 17 vistas del proyecto. Lista
# cerrada a propósito: un operador mal escrito no falla al crear la vista,
# falla al abrirla.
OPERADORES_SIN_VALOR = {"null", "not-null", "eq-userid", "ne-userid"}
OPERADORES_UN_VALOR = {"eq", "ne", "gt", "ge", "lt", "le", "like", "begins-with"}
OPERADORES_VARIOS_VALORES = {"in", "not-in"}
OPERADORES = OPERADORES_SIN_VALOR | OPERADORES_UN_VALOR | OPERADORES_VARIOS_VALORES

ANCHO_POR_DEFECTO = 150
LARGO_NOMBRE = 200

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "tabla": str, "clase": str, "descripcion": str,
          "pordefecto": bool, "columnas": list, "orden": list, "filtro": dict}

C_VISTA = "la consulta de la vista (GET savedqueries)"
C_TABLA = "la consulta de la definición de la tabla (GET EntityDefinitions)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_condiciones(condiciones, donde):
    for i, c in enumerate(condiciones):
        aqui = f"{donde}.condiciones[{i}]"
        exigir_forma(c, dict, aqui, "condicion")
        faltan = sorted({"columna", "operador"} - set(c))
        sobran = sorted(set(c) - {"columna", "operador", "valores"})
        if faltan or sobran:
            raise ErrorPlaybook(f"{aqui}: faltan {faltan}, sobran {sobran}; se admite {{columna, operador, valores}}")
        exigir_forma(c["columna"], str, aqui, "columna", no_vacio=True)
        operador = exigir_forma(c["operador"], str, aqui, "operador", no_vacio=True)
        if operador not in OPERADORES:
            raise ErrorPlaybook(f"{aqui}: operador {operador!r} no admitido; los válidos son {sorted(OPERADORES)}")
        valores = c.get("valores", [])
        exigir_forma(valores, list, aqui, "valores")
        if operador in OPERADORES_SIN_VALOR and valores:
            raise ErrorPlaybook(f"{aqui}: el operador {operador!r} no lleva valores y el playbook trae {len(valores)}")
        if operador in OPERADORES_UN_VALOR and len(valores) != 1:
            raise ErrorPlaybook(f"{aqui}: el operador {operador!r} lleva exactamente un valor, y trae {len(valores)}")
        if operador in OPERADORES_VARIOS_VALORES and not valores:
            raise ErrorPlaybook(f"{aqui}: el operador {operador!r} necesita al menos un valor")


def _validar_enlaces(enlaces, donde, profundidad=0):
    if profundidad > 3:
        # Un fetch con más de tres saltos es señal de que la vista quiere algo
        # que no es una vista. "Mis clientes" usa dos (Fila → Plan → Cliente).
        raise ErrorPlaybook(f"{donde}: los enlaces anidan más de 3 niveles; eso no es una vista de grilla")
    for i, e in enumerate(enlaces):
        aqui = f"{donde}.enlaces[{i}]"
        exigir_forma(e, dict, aqui, "enlace")
        faltan = sorted({"tabla", "de", "a", "alias"} - set(e))
        sobran = sorted(set(e) - {"tabla", "de", "a", "alias", "condiciones", "enlaces"})
        if faltan or sobran:
            raise ErrorPlaybook(f"{aqui}: faltan {faltan}, sobran {sobran}")
        for campo in ("tabla", "de", "a", "alias"):
            exigir_forma(e[campo], str, aqui, campo, no_vacio=True)
        _validar_condiciones(exigir_forma(e.get("condiciones", []), list, aqui, "condiciones"), aqui)
        _validar_enlaces(exigir_forma(e.get("enlaces", []), list, aqui, "enlaces"), aqui, profundidad + 1)


def _validar_estructura(datos):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque de la vista no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque de la vista", clave, no_vacio=(tipo is str))
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque de la vista dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    exigir_sin_tildes(datos["nombre"], "nombre")
    if len(datos["nombre"]) > LARGO_NOMBRE:
        raise ErrorPlaybook(f"nombre tiene {len(datos['nombre'])} caracteres; el máximo es {LARGO_NOMBRE}")
    if datos["clase"] not in CLASES:
        raise ErrorPlaybook(f"clase = {datos['clase']!r} no es válida; las válidas son {sorted(CLASES)}")

    columnas = exigir_forma(datos["columnas"], list, "el bloque de la vista", "columnas", no_vacio=True)
    nombres = []
    for i, c in enumerate(columnas):
        aqui = f"la columna [{i}]"
        exigir_forma(c, dict, aqui, "columna")
        sobran = sorted(set(c) - {"nombre", "ancho", "enlace"})
        if "nombre" not in c or sobran:
            raise ErrorPlaybook(f"{aqui}: se admite {{nombre, ancho, enlace}}; falta 'nombre' o sobra {sobran}")
        nombre = exigir_forma(c["nombre"], str, aqui, "nombre", no_vacio=True)
        if "enlace" in c:
            exigir_forma(c["enlace"], str, aqui, "enlace", no_vacio=True)
            nombre = c["enlace"] + "." + nombre  # la huella para detectar repetidas
        if "ancho" in c:
            ancho = exigir_forma(c["ancho"], int, aqui, "ancho")
            if not 25 <= ancho <= 800:
                raise ErrorPlaybook(f"{aqui}: ancho {ancho} fuera de 25..800")
        nombres.append(nombre)
    if len(set(nombres)) != len(nombres):
        raise ErrorPlaybook(f"hay columnas repetidas en la vista: {sorted({n for n in nombres if nombres.count(n) > 1})}")

    for i, o in enumerate(exigir_forma(datos["orden"], list, "el bloque de la vista", "orden")):
        aqui = f"el orden [{i}]"
        exigir_forma(o, dict, aqui, "orden")
        if sorted(o) != ["columna", "sentido"]:
            raise ErrorPlaybook(f"{aqui}: se admite exactamente {{columna, sentido}}")
        exigir_forma(o["columna"], str, aqui, "columna", no_vacio=True)
        if o["sentido"] not in ("asc", "desc"):
            raise ErrorPlaybook(f"{aqui}: sentido = {o['sentido']!r}; solo 'asc' o 'desc'")
        if o["columna"] not in nombres:
            # Ordenar por una columna que no se muestra deja al usuario sin
            # entender por qué la grilla está en ese orden.
            raise ErrorPlaybook(f"{aqui}: se ordena por '{o['columna']}', que la vista no muestra")

    filtro = datos["filtro"]
    sobran = sorted(set(filtro) - {"tipo", "condiciones", "enlaces"})
    if sobran:
        raise ErrorPlaybook(f"el filtro solo admite {{tipo, condiciones, enlaces}}; sobra {sobran}")
    if filtro.get("tipo", "and") not in ("and", "or"):
        raise ErrorPlaybook(f"el filtro tiene tipo = {filtro.get('tipo')!r}; solo 'and' u 'or'")
    _validar_condiciones(exigir_forma(filtro.get("condiciones", []), list, "el filtro", "condiciones"), "el filtro")
    _validar_enlaces(exigir_forma(filtro.get("enlaces", []), list, "el filtro", "enlaces"), "el filtro")

    # Una columna que viene de una tabla enlazada tiene que nombrar un alias que
    # exista: si no, la celda queda vacia y eso no falla al crear la vista.
    alias_declarados = _alias_de(filtro.get("enlaces", []))
    for c in columnas:
        if "enlace" in c and c["enlace"] not in alias_declarados:
            raise ErrorPlaybook(
                f"la columna '{c['nombre']}' viene del enlace '{c['enlace']}', que el filtro no declara; "
                f"los alias declarados son {sorted(alias_declarados) or 'ninguno'}")


def _alias_de(enlaces):
    alias = set()
    for e in enlaces:
        alias.add(e["alias"])
        alias |= _alias_de(e.get("enlaces", []))
    return alias


def validar_playbook(datos):
    _validar_estructura(datos)


# ---------------------------------------------------------------------------
# Generación del XML
# ---------------------------------------------------------------------------
def _xml_condiciones(condiciones, sangria):
    partes = []
    for c in condiciones:
        attrs = f"attribute={quoteattr(c['columna'])} operator={quoteattr(c['operador'])}"
        valores = c.get("valores", [])
        if c["operador"] in OPERADORES_VARIOS_VALORES:
            internos = "".join(f"<value>{escape(str(v))}</value>" for v in valores)
            partes.append(f"{sangria}<condition {attrs}>{internos}</condition>")
        elif valores:
            partes.append(f"{sangria}<condition {attrs} value={quoteattr(str(valores[0]))} />")
        else:
            partes.append(f"{sangria}<condition {attrs} />")
    return partes


def _xml_enlaces(enlaces, sangria, atributos_por_alias=None):
    atributos_por_alias = atributos_por_alias or {}
    partes = []
    for e in enlaces:
        cabecera = (f"{sangria}<link-entity name={quoteattr(e['tabla'])} from={quoteattr(e['de'])} "
                    f"to={quoteattr(e['a'])} alias={quoteattr(e['alias'])} link-type=\"inner\">")
        partes.append(cabecera)
        for atributo in atributos_por_alias.get(e["alias"], []):
            partes.append(f"{sangria}  <attribute name={quoteattr(atributo)} />")
        condiciones = e.get("condiciones", [])
        if condiciones:
            partes.append(f"{sangria}  <filter type=\"and\">")
            partes.extend(_xml_condiciones(condiciones, sangria + "    "))
            partes.append(f"{sangria}  </filter>")
        partes.extend(_xml_enlaces(e.get("enlaces", []), sangria + "  ", atributos_por_alias))
        partes.append(f"{sangria}</link-entity>")
    return partes


def fetchxml(datos, primaria):
    """El `fetchxml` de la vista. La columna primaria va siempre: la grilla la
    necesita para abrir el registro."""
    propias = [c["nombre"] for c in datos["columnas"] if "enlace" not in c]
    atributos = [primaria] + [c for c in propias if c != primaria]
    por_alias = {}
    for c in datos["columnas"]:
        if "enlace" in c:
            por_alias.setdefault(c["enlace"], []).append(c["nombre"])
    partes = ['<fetch version="1.0" output-format="xml-platform" mapping="logical">',
              f'  <entity name={quoteattr(datos["tabla"])}>']
    partes += [f'    <attribute name={quoteattr(a)} />' for a in atributos]
    for o in datos["orden"]:
        partes.append(f'    <order attribute={quoteattr(o["columna"])} descending="{str(o["sentido"] == "desc").lower()}" />')
    filtro = datos["filtro"]
    condiciones = filtro.get("condiciones", [])
    if condiciones:
        partes.append(f'    <filter type={quoteattr(filtro.get("tipo", "and"))}>')
        partes.extend(_xml_condiciones(condiciones, "      "))
        partes.append("    </filter>")
    partes.extend(_xml_enlaces(filtro.get("enlaces", []), "    ", por_alias))
    partes += ["  </entity>", "</fetch>"]
    return "\n".join(partes)


def layoutxml(datos, primaria, codigo_tabla):
    """El `layoutxml`. Cada `<cell>` tiene que tener su `<attribute>` en el
    fetch: por eso los dos se generan del mismo playbook y nunca a mano."""
    def celda(c):
        return c["enlace"] + "." + c["nombre"] if "enlace" in c else c["nombre"]

    partes = [f'<grid name="resultset" object="{codigo_tabla}" jump={quoteattr(celda(datos["columnas"][0]))} '
              'select="1" preview="1" icon="1">',
              f'  <row name="result" id={quoteattr(primaria)}>']
    for c in datos["columnas"]:
        partes.append(f'    <cell name={quoteattr(celda(c))} width="{c.get("ancho", ANCHO_POR_DEFECTO)}" />')
    partes += ["  </row>", "</grid>"]
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _definicion_de_tabla(dv, logical_name):
    ruta = f"EntityDefinitions(LogicalName='{logical_name}')?$select=PrimaryIdAttribute,ObjectTypeCode,MetadataId"
    cuerpo = leer_entorno(dv, ruta, C_TABLA, admite_404=True)
    if cuerpo is None:
        raise Bloqueado(f"la tabla '{logical_name}' no existe en el entorno")
    return (exigir_forma(cuerpo.get("PrimaryIdAttribute"), str, C_TABLA, "PrimaryIdAttribute", no_vacio=True),
            exigir_forma(cuerpo.get("ObjectTypeCode"), int, C_TABLA, "ObjectTypeCode"),
            exigir_forma(cuerpo.get("MetadataId"), str, C_TABLA, "MetadataId", no_vacio=True))


def _leer_vista(dv, nombre, tabla):
    ruta = ("savedqueries?$select=savedqueryid,name,returnedtypecode,querytype,isdefault,description,"
            "fetchxml,layoutxml,statecode,ismanaged"
            f"&$filter=name eq '{nombre}' and returnedtypecode eq '{tabla}'")
    cuerpo = leer_entorno(dv, ruta, C_VISTA)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_VISTA, "value")
    if len(filas) > 1:
        raise ErrorEntorno(
            f"{C_VISTA} devolvió {len(filas)} vistas llamadas '{nombre}' sobre '{tabla}'; el nombre es la clave de negocio")
    return filas[0] if filas else None


def _normalizar_xml(texto):
    """Compara XML sin que cuenten como diferencia ni los espacios ni el
    `savedqueryid` que la plataforma INYECTA en el `fetchxml` al guardarlo
    (verificado en Dev el 2026-09-22): ese atributo no lo escribimos nosotros y
    no puede estar en el XML generado, así que compararlo daría "difiere"
    siempre."""
    apretado = "".join((texto or "").split())
    while True:
        i = apretado.find('savedqueryid="')
        if i < 0:
            return apretado
        fin = apretado.find('"', i + len('savedqueryid="'))
        if fin < 0:
            return apretado
        apretado = apretado[:i] + apretado[fin + 1:]


def _diferencias(datos, vista, fetch, layout):
    difs, corregibles = [], {}
    if vista.get("querytype") != CLASES[datos["clase"]]:
        difs.append(f"querytype es {vista.get('querytype')!r} y el playbook dice {datos['clase']} "
                    "(INMUTABLE en la práctica: conviene borrar la vista y rehacerla)")
    for campo, valor in (("name", datos["nombre"]), ("description", datos["descripcion"]),
                         ("isdefault", datos["pordefecto"])):
        if vista.get(campo) != valor:
            difs.append(f"{campo} es {vista.get(campo)!r} y el playbook dice {valor!r}")
            corregibles[campo] = valor
    for campo, generado in (("fetchxml", fetch), ("layoutxml", layout)):
        if _normalizar_xml(vista.get(campo)) != _normalizar_xml(generado):
            difs.append(f"{campo} no coincide con el que genera el playbook")
            corregibles[campo] = generado
    if vista.get("ismanaged"):
        difs.append("la vista está managed en este entorno; no se toca desde acá")
        corregibles.clear()
    return difs, corregibles


COMPONENTE_TABLA = 1
INCLUYE_SUBCOMPONENTES = 0


def _tabla_en_la_solucion(dv, solution_id, metadata_id):
    """Una vista **no tiene fila propia** en `solutioncomponents`: viaja dentro
    de su tabla, igual que una clave alternativa o una relación (verificado en
    Dev el 2026-09-22). Lo que hay que comprobar es que la TABLA esté en la
    solución con `rootcomponentbehavior = 0` (incluir subcomponentes); si
    estuviera con otro comportamiento, la vista no viajaría."""
    ruta = ("solutioncomponents?$select=componenttype,rootcomponentbehavior,objectid"
            f"&$filter=_solutionid_value eq {solution_id} and objectid eq {metadata_id} "
            f"and componenttype eq {COMPONENTE_TABLA}")
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _otras_por_defecto(dv, tabla, id_vista):
    """Las OTRAS vistas publicas de la misma tabla marcadas por defecto.

    Dataverse NO desmarca sola la anterior al crear una nueva con
    `isdefault = true`: quedan dos, y con dos la plataforma elige una y la
    declaracion del playbook pasa a ser mentira. Toda tabla nace con una
    "Active X" de fabrica marcada por defecto, asi que esto pasa SIEMPRE
    (verificado en Dev el 2026-09-22, 8 tablas con dos defaults)."""
    ruta = ("savedqueries?$select=savedqueryid,name"
            f"&$filter=returnedtypecode eq '{tabla}' and querytype eq {CLASES['Publica']} and isdefault eq true")
    cuerpo = leer_entorno(dv, ruta, C_VISTA)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_VISTA, "value")
    return [f for f in filas if f.get("savedqueryid") != id_vista]


def _publicar(dv, tabla, dormir):
    """Learn: una personalización se publica sola al CREARSE; hay que publicar
    después de ACTUALIZARLA. Se publica la tabla entera, que es el nodo que
    Learn documenta para vistas."""
    cuerpo = {"ParameterXml": f"<importexportxml><entities><entity>{tabla}</entity></entities></importexportxml>"}
    return escribir_metadatos(dv, "POST", "PublishXml", cuerpo, dormir=dormir)


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    primaria, codigo_tabla, metadata_id = _definicion_de_tabla(dv, datos["tabla"])
    fetch = fetchxml(datos, primaria)
    layout = layoutxml(datos, primaria, codigo_tabla)

    vista = _leer_vista(dv, datos["nombre"], datos["tabla"])
    hubo_escritura = False

    if vista is None:
        if solo_verificar:
            return "difiere", componente, f"la vista '{datos['nombre']}' no existe sobre '{datos['tabla']}'"
        cuerpo = {
            "name": datos["nombre"],
            "description": datos["descripcion"],
            "returnedtypecode": datos["tabla"],
            "querytype": CLASES[datos["clase"]],
            "isdefault": datos["pordefecto"],
            "fetchxml": fetch,
            "layoutxml": layout,
        }
        est, resp, _ = escribir_metadatos(dv, "POST", "savedqueries", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta devolvió HTTP {est} (se esperaba 204): {resp}"
        vista = _leer_vista(dv, datos["nombre"], datos["tabla"])
        if vista is None:
            return "error", componente, "el alta no dio error pero la vista no aparece al releer"
        hubo_escritura = True
    elif completar and not solo_verificar:
        difs, corregibles = _diferencias(datos, vista, fetch, layout)
        if not [d for d in difs if "INMUTABLE" in d] and corregibles:
            id_vista = exigir_forma(vista.get("savedqueryid"), str, C_VISTA, "savedqueryid", no_vacio=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"savedqueries({id_vista})", corregibles, dormir=dormir, solucion=solucion)
            if est not in (200, 204):
                return "error", componente, f"la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
            est, resp, _ = _publicar(dv, datos["tabla"], dormir)
            if est not in (200, 204):
                return "error", componente, f"la vista se corrigió pero la publicación devolvió HTTP {est}: {resp}"
            vista = _leer_vista(dv, datos["nombre"], datos["tabla"])
            hubo_escritura = True

    id_vista = exigir_forma(vista.get("savedqueryid"), str, C_VISTA, "savedqueryid", no_vacio=True)

    # Una vista por defecto tiene que ser LA unica por defecto. Esto se corrige
    # siempre que se este escribiendo, sin pedir `--completar`: no es un ajuste
    # de gusto, es que la declaracion del playbook sea cierta o no lo sea.
    if datos["pordefecto"]:
        otras = _otras_por_defecto(dv, datos["tabla"], id_vista)
        if otras and not solo_verificar:
            for otra in otras:
                est, resp, _ = escribir_metadatos(
                    dv, "PATCH", f"savedqueries({otra['savedqueryid']})", {"isdefault": False},
                    dormir=dormir, solucion=solucion)
                if est not in (200, 204):
                    return "error", componente, (
                        f"no se pudo desmarcar por defecto la vista '{otra.get('name')}': HTTP {est} {resp}")
            est, resp, _ = _publicar(dv, datos["tabla"], dormir)
            if est not in (200, 204):
                return "error", componente, f"se desmarcaron las otras por defecto pero la publicación devolvió HTTP {est}: {resp}"
            hubo_escritura = True
            otras = _otras_por_defecto(dv, datos["tabla"], id_vista)
        if otras:
            difs_extra = [f"'{o.get('name')}'" for o in otras]
            return ("error" if hubo_escritura else "difiere"), componente, (
                f"la vista se declara por defecto pero tambien lo estan {', '.join(difs_extra)}: "
                "con dos por defecto la plataforma elige una sola y la declaracion no se cumple")

    difs, _ = _diferencias(datos, vista, fetch, layout)
    fila = _tabla_en_la_solucion(dv, solution_id, metadata_id)
    if fila is None:
        difs.append(f"la tabla '{datos['tabla']}' no figura en la solución (solutionid {solution_id}), "
                    "así que la vista no viajaría con ella")
    elif fila.get("rootcomponentbehavior") != INCLUYE_SUBCOMPONENTES:
        difs.append(f"la tabla '{datos['tabla']}' está en la solución con rootcomponentbehavior "
                    f"{fila.get('rootcomponentbehavior')!r} y no {INCLUYE_SUBCOMPONENTES} (incluir subcomponentes): "
                    "la vista no viajaría con ella")

    if difs:
        estado = "error" if hubo_escritura else "difiere"
        prefijo = "se escribió pero no quedó bien: " if hubo_escritura else ""
        return estado, componente, prefijo + "; ".join(difs)

    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"savedqueryid {id_vista}, {datos['clase']} sobre {datos['tabla']}, {len(datos['columnas'])} columnas"
        f"{', por defecto' if datos['pordefecto'] else ''}; viaja dentro de la tabla, que está en la solución "
        f"'{solucion}' con rootcomponentbehavior {fila.get('rootcomponentbehavior')}")


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
        paso = "validar el bloque de la vista"
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
            "uso incorrecto: vista.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
