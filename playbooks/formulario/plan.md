# Playbook: formulario · Plan

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
  "nombre": "Plan",
  "tabla": "sanic_mppp_tbl_plan",
  "solo_lectura": false,
  "descripcion": "Formulario principal de Plan. Lo edita el Administrador de planes.",
  "pestana": "General",
  "encabezado": [
    "sanic_codigo",
    "sanic_clienteid"
  ],
  "secciones": [
    {
      "titulo": "Datos",
      "campos": [
        "sanic_nombre",
        "sanic_moneda",
        "sanic_tipoformato"
      ]
    },
    {
      "titulo": "Correos autorizados sobre este plan",
      "subgrilla": {
        "tabla": "sanic_mppp_tbl_autorizacionplan",
        "lookup": "sanic_planid",
        "vista": "Correos autorizados sobre este plan"
      }
    }
  ]
}
```

## 3. Precondiciones

- La tabla, sus columnas y las vistas de las subgrillas existen.
