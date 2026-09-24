# Playbook: vista · Reglas activas

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Reglas de validacion vigentes.

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
  "nombre": "Reglas activas",
  "tabla": "sanic_mppp_tbl_regla",
  "clase": "Publica",
  "descripcion": "Reglas de validacion vigentes.",
  "pordefecto": true,
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "ancho": 240
    },
    {
      "nombre": "sanic_nivel",
      "ancho": 120
    },
    {
      "nombre": "sanic_orden",
      "ancho": 80
    },
    {
      "nombre": "sanic_efecto",
      "ancho": 140
    },
    {
      "nombre": "sanic_dependede",
      "ancho": 260
    }
  ],
  "orden": [
    {
      "columna": "sanic_nivel",
      "sentido": "asc"
    },
    {
      "columna": "sanic_orden",
      "sentido": "asc"
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
