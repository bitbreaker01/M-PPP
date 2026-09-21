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


def salida(estado, componente, detalle):
    """Imprime la última línea del contrato (JSON de una sola línea) y
    devuelve el código de salida: 0 solo para 'creado' y 'ya_existia'."""
    print(json.dumps({"estado": estado, "componente": componente, "detalle": detalle}, ensure_ascii=False))
    return 0 if estado in ("creado", "ya_existia") else 1
