# Playbook: flujo · MPPP-COM

Inventario 11.4. Disenado en `07-flujos.md` seccion 4.

Sin logica propia: una sola accion, llamar a `MPPP-ENV` (DF-02). Todo lo que este flujo sabe hacer
lo tiene que saber hacer tambien la vigilancia.

**Concurrencia 1** (DF-06): el "como maximo una vez" depende de que dos ejecuciones no lean a la
vez "todavia no iniciado". Con unos cientos de correos por mes, serializar no cuesta nada.

El disparador filtra por estado en el servidor (`filterexpression`), asi que no se ejecuta con cada
actualizacion de la Solicitud (D-24) ni con las escrituras de `MPPP-ENV`, que solo tocan el estado
para cerrar, y Cerrada queda fuera del filtro.

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
  "nombre": "Cloud Flow - MPPP - COM - Detectar comunicacion pendiente",
  "descripcion": "Cuando una Solicitud queda En proceso, Rechazada o Procesada, llama a MPPP-ENV.",
  "archivo": "recursos/flujos/mppp-com.json",
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

- `MPPP-ENV` ya existe (11.3): un padre no se puede construir antes que su hijo.
- La connection reference `sanic_mppp_conr_dataverse` existe y esta conectada.
