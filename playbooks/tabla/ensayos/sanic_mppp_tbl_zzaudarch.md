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
  "nombre": "sanic_mppp_tbl_zzaudarch",
  "displayname": "Ensayo auditoría de archivo",
  "displayname_plural": "Ensayos auditoría de archivo",
  "descripcion": "Autorización de un correo para operar sobre un plan, con su evidencia firmada. Sin evidencia cargada, la autorización no vale.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre calculado por la solución: correo → código del plan. Nadie lo digita.",
    "largo": 400,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_documentofirmado",
      "displayname": "Documento firmado",
      "descripcion": "Evidencia de ESTA autorización: el documento firmado que respalda que este correo opere sobre este plan. Obligatoria por negocio: sin archivo, la autorización no vale.",
      "tipo": "archivo",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "tamano_kb": 10240
    },
    {
      "nombre": "sanic_fechadocumento",
      "displayname": "Fecha del documento",
      "descripcion": "Fecha del documento firmado.",
      "tipo": "fecha",
      "requerida": false,
      "protegida": false,
      "auditoria": true
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
