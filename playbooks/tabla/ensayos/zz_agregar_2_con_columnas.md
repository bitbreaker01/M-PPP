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
  "nombre": "sanic_mppp_tbl_zzagregar",
  "displayname": "zzagregar",
  "displayname_plural": "zzagregares",
  "descripcion": "Tabla descartable para ensayar --agregar-columnas.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre.",
    "largo": 100,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "displayname": "Codigo",
      "descripcion": "Columna descartable sanic_codigo.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 20
    },
    {
      "nombre": "sanic_cantidadexcel",
      "displayname": "Cantidad de Excel",
      "descripcion": "Columna descartable sanic_cantidadexcel.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 1000
    },
    {
      "nombre": "sanic_revisado",
      "displayname": "Revisado",
      "descripcion": "Columna descartable sanic_revisado.",
      "tipo": "sino",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "etiqueta_si": "Si",
      "etiqueta_no": "No",
      "defecto": false
    },
    {
      "nombre": "sanic_cuenta",
      "displayname": "Cuenta",
      "descripcion": "Columna descartable sanic_cuenta.",
      "tipo": "texto",
      "requerida": false,
      "protegida": true,
      "auditoria": false,
      "largo": 100
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
