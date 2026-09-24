# Playbook: rol · SR - MPPP - Supervisor

## 1. Identidad

```json
{
  "tipo_playbook": "rol",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "6.3",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El rol está definido en `diseno/04-matriz-privilegios.md` §2 y figura en `diseno/06-inventario-componentes.md` §6, renglón 6.3.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto.

## 2. Qué se crea

```json
{
  "tipo": "rol",
  "nombre": "SR - MPPP - Supervisor",
  "descripcion": "Supervisor: consulta catálogos y solicitudes, y aprueba o devuelve las filas digitadas.",
  "base": "App Opener",
  "tablas": {
    "sanic_mppp_tbl_cliente": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_plan": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_autorizado": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_autorizacionplan": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_regla": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_solicitud": {
      "leer": "organizacion",
      "anexar_a": "organizacion"
    },
    "sanic_mppp_tbl_fila": {
      "leer": "organizacion",
      "escribir": "organizacion",
      "anexar": "organizacion"
    },
    "sanic_mppp_tbl_resultadoregla": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_bitacora": {
      "leer": "organizacion"
    },
    "sanic_mppp_tbl_motivoaccion": {
      "crear": "usuario",
      "leer": "usuario",
      "escribir": "usuario",
      "borrar": "usuario"
    }
  },
  "otros_privilegios": {}
}
```

Un security role en la unidad de negocio raíz, con los privilegios del rol `App Opener` (los que tenga el entorno en el momento de construir) más los 12 de este playbook. Alcances: `usuario` = Basic (solo lo propio) · `unidad` = Local · `unidad_e_hijas` = Deep · `organizacion` = Global.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Descripción del rol | «Supervisor: consulta catálogos y solicitudes, y aprueba o devuelve las filas digitadas.» | La matriz trae el nombre y los privilegios; el texto lo fija el playbook |

Viene del diseño, no lo decide este playbook:

- Privilegios: `04` §2, columna Supervisor.
- Nadie borra (`04` §2).
- Mismos privilegios que el Ejecutivo sobre Fila: lo que los distingue es qué transición les permite el plugin (`04` §2).
- No tiene `escribir` sobre Solicitud: el botón "Revisado" es del Ejecutivo.
- Se parte de "App Opener", no de "Basic User" (`04` §2).

## 3. Precondiciones

Las de la receta (`seguridad/patrones.md` §2.1), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide | los de la sección 1 |
| 2 | Hay exactamente una unidad de negocio raíz | una |
| 3 | El rol base existe una vez en la unidad raíz | `App Opener` |
| 4 | Cada tabla nombrada existe, y cada privilegio admite el alcance pedido | `sanic_mppp_tbl_cliente` · `sanic_mppp_tbl_plan` · `sanic_mppp_tbl_autorizado` · `sanic_mppp_tbl_autorizacionplan` · `sanic_mppp_tbl_regla` · `sanic_mppp_tbl_solicitud` · `sanic_mppp_tbl_fila` · `sanic_mppp_tbl_resultadoregla` · `sanic_mppp_tbl_bitacora` |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/seguridad/patrones.md` §2.1 "Security role". Herramienta del proyecto: `herramientas/construir/rol.py`.

```
python3 herramientas/construir/rol.py playbooks/rol/sr_mppp_supervisor.md
```

## 5. Verificación

```
python3 herramientas/construir/rol.py playbooks/rol/sr_mppp_supervisor.md --solo-verificar
python3 herramientas/construir/muestra_rol.py playbooks/rol/sr_mppp_supervisor.md --guardar
```

Privilegios sobre las tablas de la solución. **Exactamente estos**: uno de menos, uno de más u otro alcance es `difiere`.

| Tabla | Privilegios esperados |
|---|---|
| `sanic_mppp_tbl_cliente` | `prvReadsanic_mppp_tbl_cliente` = Global |
| `sanic_mppp_tbl_plan` | `prvReadsanic_mppp_tbl_plan` = Global |
| `sanic_mppp_tbl_autorizado` | `prvReadsanic_mppp_tbl_autorizado` = Global |
| `sanic_mppp_tbl_autorizacionplan` | `prvReadsanic_mppp_tbl_autorizacionplan` = Global |
| `sanic_mppp_tbl_regla` | `prvReadsanic_mppp_tbl_regla` = Global |
| `sanic_mppp_tbl_solicitud` | `prvReadsanic_mppp_tbl_solicitud` = Global · `prvAppendTosanic_mppp_tbl_solicitud` = Global |
| `sanic_mppp_tbl_fila` | `prvReadsanic_mppp_tbl_fila` = Global · `prvWritesanic_mppp_tbl_fila` = Global · `prvAppendsanic_mppp_tbl_fila` = Global |
| `sanic_mppp_tbl_resultadoregla` | `prvReadsanic_mppp_tbl_resultadoregla` = Global |
| `sanic_mppp_tbl_bitacora` | `prvReadsanic_mppp_tbl_bitacora` = Global |

Otros privilegios:

| Privilegio | Alcance |
|---|---|
| (ninguno) | |

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET roles` por nombre en la unidad raíz | un rol · `ismanaged = false` · la descripción de la sección 2 |
| 2 | `RetrieveRolePrivilegesRole` | los privilegios de `App Opener` más los de las tablas de arriba; **ninguno más** |
| 3 | Pertenencia a la solución | el rol figura una vez en la solución de la sección 1 (`solutioncomponents`, tipo 20) |
| 4 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 5 | Comprobación independiente contra el XML exportado (`muestra_rol.py`) | `OK`, y la muestra queda en `playbooks/rol/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. La herramienta nunca quita un privilegio ni cambia un alcance. Si lo único que pasa es que **faltan** privilegios (una corrida cortada, o una actualización de Microsoft que amplió `App Opener`), se completa con `--completar`; eso lo decide quien dirige la construcción, no el constructor.

## 7. Reversa

`DELETE roles(<roleid>)`. No es posible mientras el rol esté asignado a un usuario o a un equipo. Nada es irreversible: el nombre, la descripción y los privilegios se pueden cambiar después; pero **cambiar un rol ya asignado cambia lo que esas personas pueden hacer en el momento**.

## 8. Fuera de alcance

- Asignar el rol a las personas: tarea de administración en cada entorno, inventario 13.
- Dar al rol acceso a la app model-driven: va con la app, inventario 12.
- El perfil de seguridad de columna de los datos sensibles: inventario 6.1 (espera la decisión D-8).
