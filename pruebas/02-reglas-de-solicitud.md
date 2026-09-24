# 02 — Reglas de nivel Solicitud

Las cinco reglas que miran **el sobre**, no el contenido: si hay adjunto, si es Excel, si es uno
solo, si tiene la estructura de la plantilla y si trae filas.

Cadena de dependencias (`sanic_dependede`):

```
TRAE_ADJUNTO → ADJUNTO_ES_EXCEL → UN_SOLO_EXCEL → ESTRUCTURA_PLANTILLA → TIENE_FILAS
```

Todas con efecto **Rechaza**. Que fallen deja la Solicitud en **Rechazada**, con acuse.

**Lo que más importa de este archivo**: que una regla cuya dependencia falló quede **Omitida** y no
"No cumplida", y que su razón **diga qué regla la bloqueó** (DD-13). Un sistema que dice "falló la
estructura de la plantilla" cuando en realidad no había adjunto le miente al ejecutivo.

**Antes**: `00-preparacion.md`. El caso `TRAE_ADJUNTO` está en `01` como C-08.

---

## S-01 · El adjunto no es un Excel

**Qué prueba.** `ADJUNTO_ES_EXCEL` (D-15).

**Cómo.** Correo nuevo, asunto `Prueba S-01`, adjuntando **solo** `A01-no-es-excel.txt`.

**Esperado.**

| Qué | Valor |
|---|---|
| adjuntos / excel | `1 / 0` |
| `TRAE_ADJUNTO` | Cumplida |
| `ADJUNTO_ES_EXCEL` | **NO CUMPLIDA** |
| `UN_SOLO_EXCEL`, `ESTRUCTURA_PLANTILLA`, `TIENE_FILAS` | **Omitida** |
| Estado | **Rechazada** |
| Acuse | sí |

---

## S-02 · Dos Excel en el mismo correo

**Qué prueba.** `UN_SOLO_EXCEL`. No se adivina cuál procesar.

**Cómo.** Correo nuevo adjuntando **`E01-feliz-formato11.xlsx` y `E13-formato06-referencia-libre.xlsx`**.

**Esperado.**

| Qué | Valor |
|---|---|
| adjuntos / excel | `2 / 2` |
| `UN_SOLO_EXCEL` | **NO CUMPLIDA** |
| `ESTRUCTURA_PLANTILLA`, `TIENE_FILAS` | **Omitida** |
| Estado | **Rechazada** |
| archivos | **excel: NO** — no se subió ninguno, a propósito |

> Que no se suba **ninguno** es parte del diseño: si no sabemos cuál es el bueno, no elegimos.

---

## S-03 · Un Excel y un archivo que no lo es

**Qué prueba.** Que un adjunto extra que no sea Excel **no** rompa nada: el Excel candidato sigue
siendo el único `.xlsx`.

**Cómo.** Correo nuevo adjuntando **`E01-feliz-formato11.xlsx` y `A01-no-es-excel.txt`**.

**Esperado.**

| Qué | Valor |
|---|---|
| adjuntos / excel | `2 / 1` |
| Las 5 reglas | **Cumplida** |
| Estado | **En proceso**, 3 filas Validadas |

> Caso real y frecuente: el cliente manda la plantilla y además un PDF de respaldo.

---

## S-04 · La hoja de datos tiene otro nombre

**Qué prueba.** `ESTRUCTURA_PLANTILLA` contra `plantilla.estructura` (hoja `Datos`).

**Cómo.** Correo nuevo con **`E12-hoja-renombrada.xlsx`** (la hoja se llama `Datos2`).

**Esperado.**

| Qué | Valor |
|---|---|
| `UN_SOLO_EXCEL` | Cumplida |
| `ESTRUCTURA_PLANTILLA` | **NO CUMPLIDA** |
| `TIENE_FILAS` | **Omitida** |
| Estado | **Rechazada** |

> Esto tiene que ser una **regla fallida**, no un error del sistema. Si en la Bitácora aparece un
> evento `Error` o la Solicitud queda en **Ingresada**, es FALLA: una plantilla mal armada es un
> caso de negocio esperable, no una excepción (`03` §1, "Errores").

---

## S-05 · Excel con la estructura correcta pero sin filas

**Qué prueba.** `TIENE_FILAS`.

**Cómo.** Correo nuevo con **`E11-sin-filas.xlsx`**.

**Esperado.**

| Qué | Valor |
|---|---|
| `ESTRUCTURA_PLANTILLA` | Cumplida |
| `TIENE_FILAS` | **NO CUMPLIDA** |
| Estado | **Rechazada** |
| filas t/v/r | `0 / 0 / 0` |
| Acuse | sí |

---

## S-06 · Volumen: 100 filas

**Qué prueba.** El presupuesto de tiempo (`03` §1: objetivo **< 10 s**) y que `cantidadFilas` = 100
del parámetro se respete.

**Cómo.** Correo nuevo con **`E14-volumen-100.xlsx`**. **Anotá la hora de envío.**

**Esperado.**

| Qué | Valor |
|---|---|
| filas t/v/r | `100 / 100 / 0` |
| Estado | **En proceso** |
| Las 100 filas | **Validada**, con su referencia de 20 caracteres |
| Tiempo | entre `Ingresada` y `Validacion terminada` en la Bitácora: **menos de 10 s** |

**Cómo medir**: en el visor, restá las dos marcas de la Bitácora. Si pasa de 10 s, anotalo con el
número: no es un FALLA de funcionalidad, pero es un dato para la fase de rendimiento.

---

## S-07 · El acuse de una Rechazada dice lo que tiene que decir

**Qué prueba.** DD-09 y el texto obligatorio de DF-08. Esto lo lee un cliente del banco.

**Cómo.** Tomá el acuse que llegó en cualquier caso Rechazada (S-01, S-02, S-04, S-05 o C-08) y
leelo completo en tu casilla.

**Esperado.** El correo dice, con todas las letras:

1. El **número de solicitud** (`MPPP-########`).
2. Que **no hay nada que procesar**.
3. Que **no va a recibir otro correo** por esta solicitud.
4. Que **corrija y reenvíe**.
5. El texto obligatorio: *"Para enviar una plantilla nueva o corregida, escriba un correo nuevo a
   esta dirección. No responda a este mensaje: las respuestas no se procesan."*
6. Llega **como respuesta en el hilo** del correo original, y **solo a vos** (el remitente), no a
   quienes fueran en copia.

**FALLA si**: falta cualquiera de los 6 puntos, el texto tiene HTML crudo a la vista, aparece el
nombre de una regla técnica (`TRAE_ADJUNTO` y compañía) o se menciona cualquier SDK o producto.

> El punto 5 no es decorativo: es lo que evita que el cliente conteste el acuse y su respuesta
> caiga en **Por clasificar** para siempre.

---

## Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| S-01 adjunto no Excel | | | |
| S-02 dos Excel | | | |
| S-03 Excel + otro archivo | | | |
| S-04 hoja renombrada | | | |
| S-05 sin filas | | | |
| S-06 volumen 100 | | | seg: ____ |
| S-07 texto del acuse | | | |
