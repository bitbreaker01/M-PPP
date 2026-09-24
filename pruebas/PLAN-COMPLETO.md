# Plan de pruebas funcionales — MPPP fase 1
Proyecto `2026-001-referencias-planes-pago` · Entorno **Dev** · 2026-09-23
Este documento junta los 10 archivos de `pruebas/` en uno solo, para leerlo de corrido.
Los archivos separados (y los Excel) están en el repositorio, en `pruebas/`.

---
## Índice y cómo usarlo

Proyecto: `2026-001-referencias-planes-pago` · Entorno: **Dev**

Los 170 componentes de la fase 1 están construidos y verificados **estructuralmente**: existen,
están bien formados y están en la solución. Lo que estas pruebas comprueban es otra cosa, la que
importa: **que hagan lo que el diseño dice que hacen**.

Ningún flujo se ejecutó nunca. Ningún comando de la barra se ejecutó nunca en un navegador.

---

## Cómo está organizado

| Archivo | Qué cubre | Casos |
|---|---|---|
| `00-preparacion.md` | Datos, buzón, carpeta. **Se hace una sola vez** | 6 |
| `01-clasificacion-del-correo.md` | `MPPP-REC`, `MPPP-ING`, el plugin liviano, reglas de nivel **Correo** | 8 |
| `02-reglas-de-solicitud.md` | Reglas de nivel **Solicitud**: adjunto, Excel, estructura, filas | 7 |
| `03-reglas-de-registro.md` | Reglas de nivel **Registro**: las 8 que deciden fila por fila | 14 |
| `04-comunicaciones.md` | `MPPP-COM`, `MPPP-ENV`: acuse y respuesta final, "como máximo una vez" | 7 |
| `05-app-y-comandos.md` | Los 8 comandos de la barra y el diálogo de motivo | 13 |
| `06-seguridad-vistas-formularios.md` | Roles, perfil de columnas, sitemap, 18 vistas, 9 formularios | 12 |
| `07-vigilancia.md` | `MPPP-VIG`: los 5 bloques de recuperación | 6 |
| `08-integridad-y-plugins.md` | Steps de plugin, catálogo de reglas, claves únicas | 9 |

**82 casos.** Cada uno trae: qué prueba, cómo hacerlo, **qué tiene que pasar** y cómo verificarlo.

---

## Antes de empezar

1. Corré **`00-preparacion.md`** entero. Sin eso, la mitad de los casos no
   tiene sentido: citan planes y autorizaciones que hay que crear.
2. Tené a mano la herramienta de lectura, que evita andar clickeando para ver qué pasó:

   ```bash
   python3 herramientas/pruebas/ver_solicitud.py MPPP-00001234
   python3 herramientas/pruebas/ver_solicitud.py --ultima
   ```

   Muestra, de una sola vez: estado de la Solicitud, sus contadores, **cada regla con su
   resultado y su razón**, las filas con su estado y su mensaje, y la Bitácora completa.

---

## Cómo anotar los resultados

Cada archivo termina con una tabla para llenar. Poné:

- **OK** — pasó exactamente lo esperado
- **FALLA** — pasó otra cosa. Anotá qué pasó, con el número de solicitud
- **N/A** — no se pudo correr, y por qué

**Un caso que "casi" pasa es un FALLA.** Si el estado es el correcto pero el mensaje al cliente
dice otra cosa, es un FALLA: el mensaje lo lee el cliente del banco.

---

## Dos advertencias

**Esto escribe en Dev.** Los casos crean Solicitudes, Filas y Bitácora reales, y mandan correos
reales desde el buzón. Todo con datos ficticios y con planes `PR*` que se borran después
(`preparar_datos.py --limpiar`), pero el ruido en las tablas queda.

**El orden importa dentro de cada archivo.** Varios casos usan la Solicitud que dejó el anterior
(sobre todo en `04` y `05`). Cada caso dice de qué depende.

---

## Qué NO cubren estas pruebas

Para que no haya sorpresas después:

- **Rendimiento real.** `E14-volumen-100.xlsx` mira que 100 filas entren en el presupuesto de
  10 s (`03` §1), pero no es una prueba de carga: son 7.500 filas por mes en producción.
- **Concurrencia.** Dos correos exactamente simultáneos, o dos supervisores aprobando la misma
  fila, no se prueban acá. D-43 sigue abierta.
- **Migración desde SharePoint** (RF-16): es de Producción, no de Dev.
- **Fases 2 y 3** (RPA, histórico).


---

## 00 — Preparación

Se hace **una sola vez**, antes de todos los demás archivos. Si algo de acá falla, no sigas: los
casos siguientes van a fallar por el andamio y no por el sistema, y eso no prueba nada.

---

### P-01 · La carpeta del buzón

**Qué prueba.** Que exista el destino al que `MPPP-ING` mueve el correo ya ingresado.
`MoveV2` la busca por **nombre exacto** (`folderPath`), no por identificador.

**Cómo.** Entrá al buzón compartido `mppp@55xljh.onmicrosoft.com` y fijate si existe una carpeta
de primer nivel llamada exactamente **`Procesados`** — con P mayúscula, sin tilde, sin espacios
alrededor. Si no existe, creala.

**Esperado.** La carpeta existe y está vacía (o con lo que haya de antes).

> Si preferís otro nombre, cambialo en la variable de entorno
> `sanic_mppp_ev_carpetaprocesados` y en `playbooks/variable-entorno/sanic_mppp_ev_carpetaprocesados.md`.
> **No alcanza con crear la carpeta**: el valor de la variable tiene que coincidir.

---

### P-01b · Los permisos del buzón compartido

**Qué prueba.** Que la cuenta de la **conexión de Outlook** pueda leer, mover y responder en el
buzón compartido. **Sin esto no funciona NINGÚN flujo**: los cinco pasan por ahí.

**Por qué está acá.** El 2026-09-23 los flujos fallaron con **HTTP 403** en `Leer_la_bandeja`, y
costó varias vueltas llegar: la cuenta veía el buzón en Outlook web, pero la conexión no podía
leerlo por API.

**Los siete puntos que tocan el buzón compartido**, todos con *Original Mailbox Address*:

| Flujo | Acción | Qué necesita |
|---|---|---|
| REC | trigger `SharedMailboxOnNewEmailV2` | **Full Access** |
| ING | `GetEmailV2`, `ExportEmail_V2`, `MoveV2` | **Full Access** |
| VIG | `GetEmailsV3` | **Full Access** |
| ENV | `ReplyToV3` ×2 | **Full Access + Send As** |

**Cómo.** En el Exchange admin center → **Recipients → Mailboxes** → el buzón de ingesta:

1. **Tipo de buzón**: tiene que decir **Shared**, no **User**. Las acciones con *Original Mailbox
   Address* están pensadas para buzones compartidos.
2. **Manage mailbox delegation** → la cuenta de la conexión de Outlook tiene que estar en:
   - **Full Access** — para leer, exportar y mover
   - **Send As** (o Send on Behalf) — **para responder**. Learn es explícito: *"a user with Full
     Access permission can't send email from the shared mailbox unless they also have Send As or
     Send on Behalf permission"*. Con solo Full Access, ENV falla y el cliente no recibe el acuse.
3. **Qué cuenta es**: Power Automate → Conexiones → la de Office 365 Outlook. Ojo: **la cuenta con
   la que vos abrís el buzón no es necesariamente la de la conexión.**

