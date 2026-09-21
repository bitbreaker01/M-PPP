# Playbook: tabla · sanic_mppp_tbl_bitacora

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.10",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §3.4 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.10.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_bitacora",
  "displayname": "Bitácora",
  "displayname_plural": "Bitácoras",
  "descripcion": "Renglón de la bitácora de una solicitud: qué pasó, cuándo, qué pieza lo registró y quién actuó.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre calculado por la solución. Nadie lo digita.",
    "largo": 200,
    "requerida": false,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_fechaevento",
      "displayname": "Fecha del evento",
      "descripcion": "Cuándo ocurrió el evento.",
      "tipo": "fechahora",
      "requerida": true,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_evento",
      "displayname": "Evento",
      "descripcion": "Qué ocurrió.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_eventobitacora"
    },
    {
      "nombre": "sanic_origen",
      "displayname": "Origen",
      "descripcion": "Qué pieza de la solución registró el evento.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_origenevento"
    },
    {
      "nombre": "sanic_numerofila",
      "displayname": "Número de fila",
      "descripcion": "Fila a la que se refiere el evento; 0 si es un evento de la solicitud. Es un número, no un lookup a Fila.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 100000
    },
    {
      "nombre": "sanic_actortexto",
      "displayname": "Actor",
      "descripcion": "Nombre de quien actuó, en texto.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 200
    },
    {
      "nombre": "sanic_detalle",
      "displayname": "Detalle",
      "descripcion": "Detalle del evento.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 10000
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombres visibles de las columnas | los de la sección 2 | Texto de negocio (`02` DD-19) |
| La primaria es opcional, como dice el diccionario | `requerida: false` | `02` §3.4 no la marca `S`, a diferencia de las demás tablas. La arma la solución y nadie la digita (`01` §4); el playbook no cambia lo que el diccionario decide. Si fuera una omisión del diccionario, se corrige ahí con el aprobador y se ajusta después: el nivel de requerida se puede cambiar sin costo |
| Rango de las columnas enteras | `sanic_numerofila`: 0 a 100000 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |

Viene del diseño, no lo decide este playbook: **auditoría nativa, notas y actividades** = desactivada · no · no (`02` DD-18: es parte de la unidad histórica, que ya lleva su trazabilidad en columnas propias y en la Bitácora).

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_eventobitacora`, `sanic_mppp_ch_origenevento` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos choice, entero, fechahora, memo, texto: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_bitacora.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_bitacora.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_bitacora.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_bitacora')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = false` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (7): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` texto 200 opcional · `sanic_fechaevento` fecha y hora (usuario local) requerida · `sanic_evento` choice `sanic_mppp_ch_eventobitacora` requerida · `sanic_origen` choice `sanic_mppp_ch_origenevento` requerida · `sanic_numerofila` entero 0–100000 opcional · `sanic_actortexto` texto 200 opcional · `sanic_detalle` multilínea 10000 opcional; ninguna auditada |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_bitacora')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- El lookup `sanic_solicitudid` (parental, el único de la tabla) y su relación: inventario 4.7.
- Esta tabla no tiene clave alternativa (`02` DD-04).
- El cálculo de `sanic_nombre`: plugin, inventario 7.11.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
