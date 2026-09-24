# Playbook: formulario · Fila

Inventario 12.3 (`05-app-model-driven.md` §formularios).

**Todo de solo lectura** (DA-07): el estado se cambia con los botones de la barra, y la lista
blanca del plugin rechazaria cualquier otra edicion (`04` §1). El playbook no declara etiquetas
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
  "nombre": "Fila",
  "tabla": "sanic_mppp_tbl_fila",
  "descripcion": "Formulario principal de Fila. Todo de solo lectura: el estado se cambia con los botones de la barra.",
  "pestana": "General",
  "solo_lectura": true,
  "encabezado": [
    "sanic_estado",
    "sanic_solicitudid",
    "sanic_numerofila"
  ],
  "secciones": [
    {
      "titulo": "Gestion",
      "campos": [
        "sanic_gestion",
        "sanic_clasificacion",
        "sanic_planid",
        "sanic_nombrebeneficiario",
        "sanic_tipoidentificacion",
        "sanic_numeroidentificacion",
        "sanic_numerocuenta",
        "sanic_moneda",
        "sanic_banco",
        "sanic_referencia",
        "sanic_referenciarecibida"
      ]
    },
    {
      "titulo": "Resultado",
      "campos": [
        "sanic_mensaje"
      ]
    },
    {
      "titulo": "Trazabilidad",
      "campos": [
        "sanic_fechavalidada",
        "sanic_digitadapor",
        "sanic_fechadigitada",
        "sanic_aprobadapor",
        "sanic_fechaaprobada"
      ]
    }
  ]
}
```

## 3. Precondiciones

- La tabla y sus columnas existen (P-03).