**Esperado.** Buzón de tipo Shared, y la cuenta de la conexión con **Full Access y Send As**.

> **Los permisos tardan.** Learn: de **30 a 60 minutos**, y a veces hasta 24 horas. Si acabás de
> darlos, esperá antes de dar nada por roto. El *remove and re-add* de la delegación fuerza el
> refresco del token.

> **Si el 403 persiste con los permisos puestos**, la prueba que discrimina: un flujo nuevo con una
> sola acción *Get emails (V3)*, probándolo contra **otro buzón compartido del tenant que ya
> funcione** y contra el de ingesta. Si el otro anda y el de ingesta no, el problema es del buzón,
> no del flujo ni de la cuenta.

---

### P-02 · El remitente de las pruebas

**Qué prueba.** Que tengas una casilla real desde la que mandar, y a la que lleguen las respuestas.

**Cómo.** Elegí la dirección desde la que vas a enviar todos los correos de prueba. Puede ser tu
cuenta personal del tenant. **No uses el propio buzón de ingesta**: un correo del buzón a sí mismo
se comporta distinto y ensucia los casos.

Anotala acá, porque la vas a citar en todos los casos:

```
REMITENTE = ______________________________
```

**Esperado.** Podés enviar desde esa dirección y leer lo que llega a ella.

---

### P-03 · Datos de negocio de prueba

**Qué prueba.** Que existan los planes y autorizaciones que citan los Excel de prueba.

**Cómo.**

```bash
python3 herramientas/pruebas/preparar_datos.py --remitente TU-CORREO@dominio.com
```

**Esperado.** Última línea con `"estado": "creado"` y las comprobaciones en verde. Crea:

| Qué | Detalle | Para qué |
|---|---|---|
| Cliente | `PR - Pruebas MPPP SA` | dueño de todos los planes |
| Plan `PR11` | formato **11**, COR, activo | camino feliz y reglas de formato 11 |
| Plan `PR06` | formato **06**, COR, activo | que la referencia **no** se derive (DD-15) |
| Plan `PR10` | formato **10**, **USD**, activo | `MONEDA_DEL_PLAN` |
| Plan `PRIN` | formato 06, COR, **INACTIVO** | `PLAN_EXISTE` con un plan que existe pero no vale |
| Plan `PRNA` | formato 06, COR, activo | `AUTORIZACION_CORREO_PLAN`: **sin** autorización del remitente |
| Autorizado | tu dirección | `REMITENTE_RECONOCIDO` |
| Autorizaciones | a PR11, PR06, PR10 y PRIN | **a PRNA no, a propósito** |

**Verificá** con `python3 herramientas/pruebas/preparar_datos.py --verificar --remitente TU-CORREO@dominio.com`.

> Al terminar TODAS las pruebas: `preparar_datos.py --limpiar --remitente TU-CORREO@dominio.com`.

---

### P-04 · Los Excel de los casos

**Qué prueba.** Que estén los 15 Excel y el adjunto que no es Excel.

**Cómo.**

```bash
python3 herramientas/pruebas/generar_excel.py
ls pruebas/adjuntos/
```

**Esperado.** 15 `.xlsx` y 1 `.txt` en `pruebas/adjuntos/`. Todos salen de la plantilla **real**
del cliente: misma hoja `Datos`, encabezados en la fila 12, datos desde la 13.

> Abrí `E01-feliz-formato11.xlsx` y mirá que las tres filas estén desde la fila 13, en las
> columnas B a K. Si eso está bien, los demás también.

---

### P-05 · Los cinco flujos activos

**Qué prueba.** Que la automatización esté encendida.

**Cómo.**

```bash
for f in ing rec env com vig; do python3 herramientas/construir/flujo.py playbooks/flujo/mppp-$f.md --solo-verificar; done
```

**Esperado.** Los cinco con `"estado": "ya_existia"` y la palabra **`activado`** en el detalle.
Si alguno dice `difiere ... statecode 0`, está apagado: prendelo antes de seguir.

---

### P-06 · Los parámetros cargados

**Qué prueba.** Que estén los umbrales y las listas que usa la validación.

**Cómo.**

```bash
python3 herramientas/pruebas/ver_solicitud.py --parametros
```

**Esperado.** 12 parámetros activos. Los que más van a importar:

| Parámetro | Valor esperado | Dónde pega |
|---|---|---|
| `vigilancia.minutos.sinvalidar` | `15` | caso 07 |
| `vigilancia.minutos.sinresponder` | `30` | caso 07 |
| `vigilancia.reintentos.maximo` | `3` | caso 07 |
| `clasificacion.dias.vencimiento` | `30` | caso 07 |
| `plantilla.estructura` | hoja `Datos`, encabezado 12, primera fila 13 | casos 02 y 03 |
| `plantilla.listas` | banco **BAC = código `007`** | caso 03 |
| `plantilla.obligatoriedad` | todo obligatorio salvo `referencia` | caso 03 |

> El código `007` de BAC importa: es el que se usa para construir la referencia de formato 11, y
> sale del Excel real del cliente. Si ahí dijera otra cosa, las referencias saldrían mal en AS400.

---

### Resultados

| Caso | Resultado | Notas |
|---|---|---|
| P-01 carpeta `Procesados` | | |
| **P-01b permisos del buzón** | | Full Access + Send As |
| P-02 remitente | | |
| P-03 datos de negocio | | |
| P-04 Excel generados | | |
| P-05 flujos activos | | |
| P-06 parámetros | | |


---

## 01 — Ingesta y clasificación del correo

Cubre `MPPP-REC`, `MPPP-ING` y el plugin liviano `sanic_mppp_capi_clasificarcorreo`, o sea las
reglas de **nivel Correo**: `ES_CORREO_NUEVO` y `REMITENTE_RECONOCIDO`.

**Antes**: `00-preparacion.md` completo.
**Cómo verificar**: `python3 herramientas/pruebas/ver_solicitud.py --ultima`

> Dejá pasar **1 o 2 minutos** después de enviar: el disparador de correo nuevo sondea cada minuto.

---

### C-01 · Camino feliz — correo nuevo, remitente autorizado, Excel válido

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

### C-02 · Una respuesta NO se procesa

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

### C-03 · Un reenvío SÍ se procesa

**Qué prueba.** Que `ES_CORREO_NUEVO` distinga reenvío de respuesta por el prefijo del asunto
(`FW:`, `FWD:`, `RV:`, `REENV:`, de `correo.prefijos.reenvio`).

**Cómo.** Reenviá (Forward) cualquier correo a `mppp@…`, con asunto empezando en `FW:` y adjuntando
`E01-feliz-formato11.xlsx`.

**Esperado.** Igual que C-01: **En proceso**, 3 filas Validadas, `ES_CORREO_NUEVO` **Cumplida**.

> Un reenvío trae `In-Reply-To`/`References` igual que una respuesta. Lo único que lo distingue es
> el prefijo. Si este caso queda en **No es correo nuevo**, la regla no está mirando el asunto.

---

### C-04 · Remitente no reconocido

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

### C-05 · El correo se mueve y cambia de identificador

**Qué prueba.** El paso 7 de `MPPP-ING` y DF-04: el identificador de Outlook **cambia al mover**, y
por eso hay una acción aparte que lo vuelve a guardar.

**Cómo.** Usá la Solicitud de C-01. Mirá `Procesados` en el buzón y el campo del visor.

**Esperado.**

