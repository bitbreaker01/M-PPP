# Playbook: vista · Filas

Inventario 12.2, vista 18. **Agregada el 2026-09-22**: al armar los
formularios se vio que el sitemap tiene la entrada "Filas -> Todas las Filas" y que la
Solicitud lleva una subgrilla con TODAS sus filas, y ninguna de las 17 anteriores las muestra
(las cinco de Fila filtran por estado).

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
  "nombre": "Filas",
  "tabla": "sanic_mppp_tbl_fila",
  "clase": "Publica",
  "descripcion": "Todas las filas activas, con su estado. Entrada de sitemap Filas y subgrilla del formulario de Solicitud.",
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
      "nombre": "sanic_mensaje",
      "ancho": 260
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

- La tabla Fila existe (P-03).
