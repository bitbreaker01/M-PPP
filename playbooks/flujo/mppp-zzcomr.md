# Playbook: flujo · MPPP-ZZCOMR (TEMPORAL)

**Este flujo es descartable y no forma parte del inventario de la fase 1.** Existe solo para que
las pruebas funcionales puedan correr mientras los disparadores de Dataverse no entregan eventos en
este entorno (diagnóstico completo en `diagnostico/2026-09-23-triggers-dataverse.md`). Cuando el
canal vuelva, se apaga y se borra: el componente de verdad es `MPPP-COM` (inventario 11.4), que
queda intacto y sin tocar.

Por eso lleva `ZZ` en el nombre, igual que el resto de lo descartable del proyecto.

## Por qué no es un simple cambio de disparador

`MPPP-COM` reacciona a un evento: el estado de la Solicitud CAMBIÓ. Una recurrencia no ve cambios,
ve estados — y un estado sigue ahí en el ciclo siguiente. Si este flujo levantara por estado a
secas, invocaría a `MPPP-ENV` sobre las mismas filas cada tres minutos, para siempre.

No mandaría correos repetidos: `MPPP-ENV` se protege con marcas de fecha, no con el estado
(`Toca_el_acuse` exige `sanic_fechaacuseiniciado` nulo; `Toca_la_respuesta_final` exige
`sanic_fecharespuestafinaliniciada` nula). Pero sí serían cientos de ejecuciones en vacío por día,
en un entorno Developer que tiene límites.

La solución es que el `$filter` lleve **las mismas tres marcas** que `MPPP-ENV` evalúa. Así una fila
aparece en la consulta exactamente mientras haya algo que hacer con ella, y desaparece sola en
cuanto `MPPP-ENV` la marca:

| Qué toca | Condición en el filtro |
|---|---|
| Acuse | estado ∈ {159460004, 159460005} **y** `sanic_fechaacuseiniciado` nulo |
| Respuesta final | estado = 159460006 **y** `sanic_fechaacuseenviado` no nulo **y** `sanic_fecharespuestafinaliniciada` nula |

Si mañana cambian las condiciones de `MPPP-ENV`, este filtro queda mintiendo. Es otra razón para que
el flujo no sobreviva más de lo necesario.

## Concurrencia (DF-06)

El "como máximo una vez" depende de que dos ejecuciones no lean a la vez "todavía no iniciado". Acá
hay dos lugares donde eso se puede romper, y los dos van serializados:

- **`runs: 1` en el disparador** — un ciclo de 3 minutos no arranca si el anterior sigue vivo. Sin
  esto, dos ciclos solapados leerían la misma fila antes de que `MPPP-ENV` la marque, y el cliente
  recibiría el acuse dos veces.
- **`repetitions: 1` en el `Foreach`** — las filas se procesan de a una, no en paralelo.

## Diferencias declaradas contra `MPPP-COM`

| | MPPP-COM (el real) | MPPP-ZZCOMR (este) |
|---|---|---|
| Disparador | `SubscribeWebhookTrigger` sobre Solicitud | `Recurrence` cada 3 minutos |
| Selección | `filterexpression` en el servidor, por evento | `$filter` de `ListRecords`, por estado + marcas |
| Latencia | inmediata | hasta 3 minutos |
| Lote | una fila por ejecución (`splitOn`) | hasta 50 filas por ciclo (`$top`) |

**El `$top: 50` es un techo declarado.** Con más de 50 Solicitudes esperando en un mismo ciclo, las
que sobran esperan al siguiente — no se pierden, porque el filtro las vuelve a levantar. Para el
volumen de las pruebas sobra.

## 1. Identidad

```json
{
  "tipo_playbook": "flujo",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "11.4",
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

## 2. Qué se crea

```json
{
  "tipo": "flujo",
  "nombre": "Cloud Flow - MPPP - ZZ - COM por recurrencia (TEMPORAL)",
  "descripcion": "TEMPORAL. Reemplaza el disparador de MPPP-COM mientras los eventos de Dataverse no se entregan en este entorno. Cada 3 minutos busca Solicitudes que esperan acuse o respuesta final y llama a MPPP-ENV. Borrar cuando el canal de eventos vuelva.",
  "archivo": "recursos/flujos/mppp-zzcomr.json",
  "conexiones": {
    "dataverse": {
      "referencia": "sanic_mppp_conr_dataverse",
      "api": "shared_commondataserviceforapps"
    }
  },
  "variables": [],
  "hijos": [
    "Cloud Flow - MPPP - ENV - Enviar comunicacion al cliente"
  ],
  "activar": true
}
```

## 3. Precondiciones

- `MPPP-ENV` ya existe y fue activado al menos una vez: un flujo hijo que nunca se publicó hace
  fallar la activación del padre con `ChildFlowNeverPublished`.
- La connection reference `sanic_mppp_conr_dataverse` existe y está conectada.
- **`MPPP-COM` debe quedar APAGADO mientras este flujo esté encendido.** Si el canal de eventos se
  restablece con los dos activos, los dos llaman a `MPPP-ENV` sobre la misma fila. No habría correo
  duplicado (las marcas de fecha lo impiden), pero sí una carrera evitable.

## 4. Cómo se retira

1. Apagar y borrar este flujo.
2. Encender `MPPP-COM`.
3. Verificar que dispara: modificar el estado de una Solicitud de prueba y mirar su historial.
4. Borrar `recursos/flujos/mppp-zzcomr.json` y este playbook.
