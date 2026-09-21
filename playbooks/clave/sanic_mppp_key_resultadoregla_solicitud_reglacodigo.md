# Playbook: clave alternativa · sanic_mppp_key_resultadoregla_solicitud_reglacodigo

## 1. Identidad

```json
{
  "tipo_playbook": "clave",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "5.10",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La clave está definida en `diseno/02-diccionario-datos.md` §3.3 y figura en `diseno/06-inventario-componentes.md` §5, renglón 5.10.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "clave",
  "nombre": "sanic_mppp_key_resultadoregla_solicitud_reglacodigo",
  "displayname": "KEY - MPPP - Resultado de regla - Solicitud y código de regla",
  "tabla": "sanic_mppp_tbl_resultadoregla",
  "columnas": [
    "sanic_solicitudid",
    "sanic_reglacodigo"
  ]
}
```

Una clave alternativa sobre `sanic_mppp_tbl_resultadoregla`: la plataforma no admite dos registros con la misma combinación de `sanic_solicitudid` · `sanic_reglacodigo`.

Valores vacíos:

- **`sanic_solicitudid` es opcional**: mientras un registro tenga esa columna vacía, la plataforma **no le exige unicidad** a ese registro. La clave protege solo a los registros que la tienen cargada.

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la clave | «KEY - MPPP - Resultado de regla - Solicitud y código de regla» | El inventario trae el nombre lógico; el visible sigue el patrón `KEY - MPPP - Tabla - Campos` (`01` §2) |

Viene del diseño, no lo decide este playbook:

- Columnas de la clave: `02` §3.3 e inventario §5, renglón 5.10.
- Una regla se evalúa una sola vez por solicitud.
- `sanic_solicitudid` es opcional en `02` §3.3 (pendiente D-7): si D-7 lo vuelve requerido, la clave no cambia.
- El nombre visible lleva tilde por la excepción D-10 (`PENDIENTES.md`, aprobador, 2026-09-21): la clave ya estaba construida cuando se decidió BP-PP-197 y el Web API no deja cambiar el nombre visible de una clave. No es un modelo para claves nuevas.

## 3. Precondiciones

Las de la receta (`patrones.md` §2.4), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | La tabla existe | `sanic_mppp_tbl_resultadoregla` (construida) |
| 4 | Cada columna de la clave existe, es de un tipo que admite clave y no tiene seguridad de columna | `sanic_solicitudid` · `sanic_reglacodigo` |
| 5 | La clave no pasa de 900 bytes (un texto ocupa 2 por carácter) | la herramienta lo calcula con los largos reales del entorno; la plataforma no lo comprueba al crear |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.4 "Clave alternativa". Herramienta del proyecto: `herramientas/construir/clave.py`. El índice de la clave se arma en segundo plano y tarda unos dos minutos aun con la tabla vacía: la herramienta espera hasta verlo `Active`.

```
python3 herramientas/construir/clave.py playbooks/clave/sanic_mppp_key_resultadoregla_solicitud_reglacodigo.md
```

## 5. Verificación

```
python3 herramientas/construir/clave.py playbooks/clave/sanic_mppp_key_resultadoregla_solicitud_reglacodigo.md --solo-verificar
python3 herramientas/construir/muestra_clave.py playbooks/clave/sanic_mppp_key_resultadoregla_solicitud_reglacodigo.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_resultadoregla.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_resultadoregla')/Keys(LogicalName='sanic_mppp_key_resultadoregla_solicitud_reglacodigo')` | 200 · `IsManaged = false` · nombre visible «KEY - MPPP - Resultado de regla - Solicitud y código de regla» en 1033, sin etiquetas en otro idioma |
| 2 | Columnas de la clave (`KeyAttributes`, sin importar el orden) | `sanic_solicitudid` · `sanic_reglacodigo` |
| 3 | Índice (`EntityKeyIndexStatus`) | `Active` |
| 4 | Pertenencia a la solución | la de la tabla: `sanic_mppp_tbl_resultadoregla` está una vez en la solución de la sección 1, con todos sus subcomponentes (una clave no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla sigue coincidiendo con su propio playbook | `ya_existia`: una clave no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_clave.py`) | `OK`, y la muestra queda en `playbooks/clave/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. Un índice `Failed` también es `difiere`: casi siempre hay datos duplicados, y eso lo resuelve una persona antes de reactivar la clave.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_resultadoregla')/Keys(<MetadataId>)`. No borra datos ni columnas: solo deja de exigir la unicidad. **Irreversible desde que se crea**: el nombre de la clave. Las columnas de una clave no se editan: para cambiarlas se borra la clave y se crea otra. Mientras la clave exista, sus columnas no se pueden borrar.

## 8. Fuera de alcance

- La relación que crea el lookup de esta clave: inventario 4.6, ya construida.
- El plugin o Custom API que usa esta clave para detectar duplicados: inventario 7 y 8.
- Importación de datos por clave (semillas): inventario 9.
