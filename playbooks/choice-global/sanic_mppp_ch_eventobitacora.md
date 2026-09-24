# Playbook: choice-global · sanic_mppp_ch_eventobitacora

## 1. Identidad

```json
{
  "tipo_playbook": "choice-global",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "2.13",
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

De dónde sale cada dato: todos de `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. El componente está definido en `diseno/02-diccionario-datos.md` §1 y figura en `diseno/06-inventario-componentes.md` §2, renglón 2.13.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name y prefijo de opciones 10000; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "choice-global",
  "nombre": "sanic_mppp_ch_eventobitacora",
  "displayname": "CH - MPPP - Evento de bitacora",
  "descripcion": "Qué ocurrió en un renglón de la bitácora de una solicitud. La usa la tabla Bitacora.",
  "opciones": [
    {
      "valor": 159460001,
      "etiqueta": "Ingresada",
      "descripcion": ""
    },
    {
      "valor": 159460002,
      "etiqueta": "Validacion terminada",
      "descripcion": ""
    },
    {
      "valor": 159460003,
      "etiqueta": "Acuse iniciado",
      "descripcion": ""
    },
    {
      "valor": 159460004,
      "etiqueta": "Acuse enviado",
      "descripcion": ""
    },
    {
      "valor": 159460005,
      "etiqueta": "Fila digitada",
      "descripcion": ""
    },
    {
      "valor": 159460006,
      "etiqueta": "Fila aprobada",
      "descripcion": ""
    },
    {
      "valor": 159460007,
      "etiqueta": "Fila devuelta",
      "descripcion": ""
    },
    {
      "valor": 159460008,
      "etiqueta": "Fila rechazada en AS400",
      "descripcion": ""
    },
    {
      "valor": 159460018,
      "etiqueta": "Fila anulada",
      "descripcion": ""
    },
    {
      "valor": 159460009,
      "etiqueta": "Procesada",
      "descripcion": ""
    },
    {
      "valor": 159460010,
      "etiqueta": "Respuesta final iniciada",
      "descripcion": ""
    },
    {
      "valor": 159460011,
      "etiqueta": "Respuesta final enviada",
      "descripcion": ""
    },
    {
      "valor": 159460012,
      "etiqueta": "Cerrada",
      "descripcion": ""
    },
    {
      "valor": 159460013,
      "etiqueta": "No reconocida atendida",
      "descripcion": ""
    },
    {
      "valor": 159460014,
      "etiqueta": "Descartada",
      "descripcion": ""
    },
    {
      "valor": 159460015,
      "etiqueta": "Reintento",
      "descripcion": ""
    },
    {
      "valor": 159460016,
      "etiqueta": "Requiere revision",
      "descripcion": ""
    },
    {
      "valor": 159460017,
      "etiqueta": "Error",
      "descripcion": ""
    },
    {
      "valor": 159460019,
      "etiqueta": "Correo clasificado",
      "descripcion": ""
    },
    {
      "valor": 159460020,
      "etiqueta": "Vencida",
      "descripcion": ""
    },
    {
      "valor": 159460021,
      "etiqueta": "Revision atendida",
      "descripcion": "Una persona apago la marca de revision. El detalle lleva el motivo que habia escrito la maquina."
    }
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
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_eventobitacora.md
```

## 5. Verificación

```
python3 herramientas/construir/choice_global.py playbooks/choice-global/sanic_mppp_ch_eventobitacora.md --solo-verificar
```

Las comprobaciones de la receta, con estos valores esperados:

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET GlobalOptionSetDefinitions(Name='sanic_mppp_ch_eventobitacora')` | 200 · `IsGlobal = true` · `OptionSetType = Picklist` · `IsManaged = false` |
| 2 | Display name y descripción en 1033 | los de la sección 2 |
| 3 | Opciones, en orden, con valor, etiqueta y descripción | `159460001 = Ingresada`, `159460002 = Validacion terminada`, `159460003 = Acuse iniciado`, `159460004 = Acuse enviado`, `159460005 = Fila digitada`, `159460006 = Fila aprobada`, `159460007 = Fila devuelta`, `159460008 = Fila rechazada en AS400`, `159460018 = Fila anulada`, `159460009 = Procesada`, `159460010 = Respuesta final iniciada`, `159460011 = Respuesta final enviada`, `159460012 = Cerrada`, `159460013 = No reconocida atendida`, `159460014 = Descartada`, `159460015 = Reintento`, `159460016 = Requiere revision`, `159460017 = Error`, `159460019 = Correo clasificado`, `159460020 = Vencida`, `159460021 = Revision atendida`; ninguna más; ninguna etiqueta en otro idioma |
| 4 | Pertenece a la solución de la sección 1 | exactamente una fila en `solutioncomponents` |
| 5 | Segunda ejecución de la herramienta sin `--solo-verificar` | estado `ya_existia`, código de salida 0, no cambia nada |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE GlobalOptionSetDefinitions(Name='sanic_mppp_ch_eventobitacora')`, posible solo mientras ninguna columna lo use. **Irreversible desde que tenga uso**: el nombre lógico `sanic_mppp_ch_eventobitacora` y los valores de sus 20 opciones una vez que haya datos con ellos; nunca se renumeran ni se reutilizan.

## 8. Fuera de alcance

La columna `sanic_evento` de Bitacora: nace con el playbook de esa tabla (inventario 3.10).
