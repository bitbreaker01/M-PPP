"""Utilidades compartidas por las herramientas de `herramientas/construir/`.

Lee el playbook (formato común de `power-platform-especificar` §3, versión
que ya reemplazó la tabla de prosa de "## 1. Identidad" por un bloque
```json```): separa sus secciones `## N. Título`, y expone el único bloque
```json``` de cada sección que hace falta. **La herramienta nunca lee prosa
ni tablas del playbook, y nunca deduce un dato de otro** (por ejemplo, la
abreviatura a partir del nombre de la solución): todo lo que hace falta para
construir viene explícito en alguno de los dos bloques json.

Sin dependencias fuera de la librería estándar.
"""
import json
import re

# Claves exactas del bloque json de '## 1. Identidad' (formato común de la
# skill `power-platform-especificar`, §3) y su tipo esperado. Vale para
# cualquier tipo de playbook, no solo choice global.
CLAVES_IDENTIDAD = {
    "tipo_playbook": str,
    "version_skill": str,
    "proyecto": str,
    "inventario": str,
    "fase": int,
    "entorno_url": str,
    "solucion": str,
    "publisher": str,
    "prefijo": str,
    "abrev": str,
    "prefijo_opciones": int,
    "lcid": int,
}


class ErrorPlaybook(Exception):
    """El playbook o alguno de sus bloques json está mal formado, incompleto,
    o no es del tipo que espera la herramienta. Nunca se llegó a tocar el
    entorno: ni siquiera se intentó construir el cliente de Dataverse."""


class Bloqueado(Exception):
    """Una precondición no se cumple (del playbook contra sí mismo, o contra
    lo que dice el entorno). Nunca se llegó a crear, modificar ni borrar
    nada."""


class ErrorEntorno(Exception):
    """No se pudo averiguar algo contra el entorno: una consulta de
    precondición o de verificación devolvió un HTTP inesperado, o devolvió
    200 con una forma inesperada (cuerpo que no es un objeto, o un campo que
    la consulta declara devolver —'value', 'RetrieveProvisionedLanguages',
    'MetadataId', etc.— ausente o de otro tipo del esperado). Nunca se llegó
    a determinar si la precondición se cumple o no: por eso nunca es
    `Bloqueado`, siempre termina en el estado `error`."""


_NOMBRE_TIPO = {int: "un entero", str: "un texto", bool: "un booleano", dict: "un objeto", list: "una lista"}


def _es_del_tipo(valor, tipo):
    if tipo is int:
        # En Python `bool` es subclase de `int`: True no es un entero válido.
        return isinstance(valor, int) and not isinstance(valor, bool)
    return isinstance(valor, tipo)


def _acotado(valor, largo=160):
    texto = repr(valor)
    return texto if len(texto) <= largo else texto[:largo] + "…"


def exigir_forma(valor, tipo, consulta, campo, no_vacio=False, permite_nulo=False):
    """Único punto donde se valida el TIPO de un valor leído de una respuesta
    del entorno, antes de usarlo para decidir algo. Devuelve el valor si
    cumple; si no, lanza `ErrorEntorno` con un mensaje uniforme que nombra la
    consulta, el campo, qué se esperaba y qué llegó (acotado en largo).

    `tipo` es `int`, `str`, `bool`, `dict` o `list`; o una lista de un
    elemento (`[int]`, `[dict]`...) para "lista de", que valida CADA elemento
    y dice cuál falló. `no_vacio` aplica a textos y listas. `permite_nulo`
    acepta `None` (para lo que la plataforma devuelve nulo legítimamente).

    Regla: un valor ausente o de otro tipo con HTTP 200 es "no se pudo
    averiguar" (`error`), nunca una respuesta de negocio. Quien llama decide
    aparte qué vacíos SÍ son de negocio (p. ej. `value: []` en `solutions`)."""
    if valor is None and permite_nulo:
        return None
    lista_de = isinstance(tipo, list)
    base = list if lista_de else tipo
    esperado = f"una lista de {_NOMBRE_TIPO[tipo[0]][3:]}s" if lista_de else _NOMBRE_TIPO[base]

    def fallar(nombre_campo, se_esperaba, llego):
        raise ErrorEntorno(
            f"{consulta} devolvió 200 con forma inesperada: '{nombre_campo}' debía ser {se_esperaba} "
            f"y llegó {_acotado(llego)}"
        )

    if not _es_del_tipo(valor, base):
        fallar(campo, esperado, valor)
    if lista_de:
        for i, elemento in enumerate(valor):
            if not _es_del_tipo(elemento, tipo[0]):
                fallar(f"{campo}[{i}]", _NOMBRE_TIPO[tipo[0]], elemento)
    if no_vacio and not valor:
        fallar(campo, f"{esperado} no vacío", valor)
    return valor


