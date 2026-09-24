# Playbook: flujo · MPPP-ENV

Inventario 11.3. Disenado en `07-flujos.md` seccion 5. La definicion vive en
`recursos/flujos/mppp-env.json`.

**Es un flujo HIJO**: su disparador es manual y lo llaman `MPPP-COM` y `MPPP-VIG` (DF-02).

`activar` es **`true`**, y no por gusto: la plataforma rechaza activar un padre cuyo hijo nunca se
publico (`ChildFlowNeverPublished`, verificado en Dev el 2026-09-22). Un hijo activado no se
dispara solo — su disparador es manual —, pero queda publicado y el padre lo puede llamar.

Ademas necesita una accion **`Response`**: sin ella la plataforma deja CREAR el hijo y despues
rechaza activar al padre con `ChildFlowMissingResponseOperation`, un error que aparece lejos del
archivo que lo causa. La herramienta ahora lo valida sin red.

Entradas: `text` = identificador de la Solicitud, `text_1` = el VALOR de la opcion `sanic_origen`
del flujo que llama (159460003 MPPP-COM, 159460005 MPPP-VIG). Va el numero y no el texto porque
la Bitacora guarda el origen como choice.

**Nunca reenvia ante la duda** (D-21): si una comunicacion quedo iniciada y sin confirmar, el flujo
no envia nada y levanta la Solicitud para revision humana. Es el costo aceptado de garantizar que
el cliente jamas reciba dos veces lo mismo.

Divergencia declarada respecto del diseno: el paso 3 de la seccion 5 preve que, si el identificador
de Outlook no sirve, se busque el mensaje en la carpeta de procesados por su Internet Message-ID y
se reintente una vez. **Eso no esta implementado.** Si `ReplyToV3` falla, la comunicacion queda
iniciada sin enviar y la vigilancia la levanta para revision, que es el mismo camino seguro. Se
declara para no dar por hecho algo que no esta.

## 1. Identidad

```json
{
  "tipo_playbook": "flujo",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "11.3",
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
  "nombre": "Cloud Flow - MPPP - ENV - Enviar comunicacion al cliente",
  "descripcion": "Hijo. Decide sola que comunicacion toca (acuse o respuesta final) y la envia como respuesta en el hilo, solo al remitente, como maximo una vez.",
  "archivo": "recursos/flujos/mppp-env.json",
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
  "hijos": [],
  "activar": true
}
```

## 3. Precondiciones

- Las connection references `sanic_mppp_conr_dataverse` y `sanic_mppp_conr_outlook` existen y estan
  conectadas.
- La variable `sanic_mppp_ev_buzoningesta` existe y tiene valor.
- Las tablas Solicitud y Bitacora existen.
