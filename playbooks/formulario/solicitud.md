# Playbook: formulario · Solicitud

Inventario 12.3 (`05-app-model-driven.md` §formularios). El playbook no declara etiquetas
ni classid: la herramienta los resuelve contra la metadata de la tabla.

## 1. Identidad

```json
{
  "tipo_playbook": "formulario",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.3",
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
  "tipo": "formulario",
  "nombre": "Solicitud",
  "tabla": "sanic_mppp_tbl_solicitud",
  "solo_lectura": true,
  "descripcion": "Formulario principal de Solicitud. Solo lectura: los estados los mueven el plugin y los botones.",
  "pestana": "General",
  "encabezado": [
    "sanic_nombre",
    "sanic_estadoprocesamiento",
    "sanic_remitente"
  ],
  "secciones": [
    {
      "titulo": "Correo",
      "campos": [
        "sanic_fecharecibido",
        "sanic_asunto",
        "sanic_messageid",
        "sanic_correocrudo",
        "sanic_exceloriginal",
        "sanic_cantidadadjuntos",
        "sanic_cantidadexcel",
        "sanic_motivoclasificacion"
      ]
    },
    {
      "titulo": "Filas",
      "subgrilla": {
        "tabla": "sanic_mppp_tbl_fila",
        "lookup": "sanic_solicitudid",
        "vista": "Filas"
      }
    },
    {
      "titulo": "Reglas",
      "subgrilla": {
        "tabla": "sanic_mppp_tbl_resultadoregla",
        "lookup": "sanic_solicitudid",
        "vista": "Reglas evaluadas"
      }
    },
    {
      "titulo": "Comunicaciones",
      "campos": [
        "sanic_fechavalidada",
        "sanic_filastotales",
        "sanic_filasvalidas",
        "sanic_filasrechazadas",
        "sanic_acusecontenido",
        "sanic_fechaacuseenviado",
        "sanic_respuestafinalcontenido",
        "sanic_fecharespuestafinalenviada",
        "sanic_fechacerrada"
      ]
    },
    {
      "titulo": "Correo enviado al cliente",
      "webresource": {
        "nombre": "sanic_mppp_wr_html_comunicacion",
        "alto": 14
      }
    },
    {
      "titulo": "Revision",
      "campos": [
        "sanic_requiererevision",
        "sanic_motivorevision",
        "sanic_reintentosvalidacion",
        "sanic_versionparametros"
      ]
    },
    {
      "titulo": "Bitacora",
      "subgrilla": {
        "tabla": "sanic_mppp_tbl_bitacora",
        "lookup": "sanic_solicitudid",
        "vista": "Eventos de la solicitud"
      }
    }
  ]
}
```

## 3. Precondiciones

- El web resource `sanic_mppp_wr_html_comunicacion` existe (12.9): muestra el correo enviado al cliente **tal cual**, dentro de un `iframe` con sandbox.

- La tabla, sus columnas y las vistas de las subgrillas existen.
