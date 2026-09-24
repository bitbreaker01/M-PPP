# 01 — Ingesta y clasificación del correo

Cubre `MPPP-REC`, `MPPP-ING` y el plugin liviano `sanic_mppp_capi_clasificarcorreo`, o sea las
reglas de **nivel Correo**: `ES_CORREO_NUEVO` y `REMITENTE_RECONOCIDO`.

**Antes**: `00-preparacion.md` completo.
**Cómo verificar**: `python3 herramientas/pruebas/ver_solicitud.py --ultima`

> Dejá pasar **1 o 2 minutos** después de enviar: el disparador de correo nuevo sondea cada minuto.

---

## C-01 · Camino feliz — correo nuevo, remitente autorizado, Excel válido

**Qué prueba.** La cadena entera: `MPPP-REC` → `MPPP-ING` → clasificación → validación.

**Cómo.** Desde tu `REMITENTE`, mandá a `mppp@55xljh.onmicrosoft.com`:

- Asunto: `Prueba C-01 inclusiones`
- Cuerpo: cualquier texto
- Adjunto: **`E01-feliz-formato11.xlsx`**

**Esperado.**

| Qué | Valor |
|---|---|
| Solicitud | se crea, número `MPPP-########` |
| Estado | **En proceso** |
| adjuntos / excel | `1 / 1` |
| filas t/v/r | `3 / 3 / 0` |
| archivos | correo: **sí** · excel: **sí** |
| outlook message id | **sí** |
| Reglas de Solicitud | las 5 en **Cumplida** |
| Las 3 filas | **Validada**, sin mensaje |
| Referencia de cada fila | `007` + cuenta rellena con ceros a la izquierda = **20 caracteres** |
| Bitácora | `Ingresada` (MPPP-REC) y `Validacion terminada` (Custom API) |
| Acuse | `sanic_acusecontenido` con texto, y **acuse enviado con fecha** |
| El correo | ya **no** está en la bandeja: está en `Procesados` |

**Referencia esperada, fila por fila** (regla D-17: código de banco 3 + cuenta rellena a 17):

| Cuenta en el Excel (14 dígitos) | Rellena a 17 | Referencia esperada (20) |
|---|---|---|
| `10203040506070` | `00010203040506070` | `00700010203040506070` |
| `11223344556677` | `00011223344556677` | `00700011223344556677` |
| `99887766554433` | `00099887766554433` | `00700099887766554433` |

> Las tres tienen que medir **exactamente 20 caracteres** y empezar con `007`. Si alguna mide
> distinto o rellena por la derecha, es **FALLA**: la referencia va a AS400 y un dígito corrido
> manda la plata a otra cuenta.

---

## C-02 · Una respuesta NO se procesa

**Qué prueba.** `ES_CORREO_NUEVO` con una respuesta (DF-08). Es lo que impide un bucle de correos
con un "fuera de oficina".

**Cómo.** Tomá el acuse que te llegó en C-01 y **respondelo** (Responder, no correo nuevo). Adjuntá
`E01-feliz-formato11.xlsx` para que quede claro que no se procesa aunque traiga plantilla.

**Esperado.**

| Qué | Valor |
|---|---|
| Estado | **No es correo nuevo** |
| motivo clasificación | dice que es una respuesta a otro correo |
| filas | **0** — no se abrió el Excel |
| `ES_CORREO_NUEVO` | **NO CUMPLIDA** |
| `REMITENTE_RECONOCIDO` | **Omitida** (la bloqueó la anterior) |
| Comunicación al cliente | **NINGUNA**. No te tiene que llegar nada |
| Aviso en la app | a todos los ejecutivos (campana) |

> **Lo más importante de este caso es lo que NO pasa**: si te llega una respuesta automática del
> sistema, es FALLA grave. Ahí está el bucle infinito que DF-08 evita.

---

## C-03 · Un reenvío SÍ se procesa

**Qué prueba.** Que `ES_CORREO_NUEVO` distinga reenvío de respuesta por el prefijo del asunto
(`FW:`, `FWD:`, `RV:`, `REENV:`, de `correo.prefijos.reenvio`).

**Cómo.** Reenviá (Forward) cualquier correo a `mppp@…`, con asunto empezando en `FW:` y adjuntando
`E01-feliz-formato11.xlsx`.

**Esperado.** Igual que C-01: **En proceso**, 3 filas Validadas, `ES_CORREO_NUEVO` **Cumplida**.

> Un reenvío trae `In-Reply-To`/`References` igual que una respuesta. Lo único que lo distingue es
> el prefijo. Si este caso queda en **No es correo nuevo**, la regla no está mirando el asunto.

---

## C-04 · Remitente no reconocido

