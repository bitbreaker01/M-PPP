# Playbook: vista · Reglas evaluadas

Inventario 12.2, vista 19. **Agregada el 2026-09-23**: la subgrilla "Reglas" del formulario de
Solicitud apuntaba a `Active Resultados de reglas`, la vista que genera Dataverse sola, que solo
trae `sanic_nombre` y `createdon`. En pantalla se veian dos renglones `RES-00000010XX` con su fecha
y nada mas: no se podia saber que regla se evaluo ni que dio. Es el mismo caso que ya se habia
resuelto con la vista `Filas` (18) para la otra subgrilla del mismo formulario.

El orden es por `sanic_orden`, que es el orden real de evaluacion del motor: leer los resultados
salteados o alfabeticos no dice nada, leerlos en el orden en que corrieron cuenta la historia de
por que la Solicitud termino como termino.

`sanic_reglacodigo` se muestra en vez del lookup `sanic_reglaid` porque es el codigo que el motor
copio al evaluar: si despues alguien renombra o desactiva la regla del catalogo, el resultado
historico sigue diciendo contra que se evaluo. Un lookup mostraria el nombre de hoy, no el de
entonces.

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
  "nombre": "Reglas evaluadas",
  "tabla": "sanic_mppp_tbl_resultadoregla",
  "clase": "Publica",
  "descripcion": "Resultados de reglas activos, en el orden en que el motor los evaluo, con su resultado, el efecto que aplico y la razon. Subgrilla Reglas del formulario de Solicitud.",
  "pordefecto": false,
  "columnas": [
    {
      "nombre": "sanic_orden",
      "ancho": 60
    },
    {
      "nombre": "sanic_reglacodigo",
      "ancho": 220
    },
    {
      "nombre": "sanic_resultado",
      "ancho": 120
    },
    {
      "nombre": "sanic_efectoaplicado",
      "ancho": 130
    },
    {
      "nombre": "sanic_razon",
      "ancho": 320
    },
    {
      "nombre": "sanic_fechaevaluacion",
      "ancho": 140
    }
  ],
  "orden": [
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

- La tabla ResultadoRegla existe (P-03) con sus columnas `sanic_orden`, `sanic_reglacodigo`,
  `sanic_resultado`, `sanic_efectoaplicado`, `sanic_razon` y `sanic_fechaevaluacion`.
- Despues de crear la vista hay que volver a aplicar el formulario de Solicitud, que es el que
  apunta la subgrilla: crear la vista sola no cambia lo que se ve en pantalla.
