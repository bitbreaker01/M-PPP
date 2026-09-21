# Playbook: perfil de seguridad de columna · CSP - MPPP - Datos sensibles

## 1. Identidad

```json
{
  "tipo_playbook": "perfil-columnas",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "6.1",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El perfil está definido en `diseno/04-matriz-privilegios.md` §4 y figura en `diseno/06-inventario-componentes.md` §6, renglón 6.1.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto.

## 2. Qué se crea

```json
{
  "tipo": "perfil-columnas",
  "nombre": "CSP - MPPP - Datos sensibles",
  "descripcion": "Lectura del número de cuenta y del número de identificación de las filas. Para ejecutivos y supervisores, por equipo.",
  "permisos": [
    {
      "tabla": "sanic_mppp_tbl_fila",
      "columna": "sanic_numeroidentificacion",
      "leer": true,
      "crear": false,
      "actualizar": false
    },
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

Un perfil de seguridad de columna de **solo lectura** sobre las dos columnas protegidas de `sanic_mppp_tbl_fila`. **Sin miembros**: quién lo recibe se resuelve fuera de la solución.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Descripción del perfil | «Lectura del número de cuenta y del número de identificación de las filas. Para ejecutivos y supervisores, por equipo.» | La matriz trae el nombre y los permisos; el texto lo fija el playbook |
| Leer sin enmascarar | No permitido | Las columnas no tienen regla de enmascarado; es el valor por defecto y el más restrictivo |

Viene del diseño, no lo decide este playbook:

- Columnas y permisos (leer sí, crear no, actualizar no): `04` §4.
- Los miembros son **equipos**, no roles ni personas sueltas: un grupo de seguridad de Entra ID con su equipo de grupo (D-8, decisión del aprobador del 2026-09-21). Es la tarea de administración 13.7, en cada entorno.
- El segundo perfil, de lectura y creación para el Histórico, nace en fase 3 (`04` §4).

## 3. Precondiciones

Las de la receta (`seguridad/patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide | los de la sección 1 |
| 2 | La tabla existe | `sanic_mppp_tbl_fila` (construida) |
| 3 | Cada columna existe y **tiene seguridad de columna** | `sanic_numeroidentificacion` · `sanic_numerocuenta` |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/seguridad/patrones.md` §2.2 "Column security profile". Herramienta del proyecto: `herramientas/construir/perfil_columnas.py`.

```
python3 herramientas/construir/perfil_columnas.py playbooks/perfil-columnas/csp_mppp_datos_sensibles.md
```

## 5. Verificación

```
python3 herramientas/construir/perfil_columnas.py playbooks/perfil-columnas/csp_mppp_datos_sensibles.md --solo-verificar
python3 herramientas/construir/muestra_perfil_columnas.py playbooks/perfil-columnas/csp_mppp_datos_sensibles.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_fila.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET fieldsecurityprofiles` por nombre | un perfil · `ismanaged = false` · la descripción de la sección 2 |
| 2 | `GET fieldpermissions` del perfil | **exactamente dos**: `sanic_mppp_tbl_fila.sanic_numeroidentificacion` y `sanic_mppp_tbl_fila.sanic_numerocuenta`, cada uno con `canread = 4` · `cancreate = 0` · `canupdate = 0` · `canreadunmasked = 0` |
| 3 | Pertenencia a la solución | el perfil figura una vez en la solución de la sección 1 (`solutioncomponents`, tipo 70) |
| 4 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 5 | La tabla sigue coincidiendo con su propio playbook | `ya_existia` |
| 6 | Comprobación independiente contra el XML exportado (`muestra_perfil_columnas.py`) | `OK`, y la muestra queda en `playbooks/perfil-columnas/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. La herramienta nunca quita ni cambia un permiso. Si lo único que pasa es que falta un permiso (una corrida cortada), se completa con `--completar`; eso lo decide quien dirige la construcción, no el constructor.

## 7. Reversa

`DELETE fieldsecurityprofiles(<id>)`: se lleva sus permisos. Quienes lo recibían dejan de ver esas dos columnas en el momento. Nada es irreversible.

## 8. Fuera de alcance

- El grupo de seguridad de Entra ID, su equipo de grupo y la asociación del equipo a este perfil: tarea de administración 13.7, en cada entorno.
- El perfil de lectura y creación para el Histórico: fase 3.
- Las columnas protegidas en sí: ya construidas con la tabla, inventario 3.8.
