# Los triggers de Dataverse no disparan en el entorno Dev

**Fecha del diagnóstico:** 2026-09-23 · **Entorno:** Dev (`org36e60d9d`)

---

## Resumen para vos (español)

Ningún flujo de Power Automate que se dispare por un cambio de fila en Dataverse
se ejecuta en este entorno **desde el 2026-08-31**. Son 13 flujos, de 5
soluciones distintas, de 5 publishers distintos. Los flujos que se disparan por
recurrencia o por correo funcionan con normalidad el mismo día, a la misma hora,
con las mismas conexiones.

Se descartaron **once** causas con evidencia leída del propio entorno. Queda una
sola en pie: el canal que lleva la notificación desde Dataverse hasta Power
Automate no está entregando.

**Qué falta hacer antes de mandar el ticket:** crear un entorno Developer nuevo
en la misma región y repetir la prueba (`EEEE control`). Si ahí dispara, el
problema es de este entorno en particular y el ticket queda quirúrgico. Si
tampoco dispara, es del tenant o de la región, y hay que escalarlo distinto.
El resultado va en la sección **Control test in a clean environment**.

**Lo único que se ejecutó contra el entorno durante el diagnóstico** fue un
`ExportSolutionAsync` (completó sin efectos) y lecturas. No se creó, modificó ni
borró ningún componente.

---

## Ticket body (English — ready to paste)

### Environment

| | |
|---|---|
| Organization URL name | `org36e60d9d` |
| Organization ID | `88c7cdef-44ef-f011-aa23-6045bd003e24` |
| Environment ID | `9c8994b8-b1bc-ee23-9184-2f6346502613` |
| Tenant ID | `7bcfee03-896e-4ad3-947b-8a2d9ce17974` |
| Geo | NA |
| Platform version | `9.2.26092.135` |
| Organization state | `3` (Active) |
| Environment type | **Developer** |
| Refresh cadence | **Frequent** (early release — receives platform builds ahead of standard environments) |
| Administration mode | **Disabled** (verified 2026-09-23) |

### Leading hypothesis: platform regression delivered through the early-release cadence

This environment is set to **Refresh cadence: Frequent**, meaning it receives
platform updates before standard-cadence environments. Its current build is
`9.2.26092.135`.

Every Dataverse trigger in the environment stopped firing on **2026-08-31**, with
no configuration change, no failed run, and no error surfaced anywhere. The
callback registrations remain present and correctly formed; no callback system job
has been produced since 2026-08-29. A brand-new flow created on 2026-09-23 against
the out-of-the-box `account` table does not fire either.

That profile is consistent with a regression introduced in a platform build that
this environment received early.

**Decisive control test:** provision a new environment in the same region with
**Standard** refresh cadence and create the same trigger. If it fires there and not
here, the difference is the platform build, not the configuration.

### Symptom

No cloud flow using the Dataverse **"When a row is added, modified or deleted"**
trigger (`SubscribeWebhookTrigger`) has executed in this environment since
**2026-08-31**. The flows remain in an Activated state. No failed run is
recorded — the runs simply never start.

Flows in the same environment that use **Recurrence** or **Outlook** triggers run
normally on the same days, using the same connection references.

### Affected flows — last recorded run

Queried from the `flowrun` table.

| Flow | Last run |
|---|---|
| CH-Flow-Notify reviewers | 2026-08-31 21:59:36 (Succeeded) |
| CH-Flow-Notify when RFC implementation finish | 2026-08-31 22:00:01 (Succeeded) |
| CH-Flow-UnblockOnClient | 2026-08-31 22:00:01 (Succeeded) |
| CH-Flow-UnblockOnClientEmail | 2026-08-31 19:57:40 (Succeeded) |
| CH-Flow-Reply to client email | 2026-08-31 17:35:07 (Succeeded) |
| Cloud Flow \| Smelter \| Smelter orchestrator | never |
| Cloud Flow \| WFE \| Envio de correos por WFE | never |
| Sigil \| Cloud Flow \| Notifications - Participant | never |
| Sigil \| Cloud Flow \| Notifications - Transaction | never |
| Cloud Flow - MPPP - COM - Detectar comunicacion | never (created 2026-09-22) |
| CCCC prueba de ejecucion (test) | never (created 2026-09-23) |
| DDDD cuentas (test, `account` table) | never (created 2026-09-23) |

Five different solutions, five different publishers. Same cut-off date.

### Control — flows with other triggers, same environment, 2026-09-23

