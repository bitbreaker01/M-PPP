# Playbook: rol · SR - MPPP - Servicio de ingesta

## 1. Identidad

```json
{
  "tipo_playbook": "rol",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "6.6",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El rol está definido en `diseno/04-matriz-privilegios.md` §3 y figura en `diseno/06-inventario-componentes.md` §6, renglón 6.6.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto.

## 2. Qué se crea

```json
{
  "tipo": "rol",
  "nombre": "SR - MPPP - Servicio de ingesta",
  "descripcion": "Cuenta de servicio de los flujos: da de alta y actualiza la solicitud, escribe eventos en la bitácora, lee los parámetros de vigilancia y ejecuta las Custom API de clasificación y validación. No lee filas, clientes, planes ni autorizados.",
  "base": "App Opener",
  "tablas": {
    "sanic_mppp_tbl_solicitud": {
      "crear": "organizacion",
      "leer": "organizacion",
      "escribir": "organizacion",
      "anexar": "organizacion",
      "anexar_a": "organizacion"
    },
    "sanic_mppp_tbl_bitacora": {
      "crear": "organizacion",
      "anexar": "organizacion"
    },
    "sanic_mppp_tbl_parametro": {
      "leer": "organizacion"
    }
  },
  "otros_privilegios": {
    "prvReadEnvironmentVariableDefinition": "organizacion",
    "prvReadconnectionreference": "organizacion"
  }
}
```

Un security role en la unidad de negocio raíz, con los privilegios del rol `App Opener` (los que tenga el entorno en el momento de construir) más los 10 de este playbook. Alcances: `usuario` = Basic (solo lo propio) · `unidad` = Local · `unidad_e_hijas` = Deep · `organizacion` = Global.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Descripción del rol | «Cuenta de servicio de los flujos: da de alta y actualiza la solicitud, escribe eventos en la bitácora, lee los parámetros de vigilancia y ejecuta las Custom API de clasificación y validación. No lee filas, clientes, planes ni autorizados.» | La matriz trae el nombre y los privilegios; el texto lo fija el playbook |

Viene del diseño, no lo decide este playbook:

- Privilegios sobre tablas: `04` §3, columna Servicio de ingesta.
- `prvReadEnvironmentVariableDefinition` y `prvReadconnectionreference`: `04` §3, "Privilegios varios" (nombres exactos aprobados el 2026-09-21). No existe un privilegio aparte para el valor de una variable de entorno: va con la definición.
- "Ejecutar flujos" (`prvFlow`, `prvWorkflowExecution` y los de `Workflow`) ya viene en App Opener: no se declara.
- Las Custom API `clasificarcorreo` y `validarsolicitud` se ejecutan con `prvCreatesanic_mppp_tbl_solicitud` (D-9), que este rol tiene por `crear` sobre Solicitud: no hace falta otro privilegio.
- No lee Fila, Cliente, Plan ni Autorizado a propósito: eso lo hace el plugin como SYSTEM (`04` §1 y §3).
- Se parte de "App Opener", no de "Basic User" (`04` §2).

## 3. Precondiciones

Las de la receta (`seguridad/patrones.md` §2.1), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide | los de la sección 1 |
| 2 | Hay exactamente una unidad de negocio raíz | una |
| 3 | El rol base existe una vez en la unidad raíz | `App Opener` |
| 4 | Cada tabla nombrada existe, y cada privilegio admite el alcance pedido | `sanic_mppp_tbl_solicitud` · `sanic_mppp_tbl_bitacora` · `sanic_mppp_tbl_parametro` |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/seguridad/patrones.md` §2.1 "Security role". Herramienta del proyecto: `herramientas/construir/rol.py`.

```
python3 herramientas/construir/rol.py playbooks/rol/sr_mppp_servicio_de_ingesta.md
```

## 5. Verificación

```
python3 herramientas/construir/rol.py playbooks/rol/sr_mppp_servicio_de_ingesta.md --solo-verificar
python3 herramientas/construir/muestra_rol.py playbooks/rol/sr_mppp_servicio_de_ingesta.md --guardar
```

Privilegios sobre las tablas de la solución. **Exactamente estos**: uno de menos, uno de más u otro alcance es `difiere`.

| Tabla | Privilegios esperados |
|---|---|
| `sanic_mppp_tbl_solicitud` | `prvCreatesanic_mppp_tbl_solicitud` = Global · `prvReadsanic_mppp_tbl_solicitud` = Global · `prvWritesanic_mppp_tbl_solicitud` = Global · `prvAppendsanic_mppp_tbl_solicitud` = Global · `prvAppendTosanic_mppp_tbl_solicitud` = Global |
| `sanic_mppp_tbl_bitacora` | `prvCreatesanic_mppp_tbl_bitacora` = Global · `prvAppendsanic_mppp_tbl_bitacora` = Global |
| `sanic_mppp_tbl_parametro` | `prvReadsanic_mppp_tbl_parametro` = Global |

Otros privilegios:

| Privilegio | Alcance |
|---|---|
| `prvReadEnvironmentVariableDefinition` | Global |
| `prvReadconnectionreference` | Global |

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

- Asignar el rol a la cuenta de servicio y licenciarla: tarea de administración 13.2.
- El registro de las Custom API con su `ExecutePrivilegeName`: inventario 8.
- A confirmar cuando existan los flujos: que con este rol la cuenta de servicio puede ser dueña de los cinco flujos y correrlos; si falta un privilegio, se agrega a la matriz y después acá.
