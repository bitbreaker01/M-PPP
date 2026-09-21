# Playbook: tabla · sanic_mppp_tbl_parametro

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.5",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §2.5 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.5.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_parametro",
  "displayname": "Parámetro",
  "displayname_plural": "Parámetros",
  "descripcion": "Parámetro de configuración de la solución, versionado. Rige la versión activa más alta de cada código; la vigente nunca se edita.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Código",
    "descripcion": "Código del parámetro, en minúscula y separado por puntos. Con la versión forma la clave alternativa.",
    "largo": 100,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_version",
      "displayname": "Versión",
      "descripcion": "Versión del parámetro. Rige la versión activa más alta.",
      "tipo": "entero",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "minimo": 1,
      "maximo": 2147483647
    },
    {
      "nombre": "sanic_tipo",
      "displayname": "Tipo",
      "descripcion": "Cómo se interpreta el valor: texto, número o JSON.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "choice": "sanic_mppp_ch_tipoparametro"
    },
    {
      "nombre": "sanic_valor",
      "displayname": "Valor",
      "descripcion": "Valor del parámetro.",
      "tipo": "memo",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "largo": 100000
    },
    {
      "nombre": "sanic_descripcion",
      "displayname": "Descripción",
      "descripcion": "Para qué sirve el parámetro y qué formato tiene su valor.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 2000
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la primaria | `Código` | La primaria **es** el código (BP-PP-192) |
| Nombres visibles de las columnas | `Versión`, `Tipo`, `Valor`, `Descripción` | Texto de negocio (`02` DD-19) |
| Rango de las columnas enteras | `sanic_version`: 1 a 2147483647 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |

Viene del diseño, no lo decide este playbook: **auditoría nativa, notas y actividades** = activada · no · no (`02` DD-18: es un catálogo).

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_tipoparametro` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos choice, entero, memo, texto; auditoría de tabla y de columna: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_parametro.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_parametro.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_parametro.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_parametro')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = true` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (5): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` texto 100 requerida · `sanic_version` entero 1–2147483647 requerida · `sanic_tipo` choice `sanic_mppp_ch_tipoparametro` requerida · `sanic_valor` multilínea 100000 requerida · `sanic_descripcion` multilínea 2000 opcional; todas auditadas |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_parametro')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- La clave alternativa `sanic_mppp_key_parametro_nombre_version`: inventario 5.6.
- Los parámetros iniciales: datos semilla, inventario 9.1.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