| Flow | Trigger | Runs that morning |
|---|---|---|
| HB \| Cloud Flow \| Watchdog | Recurrence | 69 |
| CH-Flow-MailboxSweep | Recurrence | 35 |
| Cloud Flow - MPPP - VIG | Recurrence | 48 |
| Cloud Flow \| WFE \| Rescate | Recurrence | 23 |
| Cloud Flow - MPPP - ING | Outlook | 10 |
| Cloud Flow - MPPP - REC | Outlook | 4 |

### Eleven causes ruled out, with evidence

1. **Subscription not registered.** `callbackregistration` holds 11 rows. The
   rows for the failing flows are field-for-field identical in shape to the ones
   that used to work: correct `entityname`, `message = 4` (CreateOrUpdate),
   `scope = 4` (Organization), `runas = 1`, `version = 1`, `url = null`,
   `runtimeintegrationproperties = null`.

2. **Owner must be an application user.** Ruled out: the same interactive user
   owns callback registrations for WFE, Smelter and Sigil flows that used to
   fire.

3. **Missing `sdkmessageprocessingstep` for the webhook.** No step is named after
   any callback registration GUID — neither for the failing flows nor for the
   ones that previously worked. A full comparison of every step on
   `sanic_chtblreceivedemails` (38 steps) against `sanic_mppp_tbl_solicitud`
   (40 steps) shows no difference other than two custom synchronous plugins.

4. **The row is not actually being modified.** Six rows modified after
   2026-08-31; the most recent at 2026-09-23 11:53:56, which is 32 seconds after
   the test flow's callback registration was created. No run.

5. **Environment suspended / capacity exceeded.** `organizationstate = 3`
   (Active), `isdisabled = false`, `disabledreason = null`, `State = Enabled`.
   The environment accepts writes normally — a capacity-suspended environment
   would be read-only.

6. **Platform update broke it.** The most recent managed solution installed in
   the environment is dated **2026-08-09**. Nothing was installed between then
   and today.

7. **Power Automate licensing.** Recurrence and Outlook flows run normally with
   the same connections and the same owners.

8. **Asynchronous service not processing.** `ExportSolutionAsync` was submitted
   as a test: it sat in `Ready / Waiting for resources` for 85 seconds, then ran
   and completed **Succeeded**. (85 seconds to pick up a job in an idle
   environment seems high and may be worth a look, but the service works.)

9. **Failure of `Microsoft.Dynamics.MicrosoftFlow.Plugins.AsyncUpdateModernFlowPlugin`
   on 2026-08-31 14:27:36** (`Entity 'workflow' With Id = c90419b3-a09e-f011-bbd2-7ced8d1ed971
   Does Not Exist`). Ruled out: the same "canceled because a referenced record was
   deleted" pattern appears on 2026-08-06, 2026-08-18, 2026-09-22 and 2026-09-23.
   It is routine noise from editing or deleting flows.

10. **`CallbackRegistration Expander Operation` (operationtype 79) stopped.**
    Ruled out: all 17 of its records are `Canceled` with `startedon = null`,
    going back to 2026-07-28 — while the CashHub flows were still firing
    normally. It belongs to the deletion lifecycle, not to delivery.

11. **Something specific to our custom tables or publisher.** Ruled out: test
    flow `DDDD cuentas` was created on 2026-09-23 against the out-of-the-box
    **`account`** table, Organization scope, Added-or-Modified, with a single
    Compose action. It does not fire either.

### The event pipeline itself is alive

Asynchronous plugin steps — which are only enqueued when the event pipeline
emits on a row change — ran and completed in the 48 hours before this report:

```
UserRecordChangeListenerPlugin ........ 36 Succeeded
OnAppModuleDeleteDeleteDataverseSkill . 68 Succeeded
PostComponentVersionCreatePlugin ...... 55 Succeeded
PostCreateEntityCascadeSPPlugin ....... 19 Succeeded
CreateReserveEntityPlugin ............. 19 Succeeded
```

Custom synchronous plugin steps on the affected table also execute normally.

### No delivery trace exists in Dataverse

The real `operationtype` option set was read from metadata
(`EntityDefinitions(LogicalName='asyncoperation')/Attributes(LogicalName='operationtype')/Microsoft.Dynamics.CRM.PicklistAttributeMetadata?$expand=OptionSet`).
The only value containing "endpoint" is `330 = TDS endpoint provisioning`. There
is no `ServiceEndpointNotification` operation type in this environment, and no
async operation is produced for flow callback delivery — so the delivery attempt
cannot be observed from the Web API.

### Documented cause that matches this symptom exactly

