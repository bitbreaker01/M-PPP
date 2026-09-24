# Playbook: vista · Por aprobar

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Filas digitadas esperando la aprobacion del supervisor. Entrada de sitemap Por aprobar.

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
  "nombre": "Por aprobar",
  "tabla": "sanic_mppp_tbl_fila",
  "clase": "Publica",
  "descripcion": "Filas digitadas esperando la aprobacion del supervisor. Entrada de sitemap Por aprobar.",
  "pordefecto": false,
  "columnas": [
    {
      "nombre": "sanic_solicitudid",
      "ancho": 130
    },
    {
      "nombre": "sanic_numerofila",
      "ancho": 70
    },
    {
      "nombre": "sanic_estado",
      "ancho": 130
    },
    {
      "nombre": "sanic_gestion",
      "ancho": 110
    },
    {
      "nombre": "sanic_clasificacion",
      "ancho": 100
    },
    {
      "nombre": "sanic_planid",
      "ancho": 90
    },
    {
      "nombre": "sanic_referencia",
      "ancho": 170
    },
    {
      "nombre": "sanic_nombrebeneficiario",
      "ancho": 200
    },
    {
      "nombre": "sanic_tipoidentificacion",
      "ancho": 90
    },
    {
      "nombre": "sanic_numeroidentificacion",
      "ancho": 140
    },
    {
      "nombre": "sanic_numerocuenta",
      "ancho": 140
    },
    {
      "nombre": "sanic_moneda",
      "ancho": 80
    },
    {
      "nombre": "sanic_banco",
      "ancho": 110
    },
    {
      "nombre": "sanic_digitadapor",
      "ancho": 160
    },
    {
      "nombre": "sanic_fechadigitada",
      "ancho": 130
    }
  ],
  "orden": [
    {
      "columna": "sanic_fechadigitada",
      "sentido": "asc"
    }
  ],
  "filtro": {
    "tipo": "and",
    "condiciones": [
      {
        "columna": "sanic_estado",
        "operador": "eq",
        "valores": [
          159460004
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
