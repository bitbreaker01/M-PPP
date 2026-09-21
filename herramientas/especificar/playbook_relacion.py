#!/usr/bin/env python3
"""Genera el Markdown de un playbook de tipo `relacion` a partir de una
especificación compacta (JSON), con las ocho secciones del formato de
`power-platform-especificar`. Los valores esperados de la sección 5 salen del
bloque de la sección 2: no se redactan aparte.

    python3 herramientas/especificar/playbook_relacion.py <especificacion.json> [...]

Escribe `playbooks/relacion/<nombre>.md`.
"""
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(_AQUI), "construir"))

from playbook_tabla import IDENTIDAD_BASE  # noqa: E402
from relacion import CASCADAS  # noqa: E402

QUE_HACE = {
    "parental": "parental: asignar, compartir, reasignar y **borrar** el padre arrastra a los hijos",
    "restringido": "referencial con borrado restringido: el padre no se puede borrar mientras tenga hijos",
    "quitar_vinculo": "referencial: al borrar el padre, el lookup de los hijos queda vacío",
}


def generar(esp):
    comp, nombre, k = esp["componente"], esp["componente"]["nombre"], esp["componente"]["lookup"]
    ident = dict(IDENTIDAD_BASE, tipo_playbook="relacion", inventario=esp["inventario"])
    cascadas = " · ".join(f"`{a} = {v}`" for a, v in CASCADAS[comp["comportamiento"]].items())
    decisiones = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in esp["decisiones"])
    viene = "\n".join(f"- {x}" for x in esp["viene_del_diseno"])
    fuera = "\n".join(f"- {x}" for x in esp["fuera_de_alcance"])
    si = lambda b: "true" if b else "false"  # noqa: E731
    del_sistema = not comp["tabla_padre"].startswith(ident["prefijo"] + "_")
    return f"""# Playbook: relación · {nombre}

## 1. Identidad

```json
{json.dumps(ident, ensure_ascii=False, indent=2)}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La relación está definida en `diseno/02-diccionario-datos.md` {esp["diccionario"]} y figura en `diseno/06-inventario-componentes.md` §4, renglón {esp["inventario"]}.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{json.dumps(comp, ensure_ascii=False, indent=2)}
```

Es una relación {QUE_HACE[comp["comportamiento"]]}. Crea la columna lookup `{k["nombre"]}` en `{comp["tabla_hija"]}`.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
{decisiones}

Viene del diseño, no lo decide este playbook:

{viene}

## 3. Precondiciones

Las de la receta (`patrones.md` §2.3), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Las dos tablas existen | `{comp["tabla_padre"]}`{" (tabla del sistema)" if del_sistema else " (construida)"} y `{comp["tabla_hija"]}` (construida) |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.3 "Relación 1:N con su lookup". Herramienta del proyecto: `herramientas/construir/relacion.py`.

```
python3 herramientas/construir/relacion.py playbooks/relacion/{nombre}.md
```

## 5. Verificación

```
python3 herramientas/construir/relacion.py playbooks/relacion/{nombre}.md --solo-verificar
python3 herramientas/construir/muestra_relacion.py playbooks/relacion/{nombre}.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/{comp["tabla_hija"]}.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET RelationshipDefinitions(SchemaName='{nombre}')` | 200 · `ReferencedEntity = {comp["tabla_padre"]}` · `ReferencingEntity = {comp["tabla_hija"]}` · `ReferencingAttribute = {k["nombre"]}` · `IsCustomRelationship = true` · `IsManaged = false` |
| 2 | Cascadas del comportamiento `{comp["comportamiento"]}` | {cascadas} |
| 3 | El lookup `{k["nombre"]}` | tipo lookup · `Targets = [{comp["tabla_padre"]}]` · requerida = {si(k["requerida"])} · auditoría = {si(k["auditoria"])} · sin seguridad de columna · nombre visible «{k["displayname"]}» y su descripción en 1033, sin etiquetas en otro idioma |
| 4 | Pertenencia a la solución | la de la tabla hija: `{comp["tabla_hija"]}` está una vez en la solución de la sección 1, con todos sus subcomponentes (una relación no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla hija sigue coincidiendo con su propio playbook | `ya_existia`: un lookup no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_relacion.py`) | `OK`, y la muestra queda en `playbooks/relacion/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE RelationshipDefinitions(SchemaName='{nombre}')`. **Borra también la columna lookup `{k["nombre"]}` y sus datos**, y no es posible mientras el lookup esté en un formulario, una vista o una clave alternativa. **Irreversible desde que se crea**: el nombre de la relación y el nombre lógico del lookup. El comportamiento de cascada, el requerida y la auditoría se pueden cambiar después.

## 8. Fuera de alcance

{fuera}
"""


def main():
    for ruta in sys.argv[1:]:
        esp = json.load(open(ruta, encoding="utf-8"))
        destino = os.path.join(_RAIZ, "playbooks", "relacion", esp["componente"]["nombre"] + ".md")
        open(destino, "w", encoding="utf-8").write(generar(esp))
        print("escrito", os.path.relpath(destino, _RAIZ))


if __name__ == "__main__":
    main()
