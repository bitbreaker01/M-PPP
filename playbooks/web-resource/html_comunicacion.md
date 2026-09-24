# Playbook: web-resource · WR - MPPP - HTML - Comunicacion enviada

Inventario 12.9. El contenido NO va en este playbook: vive en
`recursos/html/comunicacion.html`, se edita y se revisa como un archivo, y la herramienta lo sube.

**Para que existe.** `sanic_acusecontenido` y `sanic_respuestafinalcontenido` guardan un documento
HTML completo. En un campo de formulario comun se ve el markup crudo, ilegible justo cuando mas
importa: cuando un cliente del banco reclama por lo que recibio.

**Por que un iframe y no el editor de texto enriquecido.** El control nativo SIEMPRE sanitiza el
contenido en modo lectura (Learn, "rich text editor control"): le quita `DOCTYPE`, `html`, `head` y
`body`. Lo que se ve es parecido, no identico. Aca el objetivo es ver el documento EXACTO.

**Seguridad.** El `iframe` va con `sandbox` VACIO: sin scripts, sin formularios, sin acceso al
mismo origen, sin navegacion. El contenido lo genera codigo nuestro, pero igual se trata como no
confiable.

Solo lee, con `Xrm.WebApi`. Nunca escribe.

## 1. Identidad

```json
{
  "tipo_playbook": "web-resource",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.9",
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
  "nombre": "sanic_mppp_wr_html_comunicacion",
  "displayname": "WR - MPPP - HTML - Comunicacion enviada",
  "descripcion": "Muestra TAL CUAL el correo que se le envio al cliente (acuse y respuesta final), dentro de un iframe con sandbox.",
  "recurso": "HTML",
  "archivo": "recursos/html/comunicacion.html"
}
```

## 3. Precondiciones

- El archivo `recursos/html/comunicacion.html` existe en el repositorio.
- La tabla Solicitud y sus columnas de contenido existen.
