# Playbook: perfil-columnas · ensayo

## 1. Identidad

```json
{
  "tipo_playbook": "perfil-columnas",
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
  "tipo": "perfil-columnas",
  "nombre": "CSP - MPPP - ZZ Ensayo",
  "descripcion": "Perfil descartable de ensayo.",
  "permisos": [
    {
      "tabla": "sanic_mppp_tbl_fila",
      "columna": "sanic_numerocuenta",
      "leer": true,
      "crear": false,
      "actualizar": false
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
