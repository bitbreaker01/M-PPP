# Playbook: flujo · MPPP-ING

Inventario 11.1. Disenado en `07-flujos.md` seccion 3. La definicion vive en
`recursos/flujos/mppp-ing.json`.

**Es un flujo HIJO**: lo llaman `MPPP-REC` y `MPPP-VIG` (DF-02). Entradas: `text` = identificador
de Outlook del mensaje, `text_1` = el VALOR de la opcion `sanic_origen` del que llama
(159460001 MPPP-REC, 159460005 MPPP-VIG).

**El orden es deliberado** (seccion 3): el correo se mueve DESPUES de tener la Solicitud y sus
archivos, y ANTES de clasificar y validar. Si el flujo se cae antes de mover, el correo sigue en la
bandeja y la vigilancia lo reingresa; la clave unica evita el duplicado. Si se cae despues, la
Solicitud queda en Ingresada y la vigilancia retoma desde la clasificacion: las dos API son
idempotentes.

`Guardar_el_identificador_nuevo` corre tambien si mover fallo (DF-04): el identificador de Outlook
CAMBIA al mover, y si no se pudo mover sirve el original.

Todo va dentro de un ambito Try; el Catch escribe la Bitacora con el evento Error y **los nombres
de las acciones que fallaron, nunca el cuerpo del correo ni datos de la plantilla**.

## Dos cosas que NO estan verificadas, y hay que mirarlas en la primera corrida

1. **`ExportEmailV2`**: es el unico `operationId` de este flujo que no aparece en ningun flujo real
   del entorno; se dedujo del patron de los demas (`GetEmailV2`, `MoveV2`, `ReplyToV3`). Si la
   accion "Export email (V2)" tiene otro nombre interno, el paso falla y hay que corregirlo. Sin el
   `.eml` no hay clasificacion, porque es lo que lee el plugin liviano (DF-08).
2. **`sanic_mppp_ev_carpetaprocesados` no tiene valor todavia.** `MoveV2` espera un `folderPath`,
   o sea el NOMBRE de la carpeta (verificado: otro flujo del entorno usa `"Procesados"`), no un
   identificador. Hasta que se cargue, el paso de mover falla; el flujo sigue igual y la Solicitud
   queda usable.

## 1. Identidad

```json
{
  "tipo_playbook": "flujo",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "11.1",
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
  "nombre": "Cloud Flow - MPPP - ING - Ingerir y validar correo",
  "descripcion": "Hijo. Crea la Solicitud, sube el correo crudo y el Excel, mueve el correo, lo clasifica y, si corresponde, lo valida.",
  "archivo": "recursos/flujos/mppp-ing.json",
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
    "sanic_mppp_ev_buzoningesta",
    "sanic_mppp_ev_carpetaprocesados"
  ],
  "hijos": [],
  "activar": true
}
```

## 3. Precondiciones

- Las dos connection references existen y estan conectadas.
- Las variables `sanic_mppp_ev_buzoningesta` y `sanic_mppp_ev_carpetaprocesados` existen.
- Las Custom API `sanic_mppp_capi_clasificarcorreo` y `sanic_mppp_capi_validarsolicitud` existen.
- Las tablas Solicitud y Bitacora existen.
