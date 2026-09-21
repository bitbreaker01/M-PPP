# Playbook: rol · ensayo

## 1. Identidad

```json
{
  "tipo_playbook": "rol",
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
  "tipo": "rol",
  "nombre": "SR - MPPP - ZZ Rol viejo",
  "descripcion": "Rol descartable.",
  "base": "App Opener",
  "tablas": {
    "sanic_mppp_tbl_cliente": {
      "leer": "organizacion"
    }
  },
  "otros_privilegios": {}
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
