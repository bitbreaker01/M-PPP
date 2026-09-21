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
  "nombre": "sanic_mppp_tbl_zzpadre",
  "displayname": "Ensayo padre",
  "displayname_plural": "Ensayo padres",
  "descripcion": "Tabla descartable para ensayar relaciones.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre.",
    "largo": 100,
    "requerida": false,
    "autonumerico": "ZZ-{SEQNUM:4}"
  },
  "columnas": []
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
