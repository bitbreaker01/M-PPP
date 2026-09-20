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
