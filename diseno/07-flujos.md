# 07. Diseño de los flujos de Power Automate

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **revisado con el aprobador el 2026-09-20**. Nada de esto está construido.

Reglas citadas: BP-PP-058, 059, 061, 122, 123, 196. Requisitos: RF-01, RF-03, RF-04, RF-09, RF-10, RNF-02, RNF-05. Decisiones de la definición: D-01, D-02, D-21, D-24, D-31. Decisiones de la etapa 3: `02` DD-03, DD-08, DD-09.

## 0. Decisiones de este documento

| ID | Decisión | Motivo |
|---|---|---|
| DF-01 | **Desaparece el Flow B de la definición.** La ingesta crea la Solicitud, sube los archivos y llama ella misma a las Custom API. | La definición (D-24) disparaba la validación con un segundo flujo, por el alta de la Solicitud: un flujo encadenado a otro por un disparador, que BP-PP-058 desaconseja, con más latencia y otro punto de falla, sin dar nada a cambio: si la validación falla, la Solicitud queda en Ingresada y la vigilancia la reintenta igual. Excepción a la definición: E-15. |
| DF-02 | **Lógica compartida en flujos hijos, no duplicada.** `MPPP-ING` lo usan `MPPP-REC` y `MPPP-VIG`; `MPPP-ENV` lo usan `MPPP-COM` y `MPPP-VIG`. | La vigilancia tiene que poder hacer exactamente lo mismo que el flujo al que reemplaza cuando algo quedó a medias. Copiar las acciones en dos flujos garantiza que un día difieran. Un flujo hijo llamado para reutilizar lógica no es el "bus" de BP-PP-058: no hay cadena de eventos, hay una llamada con respuesta. |
| DF-03 | **Las dos comunicaciones salen como respuesta en el hilo** del correo original, desde el buzón, **solo al remitente**. | Decisión del aprobador. Al cliente le queda todo en una conversación; y solo se le responde a quien se le verificó la autorización, nunca a quienes iban en copia. |
| DF-04 | **Se guarda el identificador de Outlook del correo después de moverlo**, en `sanic_outlookmessageid`, con una acción propia. | Para responder en el hilo hace falta el identificador de Outlook, no el Internet Message-ID, y ese identificador **cambia cuando el correo se mueve de carpeta** (Learn lo advierte: "IDs might change after certain actions such as copy or move"). Como la Solicitud se crea antes de mover, hace falta una actualización explícita después. |
| DF-05 | **El buzón es una environment variable**, `sanic_mppp_ev_buzoningesta`; en el Dev del aprobador vale `mppp@55xljh.onmicrosoft.com`. Es un **buzón compartido**. La carpeta de procesados es otra variable, `sanic_mppp_ev_carpetaprocesados`. | Decisión del aprobador y BP-PP-123. El Dev actual es un tenant propio del aprobador; la solución pasa después al Dev de BAC, donde estos valores se cargan de nuevo. |
| DF-06 | **`MPPP-COM` procesa de a una Solicitud por vez** (concurrencia del disparador en 1). | El "como máximo una vez" depende de que dos ejecuciones no lean a la vez "todavía no iniciado". Con unos cientos de correos por mes, serializar no cuesta nada. |
| DF-07 | **Los adjuntos en línea no cuentan.** Firmas e imágenes incrustadas llegan con `isInline = true`; se descartan antes de contar. | Sin esto, un correo con firma con logo y la plantilla tendría "dos adjuntos" y fallaría `UN_SOLO_EXCEL`. |
| DF-08 | **Solo se procesan correos nuevos. Una respuesta no se procesa nunca; un reenvío, sí.** Lo decide un **plugin liviano**, `sanic_mppp_capi_clasificarcorreo` (`03` §0), antes y aparte del plugin que lee la plantilla. | Regla del aprobador. Una respuesta automática de "fuera de oficina" es siempre una respuesta a algo que le mandamos: al no procesar respuestas, no se le contesta y el bucle no puede empezar. Cubre también al cliente que contesta "gracias" a un acuse. En un plugin y no en el flujo: la regla se prueba con tests, vive en el catálogo de reglas, y no depende de que el conector de Outlook deje leer cabeceras (no se pudo verificar). Y aparte del plugin grande, porque son dos preguntas distintas: "¿este correo merece procesarse?" y "¿qué dice la plantilla?". |
| DF-09 | **Lo que no se procesa va a la bandeja "Por clasificar" y vence.** Estados No reconocida y **No es correo nuevo**; si nadie lo atiende ni lo descarta en `clasificacion.dias.vencimiento` días (inicial 30), pasa a **Vencida**, terminal. | Decisión del aprobador; aplica a los dos estados. Vencida y no Descartada, para distinguir "alguien decidió ignorarlo" de "nadie lo miró". |
| DF-10 | **Sin cortacircuito por remitente, por ahora.** | Decisión del aprobador. Riesgo aceptado: un sistema ajeno que conteste cada mensaje nuestro con un correo **nuevo** (no una respuesta) desde la dirección de un autorizado no queda cubierto por DF-08. |
| DF-11 | **Cada flujo tiene un identificador corto**, `MPPP-` + tres letras, que va en su nombre y es el valor que se anota como origen en la Bitácora. | El aprobador rechazó las letras A, B, C, W de la definición: no dicen nada. El identificador se reconoce aun sin saber de qué solución es el flujo (BP-PP-196). |