- El correo de C-01 está en **`Procesados`**, no en la bandeja de entrada.
- `outlook message id` dice **sí**.

> Si el correo quedó en la bandeja, `MPPP-VIG` lo va a reingerir a los 15 minutos y vas a ver una
> segunda Solicitud… **no**: la clave única lo impide (C-07). Vas a ver reintentos en la Bitácora.

---

### C-06 · El `.eml` queda guardado

**Qué prueba.** RF-10 y el insumo del plugin liviano: sin el `.eml` no hay clasificación.

**Cómo.** Abrí la Solicitud de C-01 en la app, pestaña con los archivos.

**Esperado.** `sanic_correocrudo` tiene un archivo `correo.eml` descargable, y `sanic_exceloriginal`
tiene el `.xlsx` con **el nombre original** del adjunto.

> Descargá el `.eml` y abrilo con un editor de texto: tienen que verse las cabeceras
> (`From:`, `Subject:`, `Message-ID:`). Es lo que lee el clasificador.

---

### C-07 · El mismo correo dos veces no duplica

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

### C-08 · Sin adjunto

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

### Resultados

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


---

## 02 — Reglas de nivel Solicitud

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

### S-01 · El adjunto no es un Excel

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

### S-02 · Dos Excel en el mismo correo

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

### S-03 · Un Excel y un archivo que no lo es

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

### S-04 · La hoja de datos tiene otro nombre

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

### S-05 · Excel con la estructura correcta pero sin filas

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

### S-06 · Volumen: 100 filas

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

### S-07 · El acuse de una Rechazada dice lo que tiene que decir

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

### Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| S-01 adjunto no Excel | | | |
| S-02 dos Excel | | | |
| S-03 Excel + otro archivo | | | |
| S-04 hoja renombrada | | | |
| S-05 sin filas | | | |
| S-06 volumen 100 | | | seg: ____ |
| S-07 texto del acuse | | | |


---

## 03 — Reglas de nivel Registro

Las ocho reglas que deciden **fila por fila**. Son el corazón del sistema: de acá sale si una
referencia entra a AS400 o no.

```
LISTAS_VALIDAS ──┬─→ FORMATO_11_SOLO_ACH ─┬─→ REFERENCIA_FORMATO_11
LARGOS_Y_FORMATO │                         │
PLAN_EXISTE ─────┼─→ OBLIGATORIEDAD ───────┘
                 ├─→ MONEDA_DEL_PLAN
                 └─→ AUTORIZACION_CORREO_PLAN
```

**Tres cosas que este archivo vigila especialmente:**

1. **El historial regla por regla es del sobre, no de la fila** (`03` §5). En `ResultadoRegla` ves
   Cumplida/No cumplida/Omitida del **correo**; en `sanic_mensaje` de cada fila ves **solo los
   motivos que fallaron en esa fila**.
2. **`Sin autorización` gana** sobre `Rechazada en validación`, aunque además falle otra regla
   (D-14), pero el mensaje lleva **todos** los motivos.
3. **Un valor inválido no se cita** en el mensaje (DD-01, D-41): se nombra el campo, no el valor.
   Los datos del cliente no se repiten en un texto que puede terminar en cualquier lado.

**Antes**: `00-preparacion.md`, con los planes `PR11`, `PR06`, `PR10`, `PRIN` y `PRNA`.

---

### R-01 · Valores fuera de las listas

**Qué prueba.** `LISTAS_VALIDAS` contra `plantilla.listas`.

**Cómo.** Correo nuevo con **`E02-listas-invalidas.xlsx`** (5 filas, una por campo).

**Esperado.** Las 5 filas en **Rechazada en validación**. Cada `sanic_mensaje` nombra **el campo**:

| Fila | Qué trae mal | Mensaje esperado (nombra el campo) |
|---|---|---|
| 1 | `gestion = Alta` | …no son válidos: **Gestión** |
| 2 | `moneda = EUR` | …no son válidos: **Moneda** |
| 3 | `banco = SANTANDER` | …no son válidos: **Banco** |
| 4 | `tipoIdentificacion = XXX` | …no son válidos: **Tipo de identificación** |
| 5 | `clasificacion = TRANSFER` | …no son válidos: **Clasificación** |

**FALLA si** el mensaje **cita el valor** (`"Alta no es válido"`, `"EUR"`, `"SANTANDER"`). Eso es
DD-01/D-41: se nombra el campo, nunca el dato del cliente.

| Qué | Valor |
|---|---|
| Estado de la Solicitud | **Rechazada** (ninguna fila quedó Validada) |
| filas t/v/r | `5 / 0 / 5` |

---

### R-02 · Largos y formato

**Qué prueba.** `LARGOS_Y_FORMATO` contra los `largoMinimo`/`largoMaximo` de `plantilla.estructura`.

**Cómo.** Correo nuevo con **`E03-largos-invalidos.xlsx`**.

**Esperado.** Las 4 filas en **Rechazada en validación**:

| Fila | Qué trae mal | Máximo |
|---|---|---|
| 1 | nombre de 64 caracteres | 44 |
| 2 | plan `PR11XX` (6) | 4 |
| 3 | cuenta de 21 | 16 |
| 4 | identificación de 22 | 16 |

> La fila 2 es interesante: el plan es **largo**, así que falla `LARGOS_Y_FORMATO`. Mirá qué pasa
> con `PLAN_EXISTE` en esa fila — el plan `PR11XX` tampoco existe. El mensaje puede traer los dos
> motivos, y está bien: `sanic_mensaje` lleva **todos** los que fallaron.

---

### R-03 · Plan que no existe

**Qué prueba.** `PLAN_EXISTE`. **Nunca se adivina un plan parecido.**

**Cómo.** Correo nuevo con **`E04-plan-inexistente.xlsx`** (plan `ZZ99`).

**Esperado.**

| Qué | Valor |
|---|---|
| La fila | **Rechazada en validación** |
| `sanic_planid` de la fila | **vacío** |
| Mensaje | que el plan no existe o no está activo |
| Estado | **Rechazada** |

**FALLA si** la fila quedó enganchada a `PR11` u otro plan "parecido". Adivinar un plan es mandar
plata al cliente equivocado.

---

### R-04 · Plan que existe pero está inactivo

**Qué prueba.** Que `PLAN_EXISTE` exija **activo**, no solo que exista.

**Cómo.** Correo nuevo con **`E15-plan-inactivo.xlsx`** (plan `PRIN`, que `preparar_datos.py`
desactivó a propósito).

**Esperado.** Igual que R-03: fila **Rechazada en validación**, `sanic_planid` vacío.

> Este caso y R-03 se ven iguales desde afuera, y así tiene que ser. Lo que prueba es que el
> filtro de la consulta lleva el estado, no solo el código.

---

### R-05 · Plan formato 11 con clasificación que no es ACH

**Qué prueba.** `FORMATO_11_SOLO_ACH` (DD-17).

**Cómo.** Correo nuevo con **`E05-formato11-no-ach.xlsx`** (plan `PR11`, clasificaciones `BAC` y `CK`).

**Esperado.**

| Qué | Valor |
|---|---|
| Las 2 filas | **Rechazada en validación** |
| Mensaje | que un plan de formato 11 solo admite ACH |
| `REFERENCIA_FORMATO_11` en esas filas | no aplica: su dependencia falló |

---

### R-06 · Campos obligatorios vacíos, y el opcional

