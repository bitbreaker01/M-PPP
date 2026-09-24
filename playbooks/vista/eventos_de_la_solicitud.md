# Playbook: vista · Eventos de la solicitud

Inventario 12.2, vista 20. **Agregada el 2026-09-23**, por la misma razon que `Reglas evaluadas`
(19): la subgrilla "Bitacora" del formulario de Solicitud apuntaba a `Active Bitácoras`, la vista
que genera Dataverse sola, que solo trae `sanic_nombre` y `createdon`. En pantalla se veian cinco
renglones `BIT-00000010XX` con la misma hora y nada mas.

Una bitacora existe para contestar "que paso con este caso, en que orden y quien lo hizo". Sin
evento, origen ni actor no contesta nada.

**Orden ascendente, y con desempate.** Se lee de arriba hacia abajo como la historia del caso, no
al reves. Y `sanic_fechaevento` empata seguido: los cinco eventos de la captura que motivo esta
vista eran todos de las 10:23. Por eso el segundo criterio es `sanic_nombre`, que es autonumerico
y por lo tanto refleja el orden real de creacion. Sin ese desempate, cinco eventos de la misma
hora salen en un orden que la plataforma elige sola y que puede cambiar entre refrescos.

`sanic_nombre` va como primera columna porque la herramienta exige que toda columna de orden se
muestre, y tiene razon: una grilla ordenada por algo que no se ve deja al que la lee sin entender
por que las filas estan en ese orden.

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
  "nombre": "Eventos de la solicitud",
  "tabla": "sanic_mppp_tbl_bitacora",
  "clase": "Publica",
  "descripcion": "Eventos activos de la Bitacora en orden cronologico, con el evento, su origen, quien actuo y el detalle. Subgrilla Bitacora del formulario de Solicitud.",
  "pordefecto": false,
  "columnas": [
    {
      "nombre": "sanic_nombre",
      "ancho": 130
    },
    {
      "nombre": "sanic_fechaevento",
      "ancho": 150
    },
    {
      "nombre": "sanic_evento",
      "ancho": 190
    },
    {
      "nombre": "sanic_origen",
      "ancho": 130
    },
    {
      "nombre": "sanic_actortexto",
      "ancho": 160
    },
    {
      "nombre": "sanic_numerofila",
      "ancho": 70
    },
    {
      "nombre": "sanic_detalle",
      "ancho": 300
    }
  ],
  "orden": [
    {
      "columna": "sanic_fechaevento",
      "sentido": "asc"
    },
    {
      "columna": "sanic_nombre",
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

- La tabla Bitacora existe (P-03) con sus columnas `sanic_fechaevento`, `sanic_evento`,
  `sanic_origen`, `sanic_actortexto`, `sanic_numerofila` y `sanic_detalle`.
- Despues de crear la vista hay que volver a aplicar el formulario de Solicitud, que es el que
  apunta la subgrilla: crear la vista sola no cambia lo que se ve en pantalla.
