# Playbook: tabla · ensayo

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "ensayo",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_zzensayo",
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
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_zzrenombrar",
  "displayname": "ZZ Final",
  "displayname_plural": "ZZ Finales",
  "descripcion": "Descripción de la tabla.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre final",
    "descripcion": "Nombre.",
    "largo": 100,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "displayname": "Codigo final",
      "descripcion": "Descripción.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 50
    },
    {
      "nombre": "sanic_orden",
      "displayname": "Orden final",
      "descripcion": "Descripción.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 10
    },
    {
      "nombre": "sanic_activo",
      "displayname": "Activo final",
      "descripcion": "Descripción.",
      "tipo": "sino",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "etiqueta_si": "Si final",
      "etiqueta_no": "No final",
      "defecto": false
    },
    {
      "nombre": "sanic_tipo",
      "displayname": "Tipo final",
      "descripcion": "Descripción.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_zzrenombrar"
    },
    {
      "nombre": "sanic_detalle",
      "displayname": "Detalle final",
      "descripcion": "Descripción.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 500
    },
    {
      "nombre": "sanic_fecha",
      "displayname": "Fecha final",
      "descripcion": "Descripción.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