## 1. Mapa

| ID | Nombre | Disparador | Qué hace |
|---|---|---|---|
| `MPPP-REC` | `Cloud Flow - MPPP - REC - Recibir correo nuevo` | Llega un correo a la bandeja de entrada del buzón compartido | Llama a `MPPP-ING` |
| `MPPP-ING` | `Cloud Flow - MPPP - ING - Ingerir y validar correo` | Hijo | Crea la Solicitud, sube archivos, mueve el correo, lo clasifica y, si corresponde, lo valida |
| `MPPP-COM` | `Cloud Flow - MPPP - COM - Detectar comunicación pendiente` | Cambia el estado de una Solicitud | Llama a `MPPP-ENV` |
| `MPPP-ENV` | `Cloud Flow - MPPP - ENV - Enviar comunicación al cliente` | Hijo | Envía el acuse o la respuesta final, como máximo una vez |
| `MPPP-VIG` | `Cloud Flow - MPPP - VIG - Vigilar pendientes` | Cada 10 minutos | Recupera lo que quedó a medias llamando a `MPPP-ING` y a `MPPP-ENV`, levanta para revisión lo que no se puede reintentar, y vence lo que nadie clasificó |

Todos son propiedad de la **cuenta de servicio** (D-01, estándar regional de BAC; BP-PP-122 pide un service principal, y esa excepción ya está en la definición). Usan dos connection references, `sanic_mppp_conr_outlook` y `sanic_mppp_conr_dataverse`. Todas las acciones de Outlook son las de buzón compartido o llevan la dirección del buzón como parámetro. Ninguno lee filas, clientes ni planes (`04` §3). Cuando un hijo escribe en la Bitácora, el origen es el flujo **que lo llamó**, que recibe como parámetro.

## 2. `MPPP-REC` — Recibir correo nuevo

- **Disparador**: *When a new email arrives in a shared mailbox (V2)*. Buzón = `sanic_mppp_ev_buzoningesta`; carpeta = Bandeja de entrada; **Include Attachments = No** (los trae `MPPP-ING`; el disparador queda liviano y no falla por tamaño).
- **Concurrencia del disparador**: activada, grado 5. Dos correos distintos no se pisan: cada uno tiene su clave.
- **Acción única**: *Run a Child Flow* → `MPPP-ING`, con el identificador de Outlook del mensaje y `origen = MPPP-REC`.
- Sin condiciones ni lógica: todo lo que este flujo sabe hacer lo tiene que saber hacer la vigilancia.

## 3. `MPPP-ING` — Ingerir y validar correo

Entrada: identificador de Outlook del mensaje y origen. Salida: identificador de la Solicitud y resultado (`creada` · `ya_existia` · `error`).

