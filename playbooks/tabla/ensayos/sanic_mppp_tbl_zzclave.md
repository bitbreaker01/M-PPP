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
  "nombre": "sanic_mppp_tbl_zzclave",
  "displayname": "ZZ Clave",
  "displayname_plural": "ZZ Claves",
  "descripcion": "Tabla descartable para ensayar claves alternativas.",
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
      "displayname": "Código",
      "descripcion": "Columna de ensayo.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 450
    },
    {
      "nombre": "sanic_largo",
      "displayname": "Largo",
      "descripcion": "Columna de ensayo.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 451
    },
    {
      "nombre": "sanic_numero",
      "displayname": "Número",
      "descripcion": "Columna de ensayo.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 1000
    },
    {
      "nombre": "sanic_secreto",
      "displayname": "Secreto",
      "descripcion": "Columna de ensayo.",
      "tipo": "texto",
      "requerida": false,
      "protegida": true,
      "auditoria": false,
      "largo": 20
    },
    {
      "nombre": "sanic_detalle",
      "displayname": "Detalle",
      "descripcion": "Columna de ensayo.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 2000
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
