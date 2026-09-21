# Playbook: clave alternativa · sanic_mppp_key_regla_codigo

## 1. Identidad

```json
{
  "tipo_playbook": "clave",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "5.7",
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

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La clave está definida en `diseno/02-diccionario-datos.md` §2.6 y figura en `diseno/06-inventario-componentes.md` §5, renglón 5.7.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "clave",
  "nombre": "sanic_mppp_key_regla_codigo",
  "displayname": "KEY - MPPP - Regla - Codigo",
  "tabla": "sanic_mppp_tbl_regla",
  "columnas": [
    "sanic_codigo"
  ]
}
```

Una clave alternativa sobre `sanic_mppp_tbl_regla`: la plataforma no admite dos registros con la misma combinación de `sanic_codigo`.

Valores vacíos:

Todas las columnas de la clave son requeridas en el diseño: ningún registro creado desde la app queda fuera de la unicidad. (El nivel requerido lo aplica la app, no el servicio: lo que entra por API con una columna vacía queda fuera de la unicidad.)

Decisiones que este playbook toma y el diseño no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la clave | «KEY - MPPP - Regla - Codigo» | El inventario trae el nombre lógico; el visible sigue el patrón `KEY - MPPP - Tabla - Campos` (`01` §2) |

Viene del diseño, no lo decide este playbook:

- Columnas de la clave: `02` §2.6 e inventario §5, renglón 5.7.
- El código C# tiene un evaluador por código de regla.

## 3. Precondiciones

Las de la receta (`patrones.md` §2.4), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | La tabla existe | `sanic_mppp_tbl_regla` (construida) |
| 4 | Cada columna de la clave existe, es de un tipo que admite clave y no tiene seguridad de columna | `sanic_codigo` |
| 5 | La clave no pasa de 900 bytes (un texto ocupa 2 por carácter) | la herramienta lo calcula con los largos reales del entorno; la plataforma no lo comprueba al crear |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.4 "Clave alternativa". Herramienta del proyecto: `herramientas/construir/clave.py`. El índice de la clave se arma en segundo plano y tarda unos dos minutos aun con la tabla vacía: la herramienta espera hasta verlo `Active`.

```
python3 herramientas/construir/clave.py playbooks/clave/sanic_mppp_key_regla_codigo.md
```

## 5. Verificación

```
python3 herramientas/construir/clave.py playbooks/clave/sanic_mppp_key_regla_codigo.md --solo-verificar
python3 herramientas/construir/muestra_clave.py playbooks/clave/sanic_mppp_key_regla_codigo.md --guardar
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_regla.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_regla')/Keys(LogicalName='sanic_mppp_key_regla_codigo')` | 200 · `IsManaged = false` · nombre visible «KEY - MPPP - Regla - Codigo» en 1033, sin etiquetas en otro idioma |
| 2 | Columnas de la clave (`KeyAttributes`, sin importar el orden) | `sanic_codigo` |
| 3 | Índice (`EntityKeyIndexStatus`) | `Active` |
| 4 | Pertenencia a la solución | la de la tabla: `sanic_mppp_tbl_regla` está una vez en la solución de la sección 1, con todos sus subcomponentes (una clave no es un componente propio) |
| 5 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 6 | La tabla sigue coincidiendo con su propio playbook | `ya_existia`: una clave no la hace diferir |
| 7 | Comprobación independiente contra el XML exportado (`muestra_clave.py`) | `OK`, y la muestra queda en `playbooks/clave/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**. Un índice `Failed` también es `difiere`: casi siempre hay datos duplicados, y eso lo resuelve una persona antes de reactivar la clave.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_regla')/Keys(<MetadataId>)`. No borra datos ni columnas: solo deja de exigir la unicidad. **Irreversible desde que se crea**: el nombre de la clave. Las columnas de una clave no se editan: para cambiarlas se borra la clave y se crea otra. Mientras la clave exista, sus columnas no se pueden borrar.

## 8. Fuera de alcance

- El plugin o Custom API que usa esta clave para detectar duplicados: inventario 7 y 8.
- Importación de datos por clave (semillas): inventario 9.
