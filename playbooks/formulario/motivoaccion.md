# Playbook: formulario · Motivo de accion (creacion rapida)

Inventario 12.4. **Este formulario ES el dialogo de motivo.**

**Corregido el 2026-09-23.** Este playbook construia un formulario PRINCIPAL, y decia: *"No es un
Quick Create: `navigateTo` con `pageType: entityrecord` ... devuelve `savedEntityReference[0]` ...
asi que no hace falta un formulario de creacion rapida aparte."* Las dos mitades de esa frase son
ciertas por separado y la conclusion es falsa:

- que `navigateTo` devuelva el registro **no implica** que la creacion rapida no lo devuelva. Learn
  lo dice textual sobre `openForm`: *"The `successCallback` function is executed **only when you
  save a record in a quick create form** that was opened using the openForm method"*, y ese
  callback recibe `savedEntityReference`. El argumento de DA-03 valia contra una **pagina custom**,
  que efectivamente resuelve sin valor; nunca valio contra la creacion rapida.
- y el costo de la conclusion se vio en pantalla: `pageType: entityrecord` abre el formulario
  principal COMPLETO dentro del modal, con barra de comandos (Guardar, Nuevo, Flujo), titulo de
  registro ("New Motivo de accion"), pestaña "General" y la barra de Copilot. Para pedir una sola
  linea de texto.

Un formulario de creacion rapida no trae nada de eso: el campo y "Guardar y cerrar".

**Precondicion propia**: la tabla tiene que tener `IsQuickCreateEnabled` en `true`, o la plataforma
no muestra el formulario y `openForm` cae al principal sin avisar.

El formulario muestra UN solo campo: `sanic_motivo`. El contexto (que accion y sobre cuantas filas)
lo pone el comando en el titulo del dialogo, no en una columna prellenada.

## 1. Identidad

```json
{
  "tipo_playbook": "formulario",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "12.4",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
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
  "tipo": "formulario",
  "clase": "creacion_rapida",
  "nombre": "Motivo de accion",
  "tabla": "sanic_mppp_tbl_motivoaccion",
  "solo_lectura": false,
  "descripcion": "El dialogo de motivo (12.4). Lo abre un comando de la barra con openForm y useQuickCreateForm.",
  "pestana": "General",
  "encabezado": [],
  "secciones": [
    {
      "titulo": "Motivo",
      "campos": [
        "sanic_motivo"
      ]
    }
  ]
}
```

## 3. Precondiciones

- La tabla `sanic_mppp_tbl_motivoaccion` y sus dos columnas existen (3.12).
- La tabla tiene `IsQuickCreateEnabled = true`.
