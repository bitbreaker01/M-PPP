# 07 — MPPP-VIG, la red de seguridad

`MPPP-VIG` corre **cada 10 minutos** y recupera lo que quedó a medias. Hace lo mismo que `MPPP-REC`
y `MPPP-COM` cuando algo falló, y por eso esos dos no tienen lógica propia (DF-02).

**Estos casos son lentos**: hay que esperar a que se cumplan los umbrales y a que corra el flujo.
Dejalos corriendo y hacé otra cosa mientras.

**Umbrales** (de la tabla de Parámetros, `--parametros` del visor):

| Parámetro | Valor | Bloque |
|---|---|---|
| `vigilancia.minutos.sinvalidar` | 15 | 1 y 2 |
| `vigilancia.minutos.sinresponder` | 30 | 3 y 4 |
| `vigilancia.reintentos.maximo` | 3 | 2 |
| `clasificacion.dias.vencimiento` | 30 | 5 |

> **Atajo**: para no esperar 15 o 30 minutos reales, bajá el parámetro a `1` en la tabla de
> Parámetros, corré el caso, y **devolvelo al valor original al terminar**. Si lo hacés, anotalo en
> las notas del caso: cambia lo que estás probando.

**Cómo mirar si corrió**: en Power Automate, `Cloud Flow - MPPP - VIG`, pestaña de **ejecuciones**.
Casi todas terminan en segundos sin hacer nada — eso es lo normal y lo esperado.

---

## V-01 · Corre y no hace nada

**Qué prueba.** Que la recurrencia esté viva y que una ejecución vacía sea barata.

**Cómo.** Sin tocar nada, mirá las ejecuciones de `MPPP-VIG` de la última hora.

**Esperado.**

| Qué | Valor |
|---|---|
| Ejecuciones | una cada ~10 minutos |
| Resultado | **Succeeded** |
| Duración | segundos |
| Efectos | **ninguno**: no crea filas, no cambia estados, no manda correos |

**FALLA si** hay ejecuciones fallidas, o si alguna cambió algo sin que hubiera nada pendiente.

---

## V-02 · Bloque 1 — un correo que quedó en la bandeja

**Qué prueba.** Que un correo que `MPPP-REC` no llegó a procesar se ingiera igual.

**Cómo.**
1. **Apagá** `Cloud Flow - MPPP - REC` (Turn off).
2. Mandá un correo nuevo con `E01-feliz-formato11.xlsx`.
3. Comprobá que **no** se creó ninguna Solicitud (REC está apagado).
4. Esperá a que pasen los 15 minutos del umbral + una corrida de VIG.
5. **Volvé a prender** `MPPP-REC` al terminar.

**Esperado.**

| Qué | Valor |
|---|---|
| Se crea la Solicitud | **sí**, la ingirió VIG |
| Bitácora `Ingresada` | origen **MPPP-VIG** (no MPPP-REC) |
| El resto | igual que C-01: En proceso, 3 filas Validadas, acuse enviado |

> Esto prueba lo que promete DF-02: si el disparador de correo se cae, **no se pierde ningún
> correo**. Es la garantía más valiosa del diseño.

---

## V-03 · Bloque 2 — una Solicitud que quedó en Ingresada

**Qué prueba.** El reintento de clasificación y validación, con su contador.

**Cómo.** En la app, abrí una Solicitud **Cerrada** o **En proceso** y volvela a **Ingresada**
(y poné `sanic_fechaingresada` con la hora de hace 20 minutos). Esperá a que corra VIG.

**Esperado.**

| Qué | Valor |
|---|---|
| `sanic_reintentosvalidacion` | pasa de vacío a **1** |
| Bitácora | `Reintento`, origen **MPPP-VIG** |
| La Solicitud | se reclasifica y revalida, y termina en su estado final |
| Filas | **no se duplican** (las API son idempotentes) |

**FALLA si** las filas se duplican. Sería procesar dos veces la misma plantilla.

---

## V-04 · Bloque 2 — se acaban los reintentos

**Qué prueba.** Que después de `vigilancia.reintentos.maximo` se levante para revisión humana en
vez de reintentar para siempre.

**Cómo.** Sobre una Solicitud en **Ingresada** vieja, poné `sanic_reintentosvalidacion = 3`
(el máximo). Esperá a que corra VIG.

**Esperado.**

| Qué | Valor |
|---|---|
| **No** se reintenta | no hay `Reintento` nuevo |
| `sanic_requiererevision` | **sí** |
| `sanic_motivorevision` | *"Validacion fallida 3 veces."* |
| Dónde se ve | vista **Para revisar** |

---

## V-05 · Bloque 3 — una comunicación que no salió

**Qué prueba.** Que una Solicitud En proceso sin acuse se recupere.

**Cómo.**
1. **Apagá** `Cloud Flow - MPPP - COM`.
2. Mandá un correo con `E01-feliz-formato11.xlsx`.
3. Comprobá que la Solicitud quedó **En proceso** y **sin acuse**.
4. Esperá los 30 minutos del umbral + una corrida de VIG.
5. **Volvé a prender** `MPPP-COM` al terminar.

**Esperado.**

| Qué | Valor |
|---|---|
| Llega el acuse | **sí** |
| Bitácora `Acuse iniciado` / `Acuse enviado` | origen **MPPP-VIG** (no MPPP-COM) |
| Llega **una sola vez** | sí |

---

## V-06 · Bloque 5 — los correos por clasificar vencen

**Qué prueba.** DF-09: lo que nadie clasifica en 30 días pasa a **Vencida**.

**Cómo.** Tomá una Solicitud en **No reconocida** (C-04) y poné `sanic_fecharecibido` con una fecha
de hace **40 días**. Esperá a que corra VIG.

**Esperado.**

| Qué | Valor |
|---|---|
| Estado | **Vencida** |
| `sanic_fechacerrada` | con fecha |
| Bitácora | `Vencida`, origen **MPPP-VIG** |
| Comunicación al cliente | **ninguna** |
| Sale de | **Por clasificar** |

> **Vencida** y no **Descartada**: la distinción es a propósito. Descartada = alguien decidió
> ignorarlo. Vencida = **nadie lo miró**, y eso es un dato de gestión.

---

## Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| V-01 corre en vacío | | | |
| **V-02 correo en la bandeja** | | | |
| V-03 reintento | | | |
| V-04 se acaban los reintentos | | | |
| V-05 comunicación pendiente | | | |
| V-06 vencimiento | | | |

> **Acordate de dejar todo como estaba**: `MPPP-REC` y `MPPP-COM` prendidos, y los parámetros con
> sus valores originales si los bajaste para no esperar.
