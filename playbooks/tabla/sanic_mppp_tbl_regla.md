# Playbook: tabla · sanic_mppp_tbl_regla

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.6",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §2.6 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.6.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_regla",
  "displayname": "Regla",
  "displayname_plural": "Reglas",
  "descripcion": "Regla de validación del catálogo, con su nivel, su orden, las reglas de las que depende y su efecto. El código C# tiene un evaluador por código de regla.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Numero",
    "descripcion": "Número que la plataforma asigna sola al crear el registro. Nadie lo digita.",
    "largo": 200,
    "requerida": false,
    "autonumerico": "REG-{SEQNUM:4}"
  },
  "columnas": [
    {
      "nombre": "sanic_codigo",
      "displayname": "Codigo",
      "descripcion": "Código de la regla; identifica a su evaluador en el código. Es clave alternativa.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "largo": 50
    },
    {
      "nombre": "sanic_nivel",
      "displayname": "Nivel",
      "descripcion": "A qué se aplica: al correo, a la solicitud o a cada registro.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": true,
      "choice": "sanic_mppp_ch_nivelregla"
    },
    {
      "nombre": "sanic_orden",
      "displayname": "Orden",
      "descripcion": "Orden de evaluación dentro de su nivel.",
      "tipo": "entero",
      "requerida": true,
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
      "requerida": true,
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

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la primaria | `Numero` | Es un autonumérico (`02` DD-20); "Nombre" confundiría |
| Nombres visibles de las columnas | `Nombre`, `Codigo`, `Nivel`, `Orden`, `Depende de`, `Efecto`, `Mensaje para el cliente` | Texto de negocio (`02` DD-19) |
| Rango de las columnas enteras | `sanic_orden`: 0 a 100000 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |

Viene del diseño, no lo decide este playbook: **auditoría nativa, notas y actividades** = activada · no · no (`02` DD-18: es un catálogo).

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_efectoregla`, `sanic_mppp_ch_nivelregla` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos autonumerico, choice, entero, memo, texto; primaria autonumérica, auditoría de tabla y de columna: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_regla.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_regla.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_regla.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_regla')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = true` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (7): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` autonumérico `REG-{SEQNUM:4}` (largo 200) opcional · `sanic_codigo` texto 50 requerida · `sanic_nivel` choice `sanic_mppp_ch_nivelregla` requerida · `sanic_orden` entero 0–100000 requerida · `sanic_dependede` texto 500 opcional · `sanic_efecto` choice `sanic_mppp_ch_efectoregla` requerida · `sanic_mensajecliente` multilínea 2000 opcional; todas auditadas |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_regla')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- La clave alternativa `sanic_mppp_key_regla_codigo`: inventario 5.7.
- La validación de `sanic_dependede` (los códigos existen, mismo nivel, orden menor, sin ciclos): plugin, inventario 7.10.
- Las reglas iniciales: datos semilla, inventario 9.2 y 9.3.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
