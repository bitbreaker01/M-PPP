# Playbook: vista · Mis clientes - por digitar

Inventario 12.2, vista 1 de 17 (`05-app-model-driven.md` §vistas).

La mas dificil de las 17 y por eso la primera: el filtro "mis clientes" son DOS saltos
(Fila -> Plan -> Cliente) y el dueno se compara con quien mira (`eq-userid`), no con un
usuario fijo. Si esta anda, el resto son variaciones mas simples.

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
  "nombre": "Mis clientes - por digitar",
  "tabla": "sanic_mppp_tbl_fila",
  "clase": "Publica",
  "descripcion": "Filas validadas de los clientes cuyo ejecutivo es quien mira. Entrada de sitemap Por digitar.",
  "pordefecto": true,
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
      "nombre": "sanic_fechavalidada",
      "ancho": 130
    }
  ],
  "orden": [
    {
      "columna": "sanic_solicitudid",
      "sentido": "asc"
    },
    {
      "columna": "sanic_numerofila",
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
          159460003
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
    "enlaces": [
      {
        "tabla": "sanic_mppp_tbl_plan",
        "de": "sanic_mppp_tbl_planid",
        "a": "sanic_planid",
        "alias": "plan",
        "enlaces": [
          {
            "tabla": "sanic_mppp_tbl_cliente",
            "de": "sanic_mppp_tbl_clienteid",
            "a": "sanic_clienteid",
            "alias": "cliente",
            "condiciones": [
              {
                "columna": "ownerid",
                "operador": "eq-userid"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

## 3. Precondiciones

- Las tablas Fila, Plan y Cliente existen con sus relaciones (P-03 y P-04, hechas).
- El `fetchxml` y el `layoutxml` NO se escriben aca: los genera la herramienta desde las
  columnas, el orden y el filtro de arriba.
