# Playbook: relación · sanic_mppp_autorizado_autorizacionplan

## 1. Identidad

```json
{
  "tipo_playbook": "relacion",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "4.3",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
  "publisher": "Sistemas_Abiertos_Nicaragua",
  "prefijo": "sanic",
  "abrev": "mppp",
  "prefijo_opciones": 15946,
  "lcid": 1033
}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La relación está definida en `diseno/02-diccionario-datos.md` §2.4 y §5 y figura en `diseno/06-inventario-componentes.md` §4, renglón 4.3.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "relacion",
  "nombre": "sanic_mppp_autorizado_autorizacionplan",
  "tabla_padre": "sanic_mppp_tbl_autorizado",
  "tabla_hija": "sanic_mppp_tbl_autorizacionplan",
  "comportamiento": "restringido",
  "lookup": {
    "nombre": "sanic_autorizadoid",
    "displayname": "Correo autorizado",
    "descripcion": "Correo autorizado al que se le da permiso sobre el plan.",
    "requerida": true,
    "auditoria": true
  }
}
```

Es una relación referencial con borrado restringido: el padre no se puede borrar mientras tenga hijos. Crea la columna lookup `sanic_autorizadoid` en `sanic_mppp_tbl_autorizacionplan`.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible y descripción del lookup | «Correo autorizado» | El diccionario trae el nombre lógico; el texto de negocio lo fija el playbook (`02` DD-19) |

Viene del diseño, no lo decide este playbook:

- Comportamiento `restringido`: `02` §5 e inventario §4.
- Requerida = sí: el `Req` de `sanic_autorizadoid` en `02` §2.4.
- Auditoría del lookup = sí: `02` DD-18: la tabla hija es un catálogo, sus columnas se auditan.

## 3. Precondiciones

Las de la receta (`patrones.md` §2.3), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Las dos tablas existen | `sanic_mppp_tbl_autorizado` (construida) y `sanic_mppp_tbl_autorizacionplan` (construida) |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.3 "Relación 1:N con su lookup". Herramienta del proyecto: `herramientas/construir/relacion.py`.

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_autorizado_autorizacionplan.md
```

## 5. Verificación

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_autorizado_autorizacionplan.md --solo-verificar
python3 herramientas/construir/muestra_relacion.py playbooks/relacion/sanic_mppp_autorizado_autorizacionplan.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_autorizacionplan.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET RelationshipDefinitions(SchemaName='sanic_mppp_autorizado_autorizacionplan')` | 200 · `ReferencedEntity = sanic_mppp_tbl_autorizado` · `ReferencingEntity = sanic_mppp_tbl_autorizacionplan` · `ReferencingAttribute = sanic_autorizadoid` · `IsCustomRelationship = true` · `IsManaged = false` |
| 2 | Cascadas del comportamiento `restringido` | `Assign = NoCascade` · `Merge = NoCascade` · `Reparent = NoCascade` · `Share = NoCascade` · `Unshare = NoCascade` · `RollupView = NoCascade` · `Delete = Restrict` |
| 3 | El lookup `sanic_autorizadoid` | tipo lookup · `Targets = [sanic_mppp_tbl_autorizado]` · requerida = true · auditoría = true · sin seguridad de columna · nombre visible «Correo autorizado» y su descripción en 1033, sin etiquetas en otro idioma |
| 4 | Pertenencia a la solución | la de la tabla hija: `sanic_mppp_tbl_autorizacionplan` está una vez en la solución de la sección 1, con todos sus subcomponentes (una relación no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla hija sigue coincidiendo con su propio playbook | `ya_existia`: un lookup no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_relacion.py`) | `OK`, y la muestra queda en `playbooks/relacion/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE RelationshipDefinitions(SchemaName='sanic_mppp_autorizado_autorizacionplan')`. **Borra también la columna lookup `sanic_autorizadoid` y sus datos**, y no es posible mientras el lookup esté en un formulario, una vista o una clave alternativa. **Irreversible desde que se crea**: el nombre de la relación y el nombre lógico del lookup. El comportamiento de cascada, el requerida y la auditoría se pueden cambiar después.

## 8. Fuera de alcance

- La clave alternativa `sanic_mppp_key_autorizacionplan_autorizado_plan` usa este lookup: inventario 5.5, después de las relaciones 4.3 y 4.4.
- La regla de integridad (el cliente del plan es el del autorizado): plugin, inventario 7.11.
- Vistas y formularios que muestran este lookup: inventario 12.
