# Playbook: vista · Por clasificar

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Correos que nadie reconocio o que no son nuevos, esperando que un ejecutivo los atienda o los descarte.

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
  "nombre": "Por clasificar",
  "tabla": "sanic_mppp_tbl_solicitud",
  "clase": "Publica",
  "descripcion": "Correos que nadie reconocio o que no son nuevos, esperando que un ejecutivo los atienda o los descarte.",
  "pordefecto": false,
  "columnas": [
    {
      "nombre": "sanic_fecharecibido",
      "ancho": 140
    },
    {
      "nombre": "sanic_remitente",
      "ancho": 220
    },
    {
      "nombre": "sanic_asunto",
      "ancho": 280
    },
    {
      "nombre": "sanic_motivoclasificacion",
      "ancho": 240
    },
    {
      "nombre": "sanic_cantidadadjuntos",
      "ancho": 90
    }
  ],
  "orden": [
    {
      "columna": "sanic_fecharecibido",
      "sentido": "asc"
    }
  ],
  "filtro": {
    "tipo": "and",
    "condiciones": [
      {
        "columna": "sanic_estadoprocesamiento",
        "operador": "in",
        "valores": [
          159460002,
          159460008
        ]
      },
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