| # | Acción | Detalle |
|---|---|---|
| 1 | *Get email (V2)* | Con adjuntos. Trae `internetMessageId`, remitente, asunto y fecha de recepción. |
| 2 | Componer la clave | `take(replace(replace(internetMessageId,'<',''),'>',''), 450)` (DD-03). |
| 3 | Filtrar adjuntos | `isInline` = false (DF-07). `cantidadadjuntos` = cuántos quedan. El Excel candidato es el único que termina en `.xlsx`; si hay cero o más de uno no se sube ninguno, y la regla correspondiente falla en la validación, que es donde tiene que fallar. |
| 4 | *Add a new row* → Solicitud | `sanic_messageid`, remitente, asunto, `sanic_fecharecibido` (la del correo), `sanic_fechaingresada` = `utcNow()`, estado = Ingresada, `sanic_cantidadadjuntos`. **Alta simple, nunca upsert por clave** (DD-03). |
| 4b | Si el alta falla por **clave duplicada** | La Solicitud ya existe. Se busca por `sanic_messageid` con *List rows*, se sigue desde el paso 7 con esa Solicitud, y el resultado es `ya_existia`. Cualquier **otro** error va al bloque de errores. |
| 5 | *Export email (V2)* → *Upload a file or an image* | El `.eml` a `sanic_correocrudo` (RF-10). Es lo que lee el plugin liviano. |
| 6 | *Upload a file or an image* | El Excel a `sanic_exceloriginal`, si hay exactamente uno (D-31). |
| 7 | *Move email (V2)* | A `sanic_mppp_ev_carpetaprocesados`. **El correo cambia de identificador al moverse**: el nuevo es el que devuelve esta acción. |
| 7b | *Update a row* → Solicitud | **Acción propia, inmediatamente después de mover**: `sanic_outlookmessageid` = el identificador que devolvió el paso 7 (DF-04). Si falla, el flujo sigue: `MPPP-ENV` encuentra el mensaje por su Internet Message-ID en la carpeta de procesados y completa la columna en ese momento. |
| 8 | *Perform an unbound action* → `sanic_mppp_capi_clasificarcorreo` | Parámetro `solicitudid`. Devuelve `procesar` (sí/no) y `clasificacion`. Si `procesar` = no, la API ya dejó la Solicitud en No es correo nuevo o en No reconocida, con su aviso a los ejecutivos: **el flujo termina acá, sin validar y sin responderle a nadie**. |
| 9 | *Perform an unbound action* → `sanic_mppp_capi_validarsolicitud` | Solo si `procesar` = sí. Parámetro `solicitudid`. Política de reintento de la acción: **ninguna**; el reintento lo gobierna la vigilancia, con su contador. |
| 10 | Bitácora | Evento "Ingresada", con el origen recibido, actor "Cuenta de servicio". |

**Orden deliberado**: el correo se mueve (7) **después** de tener la Solicitud y sus archivos, y **antes** de clasificar y validar. Si el flujo se cae antes del 7, el correo sigue en la bandeja de entrada y la vigilancia lo reingresa; la clave única evita el duplicado. Si se cae después, la Solicitud queda en Ingresada y la vigilancia retoma desde el paso 8: las dos API son idempotentes.

**Errores**: los pasos van dentro de un ámbito *Try*. Un ámbito *Catch* (corre si *Try* falla o agota el tiempo) escribe la Bitácora con el evento "Error" y el nombre de la acción que falló, **sin el cuerpo del correo ni datos de la plantilla**, y termina el flujo como fallido para que quede en el historial. No hay limpieza: todo lo que queda a medias es recuperable.

## 4. `MPPP-COM` — Detectar comunicación pendiente

- **Disparador**: *When a row is added, modified or deleted*, tabla Solicitud, cambio = Modified, **Select columns** = `sanic_estadoprocesamiento`, **Filter rows** = estado En proceso, Rechazada o Procesada. No corre en cada actualización de la Solicitud (D-24) ni se dispara con las escrituras de `MPPP-ENV`, que no tocan el estado salvo para cerrar, y Cerrada queda fuera del filtro.
- **Concurrencia del disparador**: grado 1 (DF-06).
- **Acción única**: *Run a Child Flow* → `MPPP-ENV`, con el identificador de la Solicitud y `origen = MPPP-COM`.

## 5. `MPPP-ENV` — Enviar comunicación al cliente

Entrada: identificador de la Solicitud y origen. Decide sola qué comunicación toca; por eso la pueden llamar `MPPP-COM` y `MPPP-VIG` sin decirle nada más.

| Estado de la Solicitud | Acuse enviado | Respuesta final enviada | Qué hace |
|---|---|---|---|
| En proceso o Rechazada | no | — | Envía el **acuse** con `sanic_acusecontenido` |
| Procesada | sí | no | Envía la **respuesta final** con `sanic_respuestafinalcontenido` |
| cualquier otro caso | | | No hace nada y termina bien |

Secuencia de un envío, idéntica para las dos comunicaciones (D-21):

