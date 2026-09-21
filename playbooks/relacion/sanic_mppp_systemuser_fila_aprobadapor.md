# Playbook: relación · sanic_mppp_systemuser_fila_aprobadapor

## 1. Identidad

```json
{
  "tipo_playbook": "relacion",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "4.11",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La relación está definida en `diseno/02-diccionario-datos.md` §3.2 y figura en `diseno/06-inventario-componentes.md` §4, renglón 4.11.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "relacion",
  "nombre": "sanic_mppp_systemuser_fila_aprobadapor",
  "tabla_padre": "systemuser",
  "tabla_hija": "sanic_mppp_tbl_fila",
  "comportamiento": "restringido",
  "lookup": {
    "nombre": "sanic_aprobadapor",
    "displayname": "Aprobada por",
    "descripcion": "Quién marcó la fila como aprobada: es el aprobador de AS400. La escribe el plugin, nunca quien llama.",
    "requerida": false,
    "auditoria": false
  }
}
```

Es una relación referencial con borrado restringido: el padre no se puede borrar mientras tenga hijos. Crea la columna lookup `sanic_aprobadapor` en `sanic_mppp_tbl_fila`.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Sufijo en el nombre de la relación | `_aprobadapor` | Hay dos relaciones entre `systemuser` y Fila: la regla `<padre>_<hijo>` les daría el mismo nombre. Con más de una relación entre el mismo par, cada una lleva como sufijo el nombre de su lookup sin prefijo (BP-PP-188; aprobado por el aprobador el 2026-09-20) |
| Nombre visible y descripción del lookup | «Aprobada por» | El diccionario trae el nombre lógico; el texto de negocio lo fija el playbook (`02` DD-19) |
| Comportamiento | `restringido` | El inventario la marca `R`. Un usuario del sistema no se borra (se deshabilita), así que en la práctica nunca se dispara |

Viene del diseño, no lo decide este playbook:

- Comportamiento `restringido`: `02` §5 e inventario §4.
- Requerida = no: el `Req` de `sanic_aprobadapor` en `02` §3.2.
- Auditoría del lookup = no: `02` DD-18: la tabla hija es de la unidad histórica, sin auditoría nativa.

## 3. Precondiciones

Las de la receta (`patrones.md` §2.3), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Las dos tablas existen | `systemuser` (tabla del sistema) y `sanic_mppp_tbl_fila` (construida) |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.3 "Relación 1:N con su lookup". Herramienta del proyecto: `herramientas/construir/relacion.py`.

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_systemuser_fila_aprobadapor.md
```

## 5. Verificación

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_systemuser_fila_aprobadapor.md --solo-verificar
python3 herramientas/construir/muestra_relacion.py playbooks/relacion/sanic_mppp_systemuser_fila_aprobadapor.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_fila.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET RelationshipDefinitions(SchemaName='sanic_mppp_systemuser_fila_aprobadapor')` | 200 · `ReferencedEntity = systemuser` · `ReferencingEntity = sanic_mppp_tbl_fila` · `ReferencingAttribute = sanic_aprobadapor` · `IsCustomRelationship = true` · `IsManaged = false` |
| 2 | Cascadas del comportamiento `restringido` | `Assign = NoCascade` · `Merge = NoCascade` · `Reparent = NoCascade` · `Share = NoCascade` · `Unshare = NoCascade` · `RollupView = NoCascade` · `Delete = Restrict` |
| 3 | El lookup `sanic_aprobadapor` | tipo lookup · `Targets = [systemuser]` · requerida = false · auditoría = false · sin seguridad de columna · nombre visible «Aprobada por» y su descripción en 1033, sin etiquetas en otro idioma |
| 4 | Pertenencia a la solución | la de la tabla hija: `sanic_mppp_tbl_fila` está una vez en la solución de la sección 1, con todos sus subcomponentes (una relación no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla hija sigue coincidiendo con su propio playbook | `ya_existia`: un lookup no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_relacion.py`) | `OK`, y la muestra queda en `playbooks/relacion/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE RelationshipDefinitions(SchemaName='sanic_mppp_systemuser_fila_aprobadapor')`. **Borra también la columna lookup `sanic_aprobadapor` y sus datos**, y no es posible mientras el lookup esté en un formulario, una vista o una clave alternativa. **Irreversible desde que se crea**: el nombre de la relación y el nombre lógico del lookup. El comportamiento de cascada, el requerida y la auditoría se pueden cambiar después.

## 8. Fuera de alcance

- Quién puede escribir esta columna y la segregación de funciones: plugin de transición, inventario 7.9.
- Vistas y formularios que muestran este lookup: inventario 12.