**Qué prueba.** `OBLIGATORIEDAD` contra `plantilla.obligatoriedad` (todo obligatorio **salvo
`referencia`**, DD-16).

**Cómo.** Correo nuevo con **`E06-obligatoriedad.xlsx`** (4 filas).

**Esperado.**

| Fila | Qué falta | Resultado |
|---|---|---|
| 1 | nombre del beneficiario | **Rechazada en validación** |
| 2 | número de cuenta | **Rechazada en validación** |
| 3 | tipo de identificación | **Rechazada en validación** |
| 4 | **solo la referencia** | **Validada** ← la referencia es opcional |

| Qué | Valor |
|---|---|
| filas t/v/r | `4 / 1 / 3` |
| Estado | **En proceso** (hay una válida) |

> **La fila 4 es el caso que más vale.** Si queda Rechazada, la obligatoriedad está mal leída y el
> sistema va a rechazar plantillas perfectamente correctas. Además, como es plan formato 11, su
> referencia se **construye** igual (no la trae el cliente): mirá que tenga sus 20 caracteres.

---

### R-07 · Moneda distinta de la del plan

**Qué prueba.** `MONEDA_DEL_PLAN` (RF-07).

**Cómo.** Correo nuevo con **`E07-moneda-distinta.xlsx`** (plan `PR10` es **USD**, la fila trae **COR**).

**Esperado.** La fila **Rechazada en validación**, mensaje sobre la moneda del plan.

---

### R-08 · Sin autorización sobre ese plan

**Qué prueba.** `AUTORIZACION_CORREO_PLAN` (RF-02) y el estado propio **Sin autorización**.

**Cómo.** Correo nuevo con **`E08-sin-autorizacion.xlsx`** (plan `PRNA`, al que tu remitente no
está autorizado).

**Esperado.**

| Qué | Valor |
|---|---|
| La fila | **Sin autorización** ← un estado distinto de "Rechazada en validación" |
| Mensaje | *"Su correo no está autorizado sobre el plan PRNA"* — **nombra el plan** |
| Estado de la Solicitud | **Rechazada** |

> Ojo con el matiz: el **remitente sí está reconocido** (tiene autorización sobre otros planes), así
> que el correo se procesa. Lo que no está autorizado es **ese plan**. Si la Solicitud quedó en
> **No reconocida**, se están confundiendo las dos reglas.

---

### R-09 · Sin autorización GANA sobre otra regla que rechaza

**Qué prueba.** D-14: `Sin autorización` tiene prioridad, **pero el mensaje lleva todos los motivos**.

**Cómo.** Hacé un Excel a mano a partir de `E08-sin-autorizacion.xlsx`: en la fila 13, dejá el plan
`PRNA` **y además** poné `moneda = EUR`. Mandalo.

**Esperado.**

| Qué | Valor |
|---|---|
| Estado de la fila | **Sin autorización** (no "Rechazada en validación") |
| `sanic_mensaje` | trae **los dos** motivos: el de autorización **y** el de la lista de Moneda |

**FALLA si** el estado es Rechazada en validación, o si el mensaje trae un solo motivo.

---

### R-10 · La referencia de formato 11 se construye sola

**Qué prueba.** `REFERENCIA_FORMATO_11` con D-17 y DD-10, y que la recibida se guarde aparte.

**Cómo.** Usá la Solicitud de **C-01** (`E01-feliz-formato11.xlsx`).

**Esperado.** Por cada fila:

| Campo | Valor |
|---|---|
| `sanic_referencia` | **construida**: `007` + cuenta rellena con ceros **a la izquierda** hasta 17 = **20 exactos** |
| `sanic_referenciarecibida` | lo que vino en el Excel, **tal cual** (en E01 viene vacía) |

**Verificá con la calculadora a mano** para al menos una fila. Cuenta `10203040506070` (14 dígitos):

```
007 + 000 + 10203040506070  =  00700010203040506070   (20 caracteres)
```

**FALLA si**: mide distinto de 20, rellena por la derecha, o usa un código de banco que no sea el
de `plantilla.listas` (BAC = `007`).

> Esta es **la prueba más importante de todo el plan**. Una referencia mal construida no falla: le
> paga a otra persona.

---

### R-11 · La referencia de formato 11 que NO se puede construir

**Qué prueba.** Los tres casos en que `REFERENCIA_FORMATO_11` falla (D-17).

**Cómo.** Correo nuevo con **`E09-referencia-formato11.xlsx`**.

**Esperado.** Las 2 filas en **Rechazada en validación**:

| Fila | Cuenta | Por qué falla |
|---|---|---|
| 1 | `1234ABCD5678` | trae algo que no son dígitos |
| 2 | `123456789012345678` (18) | más de 17 caracteres |

> Que una cuenta con letras **rechace** en vez de construir una referencia rara es exactamente lo
> que protege a AS400.

---

### R-12 · Formato 06: la referencia NO se deriva

**Qué prueba.** DD-15: en formatos 06 y 10 la referencia es **la recibida**, aunque venga vacía.

**Cómo.** Correo nuevo con **`E13-formato06-referencia-libre.xlsx`** (plan `PR06`, referencia
`REF-LIBRE-000123`).

**Esperado.**

| Campo | Valor |
|---|---|
| Estado de la fila | **Validada** |
| `sanic_referencia` | **`REF-LIBRE-000123`** — tal cual, sin tocar |
| `sanic_referenciarecibida` | `REF-LIBRE-000123` |

**FALLA si** la referencia salió con `007` adelante o rellena con ceros: se estaría aplicando la
regla de formato 11 a un plan que no es 11.

---

### R-13 · Mezcla de filas válidas y rechazadas

**Qué prueba.** Que una plantilla con de todo se procese fila por fila y la Solicitud quede
**En proceso** mientras haya al menos una válida (`03` §7).

**Cómo.** Correo nuevo con **`E10-mixto.xlsx`** (4 filas).

**Esperado.**

| Fila | Estado esperado |
|---|---|
| 1 | **Validada** |
| 2 | **Validada** |
| 3 (plan `PRNA`) | **Sin autorización** |
| 4 (`moneda = EUR`) | **Rechazada en validación** |

| Qué | Valor |
|---|---|
| filas t/v/r | `4 / 2 / 2` |
| Estado | **En proceso** |
| Acuse | sí, y **detalla fila por fila** cuáles entraron y cuáles no, y por qué |
| Vista **Por digitar** | muestra **las 2 validadas**, no las otras |

> Leé el acuse completo. Es el caso más parecido a la realidad: el cliente manda 25 filas y algunas
> fallan. El acuse tiene que dejarle clarísimo qué corregir.

---

### R-14 · Duplicados dentro de la plantilla NO se validan

**Qué prueba.** DD-12: el control de duplicados está en AS400, no acá.

**Cómo.** Hacé un Excel con **la misma fila repetida tres veces** (copiá la fila 13 de
`E01-feliz-formato11.xlsx` a las filas 14 y 15). Mandalo.

**Esperado.** Las **3 filas Validadas**. `3 / 3 / 0`, Solicitud **En proceso**.

**FALLA si** alguna quedó rechazada por duplicada: sería una regla que el diseño no pidió.

---

### Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| R-01 listas inválidas | | | ¿cita el valor? |
| R-02 largos | | | |
| R-03 plan inexistente | | | |
| R-04 plan inactivo | | | |
| R-05 formato 11 no ACH | | | |
| R-06 obligatoriedad | | | fila 4 = Validada |
| R-07 moneda | | | |
| R-08 sin autorización | | | |
| R-09 prioridad + motivos | | | |
| **R-10 referencia construida** | | | **contá los 20** |
| R-11 referencia imposible | | | |
| R-12 formato 06 sin derivar | | | |
| R-13 mezcla | | | |
| R-14 duplicados pasan | | | |


---

## 04 — Comunicaciones al cliente

Cubre `MPPP-COM` (detecta) y `MPPP-ENV` (envía). Las dos comunicaciones son **el acuse** y **la
respuesta final**, y las dos salen como **respuesta en el hilo**, desde el buzón, **solo al
remitente** (DF-03).

**La garantía que hay que romper para que esto falle**: *el cliente nunca recibe dos veces lo
mismo*. Ante la duda, no se reenvía y lo mira una persona (D-21).

**Antes**: `01` y `03`, sobre todo C-01 y R-13.

---

### M-01 · El acuse llega, y llega una sola vez

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

### M-02 · El acuse de una Rechazada cierra la Solicitud

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

### M-03 · Copia y remitente

**Qué prueba.** DF-03: solo al remitente, nunca a los de copia.

**Cómo.** Correo nuevo con `E01-feliz-formato11.xlsx`, pero poné **otra dirección tuya en CC**.

**Esperado.** El acuse llega **solo** a la dirección del **De**. A la de CC **no le llega nada**.

**FALLA si** le llega a la copia: se le estaría verificando la autorización a uno y respondiéndole
a otro.

---

### M-04 · La respuesta final, cuando todas las filas se resuelven

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

### M-05 · Nunca dos veces lo mismo

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

### M-06 · Envío iniciado sin confirmar → revisión humana

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

### M-07 · El cuerpo lo arma el código, no el flujo

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

### Resultados

| Caso | Solicitud | Resultado | Notas |
|---|---|---|---|
| M-01 acuse, una sola vez | | | |
| M-02 Rechazada → Cerrada | | | |
| M-03 solo al remitente | | | |
| M-04 respuesta final | | | |
| **M-05 nunca dos veces** | | | |
| M-06 a medias → revisión | | | |
| M-07 cuerpo del código | | | |


---

## 05 — La app y sus 8 comandos

Los 8 botones de la barra nunca se ejecutaron en un navegador. Este archivo es el que más
probabilidad tiene de encontrar defectos.

**Dónde**: app **MDA - MPPP - Mantenimiento PPP**.

**Si NINGÚN botón aparece**, antes de reportar caso por caso mirá esto: en el `RibbonDiffXml` la
biblioteca se referencia como `$webresource:sanic_mppp_wr_js_comandos`, **sin `.js`**. El ejemplo
real del entorno que se usó de modelo sí llevaba la extensión en el nombre. Es el sospechoso
número uno y el arreglo es de un minuto.

**Antes**: `01` y `03`. Hace falta al menos una Solicitud **En proceso** con filas Validadas
(C-01) y una **No reconocida** (C-04).

---

### A-01 · Los botones aparecen donde deben

**Qué prueba.** Los `CustomAction` en sus dos ubicaciones.

**Cómo.** Abrí la vista **Por digitar** (grilla de Filas) y seleccioná una fila.

**Esperado.** En la barra aparecen **5 botones propios** con su ícono:

`Digitada` · `Rechazada en AS400` · `Anular` · `Aprobar` · `Devolver`

Y en **Solicitudes**, seleccionando una fila: `Atendido` · `Descartar` · `Revisado`.

**También verificá en la subgrilla**: abrí una Solicitud y mirá su subgrilla de Filas. Los 5 de
Fila tienen que estar ahí también.

---

### A-02 · Los comandos genéricos NO aparecen (12.6)

**Qué prueba.** Los `HideCustomAction` en las 10 tablas.

**Cómo.** En **cada** entrada del sitemap, seleccioná una fila y mirá la barra (incluido el menú
`…`).

**Esperado.** En **ninguna** tabla aparecen: **Eliminar**, **Asignar**, **Compartir**, **Flujo**,
**Enviar vínculo**, **Combinar**. Y **Nuevo** no aparece en Solicitud, Fila, ResultadoRegla ni
Bitácora (sí en los catálogos, donde el alta es de una persona).

| Tabla | Sin los 6 genéricos | Sin "Nuevo" |
|---|---|---|
| Solicitud | | **sí** |
| Fila | | **sí** |
| ResultadoRegla | | **sí** |
| Bitácora | | **sí** |
| Cliente, Plan, Autorizado, Autorización, Parámetro, Regla | | (Nuevo **sí** aparece) |

---

### A-03 · Digitada, sobre varias filas a la vez

**Qué prueba.** `Sanic.Mppp.Comandos.digitada` y la acción masiva (DA-02).

**Cómo.** Vista **Por digitar**, seleccioná **las 3 filas** de C-01, botón **Digitada**.

**Esperado.**

| Paso | Qué pasa |
|---|---|
| Al apretar | Diálogo de confirmación que **dice la cantidad**: *"¿Aplicar 'Digitada' a 3 fila(s) seleccionada(s)?"* |
| Al confirmar | Mensaje: *"3 de 3 fila(s) actualizada(s)."* |
| Las filas | pasan a **Digitada** |
| La grilla | se refresca sola y las filas **desaparecen** de Por digitar |
| Bitácora | `Fila digitada`, origen **App** |

**FALLA si**: el diálogo no dice la cantidad, hay que refrescar a mano, o el texto sale en inglés
teniendo el usuario español.

---

### A-04 · Cancelar no cambia nada

**Qué prueba.** Que el diálogo de confirmación realmente frene.

**Cómo.** Seleccioná filas, apretá **Digitada** y dale **Cancelar**.

**Esperado.** **Nada** cambia. Ninguna fila cambia de estado, no hay entradas nuevas en Bitácora.

---

### A-05 · Sin selección

**Qué prueba.** El `EnableRule` `Mscrm.SelectionCountAtLeastOne`.

**Cómo.** Sin seleccionar ninguna fila, mirá la barra.

**Esperado.** Los botones propios están **deshabilitados** (grises). Si se pudiera apretar, el
mensaje sería *"No hay ninguna fila seleccionada."*

---

### A-06 · Aprobar, como Supervisor

**Qué prueba.** `Sanic.Mppp.Comandos.aprobar`.

**Cómo.** Entrá con un usuario con rol **SR - MPPP - Supervisor**. Vista **Por aprobar**,
seleccioná las filas de A-03, botón **Aprobar**.

**Esperado.** Las filas pasan a **Aprobada**; cuando se resuelven **todas** las de la Solicitud,
pasa a **Procesada** y arranca la respuesta final (caso M-04).

---

### A-07 · El plugin manda, no el botón (DA-07)

**Qué prueba.** Lo más importante de la seguridad: la regla real está en el servidor.

**Cómo.** Con el Supervisor, intentá **Aprobar** una fila que **él mismo digitó** (segregación de
funciones), o **Digitada** sobre una fila que ya está **Aprobada**.

**Esperado.**

| Qué | Valor |
|---|---|
| La operación | **falla** |
| El mensaje | *"N de M fila(s) actualizada(s). X no se pudieron actualizar:"* seguido del motivo que devuelve el plugin |
| Las otras filas de la tanda | **sí** se aplican |
| Ninguna fila | queda a medias |

