# Playbook: tabla · sanic_mppp_tbl_motivoaccion

Inventario 3.12. **Tabla tecnica, no de negocio.** Existe solo para que un comando de la barra
pueda pedirle un texto al usuario: su formulario de creacion rapida ES el dialogo de motivo
(12.4, DA-03 corregida el 2026-09-22).

Por que existe: una pagina custom abierta como dialogo **no devuelve ningun valor** al comando
que la abrio, y tampoco admite recibir varias filas. `pageType: "entityrecord"` en modo create
si devuelve `savedEntityReference[0]`, asi que el comando lee el motivo de este registro y lo
aplica a TODAS las filas seleccionadas. Ver `05-app-model-driven.md` DA-03.

Ciclo de vida: el comando crea el registro (via el dialogo), lo lee y lo **borra**. No queda
historia aca: el motivo vive en `sanic_mensaje` de la fila o en la Bitacora.

Sin auditoria y sin notas: no hay nada que auditar en un registro que dura segundos.

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.12",
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
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_motivoaccion",
  "displayname": "Motivo de accion",
  "displayname_plural": "Motivos de accion",
  "descripcion": "Tabla tecnica: transporta el motivo que el usuario escribe en el dialogo de un comando (Rechazada en AS400, Anular, Devolver, Revisado). No es dato de negocio: el motivo queda en la fila o en la bitacora, y el comando borra este registro despues de leerlo.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Accion",
    "descripcion": "No se usa: el contexto de la accion va en el TITULO del dialogo, que es seguro y documentado. Prellenar columnas con 'data' de navigateTo puede fallar ('Invalid parameters cause an error') y no hay como probarlo sin navegador.",
    "largo": 200,
    "requerida": false,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_motivo",
      "displayname": "Motivo",
      "descripcion": "El texto que el usuario escribe. El comando lo copia a 'sanic_mensaje' de cada fila afectada.",
      "tipo": "memo",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 2000
    }
  ]
}
```

Decisiones que este playbook toma:

| Decisión | Valor | Por qué |
|---|---|---|
| Propiedad | usuario | Cada quien crea los suyos y los borra el comando; no hace falta que sean de organizacion |
| Auditoría | no | El registro dura segundos y no es dato de negocio |
| `sanic_motivo` obligatoria | sí | Es todo el proposito del dialogo. La obligatoriedad la impone el formulario y la plataforma, no un plugin |
| Largo 2000 | | El mismo tope que `sanic_mensaje` de la fila, que es donde termina el texto |

## 3. Precondiciones

- La solucion existe y es unmanaged.
