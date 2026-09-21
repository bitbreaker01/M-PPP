#!/usr/bin/env python3
"""Genera el Markdown de un playbook de tipo `tabla` a partir de una
especificación compacta (JSON), con las ocho secciones del formato de
`power-platform-especificar`. El contenido lo decide quien escribe la
especificación; esto solo le da forma pareja a todos los playbooks.

    python3 herramientas/especificar/playbook_tabla.py <especificacion.json> [...]

Escribe `playbooks/tabla/<nombre>.md`.
"""
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IDENTIDAD_BASE = {
    "tipo_playbook": "tabla", "version_skill": "0.1.0", "proyecto": "2026-001-referencias-planes-pago", "inventario": "",
    "fase": 1, "entorno_url": "https://org36e60d9d.crm.dynamics.com/", "solucion": "sanic_mppp_sol_mantenimientoppp",
    "publisher": "Sistemas_Abiertos_Nicaragua", "prefijo": "sanic", "abrev": "mppp", "prefijo_opciones": 15946, "lcid": 1033,
}
TIPO_TEXTO = {"texto": "texto {largo}", "autonumerico": "autonumérico `{formato}` (largo {largo})", "memo": "multilínea {largo}",
              "entero": "entero {minimo}–{maximo}", "choice": "choice `{choice}`", "sino": "sí/no (por defecto {defecto})",
              "fecha": "fecha sola", "fechahora": "fecha y hora (usuario local)", "archivo": "archivo hasta {tamano_kb} KB"}


def _col_texto(c):
    return f"`{c['nombre']}` " + TIPO_TEXTO[c["tipo"]].format(**c) + (" requerida" if c["requerida"] else " opcional") + (" **protegida**" if c["protegida"] else "")


def generar(esp):
    comp, nombre = esp["componente"], esp["componente"]["nombre"]
    ident = dict(IDENTIDAD_BASE, inventario=esp["inventario"])
    p = comp["primaria"]
    prim = {**p, "tipo": "autonumerico" if p["autonumerico"] else "texto", "formato": p["autonumerico"], "protegida": False}
    choices = sorted({c["choice"] for c in comp["columnas"] if c["tipo"] == "choice"})
    usa = sorted({c["tipo"] for c in comp["columnas"]} | {prim["tipo"]})
    extras = [x for x, si in (("primaria autonumérica", bool(p["autonumerico"])), ("columnas protegidas", any(c["protegida"] for c in comp["columnas"])),
                              ("auditoría de tabla y de columna", comp["auditoria"])) if si]
    # La primaria hereda la auditoría de la tabla: cuenta como una columna más.
    con_aud = [(p["nombre"], comp["auditoria"])] + [(c["nombre"], c["auditoria"]) for c in comp["columnas"]]
    if all(v for _, v in con_aud):
        aud_txt = "todas auditadas"
    elif not any(v for _, v in con_aud):
        aud_txt = "ninguna auditada"
    else:
        aud_txt = "auditadas: " + ", ".join(f"`{n}`" for n, v in con_aud if v) + "; las demás, no"
    # Lo que el diseño ya decide (auditoría, notas, actividades: `02` DD-18) no es una decisión del playbook.
    propias = [d for d in esp["decisiones"] if not d[0].startswith("Auditoría nativa")]
    del_diseno = [d for d in esp["decisiones"] if d[0].startswith("Auditoría nativa")]
    decisiones = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in propias)
    viene = "".join(f"\n\nViene del diseño, no lo decide este playbook: **{a.lower()}** = {b} ({c})." for a, b, c in del_diseno)
    fuera = "\n".join(f"- {x}" for x in esp["fuera_de_alcance"])
    columnas = " · ".join(_col_texto(c) for c in [prim] + comp["columnas"])
    si = lambda b: "true" if b else "false"  # noqa: E731
    return f"""# Playbook: tabla · {nombre}

## 1. Identidad

```json
{json.dumps(ident, ensure_ascii=False, indent=2)}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` {esp["diccionario"]} y figura en `diseno/06-inventario-componentes.md` §3, renglón {esp["inventario"]}.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{json.dumps(comp, ensure_ascii=False, indent=2)}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
{decisiones}{viene}

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | {", ".join(f"`{c}`" for c in choices) + " (construidos)" if choices else "esta tabla no usa ninguno"} |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos {", ".join(usa)}{"; " + ", ".join(extras) if extras else ""}: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/{nombre}.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/{nombre}.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/{nombre}.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='{nombre}')` | 200 · `OwnershipType = {"UserOwned" if comp["propiedad"] == "usuario" else "OrganizationOwned"}` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = {si(comp["notas"])}` · `HasActivities = {si(comp["actividades"])}` · `IsAuditEnabled = {si(comp["auditoria"])}` · `PrimaryNameAttribute = {p["nombre"]}` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas ({1 + len(comp["columnas"])}): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | {columnas}; {aud_txt} |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='{nombre}')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`{comp["propiedad"]}`), el tipo de cada columna{", a qué choice global apunta cada una" if choices else ""}{" y el comportamiento de fecha sola de las columnas de tipo fecha" if any(c["tipo"] == "fecha" for c in comp["columnas"]) else ""}. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

{fuera}
"""


def main():
    for ruta in sys.argv[1:]:
        esp = json.load(open(ruta, encoding="utf-8"))
        destino = os.path.join(_RAIZ, "playbooks", "tabla", esp["componente"]["nombre"] + ".md")
        open(destino, "w", encoding="utf-8").write(generar(esp))
        print("escrito", os.path.relpath(destino, _RAIZ))


if __name__ == "__main__":
    main()
