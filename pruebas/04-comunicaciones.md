# 04 — Comunicaciones al cliente

Cubre `MPPP-COM` (detecta) y `MPPP-ENV` (envía). Las dos comunicaciones son **el acuse** y **la
respuesta final**, y las dos salen como **respuesta en el hilo**, desde el buzón, **solo al
remitente** (DF-03).

**La garantía que hay que romper para que esto falle**: *el cliente nunca recibe dos veces lo
mismo*. Ante la duda, no se reenvía y lo mira una persona (D-21).

**Antes**: `01` y `03`, sobre todo C-01 y R-13.

---

## M-01 · El acuse llega, y llega una sola vez

**Qué prueba.** La cadena `Validación` → estado En proceso → `MPPP-COM` → `MPPP-ENV`.

**Cómo.** Usá la Solicitud de **C-01**. Mirá tu casilla.

**Esperado.**

| Qué | Valor |
|---|---|
| Llega | **un** correo, como **respuesta en el hilo** de tu envío original |
| Destinatario | **solo vos**, no quienes fueran en copia |
| `sanic_fechaacuseiniciado` | con fecha |
| `sanic_fechaacuseenviado` | con fecha |
| Bitácora | `Acuse iniciado` y `Acuse enviado`, **origen MPPP-COM** |
| Estado de la Solicitud | sigue en **En proceso** (un acuse de En proceso no cambia el estado) |

**Esperá 5 minutos y mirá otra vez**: no tiene que llegar un segundo acuse. `MPPP-VIG` corre cada
10 minutos y **no** debe reenviar nada.

---

## M-02 · El acuse de una Rechazada cierra la Solicitud

**Qué prueba.** DD-09: acuse de una **Rechazada** → **Cerrada** + `sanic_fechacerrada`.

**Cómo.** Usá cualquier Solicitud que haya quedado **Rechazada** (S-01, S-05, C-08…).

**Esperado.**

| Qué | Valor |
|---|---|
| Llega el acuse | sí |
| Estado después | **Cerrada** |
| `sanic_fechacerrada` | con fecha |
| Bitácora | `Acuse enviado` y después `Cerrada` |

> La diferencia con M-01 es todo el punto: una Rechazada **termina acá** (no hay nada que digitar),
> una En proceso sigue viva hasta que se digiten y aprueben sus filas.

---

## M-03 · Copia y remitente

**Qué prueba.** DF-03: solo al remitente, nunca a los de copia.

**Cómo.** Correo nuevo con `E01-feliz-formato11.xlsx`, pero poné **otra dirección tuya en CC**.

**Esperado.** El acuse llega **solo** a la dirección del **De**. A la de CC **no le llega nada**.

**FALLA si** le llega a la copia: se le estaría verificando la autorización a uno y respondiéndole
a otro.

---

## M-04 · La respuesta final, cuando todas las filas se resuelven

**Qué prueba.** El ciclo completo hasta **Procesada** → respuesta final → **Cerrada**.

**Depende de**: `05-app-y-comandos.md`, porque hay que digitar y aprobar desde la app.

**Cómo.**

1. Tomá la Solicitud de **C-01** (3 filas Validadas, En proceso).
2. En la app, vista **Por digitar**: seleccioná las 3 y **Digitada**.
3. Entrá como Supervisor, vista **Por aprobar**: seleccioná las 3 y **Aprobar**.

**Esperado.**

| Momento | Qué pasa |
|---|---|
| Al aprobar la última fila | La Solicitud pasa a **Procesada** |
| Enseguida | `MPPP-COM` dispara `MPPP-ENV` |
| Llega | la **respuesta final**, en el mismo hilo, solo al remitente |
| Estado final | **Cerrada** + `sanic_fechacerrada` |
| Bitácora | `Procesada`, `Respuesta final iniciada`, `Respuesta final enviada`, `Cerrada` |

**Leé la respuesta final completa.** Tiene que decir qué pasó con cada fila y llevar el texto
obligatorio de DF-08 ("no responda a este mensaje…").

---

## M-05 · Nunca dos veces lo mismo

**Qué prueba.** D-21 y el paso 1 de `MPPP-ENV`: si el acuse ya está **iniciado**, no se envía otra vez.

**Cómo.** Forzá un segundo disparo de `MPPP-COM` sobre una Solicitud que ya tiene acuse enviado:
en la app, abrí la Solicitud de **C-01** y cambiale el estado a **En proceso** (si ya está ahí,
tocá y guardá cualquier otro campo para que se dispare una actualización).

**Esperado.**

| Qué | Valor |
|---|---|
| Llega un segundo acuse | **NO** |
| `sanic_fechaacuseenviado` | **no cambia** |
| Nuevas entradas de Bitácora de acuse | ninguna |

**FALLA si** llega un segundo correo. Es el defecto más caro de todos: el cliente recibe dos acuses
contradictorios de la misma solicitud.

---

## M-06 · Envío iniciado sin confirmar → revisión humana

**Qué prueba.** Que una comunicación a medias **no se reenvíe** y levante bandera (D-21).

**Cómo.** Simulá el estado a medias: en la app, sobre una Solicitud **En proceso** que todavía no
tenga acuse, poné `sanic_fechaacuseiniciado` con la hora de hace 40 minutos y dejá
`sanic_fechaacuseenviado` **vacío**. Esperá a que corra `MPPP-VIG` (hasta 10 minutos).

**Esperado.**

| Qué | Valor |
|---|---|
| Llega un acuse | **NO** |
| `sanic_requiererevision` | **sí** |
| `sanic_motivorevision` | *"Envio iniciado sin confirmar…"* |
| Bitácora | `Requiere revision`, origen **MPPP-VIG** |
| Dónde se ve | vista **Para revisar** del sitemap |

> Éste es el costo aceptado del diseño: ante la duda no se reenvía y lo mira una persona. Si acá
> llega un correo, la garantía de "como máximo una vez" no existe.

---

## M-07 · El cuerpo lo arma el código, no el flujo

**Qué prueba.** DD-08: el contenido viene de `sanic_acusecontenido`, que escribe la Custom API.

**Cómo.** Abrí una Solicitud con acuse y compará el campo `sanic_acusecontenido` con el correo que
te llegó:

```bash
python3 herramientas/pruebas/ver_solicitud.py MPPP-########
```

**Esperado.** El cuerpo del correo es **exactamente** el HTML de ese campo. No hay texto agregado
por el flujo.

**FALLA si** el correo trae algo que no está en el campo (una firma automática, un encabezado
puesto por Power Automate, un "Sent from…").

---

## Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| M-01 acuse, una sola vez | | | |
| M-02 Rechazada → Cerrada | | | |
| M-03 solo al remitente | | | |
| M-04 respuesta final | | | |
| **M-05 nunca dos veces** | | | |
| M-06 a medias → revisión | | | |
| M-07 cuerpo del código | | | |
