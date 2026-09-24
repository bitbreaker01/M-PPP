# Playbook: flujo · MPPP-VIG

Inventario 11.5. Disenado en `07-flujos.md` seccion 6.

Es la red de seguridad de todo el sistema: hace lo mismo que `MPPP-REC` y `MPPP-COM` cuando algo
quedo a medias (DF-02). Por eso ninguno de esos dos tiene logica propia.

Los cinco bloques de la seccion 6, cada uno en su ambito y **encadenados con
`runAfter: [Succeeded, Failed]`**: que un bloque falle no puede dejar sin correr a los otros
cuatro. La mayoria de las ejecuciones termina en segundos sin nada que hacer.

Los umbrales salen de la tabla de Parametros, leidos al empezar cada ejecucion, con un valor de
respaldo por si el parametro no esta: 15 minutos sin validar, 30 sin responder, 3 reintentos,
30 dias de vencimiento.

## Divergencias declaradas respecto del diseno

- El bloque 5 (vencer los que nadie clasifico) corre en **todas** las ejecuciones, no "solo en la
  primera de cada dia". Es idempotente —lo que ya esta Vencida sale del filtro— y determinar "la
  primera del dia" exige estado que el flujo no tiene. El costo es una consulta mas cada 10
  minutos, que no devuelve nada casi nunca.
- Cada bloque toma como mucho **25** registros por ejecucion. Con unos cientos de correos por mes
  sobra, y evita una ejecucion eterna si algo se acumula.

## 1. Identidad

```json
{
  "tipo_playbook": "flujo",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "11.5",
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
  "nombre": "Cloud Flow - MPPP - VIG - Vigilar pendientes",
  "descripcion": "Cada 10 minutos: recupera lo que quedo a medias llamando a MPPP-ING y MPPP-ENV, levanta para revision lo que no se puede reintentar, y vence lo que nadie clasifico.",
  "archivo": "recursos/flujos/mppp-vig.json",
  "conexiones": {
    "dataverse": {
      "referencia": "sanic_mppp_conr_dataverse",
      "api": "shared_commondataserviceforapps"
    },
    "outlook": {
      "referencia": "sanic_mppp_conr_outlook",
      "api": "shared_office365"
    }
  },
  "variables": [
    "sanic_mppp_ev_buzoningesta"
  ],
  "hijos": [
    "Cloud Flow - MPPP - ING - Ingerir y validar correo",
    "Cloud Flow - MPPP - ENV - Enviar comunicacion al cliente"
  ],
  "activar": true
}
```

## 3. Precondiciones

- `MPPP-ING` (11.1) y `MPPP-ENV` (11.3) existen y estan ACTIVADOS: un padre activo no puede llamar
  a un hijo que nunca se publico.
- Las dos connection references existen y estan conectadas.
- La tabla de Parametros tiene cargados los cuatro umbrales (9.1).
