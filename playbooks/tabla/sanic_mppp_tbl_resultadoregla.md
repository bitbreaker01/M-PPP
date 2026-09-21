# Playbook: tabla · sanic_mppp_tbl_resultadoregla

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.9",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §3.3 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.9.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_resultadoregla",
  "displayname": "Resultado de regla",
  "displayname_plural": "Resultados de reglas",
  "descripcion": "Resultado de evaluar una regla de nivel Correo o Solicitud sobre una solicitud, una fila por regla. Es el historial del sobre.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre que arma la solución al registrar el resultado. Nadie lo digita.",
    "largo": 200,
    "requerida": false,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_reglacodigo",
      "displayname": "Código de la regla",
      "descripcion": "Código de la regla evaluada. Con la solicitud forma la clave alternativa.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 50
    },
    {
      "nombre": "sanic_resultado",
      "displayname": "Resultado",
      "descripcion": "Cumplida, No cumplida u Omitida.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_resultadoregla"
    },
    {
      "nombre": "sanic_razon",
      "displayname": "Razón",
      "descripcion": "Por qué no se cumplió, o qué regla la bloqueó si quedó omitida.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 2000
    },
    {
      "nombre": "sanic_efectoaplicado",
      "displayname": "Efecto aplicado",
      "descripcion": "Foto del efecto que tenía la regla ese día: el catálogo es editable y el histórico tiene que seguir diciendo qué pasó.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_efectoregla"
    },
    {
      "nombre": "sanic_fechaevaluacion",
      "displayname": "Evaluada el",
      "descripcion": "Cuándo se evaluó la regla.",
      "tipo": "fechahora",
      "requerida": true,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_orden",
      "displayname": "Orden",
      "descripcion": "Orden en que se evaluó la regla.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 100000
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombres visibles de las columnas | los de la sección 2 | Texto de negocio (`02` DD-19) |
| La primaria es opcional, como dice el diccionario | `requerida: false` | `02` §3.3 no la marca `S`, a diferencia de las demás tablas. La arma la solución y nadie la digita (`01` §4); el playbook no cambia lo que el diccionario decide. Si fuera una omisión del diccionario, se corrige ahí con el aprobador y se ajusta después: el nivel de requerida se puede cambiar sin costo |
| Rango de las columnas enteras | `sanic_orden`: 0 a 100000 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |
| Auditoría nativa, notas y actividades | desactivada · no · no | `02` DD-18: es parte de la unidad histórica, que ya lleva su trazabilidad en columnas propias y en la Bitácora |

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_efectoregla`, `sanic_mppp_ch_resultadoregla` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos choice, entero, fechahora, memo, texto: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_resultadoregla.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_resultadoregla.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_resultadoregla.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_resultadoregla')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = false` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (7): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` texto 200 opcional · `sanic_reglacodigo` texto 50 requerida · `sanic_resultado` choice `sanic_mppp_ch_resultadoregla` requerida · `sanic_razon` multilínea 2000 opcional · `sanic_efectoaplicado` choice `sanic_mppp_ch_efectoregla` opcional · `sanic_fechaevaluacion` fecha y hora (usuario local) requerida · `sanic_orden` entero 0–100000 opcional; ninguna auditada |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_resultadoregla')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- Los lookups `sanic_solicitudid` (parental) y `sanic_reglaid`, con sus relaciones: inventario 4.6 y 4.9.
- La clave alternativa `sanic_mppp_key_resultadoregla_solicitud_reglacodigo`: inventario 5.10, después de la relación.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
