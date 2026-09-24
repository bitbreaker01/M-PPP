# Playbook: vista · Correos autorizados sobre este plan

Inventario 12.2 (`05-app-model-driven.md` §vistas, lista cerrada de 17).

Subgrilla del formulario de Plan: los correos que pueden modificar ese plan.

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
  "nombre": "Correos autorizados sobre este plan",
  "tabla": "sanic_mppp_tbl_autorizacionplan",
  "clase": "Publica",
  "descripcion": "Subgrilla del formulario de Plan: los correos que pueden modificar ese plan.",
  "pordefecto": false,
  "columnas": [
    {
      "nombre": "sanic_nombre",
      "ancho": 200,
      "enlace": "autorizado"
    },
    {
      "nombre": "sanic_fechadocumento",
      "ancho": 140
    }
  ],
  "orden": [
    {
      "columna": "sanic_fechadocumento",
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
    "enlaces": [
      {
        "tabla": "sanic_mppp_tbl_autorizado",
        "de": "sanic_mppp_tbl_autorizadoid",
        "a": "sanic_autorizadoid",
        "alias": "autorizado"
      }
    ]
  }
}
```

## 3. Precondiciones

- La tabla y sus relaciones existen (P-03, P-04).