def leer_texto(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def dividir_secciones(texto):
    """Devuelve {numero: {"titulo": str, "cuerpo": str}} para cada encabezado
    `## N. Título` de nivel 2, con el cuerpo hasta el siguiente encabezado de
    nivel 2 (o el final del archivo)."""
    patron = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$", re.MULTILINE)
    coincidencias = list(patron.finditer(texto))
    secciones = {}
    for i, m in enumerate(coincidencias):
        numero = m.group(1)
        inicio = m.end()
        fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(texto)
        secciones[numero] = {"titulo": m.group(2), "cuerpo": texto[inicio:fin]}
    return secciones


def _extraer_bloques_json(cuerpo_seccion):
    return re.findall(r"```json\s*\n(.*?)```", cuerpo_seccion, re.DOTALL)


def obtener_bloque_json(secciones, numero, nombre_seccion):
    """Devuelve el único bloque ```json``` (ya parseado a dict) de la sección
    `numero`. Lanza ErrorPlaybook si la sección no existe, si no tiene
    exactamente un bloque, si el bloque no es JSON válido, o si no es un
    objeto."""
    if numero not in secciones:
        raise ErrorPlaybook(f"no se encontró la sección '## {numero}. {nombre_seccion}' en el playbook")
    bloques = _extraer_bloques_json(secciones[numero]["cuerpo"])
    if len(bloques) == 0:
        raise ErrorPlaybook(f"la sección '## {numero}. {nombre_seccion}' no tiene ningún bloque ```json```")
    if len(bloques) > 1:
        raise ErrorPlaybook(
            f"la sección '## {numero}. {nombre_seccion}' tiene {len(bloques)} bloques ```json```; "
            "tiene que haber exactamente uno"
        )
    try:
        datos = json.loads(bloques[0])
    except json.JSONDecodeError as e:
        raise ErrorPlaybook(f"el bloque json de la sección {numero} no es JSON válido: {e}") from e
    if not isinstance(datos, dict):
        raise ErrorPlaybook(f"el bloque json de la sección {numero} tiene que ser un objeto")
    return datos


def _validar_claves_y_tipos(datos, claves_esperadas, de_donde):
    claves = set(datos.keys())
    esperadas = set(claves_esperadas)
    if claves != esperadas:
        faltan = sorted(esperadas - claves)
        sobran = sorted(claves - esperadas)
        raise ErrorPlaybook(f"claves de {de_donde} inválidas: faltan {faltan or 'ninguna'}, sobran {sobran or 'ninguna'}")
    for clave, tipo in claves_esperadas.items():
        valor = datos[clave]
        if tipo is int:
            if not isinstance(valor, int) or isinstance(valor, bool):
                raise ErrorPlaybook(f"'{clave}' de {de_donde} tiene que ser un entero, no {valor!r}")
        elif tipo is str:
            if not isinstance(valor, str) or not valor.strip():
                raise ErrorPlaybook(f"'{clave}' de {de_donde} tiene que ser texto no vacío")


def obtener_identidad(secciones):
    """Bloque json de '## 1. Identidad', con exactamente las claves de
    CLAVES_IDENTIDAD y sus tipos validados. No valida coherencia contra el
    entorno (eso es una precondición de cada herramienta, contra Dataverse)."""
    identidad = obtener_bloque_json(secciones, "1", "Identidad")
    _validar_claves_y_tipos(identidad, CLAVES_IDENTIDAD, "'## 1. Identidad'")
    return identidad


def obtener_componente(secciones, tipo_esperado):
    """Bloque json de '## 2. Qué se crea', confirmado del `tipo_esperado`.
    No valida las claves propias del componente: cada tipo de herramienta
    tiene su propio conjunto (ninguno de ellos trae ya `lcid`, que vive en
    Identidad)."""
    datos = obtener_bloque_json(secciones, "2", "Qué se crea")
    tipo = datos.get("tipo")
    if tipo != tipo_esperado:
        raise ErrorPlaybook(
            f"'tipo' es {tipo!r}, no {tipo_esperado!r}: esta herramienta no procesa este playbook"
        )
    return datos



def etiqueta_web_api(texto, lcid):
    """Un `Label` del Web API con una sola etiqueta, en `lcid`."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": texto, "LanguageCode": lcid}
        ],
    }


def etiqueta_y_otros_idiomas(label_obj, lcid):
    labels = (label_obj or {}).get("LocalizedLabels", []) or []
    en_lcid = None
    otros = []
    for ll in labels:
        codigo = ll.get("LanguageCode")
        if codigo == lcid:
            en_lcid = ll.get("Label")
        else:
            otros.append(codigo)
    return en_lcid, otros


def exigir_etiqueta(etiqueta, consulta, campo, permite_nulo=False):
    """Forma de un `Label` del Web API: objeto con `LocalizedLabels`, lista
    de objetos con `LanguageCode` entero y `Label` texto."""
    if exigir_forma(etiqueta, dict, consulta, campo, permite_nulo=permite_nulo) is None:
        return
    locs = exigir_forma(etiqueta.get("LocalizedLabels"), [dict], consulta, f"{campo}.LocalizedLabels", permite_nulo=True)
    for i, ll in enumerate(locs or []):
        exigir_forma(ll.get("LanguageCode"), int, consulta, f"{campo}.LocalizedLabels[{i}].LanguageCode")
        exigir_forma(ll.get("Label"), str, consulta, f"{campo}.LocalizedLabels[{i}].Label", permite_nulo=True)


class Rastro:
    """Envuelve al cliente para recordar qué consulta estaba en curso: la red
    de último recurso la nombra, así un fallo imprevisto dice dónde saltó."""

    def __init__(self, dv):
        self._dv = dv
        self.en_curso = "la preparación de la primera consulta"

    def call(self, metodo, ruta, *args, **kwargs):
        self.en_curso = f"{metodo} {ruta.split('?')[0]}"
        return self._dv.call(metodo, ruta, *args, **kwargs)


C_SOLUCION = "la consulta de la solución (GET solutions)"
C_IDIOMA_BASE = "la consulta del idioma base del entorno (GET organizations)"
C_IDIOMAS = "la consulta de idiomas provisionados (GET RetrieveProvisionedLanguages)"


def comprobar_solucion_e_idioma(dv, identidad):
    """Precondiciones comunes a toda herramienta de construcción, contra el
    entorno: la solución existe, no es managed y su publisher coincide con el
    de Identidad por unique name, prefijo y prefijo de opciones; y el `lcid`
    es el idioma base y está provisionado. Devuelve el `solutionid`. Lanza
    `Bloqueado` si una precondición no se cumple y `ErrorEntorno` si no se
    pudo averiguar."""
    solucion = identidad["solucion"]
    ruta_sol = (
        "solutions?$select=uniquename,solutionid,ismanaged"
        "&$expand=publisherid($select=uniquename,customizationprefix,customizationoptionvalueprefix)"
        f"&$filter=uniquename eq '{solucion}'"
    )
    est, cuerpo, _ = dv.call("GET", ruta_sol)
    if est != 200:
        raise ErrorEntorno(f"{C_SOLUCION} '{solucion}' devolvió HTTP {est} (se esperaba 200): {cuerpo}")
    exigir_forma(cuerpo, dict, C_SOLUCION, "cuerpo")
    filas = exigir_forma(cuerpo.get("value"), [dict], C_SOLUCION, "value")
    if len(filas) != 1:
        # 'value' con otra cantidad de filas (incluida la lista vacía) SÍ es
        # una respuesta de negocio legítima: la solución no existe (o hay
        # más de una con el mismo unique name).
        raise Bloqueado(f"la solución '{solucion}' no existe o hay más de una fila ({len(filas)})")
    fila_sol = filas[0]
    # Primero la forma de TODO lo que se va a usar; recién después se decide.
    es_managed = exigir_forma(fila_sol.get("ismanaged"), bool, C_SOLUCION, "ismanaged")
    solution_id = exigir_forma(fila_sol.get("solutionid"), str, C_SOLUCION, "solutionid", no_vacio=True)
    publisher = exigir_forma(fila_sol.get("publisherid"), dict, C_SOLUCION, "publisherid")
    pub_nombre = exigir_forma(publisher.get("uniquename"), str, C_SOLUCION, "publisherid.uniquename")
    pub_prefijo = exigir_forma(publisher.get("customizationprefix"), str, C_SOLUCION, "publisherid.customizationprefix")
    pub_prefijo_opciones = exigir_forma(
        publisher.get("customizationoptionvalueprefix"), int, C_SOLUCION, "publisherid.customizationoptionvalueprefix"
    )
    if es_managed:
        raise Bloqueado(f"la solución '{solucion}' está managed; no se construye ahí")
    if pub_nombre != identidad["publisher"]:
        raise Bloqueado(f"el publisher de '{solucion}' es {pub_nombre!r}, el playbook espera {identidad['publisher']!r}")
    if pub_prefijo != identidad["prefijo"]:
        raise Bloqueado(f"el prefijo del publisher es {pub_prefijo!r}, el playbook espera {identidad['prefijo']!r}")
    if pub_prefijo_opciones != identidad["prefijo_opciones"]:
        raise Bloqueado(
            f"el prefijo de opciones del publisher es {pub_prefijo_opciones!r}, "
            f"el playbook espera {identidad['prefijo_opciones']!r}"
        )

    est, cuerpo, _ = dv.call("GET", "organizations?$select=languagecode")
    if est != 200:
        raise ErrorEntorno(f"{C_IDIOMA_BASE} devolvió HTTP {est} (se esperaba 200): {cuerpo}")
    # Todo entorno tiene exactamente una organización con su idioma base: acá
    # una lista vacía no es una respuesta de negocio, es forma inesperada.
    exigir_forma(cuerpo, dict, C_IDIOMA_BASE, "cuerpo")
    filas_org = exigir_forma(cuerpo.get("value"), [dict], C_IDIOMA_BASE, "value", no_vacio=True)
    lcid_base = exigir_forma(filas_org[0].get("languagecode"), int, C_IDIOMA_BASE, "languagecode")

    est, cuerpo, _ = dv.call("GET", "RetrieveProvisionedLanguages")
    if est != 200:
        raise ErrorEntorno(f"{C_IDIOMAS} devolvió HTTP {est} (se esperaba 200): {cuerpo}")
    # El idioma base siempre está provisionado: una lista vacía tampoco es
    # una respuesta de negocio.
    exigir_forma(cuerpo, dict, C_IDIOMAS, "cuerpo")
    provisionados = exigir_forma(
        cuerpo.get("RetrieveProvisionedLanguages"), [int], C_IDIOMAS, "RetrieveProvisionedLanguages", no_vacio=True
    )
    if identidad["lcid"] != lcid_base or identidad["lcid"] not in provisionados:
        raise Bloqueado(
            f"lcid {identidad['lcid']} del playbook no es el idioma base ({lcid_base}) "
            f"o no está provisionado ({provisionados})"
        )
    return solution_id


def leer_entorno(dv, ruta, consulta, admite_404=False):
    """GET contra el entorno con las reglas de estado de la receta: 404 es
    "no existe" solo donde se admite; cualquier otro HTTP distinto de 200 es
    `ErrorEntorno`; y el cuerpo tiene que ser un objeto. Devuelve el cuerpo,
    o `None` si fue un 404 admitido."""
    est, cuerpo, _ = dv.call("GET", ruta)
    if est == 404 and admite_404:
        return None
    if est != 200:
        raise ErrorEntorno(f"{consulta} devolvió HTTP {est} (se esperaba 200{' o 404' if admite_404 else ''}): {cuerpo}")
    return exigir_forma(cuerpo, dict, consulta, "cuerpo")


def valor_administrado(objeto, tipo, consulta, campo):
    """Valor de una propiedad administrada del Web API (`{Value, CanBeChanged, …}`)."""
    exigir_forma(objeto, dict, consulta, campo)
    return exigir_forma(objeto.get("Value"), tipo, consulta, f"{campo}.Value")


def comparar_etiqueta(etiqueta, lcid, que, esperado, difs, consulta, campo, permite_nulo=False):
    """Valida la forma de un `Label` y agrega a `difs` lo que no coincida con
    el texto esperado en `lcid`, o si trae etiquetas en otro idioma."""
    exigir_etiqueta(etiqueta, consulta, campo, permite_nulo=permite_nulo)
    texto, otros = etiqueta_y_otros_idiomas(etiqueta, lcid)
    if (texto or "") != esperado:
        difs.append(f"{que}: entorno={texto!r} playbook={esperado!r}")
    if otros:
        difs.append(f"{que} tiene etiquetas en otro idioma: {otros}")


def nivel_requerido(requerida):
    return {"Value": "ApplicationRequired" if requerida else "None", "CanBeChanged": True,
            "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"}


def auditoria_administrada(activa):
    return {"Value": activa, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyauditsettings"}


ESPERA_BLOQUEO_SEGUNDOS = 30
REINTENTOS_BLOQUEO = 10


def _es_bloqueo_pasajero(respuesta):
    """Los dos textos con los que la plataforma dice "hay otra operación de
    metadatos o de soluciones en curso". La segunda forma aparece también
    cuando Microsoft instala sola una actualización de plataforma."""
    texto = str(respuesta)
    return "CustomizationLockException" in texto or "running at this moment" in texto


def escribir_metadatos(dv, metodo, ruta, cuerpo, dormir=None, **kw):
    """Toda escritura de metadatos de las herramientas pasa por acá. Dataverse
    admite UNA sola personalización de metadatos a la vez en el entorno: si
    otra está corriendo (otra herramienta, un ensayo, un borrado, alguien en
    el portal, o una actualización que Microsoft instala sola), responde `429`
    con `CustomizationLockException` o con "… running at this moment". Es pasajero:
    se espera y se reintenta, hasta `REINTENTOS_BLOQUEO` veces. Cualquier otra
    respuesta, incluido otro 429, se devuelve tal cual, sin reintentar."""
    if dormir is None:
        import time

        dormir = time.sleep
    for intento in range(REINTENTOS_BLOQUEO + 1):
        est, resp, cab = dv.call(metodo, ruta, cuerpo, **kw)
        if est != 429 or not _es_bloqueo_pasajero(resp) or intento == REINTENTOS_BLOQUEO:
            return est, resp, cab
        print(f"El entorno tiene otra personalización en curso; espero {ESPERA_BLOQUEO_SEGUNDOS} s y reintento ({intento + 1}/{REINTENTOS_BLOQUEO}).", flush=True)
        dormir(ESPERA_BLOQUEO_SEGUNDOS)


def exigir_sin_tildes(texto, campo):
    """BP-PP-197: ningún nombre visible lleva tildes, ñ ni otro carácter fuera
    de ASCII. El nombre visible viaja por filtros de URL, XML de la solución,
    scripts y nombres de archivo; y en un componente sin nombre lógico ES el
    identificador. Las descripciones son prosa y no pasan por acá."""
    malos = sorted({c for c in texto if ord(c) > 126 or ord(c) < 32})
    if malos:
        raise ErrorPlaybook(f"{campo} = {texto!r} lleva caracteres fuera de ASCII ({' '.join(malos)}): los nombres visibles van sin tildes ni ñ (BP-PP-197); "
                            "se escribe la palabra sin la tilde, no se la cambia por otra")


def nombre_de_archivo(texto):
    """Nombre de archivo para un componente que no tiene nombre lógico (un rol,
    un perfil): su nombre visible en minúscula, sin tildes y con guiones bajos.
    Se translitera en vez de descartar: «técnico» es `tecnico`, no `t_cnico`."""
    import re
    import unicodedata

    sin_marcas = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", sin_marcas).strip("_")


def salida(estado, componente, detalle):
    """Imprime la última línea del contrato (JSON de una sola línea) y
    devuelve el código de salida: 0 solo para 'creado' y 'ya_existia'."""
    print(json.dumps({"estado": estado, "componente": componente, "detalle": detalle}, ensure_ascii=False))
    return 0 if estado in ("creado", "ya_existia") else 1
