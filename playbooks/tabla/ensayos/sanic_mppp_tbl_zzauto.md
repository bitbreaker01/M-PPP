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
  "nombre": "sanic_mppp_tbl_zzauto",
  "displayname": "Ensayo autonumérico",
  "displayname_plural": "Ensayos autonumérico",
  "descripcion": "Regla de validación del catálogo, con su nivel, su orden, las reglas de las que depende y su efecto. El código C# tiene un evaluador por código de regla.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Nombre",
    "descripcion": "Nombre de la regla, para las personas.",
    "largo": 200,
    "requerida": false,
    "autonumerico": "REG-{SEQNUM:4}"
  },
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "displayname": "Código",
      "descripcion": "Código de la regla; identifica a su evaluador en el código. Es clave alternativa.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 50
    },
    {
      "nombre": "sanic_nivel",
      "displayname": "Nivel",
      "descripcion": "A qué se aplica: al correo, a la solicitud o a cada registro.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "choice": "sanic_mppp_ch_nivelregla"
    },
    {
      "nombre": "sanic_orden",
      "displayname": "Orden",
      "descripcion": "Orden de evaluación dentro de su nivel.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "minimo": 0,
      "maximo": 100000
    },
    {
      "nombre": "sanic_dependede",
      "displayname": "Depende de",
      "descripcion": "Códigos de las reglas de las que depende, separados por coma. Si alguna no resultó cumplida, esta regla se omite.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 500
    },
    {
      "nombre": "sanic_efecto",
      "displayname": "Efecto",
      "descripcion": "Qué pasa cuando la regla falla. Envía a revisión solo vale en el nivel Solicitud.",
      "tipo": "choice",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "choice": "sanic_mppp_ch_efectoregla"
    },
    {
      "nombre": "sanic_mensajecliente",
      "displayname": "Mensaje para el cliente",
      "descripcion": "Texto que recibe el cliente cuando la regla falla.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": true,
      "largo": 2000
    }
  ]
}
```

## 3. Precondiciones

(no hace falta para las pruebas)
