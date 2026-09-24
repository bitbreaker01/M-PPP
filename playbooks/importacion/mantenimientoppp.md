# Playbook: importacion · MDA - MPPP - Mantenimiento PPP

Inventario 12.8. Las TABLAS de la app no se pueden enganchar por Web API.

`AddAppComponents` con `@odata.type: Microsoft.Dynamics.CRM.entity` devuelve 204 y no agrega
nada: siempre deja una referencia a la tabla de metadatos `entity`, ignorando el GUID que se le
pasa. `RemoveAppComponents` tampoco borra, `DELETE appmodulecomponents(id)` responde que el
metodo no existe para ese tipo, y `ValidateApp` pasa en verde con la app vacia. Reproducido
limpio el 2026-09-22 en una solucion ZZ nueva, no es nada de esta app.

El unico camino es exportar la solucion, editar `customizations.xml` y reimportarla. Eso hace
`importar_solucion.py`, y por eso esta herramienta NO importa si no hace falta.

Se corre DESPUES de `app.py`: la app y su sitemap tienen que existir ya.

## 1. Identidad

```json
{
  "tipo_playbook": "importacion",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.8",
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
  "tipo": "importacion",
  "idiomas": [
    1033,
    3082
  ],
  "cambios": [
    {
      "clase": "app_componentes",
      "app": "sanic_mppp_mda_mantenimientoppp",
      "sitemap": "sanic_mppp_sm_mantenimientoppp",
      "tablas": [
        "sanic_mppp_tbl_fila",
        "sanic_mppp_tbl_solicitud",
        "sanic_mppp_tbl_cliente",
        "sanic_mppp_tbl_plan",
        "sanic_mppp_tbl_autorizado",
        "sanic_mppp_tbl_autorizacionplan",
        "sanic_mppp_tbl_parametro",
        "sanic_mppp_tbl_regla",
        "sanic_mppp_tbl_resultadoregla",
        "sanic_mppp_tbl_bitacora",
        "sanic_mppp_tbl_motivoaccion"
      ]
    }
  ]
}
```

## 3. Precondiciones

- La app `sanic_mppp_mda_mantenimientoppp` existe y ya tiene su sitemap enganchado (`app.py`).
- Las 10 tablas existen en el entorno.
- La solucion es unmanaged y su publisher coincide con el de Identidad.
