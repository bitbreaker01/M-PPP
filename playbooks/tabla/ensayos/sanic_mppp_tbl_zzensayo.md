# Playbook: choice-global · prueba

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
  "nombre": "sanic_mppp_tbl_zzensayo",
  "displayname": "Ensayo",
  "displayname_plural": "Ensayos",
  "descripcion": "Tabla descartable para comprobar contra la plataforma cada característica del formato. Se borra al terminar.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Número",
    "descripcion": "Primaria autonumérica de ensayo.",
    "largo": 100,
    "requerida": true,
    "autonumerico": "ZZ-{SEQNUM:8}"
  },
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "displayname": "Código",
      "descripcion": "Columna de ensayo: Código.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "largo": 9
    },
    {
      "nombre": "sanic_detalle",
      "displayname": "Detalle",
      "descripcion": "Columna de ensayo: Detalle.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 2000
    },
    {
      "nombre": "sanic_orden",
      "displayname": "Orden",
      "descripcion": "Columna de ensayo: Orden.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "minimo": 0,
      "maximo": 9999
    },
    {
      "nombre": "sanic_moneda",
      "displayname": "Moneda",
      "descripcion": "Columna de ensayo: Moneda.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "choice": "sanic_mppp_ch_moneda"
    },
    {
      "nombre": "sanic_activado",
      "displayname": "Activado",
      "descripcion": "Columna de ensayo: Activado.",
      "tipo": "sino",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "etiqueta_si": "Sí",
      "etiqueta_no": "No",
      "defecto": false
    },
    {
      "nombre": "sanic_fechadocumento",
      "displayname": "Fecha del documento",
      "descripcion": "Columna de ensayo: Fecha del documento.",
      "tipo": "fecha",
      "requerida": false,
      "protegida": false,
      "auditoria": true
    },
    {
      "nombre": "sanic_fechaevento",
      "displayname": "Fecha del evento",
      "descripcion": "Columna de ensayo: Fecha del evento.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": true
    },
    {
      "nombre": "sanic_documento",
      "displayname": "Documento",
      "descripcion": "Columna de ensayo: Documento.",
      "tipo": "archivo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "tamano_kb": 10240
    },
    {
      "nombre": "sanic_folio",
      "displayname": "Folio",
      "descripcion": "Columna de ensayo: Folio.",
      "tipo": "autonumerico",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 100,
      "formato": "F-{SEQNUM:6}"
    },
    {
      "nombre": "sanic_cuenta",
      "displayname": "Cuenta",
      "descripcion": "Columna de ensayo: Cuenta.",
      "tipo": "texto",
      "requerida": false,
      "protegida": true,
      "auditoria": true,
      "largo": 20
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
