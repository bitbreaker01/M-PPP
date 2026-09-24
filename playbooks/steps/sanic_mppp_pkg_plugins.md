# Playbook: steps · sanic_mppp_pkg_plugins

Inventario 8.2: los 20 `sdkmessageprocessingstep` del paquete. La tabla de
origen es `diseno/03-contratos-custom-api.md` §5.1, y este archivo lo genera
un script para que no se despeguen.

Precondicion: el paquete `sanic_mppp_pkg_plugins` registrado.

## 1. Identidad

```json
{
  "tipo_playbook": "steps",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "8.2",
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
  "tipo": "steps",
  "paquete": "sanic_mppp_pkg_plugins",
  "steps": [
    {
      "nombre": "MPPP - Lista blanca - Update de Fila",
      "descripcion": "Una persona solo puede escribir las columnas permitidas (04 §1).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.ListaBlancaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_fila",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 0,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Lista blanca - Update de Solicitud",
      "descripcion": "Una persona solo puede escribir las columnas permitidas (04 §1).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.ListaBlancaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_solicitud",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 0,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Create de Cliente",
      "descripcion": "Normaliza y valida el formato de sanic_cifbac, sanic_cifcom (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_cliente",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Update de Cliente",
      "descripcion": "Normaliza y valida el formato de sanic_cifbac, sanic_cifcom (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_cliente",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_cifbac",
        "sanic_cifcom"
      ],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Create de Plan",
      "descripcion": "Normaliza y valida el formato de sanic_codigo (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_plan",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Update de Plan",
      "descripcion": "Normaliza y valida el formato de sanic_codigo (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_plan",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_codigo"
      ],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Create de Autorizado",
      "descripcion": "Normaliza y valida el formato de sanic_nombre (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_autorizado",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Update de Autorizado",
      "descripcion": "Normaliza y valida el formato de sanic_nombre (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_autorizado",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_nombre"
      ],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Create de Parametro",
      "descripcion": "Normaliza y valida el formato de sanic_nombre (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_parametro",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Normalizar y validar - Update de Parametro",
      "descripcion": "Normaliza y valida el formato de sanic_nombre (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NormalizarYValidarStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_parametro",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_nombre"
      ],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Nombre calculado - Create de Plan",
      "descripcion": "Completa sanic_nombre con el valor calculado (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NombreCalculadoStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_plan",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 20,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Nombre calculado - Create de Autorizacionplan",
      "descripcion": "Completa sanic_nombre con el valor calculado (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NombreCalculadoStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_autorizacionplan",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 20,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Nombre calculado - Create de Fila",
      "descripcion": "Completa sanic_nombre con el valor calculado (03 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.NombreCalculadoStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_fila",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 20,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Transicion de Fila - Update",
      "descripcion": "Autoriza el cambio de estado de una Fila y escribe quien actuo (03 §4, D-25).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.TransicionDeFilaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_fila",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 1,
      "filtro": [
        "sanic_estado"
      ],
      "preimagen": {
        "alias": "PreImagen",
        "columnas": [
          "sanic_estado",
          "sanic_digitadapor",
          "sanic_solicitudid"
        ]
      }
    },
    {
      "nombre": "MPPP - Post transicion de Fila - Update",
      "descripcion": "Escribe la Bitacora de la transicion y evalua el cierre de la Solicitud (03 §4).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.PostTransicionDeFilaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_fila",
      "etapa": "PostOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_estado"
      ],
      "preimagen": {
        "alias": "PreImagen",
        "columnas": [
          "sanic_estado",
          "sanic_solicitudid",
          "sanic_numerofila"
        ]
      }
    },
    {
      "nombre": "MPPP - Atender correo por clasificar - Update de Solicitud",
      "descripcion": "Solo deja cerrar o descartar lo que esta por clasificar (03 §5, 07 DF-09).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.AtenderPorClasificarStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_solicitud",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 10,
      "filtro": [
        "sanic_estadoprocesamiento"
      ],
      "preimagen": {
        "alias": "PreImagen",
        "columnas": [
          "sanic_estadoprocesamiento"
        ]
      }
    },
    {
      "nombre": "MPPP - Revision atendida - Update de Solicitud",
      "descripcion": "Al apagar la marca de revision, deja el motivo en la Bitacora y limpia la columna (05 §5).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.RevisionAtendidaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_solicitud",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 20,
      "filtro": [
        "sanic_requiererevision"
      ],
      "preimagen": {
        "alias": "PreImagen",
        "columnas": [
          "sanic_requiererevision",
          "sanic_motivorevision"
        ]
      }
    },
    {
      "nombre": "MPPP - Integridad de Regla - Create",
      "descripcion": "Valida el catalogo de Reglas al guardar: codigo con evaluador, efecto segun nivel, dependencias y desactivacion (D-13, D-14, D-20).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.IntegridadDeReglaStep",
      "mensaje": "Create",
      "tabla": "sanic_mppp_tbl_regla",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 30,
      "filtro": [],
      "preimagen": null
    },
    {
      "nombre": "MPPP - Integridad de Regla - Update",
      "descripcion": "Valida el catalogo de Reglas al guardar: codigo con evaluador, efecto segun nivel, dependencias y desactivacion (D-13, D-14, D-20).",
      "plugintype": "Sanic.Mppp.Plugins.Steps.IntegridadDeReglaStep",
      "mensaje": "Update",
      "tabla": "sanic_mppp_tbl_regla",
      "etapa": "PreOperation",
      "modo": "Sincrono",
      "orden": 30,
      "filtro": [
        "sanic_codigo",
        "sanic_nivel",
        "sanic_orden",
        "sanic_dependede",
        "sanic_efecto",
        "statecode"
      ],
      "preimagen": {
        "alias": "PreImagen",
        "columnas": [
          "sanic_codigo",
          "sanic_nivel",
          "sanic_orden",
          "sanic_dependede",
          "sanic_efecto",
          "statecode"
        ]
      }
    }
  ]
}
```

## 3. Precondiciones

- Las 7 tablas involucradas existen (P-03, ya construidas).
- Los 7 `plugintype` de `Sanic.Mppp.Plugins.Steps` registrados por el paquete.

## 4. Lo que hay que mirar

- **Orden dentro de la misma tabla y mensaje.** En `Update` de Fila: lista blanca (0) antes que transicion (1). En `Update` de Solicitud: lista blanca (0) antes que atender por clasificar (10). En `Create` de Plan: normalizar (10) antes que nombre calculado (20), porque el nombre se arma con el codigo ya normalizado.
- **Cuatro steps llevan pre-imagen** y leen de ella el estado de origen. Sin la imagen no fallan al registrarse: fallan al primer guardado.
- **La lista blanca va sin filtro de atributos a proposito.** Filtrar dejaria pasar justo los `Update` que traen columnas que nadie declaro.
- **`Upsert` queda pendiente** (`PENDIENTES.md` §B): si el entorno admite registrar sobre `Upsert`, los dos primeros steps se duplican sobre ese mensaje y el total sube a 20.
