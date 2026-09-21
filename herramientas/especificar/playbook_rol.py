#!/usr/bin/env python3
"""Genera el Markdown de un playbook de tipo `rol` (security role) a partir de
una especificación compacta (JSON), con las ocho secciones del formato de
`power-platform-especificar`. Los valores esperados de la sección 5 salen del
bloque de la sección 2: no se redactan aparte.

    python3 herramientas/especificar/playbook_rol.py <especificacion.json> [...]

Escribe `playbooks/rol/<archivo>.md`, con el nombre del rol en minúscula y
guiones bajos.
"""
import json
import os
import re
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(_AQUI), "construir"))

from playbook_tabla import IDENTIDAD_BASE  # noqa: E402
from rol import ACCIONES, ALCANCES  # noqa: E402


def archivo_de(nombre):
    sin_tildes = nombre.lower().translate(str.maketrans("áéíóúñ", "aeioun"))
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes).strip("_")


def generar(esp):
    comp, nombre = esp["componente"], esp["componente"]["nombre"]
    archivo = archivo_de(nombre)
    ident = dict(IDENTIDAD_BASE, tipo_playbook="rol", inventario=esp["inventario"])
    viene = "\n".join(f"- {x}" for x in esp["viene_del_diseno"])
    fuera = "\n".join(f"- {x}" for x in esp["fuera_de_alcance"])
    filas = "\n".join(f"| `{t}` | " + " · ".join(f"`prv{ACCIONES[a]}{t}` = {ALCANCES[x]}" for a, x in acciones.items()) + " |" for t, acciones in comp["tablas"].items())
    otros = "\n".join(f"| `{n}` | {ALCANCES[x]} |" for n, x in comp["otros_privilegios"].items()) or "| (ninguno) | |"
    total = sum(len(a) for a in comp["tablas"].values()) + len(comp["otros_privilegios"])
    return f"""# Playbook: rol · {nombre}

## 1. Identidad

```json
{json.dumps(ident, ensure_ascii=False, indent=2)}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El rol está definido en `diseno/04-matriz-privilegios.md` {esp["matriz"]} y figura en `diseno/06-inventario-componentes.md` §6, renglón {esp["inventario"]}.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto.

## 2. Qué se crea

```json
{json.dumps(comp, ensure_ascii=False, indent=2)}
```

Un security role en la unidad de negocio raíz, con los privilegios del rol `{comp["base"]}` (los que tenga el entorno en el momento de construir) más los {total} de este playbook. Alcances: `usuario` = Basic (solo lo propio) · `unidad` = Local · `unidad_e_hijas` = Deep · `organizacion` = Global.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Descripción del rol | «{comp["descripcion"]}» | La matriz trae el nombre y los privilegios; el texto lo fija el playbook |

Viene del diseño, no lo decide este playbook:

{viene}

## 3. Precondiciones

Las de la receta (`seguridad/patrones.md` §2.1), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide | los de la sección 1 |
| 2 | Hay exactamente una unidad de negocio raíz | una |
| 3 | El rol base existe una vez en la unidad raíz | `{comp["base"]}` |
| 4 | Cada tabla nombrada existe, y cada privilegio admite el alcance pedido | {" · ".join(f"`{t}`" for t in comp["tablas"])} |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/seguridad/patrones.md` §2.1 "Security role". Herramienta del proyecto: `herramientas/construir/rol.py`.

```
python3 herramientas/construir/rol.py playbooks/rol/{archivo}.md
```

## 5. Verificación

```
python3 herramientas/construir/rol.py playbooks/rol/{archivo}.md --solo-verificar
python3 herramientas/construir/muestra_rol.py playbooks/rol/{archivo}.md --guardar
```

Privilegios sobre las tablas de la solución. **Exactamente estos**: uno de menos, uno de más u otro alcance es `difiere`.

| Tabla | Privilegios esperados |
|---|---|
{filas}

Otros privilegios:

| Privilegio | Alcance |
|---|---|
{otros}

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET roles` por nombre en la unidad raíz | un rol · `ismanaged = false` · la descripción de la sección 2 |
| 2 | `RetrieveRolePrivilegesRole` | los privilegios de `{comp["base"]}` más los de las tablas de arriba; **ninguno más** |
| 3 | Pertenencia a la solución | el rol figura una vez en la solución de la sección 1 (`solutioncomponents`, tipo 20) |
| 4 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 5 | Comprobación independiente contra el XML exportado (`muestra_rol.py`) | `OK`, y la muestra queda en `playbooks/rol/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. La herramienta nunca quita un privilegio ni cambia un alcance. Si lo único que pasa es que **faltan** privilegios (una corrida cortada, o una actualización de Microsoft que amplió `{comp["base"]}`), se completa con `--completar`; eso lo decide quien dirige la construcción, no el constructor.

## 7. Reversa

`DELETE roles(<roleid>)`. No es posible mientras el rol esté asignado a un usuario o a un equipo. Nada es irreversible: el nombre, la descripción y los privilegios se pueden cambiar después; pero **cambiar un rol ya asignado cambia lo que esas personas pueden hacer en el momento**.

## 8. Fuera de alcance

{fuera}
"""


def main():
    for ruta in sys.argv[1:]:
        esp = json.load(open(ruta, encoding="utf-8"))
        destino = os.path.join(_RAIZ, "playbooks", "rol", archivo_de(esp["componente"]["nombre"]) + ".md")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        open(destino, "w", encoding="utf-8").write(generar(esp))
        print("escrito", os.path.relpath(destino, _RAIZ))


if __name__ == "__main__":
    main()