**FALLA si** la transición prohibida se aplica igual: el botón estaría decidiendo, y la regla se
saltearía llamando al Web API.

> Que **unas filas se apliquen y otras no** es el comportamiento pedido (`05` §5), no un defecto.

---

### A-08 · Rechazada en AS400 — el diálogo de motivo

**Qué prueba.** El corazón de DA-03 corregida: `navigateTo` a `entityrecord` en modo creación.

**Cómo.** Vista **Por digitar** o **Por aprobar**, seleccioná 2 filas, botón **Rechazada en AS400**.

**Esperado.**

| Paso | Qué pasa |
|---|---|
| Al apretar | Se abre un **diálogo centrado** con el título *"Rechazada en AS400 — 2 fila(s)"* |
| El diálogo | muestra **un solo campo**: **Motivo**, obligatorio |
| Si guardás vacío | la plataforma no deja: el campo es obligatorio |
| Al guardar con texto | el diálogo cierra y se aplican **las 2 filas** |
| Las filas | pasan a **Rechazada en AS400** |
| `sanic_mensaje` de cada fila | **el texto que escribiste** |
| Registro de motivo | se **borra** después de leerse (es transporte, no dato) |

**FALLA si**: el diálogo no abre, abre en blanco, o se aplica el cambio **sin** el motivo.

> Verificá que no quede basura: en la tabla **Motivo de acción** no debería quedar ningún registro
> después de usar el comando.

---

### A-09 · Cancelar el diálogo de motivo

**Qué prueba.** Que cerrar sin guardar **no cambie nada**.

**Cómo.** Apretá **Anular** sobre filas seleccionadas y cerrá el diálogo con la **X** (sin guardar).

**Esperado.** **Ninguna** fila cambia de estado. No hay registro de motivo colgado.

---

### A-10 · Anular y Devolver

**Qué prueba.** Los otros dos comandos con motivo.

**Cómo.**
- **Anular**: sobre filas en Validada o Digitada.
- **Devolver**: como **Supervisor**, sobre filas en **Digitada**.

**Esperado.**

| Comando | Estado destino | Dónde aparece después |
|---|---|---|
| Anular | **Anulada** | en ningún lado del trabajo diario |
| Devolver | **Validada** con mensaje | vista **Devueltas** del ejecutivo |

> **Devolver es el más sutil**: la fila vuelve a **Validada**, igual que una recién validada. Lo
> único que la distingue en la vista **Devueltas** es que **tiene mensaje**. Si aparece también en
> **Por digitar**, las dos vistas están mal filtradas (y está bien que aparezca en las dos si así
> lo dice el diseño — comparalo con `05` §2).

---

### A-11 · Atendido y Descartar, sobre Solicitudes

**Qué prueba.** Los dos comandos de la grilla de Solicitudes.

**Cómo.** Vista **Por clasificar** (Solicitudes en No reconocida o No es correo nuevo, de C-02 y
C-04). Seleccioná una y probá **Atendido**; con otra, **Descartar**.

**Esperado.**

| Comando | Estado destino |
|---|---|
| Atendido | **Cerrada** |
| Descartar | **Descartada** |

En los dos: confirmación con la cantidad, la Solicitud sale de **Por clasificar**, y **no se le
envía nada al cliente**.

---

### A-12 · Revisado

**Qué prueba.** El octavo comando: apaga la marca y deja la nota.

**Cómo.** Sobre una Solicitud con `sanic_requiererevision = sí` (la de M-06), vista **Para
revisar**, botón **Revisado**. Escribí una nota.

**Esperado.**

| Qué | Valor |
|---|---|
| Diálogo | igual que A-08, pide una nota |
| `sanic_requiererevision` | pasa a **no** |
| La nota | queda en `sanic_motivorevision` y el plugin la pasa a la **Bitácora** |
| La Solicitud | sale de **Para revisar** |

---

### A-13 · Multiidioma de los botones

**Qué prueba.** Que cada etiqueta tenga su texto en 1033 y 3082 (convención del proyecto).

**Cómo.** Si tenés un usuario con el idioma en inglés, entrá con él. Si no, cambiá el idioma en
**Configuración personal → Idiomas**.

**Esperado.**

| Español (3082) | Inglés (1033) |
|---|---|
| Digitada | Mark as entered |
| Aprobar | Approve |
| Rechazada en AS400 | Rejected in AS400 |
| Anular | Void |
| Devolver | Send back |
| Atendido | Handled |
| Descartar | Discard |
| Revisado | Reviewed |

Y los **mensajes del JavaScript** (confirmación, resultado) también cambian de idioma.

---

### Resultados

| Caso | Resultado | Notas |
|---|---|---|
| A-01 los botones aparecen | | |
| A-02 genéricos ocultos | | |
| A-03 Digitada masiva | | |
| A-04 cancelar | | |
| A-05 sin selección | | |
| A-06 Aprobar | | |
| **A-07 el plugin manda** | | |
| A-08 diálogo de motivo | | |
| A-09 cancelar diálogo | | |
| A-10 Anular y Devolver | | |
| A-11 Atendido y Descartar | | |
| A-12 Revisado | | |
| A-13 multiidioma | | |


---

## 06 — Seguridad, sitemap, vistas y formularios

Cubre lo que el usuario ve y lo que **no** tiene que poder ver. Los casos de seguridad son los más
importantes de todo el plan: acá hay números de identificación y de cuenta de personas reales.

**Antes**: `00-preparacion.md` y al menos una Solicitud con filas (C-01).

**Vas a necesitar un usuario por rol.** Si no tenés cuatro cuentas, asigná y quitá roles de una
misma cuenta, de a uno por vez (y acordate de dejarla como estaba).

| Rol | Para qué |
|---|---|
| `SR - MPPP - Ejecutivo` | digita |
| `SR - MPPP - Supervisor` | aprueba |
| `SR - MPPP - Administrador de planes` | catálogos |
| `SR - MPPP - Administrador tecnico` | parámetros y reglas |

---

### G-01 · El sitemap: 4 áreas y 13 entradas

**Qué prueba.** El sitemap de 12.7 y que cada entrada abra **su** vista.

**Cómo.** Con un usuario que tenga **todos** los roles, recorré el menú entero.

**Esperado.**

| Área | Entradas |
|---|---|
| **Trabajo** | Por digitar · Devueltas · Por aprobar · Por clasificar · Para revisar |
| **Consulta** | Solicitudes · Filas |
| **Catálogos** | Clientes · Planes · Autorizados · Autorizaciones |
| **Configuración** | Parámetros · Reglas |

**Lo que más hay que mirar**: las 7 entradas que apuntan a **una vista específica** (no a la vista
por defecto de la tabla). Este patrón **nunca se pudo verificar** contra ningún sitemap del entorno
y quedó anotado como pendiente.

| Entrada | Tiene que abrir |
|---|---|
| Por digitar | **Mis clientes — por digitar** (no "Todos") |
| Devueltas | **Mis clientes — devueltas** |
| Por aprobar | **Por aprobar** |
| Por clasificar | **Por clasificar** |
| Para revisar | **Para revisar** |
| Solicitudes | **Solicitudes** |
| Filas | la vista de Filas que corresponda |

**FALLA si** alguna abre la vista por defecto de la tabla en vez de la suya: las cuatro entradas
sobre Fila mostrarían lo mismo y la navegación del diseño se cae.

---

### G-02 · Los íconos del sitemap

