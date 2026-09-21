# Playbook: tabla · sanic_mppp_tbl_fila

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.8",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §3.2 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.8.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_fila",
  "displayname": "Fila",
  "displayname_plural": "Filas",
  "descripcion": "Una fila de la plantilla de una solicitud: la inclusión, exclusión o modificación de una referencia en un plan. Es la unidad de trabajo del ejecutivo y del supervisor.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre calculado por la solución: número de la solicitud y número de fila. Nadie lo digita.",
    "largo": 120,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_numerofila",
      "displayname": "Número de fila",
      "descripcion": "Posición de la fila en la plantilla, de 1 en adelante. Con la solicitud forma la clave alternativa.",
      "tipo": "entero",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "minimo": 1,
      "maximo": 100000
    },
    {
      "nombre": "sanic_gestion",
      "displayname": "Gestión",
      "descripcion": "Qué pide el cliente. Vacía si el valor recibido no era válido.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_gestion"
    },
    {
      "nombre": "sanic_clasificacion",
      "displayname": "Clasificación",
      "descripcion": "Cómo se paga la referencia. Vacía si el valor recibido no era válido.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_clasificacion"
    },
    {
      "nombre": "sanic_moneda",
      "displayname": "Moneda",
      "descripcion": "Moneda de la cuenta. Vacía si el valor recibido no era válido.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_moneda"
    },
    {
      "nombre": "sanic_tipoidentificacion",
      "displayname": "Tipo de identificación",
      "descripcion": "Tipo de documento del titular. Vacía si el valor recibido no era válido.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_tipoidentificacion"
    },
    {
      "nombre": "sanic_banco",
      "displayname": "Banco",
      "descripcion": "Banco de la cuenta. Vacía si el valor recibido no era válido.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_banco"
    },
    {
      "nombre": "sanic_numeroplan",
      "displayname": "Número de plan",
      "descripcion": "Código del plan tal como quedó normalizado (4 caracteres).",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 4
    },
    {
      "nombre": "sanic_nombrebeneficiario",
      "displayname": "Nombre del beneficiario",
      "descripcion": "Nombre del titular de la referencia, como llegó.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 200
    },
    {
      "nombre": "sanic_numeroidentificacion",
      "displayname": "Número de identificación",
      "descripcion": "Número del documento de identidad del titular, como llegó. Dato sensible.",
      "tipo": "texto",
      "requerida": false,
      "protegida": true,
      "auditoria": false,
      "largo": 100
    },
    {
      "nombre": "sanic_numerocuenta",
      "displayname": "Número de cuenta",
      "descripcion": "Número de la cuenta, como llegó. Dato sensible.",
      "tipo": "texto",
      "requerida": false,
      "protegida": true,
      "auditoria": false,
      "largo": 100
    },
    {
      "nombre": "sanic_referencia",
      "displayname": "Referencia",
      "descripcion": "La referencia que rige. En formato 11 la construye la solución; en 06 y 10 es la recibida y puede quedar vacía.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 100
    },
    {
      "nombre": "sanic_referenciarecibida",
      "displayname": "Referencia recibida",
      "descripcion": "La referencia tal cual vino en el Excel; si vino vacía, queda vacía.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 100
    },
    {
      "nombre": "sanic_estado",
      "displayname": "Estado",
      "descripcion": "Estado de la fila.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_estadofila"
    },
    {
      "nombre": "sanic_mensaje",
      "displayname": "Mensaje",
      "descripcion": "Motivos de las reglas de registro que fallaron, y después el motivo de una anulación o de una devolución.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 4000
    },
    {
      "nombre": "sanic_fechavalidada",
      "displayname": "Validada el",
      "descripcion": "Cuándo se validó la fila.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fechadigitada",
      "displayname": "Digitada el",
      "descripcion": "Cuándo se marcó como digitada. La escribe el plugin, nunca quien llama.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fechaaprobada",
      "displayname": "Aprobada el",
      "descripcion": "Cuándo se marcó como aprobada. La escribe el plugin, nunca quien llama.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombres visibles de las columnas | los de la sección 2 | Texto de negocio (`02` DD-19) |
| La primaria es requerida, como dice el diccionario, aunque sea calculada | `requerida: true` | La calcula la solución y nadie la digita (`01` §4): en el formulario va en solo lectura u oculta (BP-PP-192), y una columna requerida en solo lectura u oculta no bloquea el guardado (Learn, *Troubleshoot form issues*). Eso se resuelve en el playbook del formulario, no bajando el nivel de requerida |
| Rango de las columnas enteras | `sanic_numerofila`: 1 a 100000 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |
| Columnas con seguridad de columna | `sanic_numeroidentificacion`, `sanic_numerocuenta` | `02` §3.2, columna Seg (RNF-04, BP-PP-004). La herramienta las agrega después de crear la tabla: la plataforma no las admite dentro de la creación |
| Auditoría nativa, notas y actividades | desactivada · no · no | `02` DD-18: es parte de la unidad histórica, que ya lleva su trazabilidad en columnas propias y en la Bitácora |

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_banco`, `sanic_mppp_ch_clasificacion`, `sanic_mppp_ch_estadofila`, `sanic_mppp_ch_gestion`, `sanic_mppp_ch_moneda`, `sanic_mppp_ch_tipoidentificacion` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos choice, entero, fechahora, memo, texto; columnas protegidas: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_fila.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_fila.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_fila.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_fila')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = false` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (18): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` texto 120 requerida · `sanic_numerofila` entero 1–100000 requerida · `sanic_gestion` choice `sanic_mppp_ch_gestion` opcional · `sanic_clasificacion` choice `sanic_mppp_ch_clasificacion` opcional · `sanic_moneda` choice `sanic_mppp_ch_moneda` opcional · `sanic_tipoidentificacion` choice `sanic_mppp_ch_tipoidentificacion` opcional · `sanic_banco` choice `sanic_mppp_ch_banco` opcional · `sanic_numeroplan` texto 4 opcional · `sanic_nombrebeneficiario` texto 200 opcional · `sanic_numeroidentificacion` texto 100 opcional **protegida** · `sanic_numerocuenta` texto 100 opcional **protegida** · `sanic_referencia` texto 100 opcional · `sanic_referenciarecibida` texto 100 opcional · `sanic_estado` choice `sanic_mppp_ch_estadofila` requerida · `sanic_mensaje` multilínea 4000 opcional · `sanic_fechavalidada` fecha y hora (usuario local) opcional · `sanic_fechadigitada` fecha y hora (usuario local) opcional · `sanic_fechaaprobada` fecha y hora (usuario local) opcional; ninguna auditada |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_fila')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- Los lookups `sanic_solicitudid` (parental), `sanic_planid`, `sanic_digitadapor` y `sanic_aprobadapor`, con sus relaciones: inventario 4.5, 4.8, 4.10 y 4.11.
- La clave alternativa `sanic_mppp_key_fila_solicitud_numerofila`: inventario 5.9, después de la relación.
- El perfil de seguridad de columna que da acceso a las dos columnas protegidas: inventario 6.1.
- El cálculo de `sanic_nombre`, las transiciones de estado y la lista blanca de columnas: plugins, inventario 7.8, 7.9 y 7.11.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
