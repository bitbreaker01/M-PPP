# Playbook: custom-api · sanic_mppp_capi_validarsolicitud

Inventario 8.1. Contrato en `diseno/03-contratos-custom-api.md` §1.

Precondición: el paquete `sanic_mppp_pkg_plugins` tiene que estar registrado
(`playbooks/paquete-plugins/sanic_mppp_pkg_plugins.md`).

## 1. Identidad

```json
{
  "tipo_playbook": "custom-api",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "8.1",
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
  "tipo": "custom-api",
  "nombre": "sanic_mppp_capi_validarsolicitud",
  "displayname": "CAPI - MPPP - Validar solicitud",
  "descripcion": "Valida una Solicitud ingresada: abre la plantilla, evalua las reglas y deja las filas guardadas con su estado.",
  "plugintype": "Sanic.Mppp.Plugins.Api.ValidarSolicitudApi",
  "esfuncion": false,
  "esprivada": false,
  "binding": "Global",
  "pasosdeterceros": "None",
  "habilitadaenflujos": false,
  "privilegio": "prvCreatesanic_mppp_tbl_solicitud",
  "entrada": [
    {
      "nombre": "solicitudid",
      "displayname": "CAPI_IP - MPPP - Solicitud id",
      "descripcion": "Identificador de la Solicitud a validar. Solo el identificador: el Excel se lee de sanic_exceloriginal (D-31).",
      "tipo": "Guid",
      "opcional": false
    }
  ],
  "salida": [
    {
      "nombre": "estado",
      "displayname": "CAPI_OP - MPPP - Estado",
      "descripcion": "Valor del choice EstadoSolicitud en que quedo la Solicitud.",
      "tipo": "Integer"
    },
    {
      "nombre": "yaprocesada",
      "displayname": "CAPI_OP - MPPP - Ya procesada",
      "descripcion": "Verdadero si no hizo nada porque la Solicitud ya estaba validada.",
      "tipo": "Boolean"
    },
    {
      "nombre": "filastotales",
      "displayname": "CAPI_OP - MPPP - Filas totales",
      "descripcion": "Cantidad de filas leidas de la plantilla.",
      "tipo": "Integer"
    },
    {
      "nombre": "filasvalidas",
      "displayname": "CAPI_OP - MPPP - Filas validas",
      "descripcion": "Cantidad de filas que quedaron en estado Validada.",
      "tipo": "Integer"
    },
    {
      "nombre": "filasrechazadas",
      "displayname": "CAPI_OP - MPPP - Filas rechazadas",
      "descripcion": "Cantidad de filas que no quedaron en estado Validada.",
      "tipo": "Integer"
    },
    {
      "nombre": "resumen",
      "displayname": "CAPI_OP - MPPP - Resumen",
      "descripcion": "Una linea para el run history del flujo. Nunca trae datos del cliente.",
      "tipo": "String"
    }
  ]
}
```

## 3. Precondiciones

- El paquete de plugins registrado, con `Sanic.Mppp.Plugins.Api.ValidarSolicitudApi` entre sus `plugintype`.
- El privilegio `prvCreatesanic_mppp_tbl_solicitud` existe. D-9.

## 4. Qué es inmutable

`uniquename`, `binding`, `esfuncion`, `pasosdeterceros`, `habilitadaenflujos`; y de cada parámetro,
`nombre`, `tipo` y `opcional`. Un error en cualquiera de esos obliga a borrar la API entera y rehacerla.