| # | Acción | Detalle |
|---|---|---|
| 1 | Releer la Solicitud | Si la fecha de **iniciado** de esa comunicación ya tiene valor → **no envía**. Si además la de enviado está vacía, marca `sanic_requiererevision` con el motivo "envío iniciado sin confirmar" y termina. Nunca se reenvía ante la duda. |
| 2 | Marcar **iniciado** | `sanic_fechaacuseiniciado` (o `…respuestafinaliniciada`) = `utcNow()`. Bitácora "Acuse iniciado". |
| 3 | *Reply to email (V3)* | Sobre `sanic_outlookmessageid`, buzón = `sanic_mppp_ev_buzoningesta`, **solo al remitente**, cuerpo HTML = el contenido guardado, sin adjuntos. Si el identificador no sirve, se busca el mensaje en la carpeta de procesados por su Internet Message-ID, se completa la columna y se reintenta una vez (DF-04). |
| 4 | Marcar **enviado** | La fecha de enviado = `utcNow()`. Bitácora "Acuse enviado". |
| 5 | Cerrar, si corresponde | Acuse de una **Rechazada** → Cerrada + `sanic_fechacerrada` (DD-09). Respuesta final de una **Procesada** → Cerrada + `sanic_fechacerrada`. Acuse de una En proceso → el estado no cambia. |

El cuerpo lo arma el código, nunca el flujo (DD-08). Si el paso 3 falla, la comunicación queda iniciada y sin enviar, y el paso 1 de la próxima ejecución la levanta para revisión humana: es el costo aceptado de garantizar que el cliente nunca reciba dos veces lo mismo.

**Texto obligatorio en las dos comunicaciones** (consecuencia de DF-08): *"Para enviar una plantilla nueva o corregida, escriba un correo nuevo a esta dirección. No responda a este mensaje: las respuestas no se procesan."*

## 6. `MPPP-VIG` — Vigilar pendientes

Disparador: recurrencia, cada 10 minutos. La mayoría de las ejecuciones termina en segundos sin nada que hacer. Es un sondeo, pero contra nuestro propio estado y contra un buzón que no avisa de "correo que quedó sin procesar": no aplica BP-PP-059.

| # | Qué busca | Cómo | Qué hace |
|---|---|---|---|
| 1 | Correos que quedaron en la bandeja de entrada | *Get emails (V3)*, Bandeja de entrada, recibidos hace más de `vigilancia.minutos.sinvalidar`, tope 25 | `MPPP-ING` por cada uno, con `origen = MPPP-VIG` |
| 2 | Solicitudes sin clasificar o sin validar | En Ingresada, con `sanic_fechaingresada` anterior al umbral y `sanic_requiererevision` = no | Si `sanic_reintentosvalidacion` < `vigilancia.reintentos.maximo`: suma uno y llama a las dos API en orden. Si no: `sanic_requiererevision` = sí, motivo "validación fallida N veces" |
| 3 | Comunicaciones sin enviar | En proceso o Rechazada con acuse sin iniciar, o Procesada con respuesta final sin iniciar, más viejas que `vigilancia.minutos.sinresponder` | `MPPP-ENV` por cada una |
| 4 | Envíos iniciados sin confirmar | Fecha de iniciado con valor, fecha de enviado vacía, más vieja que el umbral, `sanic_requiererevision` = no | **No reenvía.** Marca `sanic_requiererevision` = sí |
| 5 | **Correos por clasificar vencidos** (DF-09) | No reconocida o No es correo nuevo, recibidos hace más de `clasificacion.dias.vencimiento` días. Solo en la primera ejecución de cada día | Estado → **Vencida** + `sanic_fechacerrada`. Bitácora "Vencida" |

Los umbrales salen de la tabla de Parámetros, leídos al empezar cada ejecución.

## 7. Qué le agrega este diseño al resto

| Dónde | Cambio |
|---|---|
| `02` Solicitud | Columna `sanic_outlookmessageid`. Estados nuevos **No es correo nuevo** y **Vencida**. Columna `sanic_motivoclasificacion`. |
| `02` catálogo de reglas | Nivel nuevo **Correo**, con la regla `ES_CORREO_NUEVO`. Parámetros `correo.prefijos.reenvio` y `clasificacion.dias.vencimiento`. |
| `03` | Custom API nueva, `sanic_mppp_capi_clasificarcorreo`, con su plugin liviano. |
| `05` | La bandeja "No reconocidos" pasa a **Por clasificar**, con los dos estados y la columna Motivo. |
| `06` | Cinco flujos con sus identificadores; dos Custom API en la fase 1. |
| `00` | Excepción E-15. |

## 8. Pendiente

- **Probar con correos reales**, al construir: un correo nuevo, una respuesta y un reenvío, desde Outlook y desde Gmail, contra el buzón de Dev, para confirmar que el criterio de `03` §0 los separa bien. Que reenvíos y respuestas llevan las mismas cabeceras es conocimiento general, no está verificado.
- **Idioma base del Dev de BAC**: a conversar con el aprobador (`PENDIENTES.md`).
