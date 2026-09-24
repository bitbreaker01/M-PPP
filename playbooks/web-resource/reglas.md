# Playbook: web-resource · WR - MPPP - SVG - Reglas

Inventario 12.1. El contenido NO va en este playbook: vive en
`recursos/svg/reglas.svg`, se edita y se revisa como un archivo, y la herramienta lo sube.

## 1. Identidad

```json
{
  "tipo_playbook": "web-resource",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.1",
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
  "nombre": "sanic_mppp_wr_svg_reglas",
  "displayname": "WR - MPPP - SVG - Reglas",
  "descripcion": "Entrada de sitemap Reglas.",
  "recurso": "SVG",
  "archivo": "recursos/svg/reglas.svg"
}
```

## 3. Precondiciones

- El archivo existe en el repositorio y es un SVG valido.