Microsoft's own troubleshooting article states, verbatim:

> **Check whether admin mode is enabled**
>
> If you enable admin mode with background operations disabled, Dataverse
> asynchronous operations are turned off. Flows that use a **Dataverse** trigger
> (for example, **When a row is added, modified, or deleted**) don't fire because
> they depend on the Dataverse asynchronous service. Scheduled (recurrence) cloud
> flows and other flows that aren't triggered by Dataverse continue to run,
> because they run in the Power Automate service.

Source: [Troubleshoot common problems with Power Automate triggers](https://learn.microsoft.com/en-us/troubleshoot/power-platform/power-automate/flow-run-issues/triggers-troubleshoot)

This is a precise description of the observed behaviour. **To be verified in the
admin center: Environments → Dev → Details → Edit → Administration mode, and the
separate Background operations setting.**

Counter-evidence: asynchronous operations *do* execute in this environment
(`ExportSolutionAsync` completed; 36 executions of `UserRecordChangeListenerPlugin`
in 48 hours), which suggests background operations are enabled. Stated here so the
check is made rather than assumed.

### No callback system job has been produced since 2026-08-29

Microsoft documents that trigger executions are observable as system jobs:

> Because Dataverse triggers run through the asynchronous service, **each trigger
> execution creates a system job** that you can monitor in the Power Platform admin
> center. [...] Filter by **Type: Callback Registration**, **Status: Succeeded or Failed**.
>
> **If no system job exists for an expected trigger, the callback registration
> might be missing or invalid**, or the event might not match the trigger criteria.

Source: [Understand callback registration for Dataverse triggers](https://learn.microsoft.com/en-us/power-automate/dataverse/powerautomate-callbackregistration-flow)

The full `operationtype` option set was enumerated from metadata. The only
callback-related type in this environment is **79 = CallbackRegistration Expander
Operation**. Its complete history:

- 15 records, **all `Canceled`**, all with `startedon = null`
- oldest 2026-07-28, **most recent 2026-08-29 15:10:23**
- **zero** records after that date
- **zero** records in `Succeeded` or `Failed` state, ever

`Flow Notification` (type 75), `Workflow` (type 10) and `Cascade FlowSession
Permissions` (type 100) have no records at all.

So: the callback registrations are present and correctly formed, but no system job
is produced for them, which by Microsoft's own criterion means the registrations
are not being honoured.

### Control test in a clean environment

> **Pendiente.** Crear un entorno Developer nuevo en la región NA, crear un flujo
> con trigger de Dataverse sobre `account`, y anotar acá si dispara o no.

| | |
|---|---|
| New environment ID | _(completar)_ |
| Flow fires? | _(completar)_ |

### What we are asking

Confirm whether the Dataverse event-delivery channel for cloud flow triggers is
operational for this environment, and why callback registrations that are
correctly registered produce no delivery since 2026-08-31.

---

## Anexo: cómo se reprodujo cada dato

Los tres scripts son de **solo lectura** y hablan únicamente con el Dataverse del
proyecto a través de `herramientas/dataverse_api.py`.

| Script | Qué responde |
|---|---|
| `herramientas/diagnostico/entregas_webhook.py` | Estado de la cola de trabajos del sistema y si existen intentos de entrega |
| `herramientas/diagnostico/falla_flow.py` | Texto completo de las fallas del plugin de Power Automate y el catálogo real de `operationtype` |
| `herramientas/diagnostico/expansor_callbacks.py` | Historia del `CallbackRegistration Expander` y del `Update Modern Flow`, y el 31-ago sin ruido |

Las consultas puntuales de `callbackregistration`, `flowrun`, `workflow`,
`sdkmessageprocessingstep` y `organization` se hicieron en línea durante la
sesión y están citadas arriba con su resultado.

---

## Impacto en el proyecto y salida

**Componentes de M-PPP afectados: uno.** `Cloud Flow - MPPP - COM - Detectar
comunicación pendiente` es el único de los 171 que depende del trigger de
Dataverse.

**Salida sin esperar a Microsoft:** convertir COM a trigger de recurrencia,
consultando Solicitudes con `sanic_estadoprocesamiento` en 159460004 / 159460005
/ 159460006 — que es exactamente el `filterexpression` que ya tiene registrado
su webhook. `MPPP-VIG` ya funciona así en este mismo entorno, con 48 ejecuciones
correctas en una mañana.

Costo: latencia. En lugar de reaccionar al instante, reacciona en el siguiente
ciclo. Volver al trigger original, si Microsoft lo resuelve, es cambiar el
disparador del flujo.
