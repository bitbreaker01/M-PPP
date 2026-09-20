# Playbook: choice-global · sanic_mppp_ch_moneda

## 1. Identidad

| Dato | Valor | De dónde sale |
|---|---|---|
| Tipo de playbook | `choice-global`, skill `power-platform-especificar` 0.1.0 | |
| Proyecto | 2026-001-referencias-planes-pago (Mantenimiento PPP) | |
| Componente del inventario | 2.1 | `diseno/06-inventario-componentes.md` §2 |
| Fase | 1 | |
| Entorno | Dev · `https://org36e60d9d.crm.dynamics.com/` | `diseno/01-convenciones.md` §0 |
| Solución | `sanic_mppp_sol_mantenimientoppp` | `diseno/01-convenciones.md` §7 |
| Publisher | unique name **`Sistemas_Abiertos_Nicaragua`** (no confundir con "Sanic Corp", unique name `sanic`, que comparte el prefijo) | `diseno/01-convenciones.md` §0 |
| Prefijo | `sanic` | ídem |
| Prefijo numérico de opciones | `15946` | ídem, verificado en Dev el 2026-09-20 |
| Idioma de las etiquetas | LCID `1033`: idioma base y único provisionado. Las etiquetas van en español bajo 1033 | ídem |
| Definición del componente | `diseno/02-diccionario-datos.md` §1, fila `sanic_mppp_ch_moneda` | |

## 2. Qué se crea

```json
{
  "tipo": "choice-global",
  "nombre": "sanic_mppp_ch_moneda",
  "displayname": "CH - MPPP - Moneda",
  "descripcion": "Moneda de un plan de pago o de la cuenta de una referencia. La usan las tablas Plan y Fila.",
  "lcid": 1033,
  "opciones": [
    { "valor": 159460001, "etiqueta": "COR", "descripcion": "Córdoba" },
    { "valor": 159460002, "etiqueta": "USD", "descripcion": "Dólar estadounidense" }
  ]
}
```

## 3. Precondiciones

| # | Qué tiene que cumplirse | Cómo se comprueba | Esperado |
|---|---|---|---|
| 1 | La solución existe y es del publisher correcto | `GET solutions?$select=uniquename,ismanaged&$expand=publisherid($select=uniquename,customizationoptionvalueprefix)&$filter=uniquename eq 'sanic_mppp_sol_mantenimientoppp'` | Una fila; `ismanaged = false`; publisher `Sistemas_Abiertos_Nicaragua`; prefijo de opciones `15946` |
| 2 | El idioma de las etiquetas es el base y está provisionado | `GET organizations?$select=languagecode` y `GET RetrieveProvisionedLanguages` | `1033` en los dos |
| 3 | Todos los valores están en el rango del publisher | Cálculo local | `159460000 ≤ valor < 159470000` |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.1 "Choice global", con el contrato de herramientas de su §1.

Herramienta del proyecto: `herramientas/construir/choice_global.py`. **Todavía no existe: este es el primer playbook de este tipo, así que el constructor la escribe** siguiendo ese contrato, usando `herramientas/dataverse_api.py` como cliente (sin abrir nunca `local/pp_secrets.env`), y después la ejecuta:

```
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_moneda.md
```

## 5. Verificación

```
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_moneda.md --solo-verificar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET GlobalOptionSetDefinitions(Name='sanic_mppp_ch_moneda')` | 200 · `IsGlobal = true` · `OptionSetType = Picklist` · `IsManaged = false` |
| 2 | Display name en 1033 | `CH - MPPP - Moneda` |
| 3 | Opciones, en orden | `159460001 = COR`, `159460002 = USD`; ninguna más |
| 4 | Pertenece a `sanic_mppp_sol_mantenimientoppp` | Una fila en `solutioncomponents` de esa solución con el `MetadataId` del choice |
| 5 | Segunda ejecución de la herramienta sin `--solo-verificar` | Estado `ya_existia`, código de salida 0, y no cambia nada |

## 6. Si ya existe

Se compara: `Name`, display name en 1033, `IsGlobal`, `OptionSetType`, y la lista ordenada de pares valor-etiqueta. Si todo coincide: `ya_existia`. Si algo difiere: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE GlobalOptionSetDefinitions(Name='sanic_mppp_ch_moneda')`, posible solo mientras ninguna columna lo use. **Irreversible desde que tenga uso**: el nombre lógico `sanic_mppp_ch_moneda`, y los valores `159460001` y `159460002` una vez que haya datos con ellos; nunca se renumeran ni se reutilizan.

## 8. Fuera de alcance

Las columnas `sanic_moneda` de Plan y de Fila que usan este choice: nacen con el playbook de cada tabla (inventario 3.2 y 3.8). No hay opciones reservadas para fases posteriores.