**Qué prueba.** Los 22 SVG de 12.1.

**Cómo.** Mirá el menú y la app.

**Esperado.** Cada entrada tiene **su** ícono (no el genérico), y la app tiene el suyo en la barra.
Los íconos se ven bien en **tema claro y oscuro** (usan `currentColor`).

---

### G-03 · Las 18 vistas existen y filtran

**Qué prueba.** 12.2.

**Cómo.** Recorré las vistas desde el selector de cada tabla.

**Esperado.** Cada una trae lo que dice su nombre. Las más fáciles de verificar:

| Vista | Tiene que mostrar | NO tiene que mostrar |
|---|---|---|
| Mis clientes — por digitar | filas **Validada** de **tus** clientes | filas de otros clientes, ni Digitadas |
| Todos — por digitar | **todas** las Validada | |
| Por aprobar | solo **Digitada** | |
| Mis clientes — devueltas | Validada **con mensaje** | las validadas limpias |
| Terminadas | estados terminales | Validada ni Digitada |
| Por clasificar | **No reconocida** y **No es correo nuevo** | Ingresada, En proceso |
| Para revisar | `requiererevision = sí` | las demás |

---

### G-04 · La cartera del ejecutivo (RF-19, D-13)

**Qué prueba.** Que **Mis clientes — por digitar** filtre por el propietario del Cliente.

**Cómo.**
1. Poné como propietario del Cliente `PR - Pruebas MPPP SA` a **otro** usuario.
2. Entrá como **Ejecutivo** (vos) y abrí **Por digitar**.

**Esperado.** Las filas de ese cliente **no aparecen** en *Mis clientes*, pero **sí** en
*Todos — por digitar*.

> Es comodidad, no seguridad: el ejecutivo **puede** ver todo si cambia de vista. Lo que prueba es
> que la vista por defecto le muestre su cartera.

---

### G-05 · Perfil de seguridad de columna

**Qué prueba.** 12 / P-06: identificación y cuenta son columnas protegidas.

**Cómo.** Entrá con el **Administrador de planes** (que NO está en el perfil) y abrí una Fila.

**Esperado.**

| Columna | Ejecutivo y Supervisor | Administrador de planes / técnico |
|---|---|---|
| `sanic_numeroidentificacion` | **ve el valor** | **ve `*******`** o el campo bloqueado |
| `sanic_numerocuenta` | **ve el valor** | **ve `*******`** |

**FALLA si** el Administrador de planes ve el número de cuenta. Es un dato bancario de una persona
real.

> Probalo también **en la vista**, no solo en el formulario: una columna protegida tiene que
> ocultarse en los dos lados.

---

### G-06 · Lo que cada rol NO puede

**Qué prueba.** La matriz de privilegios (`04`).

**Cómo.** Con cada rol, intentá lo que no le toca.

**Esperado.**

| Rol | Tiene que poder | NO tiene que poder |
|---|---|---|
| Ejecutivo | ver y digitar Filas; ver Solicitudes | **aprobar**; editar Planes, Clientes, Parámetros, Reglas |
| Supervisor | aprobar y devolver | crear Solicitudes a mano; editar catálogos |
| Administrador de planes | crear y editar Clientes, Planes, Autorizados, Autorizaciones | ver Solicitudes ni Filas |
| Administrador técnico | editar Parámetros y Reglas | ver Filas ni Solicitudes |

**El más importante**: el **Administrador de planes no ve Solicitudes ni Filas**. Si las ve, está
viendo datos bancarios que no le corresponden.

---

### G-07 · Cada rol entra donde debe

**Qué prueba.** Que el sitemap se recorte solo, por privilegios.

**Cómo.** Entrá con cada rol **por separado** y mirá qué entradas del menú aparecen.

**Esperado.**

| Rol | Ve |
|---|---|
| Ejecutivo | Trabajo (Por digitar, Devueltas, Por clasificar, Para revisar), Consulta; Catálogos **solo lectura** |
| Supervisor | Trabajo (Por aprobar, Para revisar), Consulta |
| Administrador de planes | **solo** Catálogos |
| Administrador técnico | **solo** Configuración |

---

### G-08 · Los 9 formularios

**Qué prueba.** 12.3 + 12.4.

**Cómo.** Abrí un registro de cada tabla con interfaz.

**Esperado.** Los 9 abren sin error y muestran sus campos agrupados:

Solicitud · Fila · Cliente · Plan · Autorizado · Autorización · Parámetro · Regla · **Motivo de
acción** (el del diálogo).

**Mirá especialmente**:

- **Solicitud**: sus subgrillas de Filas, ResultadoRegla y Bitácora traen datos.
- **Autorización**: el campo de **archivo** `sanic_documentofirmado` deja subir y descargar un PDF.
- **Motivo de acción**: **un solo campo**, Motivo, obligatorio.

---

### G-09 · La vista "Autorizaciones sin evidencia"

**Qué prueba.** D-42: la evidencia **no** condiciona la vigencia; es una lista de tareas del
administrador.

**Cómo.** Como Administrador de planes, abrí **Autorizaciones** y su vista *Sin evidencia*.

**Esperado.** Muestra las autorizaciones **sin** documento firmado — incluidas las que
`preparar_datos.py` creó.

**Y lo más importante**: esas autorizaciones **igual funcionan**. El caso C-01 pasó con
autorizaciones sin evidencia. Si en algún lado una autorización sin documento hace fallar
`AUTORIZACION_CORREO_PLAN`, es **FALLA** contra D-42.

---

### G-10 · La campana de notificaciones (DA-08)

**Qué prueba.** Los avisos dentro de la app.

**Cómo.** Después de correr C-02 y C-04, entrá como **Ejecutivo** y mirá la campana.

**Esperado.** Hay avisos de que un correo fue a **Por clasificar**. Al tocarlos, **abren** la vista
o la Solicitud correspondiente.

| Cuándo | A quién |
|---|---|
| Un correo va a Por clasificar | a todos los ejecutivos |
| Una solicitud deja filas por digitar | al ejecutivo del cliente |
| Una solicitud pasa a tener filas por aprobar | a los supervisores |
| Le devuelven filas | al ejecutivo que digitó |
| Una solicitud queda para revisar | a ejecutivos y supervisores |

**Una por solicitud y por tanda, nunca una por fila.** Si aparecen 25 avisos por una plantilla de
25 filas, es FALLA.

---

### G-11 · Multiidioma de la app

**Qué prueba.** La convención: etiquetas en 1033 y en el idioma del cliente.

**Cómo.** Cambiá el idioma del usuario a inglés y recorré el sitemap y un par de formularios.

**Esperado.** Las etiquetas del sitemap, las vistas y las columnas cambian de idioma. Ninguna
queda con el texto del otro idioma ni con el nombre lógico crudo.

---

### G-12 · La app valida limpia

**Qué prueba.** Que la app no tenga componentes faltantes.

**Cómo.**

```bash
python3 herramientas/construir/app.py playbooks/app/mantenimientoppp.md --solo-verificar
```

**Esperado.** `"estado": "ya_existia"` con `11 tablas, 4 roles ... ValidateApp sin errores`.

---

### Resultados

