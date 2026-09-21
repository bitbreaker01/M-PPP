#!/usr/bin/env python3
"""Genera el Markdown de un playbook de tipo `clave` (clave alternativa) a
partir de una especificación compacta (JSON), con las ocho secciones del
formato de `power-platform-especificar`. Los valores esperados de la sección 5
salen del bloque de la sección 2: no se redactan aparte.

    python3 herramientas/especificar/playbook_clave.py <especificacion.json> [...]

Escribe `playbooks/clave/<nombre>.md`.
"""
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))

from playbook_tabla import IDENTIDAD_BASE  # noqa: E402


def generar(esp):
    comp, nombre = esp["componente"], esp["componente"]["nombre"]
    ident = dict(IDENTIDAD_BASE, tipo_playbook="clave", inventario=esp["inventario"])
    columnas = " · ".join(f"`{c}`" for c in comp["columnas"])
    viene = "\n".join(f"- {x}" for x in esp["viene_del_diseno"])
    fuera = "\n".join(f"- {x}" for x in esp["fuera_de_alcance"])
    if esp["columnas_opcionales"]:
        nulos = "\n".join(
            f"- **`{c}` es opcional**: mientras un registro tenga esa columna vacía, la plataforma **no le exige unicidad** a ese registro. "
            "La clave protege solo a los registros que la tienen cargada." for c in esp["columnas_opcionales"])
    else:
        nulos = "Todas las columnas de la clave son requeridas en el diseño: ningún registro creado desde la app queda fuera de la unicidad. (El nivel requerido lo aplica la app, no el servicio: lo que entra por API con una columna vacía queda fuera de la unicidad.)"
    return f"""# Playbook: clave alternativa · {nombre}

## 1. Identidad

```json
{json.dumps(ident, ensure_ascii=False, indent=2)}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La clave está definida en `diseno/02-diccionario-datos.md` {esp["diccionario"]} y figura en `diseno/06-inventario-componentes.md` §5, renglón {esp["inventario"]}.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{json.dumps(comp, ensure_ascii=False, indent=2)}
```

Una clave alternativa sobre `{comp["tabla"]}`: la plataforma no admite dos registros con la misma combinación de {columnas}.

Valores vacíos:

{nulos}

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la clave | «{comp["displayname"]}» | El inventario trae el nombre lógico; el visible sigue el patrón `KEY - MPPP - Tabla - Campos` (`01` §2) |

Viene del diseño, no lo decide este playbook:

{viene}

## 3. Precondiciones

Las de la receta (`patrones.md` §2.4), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | La tabla existe | `{comp["tabla"]}` (construida) |
| 4 | Cada columna de la clave existe, es de un tipo que admite clave y no tiene seguridad de columna | {columnas} |
| 5 | La clave no pasa de 900 bytes (un texto ocupa 2 por carácter) | la herramienta lo calcula con los largos reales del entorno |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.4 "Clave alternativa". Herramienta del proyecto: `herramientas/construir/clave.py`. El índice de la clave se arma en segundo plano: la herramienta espera hasta verlo `Active`.

```
python3 herramientas/construir/clave.py playbooks/clave/{nombre}.md
```

## 5. Verificación

```
python3 herramientas/construir/clave.py playbooks/clave/{nombre}.md --solo-verificar
python3 herramientas/construir/muestra_clave.py playbooks/clave/{nombre}.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/{comp["tabla"]}.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='{comp["tabla"]}')/Keys(LogicalName='{nombre}')` | 200 · `IsManaged = false` · nombre visible «{comp["displayname"]}» en 1033, sin etiquetas en otro idioma |
| 2 | Columnas de la clave (`KeyAttributes`, sin importar el orden) | {columnas} |
| 3 | Índice (`EntityKeyIndexStatus`) | `Active` |
| 4 | Pertenencia a la solución | la clave figura una vez en la solución de la sección 1 (`solutioncomponents`, tipo 14) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla sigue coincidiendo con su propio playbook | `ya_existia`: una clave no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_clave.py`) | `OK`, y la muestra queda en `playbooks/clave/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. Un índice `Failed` también es `difiere`: casi siempre hay datos duplicados, y eso lo resuelve una persona antes de reactivar la clave.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='{comp["tabla"]}')/Keys(<MetadataId>)`. No borra datos ni columnas: solo deja de exigir la unicidad. **Irreversible desde que se crea**: el nombre de la clave. Las columnas de una clave no se editan: para cambiarlas se borra la clave y se crea otra. Mientras la clave exista, sus columnas no se pueden borrar.

## 8. Fuera de alcance

{fuera}
"""


def main():
    for ruta in sys.argv[1:]:
        esp = json.load(open(ruta, encoding="utf-8"))
        destino = os.path.join(_RAIZ, "playbooks", "clave", esp["componente"]["nombre"] + ".md")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        open(destino, "w", encoding="utf-8").write(generar(esp))
        print("escrito", os.path.relpath(destino, _RAIZ))


if __name__ == "__main__":
    main()
