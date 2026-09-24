# Playbook: vista · Parametros activos

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Parametros de configuracion vigentes.

El `fetchxml` y el `layoutxml` NO se escriben aca: los genera la herramienta
desde las columnas, el orden y el filtro.

## 1. Identidad

```json
{
  "tipo_playbook": "vista",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.2",
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
  "tipo": "vista",
  "nombre": "Parametros activos",
  "tabla": "sanic_mppp_tbl_parametro",
  "clase": "Publica",
  "descripcion": "Parametros de configuracion vigentes.",
  "pordefecto": true,
  "columnas": [
    {
      "nombre": "sanic_nombre",
      "ancho": 260
    },
    {
      "nombre": "sanic_version",
      "ancho": 80
    },
    {
      "nombre": "sanic_tipo",
      "ancho": 100
    },
    {
      "nombre": "sanic_descripcion",
      "ancho": 380
    }
  ],
  "orden": [
    {
      "columna": "sanic_nombre",
      "sentido": "asc"
    },
    {
      "columna": "sanic_version",
      "sentido": "desc"
    }
  ],
  "filtro": {
    "tipo": "and",
    "condiciones": [
      {
        "columna": "statecode",
        "operador": "eq",
        "valores": [
          0
        ]
      }
    ],
    "enlaces": []
  }
}
```

## 3. Precondiciones

- La tabla y sus relaciones existen (P-03, P-04).