| Caso | Resultado | Notas |
|---|---|---|
| G-01 sitemap y sus vistas | | |
| G-02 íconos | | |
| G-03 las 18 vistas | | |
| G-04 cartera del ejecutivo | | |
| **G-05 columnas protegidas** | | |
| **G-06 lo que cada rol no puede** | | |
| G-07 sitemap por rol | | |
| G-08 los 9 formularios | | |
| G-09 sin evidencia pero válida | | |
| G-10 notificaciones | | |
| G-11 multiidioma | | |
| G-12 ValidateApp | | |


---

## 07 — MPPP-VIG, la red de seguridad

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

### V-01 · Corre y no hace nada

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

### V-02 · Bloque 1 — un correo que quedó en la bandeja

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

### V-03 · Bloque 2 — una Solicitud que quedó en Ingresada

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

### V-04 · Bloque 2 — se acaban los reintentos

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

### V-05 · Bloque 3 — una comunicación que no salió

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

### V-06 · Bloque 5 — los correos por clasificar vencen

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

### Resultados

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


---

## 08 — Integridad, plugins y claves

Cubre los **steps de plugin** que corren al guardar, y que son la red que impide dejar el sistema
en un estado imposible. Son los que protegen contra alguien que escribe por el Web API sin pasar
por la app.

Los ocho tipos registrados:

| Step | Qué protege |
|---|---|
| `NombreCalculadoStep` | el nombre de las tablas que no lo digita nadie |
| `NormalizarYValidarStep` | normaliza y valida al guardar |
| `ListaBlancaStep` | que solo se escriba lo que se puede escribir |
| `TransicionDeFilaStep` | que una transición de estado sea legal |
| `PostTransicionDeFilaStep` | los efectos posteriores (Bitácora, estado de la Solicitud) |
| `AtenderPorClasificarStep` | Atendido y Descartar |
| `IntegridadDeReglaStep` | que el catálogo de reglas sea coherente |
| `IntegridadAutorizacionPlanStep` | que una autorización tenga sentido |

**Cómo se prueban.** Casi todos se prueban **haciendo algo prohibido** y verificando que el sistema
se niegue con un mensaje claro. Un plugin que deja pasar lo prohibido es peor que no tenerlo.

---

### I-01 · El catálogo de reglas: una regla activa sin evaluador

**Qué prueba.** `IntegridadDeReglaStep` (D-13): una regla activa cuyo código no sabe evaluar.

**Cómo.** En **Configuración → Reglas**, creá una regla nueva:

- Código: `REGLA_QUE_NO_EXISTE`
- Nivel: Registro · Efecto: Rechaza · Orden: 90

**Esperado.** **No deja guardar.** El mensaje dice que esa regla no tiene evaluador programado
para su nivel.

**FALLA si** guarda. La próxima validación reventaría con una excepción y todas las Solicitudes
quedarían en Ingresada.

---

### I-02 · Una regla que depende de otra inactiva

**Qué prueba.** `IntegridadDeReglaStep`, segundo caso de D-13.

**Cómo.** Desactivá `PLAN_EXISTE` (que es de la que dependen cuatro reglas).

**Esperado.** **No deja desactivarla**, o no deja guardar la que queda colgando. El mensaje nombra
la dependencia rota.

> Acordate de dejar `PLAN_EXISTE` **activa** al terminar.

---

### I-03 · Una regla de nivel Registro con efecto "Envía a revisión"

**Qué prueba.** D-20: ese efecto solo tiene sentido a nivel Solicitud o Correo.

**Cómo.** Editá `MONEDA_DEL_PLAN` (nivel Registro) y ponele efecto **Envía a revisión**.

**Esperado.** **No deja guardar**, con un mensaje que explique por qué.

> Dejá `MONEDA_DEL_PLAN` con efecto **Rechaza** al terminar.

---

### I-04 · Una regla que depende de sí misma

**Qué prueba.** El defecto que encontró la revisión de código: la autodependencia se rechaza
**por el código**, antes de mirar ningún orden.

**Cómo.** Editá cualquier regla y poné en `sanic_dependede` **su propio código**.

**Esperado.** **No deja guardar**: *"No se puede guardar la regla 'X': no puede depender de sí
misma."*

> Probalo con una regla cuyo `orden` sea el mismo que tendría su "dependencia" — es el caso que una
> prueba mal escrita dejaba pasar por coincidencia.

---

### I-05 · Integridad de una autorización

**Qué prueba.** `IntegridadAutorizacionPlanStep`.

**Cómo.** En **Catálogos → Autorizaciones**, creá una autorización duplicada: el **mismo**
autorizado sobre el **mismo** plan que ya tiene (`TU-CORREO → PR11`).

**Esperado.** **No deja guardar** (clave alternativa o el plugin), con un mensaje entendible y
**no** un volcado técnico de la plataforma.

---

### I-06 · El nombre calculado

**Qué prueba.** `NombreCalculadoStep`.

**Cómo.** Creá una **Autorización** nueva (autorizado `TU-CORREO`, plan `PR06` si no existe ya) y
**no toques el campo Nombre**.

**Esperado.** Al guardar, el nombre queda calculado solo: **`correo → CODIGO`**.

Lo mismo con un **Plan**: el nombre se arma con su código y su cliente.

---

### I-07 · Lista blanca de escrituras

**Qué prueba.** `ListaBlancaStep`: que no se pueda escribir a mano lo que escribe el sistema.

**Cómo.** Abrí una **Fila** en la app e intentá editar a mano una columna que llena la validación
—por ejemplo `sanic_referencia`— y guardar.

**Esperado.** **No deja**, o el campo está de solo lectura en el formulario **y** el plugin lo
rechaza si se intenta por API.

> El formulario de solo lectura no alcanza: la prueba real es por el Web API. Si tenés cómo,
> probá un `PATCH` a esa columna.

---

### I-08 · Transición de estado ilegal

**Qué prueba.** `TransicionDeFilaStep`, que es lo que hace cierto DA-07.

**Cómo.** Sobre una fila en **Validada**, intentá ponerla directo en **Aprobada** (saltándose
Digitada). Hacelo desde el formulario, no con el botón.

**Esperado.** **No deja**: el mensaje dice que esa transición no es válida desde ese estado.

**Este es el caso que demuestra que la seguridad no está en el botón.** Si pasa, alguien con el
Web API puede aprobar lo que quiera.

---

### I-09 · El paquete de plugins está al día

**Qué prueba.** Que el ensamblado en el sandbox sea el del repositorio, y no una versión vieja.

**Cómo.**

```bash
python3 herramientas/construir/paquete_plugins.py playbooks/paquete-plugins/*.md --solo-verificar
```

**Esperado.** `"estado": "ya_existia"` con los **10 tipos** registrados.

> Cuidado con la trampa conocida: el sandbox puede seguir corriendo el binario viejo si no se
> subió el número de build. El síntoma es *"The plug-in type could not be found in the plug-in
> assembly"*, y la señal temprana es un `.nupkg` del mismo tamaño exacto que el anterior.

---

### Resultados

| Caso | Resultado | Notas |
|---|---|---|
| I-01 regla sin evaluador | | |
| I-02 dependencia inactiva | | |
| I-03 efecto inválido por nivel | | |
| I-04 autodependencia | | |
| I-05 autorización duplicada | | |
| I-06 nombre calculado | | |
| I-07 lista blanca | | |
| **I-08 transición ilegal** | | |
| I-09 paquete al día | | |

> Dejá el catálogo de **Reglas** como estaba: `PLAN_EXISTE` activa, `MONEDA_DEL_PLAN` con efecto
> Rechaza, y sin la regla inventada de I-01.


---

