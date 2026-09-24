# Playbook: relación · sanic_mppp_cliente_autorizado — ELIMINADA

> **Eliminado el 2026-09-24.** El correo autorizado dejó de pertenecer a un cliente: a qué planes puede tocar lo dice la tabla Autorizacion, y el cliente sale del **plan**. La consulta que valida los correos entrantes (`CatalogosDataverse.PlanesAutorizadosDe`) nunca usó este lookup — encadena Autorizado → AutorizacionPlan → Plan → Cliente —, así que sacarlo no tocó el motor de validación. **Se pierde** el control que impedía autorizar un correo sobre el plan de otro cliente: aceptado a sabiendas, el correo es libre.


## 1. Identidad

```json
{
  "tipo_playbook": "relacion",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "4.2",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La relación está definida en `diseno/02-diccionario-datos.md` §2.3 y §5 y figura en `diseno/06-inventario-componentes.md` §4, renglón 4.2.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "relacion",
  "nombre": "sanic_mppp_cliente_autorizado",
  "tabla_padre": "sanic_mppp_tbl_cliente",
  "tabla_hija": "sanic_mppp_tbl_autorizado",
  "comportamiento": "restringido",
  "lookup": {
    "nombre": "sanic_clienteid",
    "displayname": "Cliente",
    "descripcion": "Empresa cliente que autorizó este correo. Con el correo forma la clave alternativa.",
    "requerida": true,
    "auditoria": true
  }
}
```

Es una relación referencial con borrado restringido: el padre no se puede borrar mientras tenga hijos. Crea la columna lookup `sanic_clienteid` en `sanic_mppp_tbl_autorizado`.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible y descripción del lookup | «Cliente» | El diccionario trae el nombre lógico; el texto de negocio lo fija el playbook (`02` DD-19) |

Viene del diseño, no lo decide este playbook:

- Comportamiento `restringido`: `02` §5 e inventario §4.
- Requerida = sí: el `Req` de `sanic_clienteid` en `02` §2.3.
- Auditoría del lookup = sí: `02` DD-18: la tabla hija es un catálogo, sus columnas se auditan.

## 3. Precondiciones

Las de la receta (`patrones.md` §2.3), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Las dos tablas existen | `sanic_mppp_tbl_cliente` (construida) y `sanic_mppp_tbl_autorizado` (construida) |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.3 "Relación 1:N con su lookup". Herramienta del proyecto: `herramientas/construir/relacion.py`.

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_cliente_autorizado.md
```

## 5. Verificación

```
python3 herramientas/construir/relacion.py playbooks/relacion/sanic_mppp_cliente_autorizado.md --solo-verificar
python3 herramientas/construir/muestra_relacion.py playbooks/relacion/sanic_mppp_cliente_autorizado.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_autorizado.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET RelationshipDefinitions(SchemaName='sanic_mppp_cliente_autorizado')` | 200 · `ReferencedEntity = sanic_mppp_tbl_cliente` · `ReferencingEntity = sanic_mppp_tbl_autorizado` · `ReferencingAttribute = sanic_clienteid` · `IsCustomRelationship = true` · `IsManaged = false` |
| 2 | Cascadas del comportamiento `restringido` | `Assign = NoCascade` · `Merge = NoCascade` · `Reparent = NoCascade` · `Share = NoCascade` · `Unshare = NoCascade` · `RollupView = NoCascade` · `Delete = Restrict` |
| 3 | El lookup `sanic_clienteid` | tipo lookup · `Targets = [sanic_mppp_tbl_cliente]` · requerida = true · auditoría = true · sin seguridad de columna · nombre visible «Cliente» y su descripción en 1033, sin etiquetas en otro idioma |
| 4 | Pertenencia a la solución | la de la tabla hija: `sanic_mppp_tbl_autorizado` está una vez en la solución de la sección 1, con todos sus subcomponentes (una relación no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla hija sigue coincidiendo con su propio playbook | `ya_existia`: un lookup no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_relacion.py`) | `OK`, y la muestra queda en `playbooks/relacion/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE RelationshipDefinitions(SchemaName='sanic_mppp_cliente_autorizado')`. **Borra también la columna lookup `sanic_clienteid` y sus datos**, y no es posible mientras el lookup esté en un formulario, una vista o una clave alternativa. **Irreversible desde que se crea**: el nombre de la relación y el nombre lógico del lookup. El comportamiento de cascada, el requerida y la auditoría se pueden cambiar después.

## 8. Fuera de alcance

- La clave alternativa `sanic_mppp_key_autorizado_cliente_nombre` (cliente + correo) usa este lookup: inventario 5.4, después de esta relación.
- Vistas y formularios que muestran este lookup: inventario 12.