**Qué prueba.** `REMITENTE_RECONOCIDO` (RF-02).

**Cómo.** Mandá desde **otra** dirección, una que NO esté en Autorizados, con
`E01-feliz-formato11.xlsx` adjunto.

**Esperado.**

| Qué | Valor |
|---|---|
| Estado | **No reconocida** |
| motivo clasificación | que el remitente no tiene autorización vigente |
| filas | **0** |
| `ES_CORREO_NUEVO` | Cumplida |
| `REMITENTE_RECONOCIDO` | **NO CUMPLIDA** |
| Comunicación | **NINGUNA** |
| Dónde se ve | vista **Por clasificar** del sitemap |

---

## C-05 · El correo se mueve y cambia de identificador

**Qué prueba.** El paso 7 de `MPPP-ING` y DF-04: el identificador de Outlook **cambia al mover**, y
por eso hay una acción aparte que lo vuelve a guardar.

**Cómo.** Usá la Solicitud de C-01. Mirá `Procesados` en el buzón y el campo del visor.

**Esperado.**

- El correo de C-01 está en **`Procesados`**, no en la bandeja de entrada.
- `outlook message id` dice **sí**.

> Si el correo quedó en la bandeja, `MPPP-VIG` lo va a reingerir a los 15 minutos y vas a ver una
> segunda Solicitud… **no**: la clave única lo impide (C-07). Vas a ver reintentos en la Bitácora.

---

## C-06 · El `.eml` queda guardado

**Qué prueba.** RF-10 y el insumo del plugin liviano: sin el `.eml` no hay clasificación.

**Cómo.** Abrí la Solicitud de C-01 en la app, pestaña con los archivos.

**Esperado.** `sanic_correocrudo` tiene un archivo `correo.eml` descargable, y `sanic_exceloriginal`
tiene el `.xlsx` con **el nombre original** del adjunto.

> Descargá el `.eml` y abrilo con un editor de texto: tienen que verse las cabeceras
> (`From:`, `Subject:`, `Message-ID:`). Es lo que lee el clasificador.

---

## C-07 · El mismo correo dos veces no duplica

**Qué prueba.** La clave alternativa sobre `sanic_messageid` (DD-03) y el paso 4b de `MPPP-ING`.

**Cómo.** No se puede reenviar el mismo `Message-ID` desde el cliente de correo, así que se fuerza:

```bash
python3 herramientas/pruebas/ver_solicitud.py --ultima     # anotá el número
```

Pedile a quien tenga acceso al buzón que **mueva el correo de C-01 de `Procesados` de vuelta a la
bandeja de entrada**. `MPPP-VIG` lo va a reingerir en los próximos 15 minutos.

**Esperado.**

- **NO** se crea una segunda Solicitud. El total de Solicitudes no cambia.
- La Solicitud original queda como estaba (no se revalida: ya no está en Ingresada).
- En la Bitácora puede aparecer un `Reintento` con origen **MPPP-VIG**.

> Este caso protege contra el peor escenario del sistema: **procesar dos veces la misma plantilla**
> y mandarle al cliente dos acuses distintos.

---

## C-08 · Sin adjunto

**Qué prueba.** `TRAE_ADJUNTO` y, sobre todo, que las reglas que dependen de ella queden
**Omitidas** y no "No cumplidas" (DD-13).

**Cómo.** Mandá un correo nuevo desde tu `REMITENTE`, asunto `Prueba C-08 sin adjunto`,
**sin ningún archivo adjunto**.

**Esperado.**

| Regla | Resultado |
|---|---|
| `TRAE_ADJUNTO` | **NO CUMPLIDA** |
| `ADJUNTO_ES_EXCEL` | **Omitida**, razón: la bloqueó `TRAE_ADJUNTO` |
| `UN_SOLO_EXCEL` | **Omitida** |
| `ESTRUCTURA_PLANTILLA` | **Omitida** |
| `TIENE_FILAS` | **Omitida** |

| Qué | Valor |
|---|---|
| Estado | **Rechazada** |
| filas | 0 |
| Acuse | **sí**, y dice que no hay nada que procesar, que no va a recibir otro correo por esta solicitud, y que corrija y reenvíe |

> Ojo con la firma con logo: una imagen incrustada llega como adjunto `isInline = true` y **no
> cuenta** (DF-07). Si este caso dice "trae 1 adjunto", la regla no está filtrando los inline.

---

## Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| C-01 camino feliz | | | |
| C-02 respuesta no se procesa | | | |
| C-03 reenvío sí se procesa | | | |
| C-04 remitente no reconocido | | | |
| C-05 el correo se mueve | | | |
| C-06 el `.eml` queda | | | |
| C-07 no duplica | | | |
| C-08 sin adjunto | | | |
