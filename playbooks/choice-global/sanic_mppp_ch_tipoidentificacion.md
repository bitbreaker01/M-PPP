# Playbook: choice-global · sanic_mppp_ch_tipoidentificacion

## 1. Identidad

```json
{
  "tipo_playbook": "choice-global",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "2.5",
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

De dónde sale cada dato: todos de `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El componente está definido en `diseno/02-diccionario-datos.md` §1 y figura en `diseno/06-inventario-componentes.md` §2, renglón 2.5.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name y prefijo de opciones 10000; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "choice-global",
  "nombre": "sanic_mppp_ch_tipoidentificacion",
  "displayname": "CH - MPPP - Tipo de identificación",
  "descripcion": "Tipo de documento de identidad del titular de la referencia. La usa la tabla Fila.",
  "opciones": [
    { "valor": 159460001, "etiqueta": "CNA", "descripcion": "Cédula nacional" },
    { "valor": 159460002, "etiqueta": "CRE", "descripcion": "Cédula de residencia" },
    { "valor": 159460003, "etiqueta": "PAS", "descripcion": "Pasaporte" },
    { "valor": 159460004, "etiqueta": "PEX", "descripcion": "Persona extranjera" },
    { "valor": 159460005, "etiqueta": "RUC", "descripcion": "Registro único de contribuyente" }
  ]
}
```

## 3. Precondiciones

Las de la receta (`patrones.md` §2.1), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | Todos los valores están en el rango del publisher | `159460000 ≤ valor < 159470000` |
| 3 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.1 "Choice global", con el contrato de herramientas de su §1.

Herramienta del proyecto: `herramientas/construir/choice_global.py`.

```
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_tipoidentificacion.md
```

## 5. Verificación

```
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_tipoidentificacion.md --solo-verificar
```

Las comprobaciones de la receta, con estos valores esperados:

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET GlobalOptionSetDefinitions(Name='sanic_mppp_ch_tipoidentificacion')` | 200 · `IsGlobal = true` · `OptionSetType = Picklist` · `IsManaged = false` |
| 2 | Display name y descripción en 1033 | los de la sección 2 |
| 3 | Opciones, en orden, con valor, etiqueta y descripción | `159460001 = CNA`, `159460002 = CRE`, `159460003 = PAS`, `159460004 = PEX`, `159460005 = RUC`; ninguna más; ninguna etiqueta en otro idioma |
| 4 | Pertenece a la solución de la sección 1 | exactamente una fila en `solutioncomponents` |
| 5 | Segunda ejecución de la herramienta sin `--solo-verificar` | estado `ya_existia`, código de salida 0, no cambia nada |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE GlobalOptionSetDefinitions(Name='sanic_mppp_ch_tipoidentificacion')`, posible solo mientras ninguna columna lo use. **Irreversible desde que tenga uso**: el nombre lógico `sanic_mppp_ch_tipoidentificacion` y los valores de sus 5 opciones una vez que haya datos con ellos; nunca se renumeran ni se reutilizan.

## 8. Fuera de alcance

La columna `sanic_tipoidentificacion` de Fila: nace con el playbook de esa tabla (inventario 3.8).
