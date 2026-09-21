# Playbook: tabla · sanic_mppp_tbl_autorizacionplan

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.4",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §2.4 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.4.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_autorizacionplan",
  "displayname": "Autorizacion",
  "displayname_plural": "Autorizaciones",
  "descripcion": "Autorización de un correo para operar sobre un plan, con su evidencia firmada. Sin evidencia cargada, la autorización no vale.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre calculado por la solución: correo → código del plan. Nadie lo digita.",
    "largo": 400,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_documentofirmado",
      "displayname": "Documento firmado",
      "descripcion": "Evidencia de ESTA autorización: el documento firmado que respalda que este correo opere sobre este plan. Obligatoria por negocio: sin archivo, la autorización no vale.",
      "tipo": "archivo",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "tamano_kb": 10240
    },
    {
      "nombre": "sanic_fechadocumento",
      "displayname": "Fecha del documento",
      "descripcion": "Fecha del documento firmado.",
      "tipo": "fecha",
      "requerida": false,
      "protegida": false,
      "auditoria": true
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la tabla | `Autorizacion` / `Autorizaciones` | Es como la nombra la app (`05` §4); el nombre lógico sigue siendo `autorizacionplan` |
| Nombres visibles de las columnas | `Nombre`, `Documento firmado`, `Fecha del documento` | Texto de negocio (`02` DD-19) |
| La primaria es requerida, como dice el diccionario, aunque sea calculada | `requerida: true` | La calcula la solución y nadie la digita (`01` §4): en el formulario va en solo lectura u oculta (BP-PP-192), y una columna requerida en solo lectura u oculta no bloquea el guardado (Learn, *Troubleshoot form issues*). Eso se resuelve en el playbook del formulario, no bajando el nivel de requerida |
| La evidencia es obligatoria pero la columna **no** es requerida | `requerida: false` | Un archivo solo se puede cargar con el registro ya creado; la obligatoriedad se cumple cerrando por defecto (`02` §2.4) |
| Tamaño máximo del documento | `10240` KB | 10 MB (`02` §2.4) |

Viene del diseño, no lo decide este playbook: **auditoría nativa, notas y actividades** = activada · no · no (`02` DD-18: es un catálogo).

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | esta tabla no usa ninguno |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos archivo, fecha, texto; auditoría de tabla y de columna: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_autorizacionplan.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_autorizacionplan.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_autorizacionplan.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_autorizacionplan')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = true` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (3): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` texto 400 requerida · `sanic_documentofirmado` archivo hasta 10240 KB opcional · `sanic_fechadocumento` fecha sola opcional; todas auditadas |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_autorizacionplan')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna y el comportamiento de fecha sola de las columnas de tipo fecha. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- Los lookups `sanic_autorizadoid` y `sanic_planid` y sus relaciones: inventario 4.3 y 4.4.
- La clave alternativa `sanic_mppp_key_autorizacionplan_autorizado_plan`: inventario 5.5, después de las relaciones.
- El cálculo de `sanic_nombre` y la regla de integridad (el cliente del plan es el del autorizado): plugins, inventario 7.11.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
