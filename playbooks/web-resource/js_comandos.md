# Playbook: web-resource · WR - MPPP - JS - Comandos

Inventario 12.5. El contenido NO va en este playbook: vive en
`recursos/js/comandos.js`, se edita y se revisa como un archivo, y la herramienta lo sube.

Trae los OCHO comandos. Los cuatro que piden un texto (Rechazada en AS400, Anular, Devolver,
Revisado) abren el dialogo de motivo: el formulario de `sanic_mppp_tbl_motivoaccion` en modo
creacion dentro de un dialogo (DA-03 corregida el 2026-09-22), leen el motivo del registro que
devuelve `savedEntityReference[0]` y lo borran.

## 1. Identidad

```json
{
  "tipo_playbook": "web-resource",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.5",
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
  "tipo": "web-resource",
  "nombre": "sanic_mppp_wr_js_comandos",
  "displayname": "WR - MPPP - JS - Comandos",
  "descripcion": "Funciones de los ocho botones de la barra de comandos de Fila y Solicitud (12.5), incluido el dialogo de motivo (12.4).",
  "recurso": "JS",
  "archivo": "recursos/js/comandos.js"
}
```

## 3. Precondiciones

- El archivo `recursos/js/comandos.js` existe en el repositorio.
