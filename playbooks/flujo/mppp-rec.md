# Playbook: flujo · MPPP-REC

Inventario 11.2. Disenado en `07-flujos.md` seccion 2.

**Sin condiciones ni logica**: una sola accion, llamar a `MPPP-ING`. Todo lo que este flujo sabe
hacer lo tiene que saber hacer tambien la vigilancia (DF-02).

`includeAttachments = false`: los adjuntos los trae `MPPP-ING`. Asi el disparador queda liviano y
no falla por tamano.

Concurrencia del disparador en 5: dos correos distintos no se pisan, cada uno tiene su clave.

## 1. Identidad

```json
{
  "tipo_playbook": "flujo",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "11.2",
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
  "nombre": "Cloud Flow - MPPP - REC - Recibir correo nuevo",
  "descripcion": "Por cada correo nuevo en la bandeja del buzon compartido, llama a MPPP-ING.",
  "archivo": "recursos/flujos/mppp-rec.json",
  "conexiones": {
    "outlook": {
      "referencia": "sanic_mppp_conr_outlook",
      "api": "shared_office365"
    }
  },
  "variables": [
    "sanic_mppp_ev_buzoningesta"
  ],
  "hijos": [
    "Cloud Flow - MPPP - ING - Ingerir y validar correo"
  ],
  "activar": true
}
```

## 3. Precondiciones

- `MPPP-ING` ya existe y esta ACTIVADO (11.1): un padre activo no puede llamar a un hijo que nunca
  se publico (`ChildFlowNeverPublished`).
- La connection reference `sanic_mppp_conr_outlook` existe y esta conectada.
- `sanic_mppp_ev_buzoningesta` tiene valor.
