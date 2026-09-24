# Playbook: custom-api · sanic_mppp_capi_clasificarcorreo

Inventario 8.0. Contrato en `diseno/03-contratos-custom-api.md` §0.

Precondición: el paquete `sanic_mppp_pkg_plugins` tiene que estar registrado
(`playbooks/paquete-plugins/sanic_mppp_pkg_plugins.md`), porque esta API apunta
a un `plugintype` que solo existe después de subir el paquete.

## 1. Identidad

```json
{
  "tipo_playbook": "custom-api",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "8.0",
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
  "nombre": "sanic_mppp_capi_clasificarcorreo",
  "displayname": "CAPI - MPPP - Clasificar correo",
  "descripcion": "Clasifica una Solicitud recien ingresada y decide si el flujo sigue con la validacion.",
  "plugintype": "Sanic.Mppp.Plugins.Api.ClasificarCorreoApi",
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
      "descripcion": "Identificador de la Solicitud a clasificar.",
      "tipo": "Guid",
      "opcional": false
    }
  ],
  "salida": [
    {
      "nombre": "procesar",
      "displayname": "CAPI_OP - MPPP - Procesar",
      "descripcion": "Verdadero: el flujo sigue con la validacion. Falso: el flujo termina y no se le responde a nadie.",
      "tipo": "Boolean"
    },
    {
      "nombre": "clasificacion",
      "displayname": "CAPI_OP - MPPP - Clasificacion",
      "descripcion": "nuevo, reenvio, respuesta, remitente_no_reconocido o ilegible.",
      "tipo": "String"
    },
    {
      "nombre": "yaprocesada",
      "displayname": "CAPI_OP - MPPP - Ya procesada",
      "descripcion": "Verdadero si la Solicitud ya no estaba en Ingresada.",
      "tipo": "Boolean"
    }
  ]
}
```

## 3. Precondiciones

- El paquete de plugins registrado, con `Sanic.Mppp.Plugins.Api.ClasificarCorreoApi` entre sus `plugintype`.
- El privilegio `prvCreatesanic_mppp_tbl_solicitud` existe (lo crea la tabla Solicitud, ya construida). D-9.

## 4. Qué es inmutable

`uniquename`, `binding`, `esfuncion`, `pasosdeterceros`, `habilitadaenflujos`; y de cada parámetro,
`nombre`, `tipo` y `opcional`. Un error en cualquiera de esos obliga a borrar la API entera y rehacerla.
