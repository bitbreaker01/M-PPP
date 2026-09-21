# Playbook: choice-global · prueba

## 1. Identidad

```json
{
  "tipo_playbook": "relacion",
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
  "tipo": "relacion",
  "nombre": "sanic_mppp_zzotro_zzhija",
  "tabla_padre": "sanic_mppp_tbl_zzotro",
  "tabla_hija": "sanic_mppp_tbl_zzhija",
  "comportamiento": "restringido",
  "lookup": {
    "nombre": "sanic_zzotroid",
    "displayname": "Otro",
    "descripcion": "Otro catálogo.",
    "requerida": false,
    "auditoria": true
  }
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
