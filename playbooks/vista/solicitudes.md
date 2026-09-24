# Playbook: vista · Solicitudes

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Todas las solicitudes con sus contadores. Entrada de sitemap Solicitudes.

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
  "nombre": "Solicitudes",
  "tabla": "sanic_mppp_tbl_solicitud",
  "clase": "Publica",
  "descripcion": "Todas las solicitudes con sus contadores. Entrada de sitemap Solicitudes.",
  "pordefecto": true,
  "columnas": [
    {
      "nombre": "sanic_nombre",
      "ancho": 140
    },
    {
      "nombre": "sanic_fecharecibido",
      "ancho": 140
    },
    {
      "nombre": "sanic_remitente",
      "ancho": 220
    },
    {
      "nombre": "sanic_estadoprocesamiento",
      "ancho": 140
    },
    {
      "nombre": "sanic_filastotales",
      "ancho": 90
    },
    {
      "nombre": "sanic_filasvalidas",
      "ancho": 90
    },
    {
      "nombre": "sanic_filasrechazadas",
      "ancho": 100
    },
    {
      "nombre": "sanic_fechacerrada",
      "ancho": 140
    }
  ],
  "orden": [
    {
      "columna": "sanic_fecharecibido",
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
