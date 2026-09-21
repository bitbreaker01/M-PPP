# Playbook: tabla · sanic_mppp_tbl_cliente

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.1",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §2.1 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.1.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID (todas son etiquetas de metadatos, `01` §0).

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_cliente",
  "displayname": "Cliente",
  "displayname_plural": "Clientes",
  "descripcion": "Empresa cliente del banco que administra planes de pago de planilla o de proveedores. Su propietario es el ejecutivo asignado.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": true,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Razón social",
    "descripcion": "Razón social de la empresa cliente.",
    "largo": 200,
    "requerida": true,
    "autonumerico": ""
  },
  "columnas": [
    {
      "nombre": "sanic_cifbac",
      "displayname": "CIF BAC",
      "descripcion": "Número de cliente en BAC. Solo dígitos; se guarda rellenado con ceros a la izquierda hasta 9. Es clave alternativa.",
      "tipo": "texto",
      "largo": 9,
      "requerida": true,
      "protegida": false,
      "auditoria": true
    },
    {
      "nombre": "sanic_cifcom",
      "displayname": "CIF COM",
      "descripcion": "CIF comercial: 9 caracteres alfanuméricos o espacio más 3 dígitos, en mayúscula. Es clave alternativa.",
      "tipo": "texto",
      "largo": 12,
      "requerida": true,
      "protegida": false,
      "auditoria": true
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía (las aprueba el aprobador antes de construir):

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la primaria | `Razón social` | El diccionario dice qué guarda; "Nombre" a secas no le dice nada a quien carga un cliente |
| Nombres visibles de las columnas | `CIF BAC`, `CIF COM` | Así los nombra el negocio |
| Auditoría nativa de la tabla y de sus columnas | activada | Es un catálogo de poco volumen, y en un banco importa quién cambió un CIF o reasignó un cliente. Solo registra si además la auditoría está activada a nivel de entorno |
| Notas y actividades | desactivadas | No se usan; activarlas después es posible, desactivarlas no |

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | esta tabla no usa ninguno |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | texto, auditoría de tabla y de columna: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas".

Herramienta del proyecto: `herramientas/construir/tabla.py`. La tabla y sus tres columnas viajan en un solo POST.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_cliente.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_cliente.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_cliente')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = true` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas: tipo, requerida, protegida, auditoría, nombre visible y descripción | `sanic_nombre` texto 200 requerida · `sanic_cifbac` texto 9 requerida · `sanic_cifcom` texto 12 requerida; las tres auditadas, ninguna protegida |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | exactamente una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0, no cambia nada |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_cliente')`, posible mientras la tabla esté vacía y nada la referencie (una relación, una vista de otra tabla, un flujo). **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`) y el tipo de cada columna. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- Las claves alternativas `sanic_mppp_key_cliente_cifbac` y `sanic_mppp_key_cliente_cifcom`: inventario 5.1 y 5.2.
- Las relaciones cliente → plan y cliente → autorizado, con sus lookups: inventario 4.1 y 4.2.
- La normalización y validación de los dos CIF (relleno con ceros, mayúscula, formato): plugin PreOperation, inventario 7.10.
- El ejecutivo asignado es el propietario del registro (`ownerid`, columna del sistema): no se crea.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
