# Playbook: datos · prueba de humo · plan

Datos FICTICIOS para la prueba de humo de punta a punta (P-09 §B). Todo lleva `ZZ` o
`zzensayo` para que se distinga de un dato real de un vistazo. No son datos de clientes.

## 1. Identidad

```json
{
  "tipo_playbook": "datos",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "prueba-humo",
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
  "tipo": "datos",
  "tabla": "sanic_mppp_tbl_plan",
  "clave": [
    "sanic_codigo"
  ],
  "filas": [
    {
      "sanic_codigo": "ZZ01",
      "sanic_tipoformato": {
        "choice": "sanic_mppp_ch_tipoformatoplan",
        "etiqueta": "11"
      },
      "sanic_moneda": {
        "choice": "sanic_mppp_ch_moneda",
        "etiqueta": "USD"
      },
      "sanic_clienteid": {
        "lookup": {
          "tabla": "sanic_mppp_tbl_cliente",
          "clave": {
            "sanic_cifbac": "999000111"
          }
        }
      }
    }
  ]
}
```

## 3. Precondiciones

- Se cargan EN ESTE ORDEN: cliente, plan, autorizado, autorizacionplan.
