# 07. Diseño de los flujos de Power Automate

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **borrador para revisión del aprobador**. Nada de esto está construido.

Reglas citadas: BP-PP-058, 059, 061, 122, 123. Requisitos: RF-01, RF-03, RF-04, RF-09, RF-10, RNF-02, RNF-05. Decisiones de la definición: D-01, D-21, D-24, D-31. Decisiones de la etapa 3: `02` DD-03, DD-08, DD-09.

## 0. Decisiones de este documento

| ID | Decisión | Motivo |
|---|---|---|
| DF-01 | **Desaparece Flow B.** La ingesta crea la Solicitud, sube los archivos y **llama ella misma a la Custom API de validación**. | La definición (D-24) separaba A (ingesta) de B (validación), con B disparado por el alta. Eso es A → B encadenados por un disparador, lo que BP-PP-058 desaconseja, y agrega latencia y un segundo punto de falla sin dar nada a cambio: si la validación falla, la Solicitud queda en Ingresada y la vigilancia la reintenta igual, exista B o no. Un flujo menos, una espera de disparador menos (RNF-02). Excepción a la definición: E-15. |
| DF-02 | **Lógica compartida en flujos hijos, no duplicada.** `I - Ingerir correo` (lo usan A y W) y `E - Enviar comunicación` (lo usan C y W). | W tiene que poder hacer exactamente lo mismo que A y que C cuando algo quedó a medias. Copiar las acciones en dos flujos garantiza que un día difieran. Un flujo hijo invocado para reutilizar lógica no es el "bus" de BP-PP-058: no hay cadena de eventos, hay una llamada con respuesta. |
| DF-03 | **Las dos comunicaciones salen como respuesta en el hilo** del correo original, desde el buzón dedicado. | Decisión del aprobador (2026-09-20). Al cliente le queda todo en una sola conversación. |
| DF-04 | **Se guarda el identificador de Outlook del correo después de moverlo**, en una columna nueva de Solicitud, `sanic_outlookmessageid`. | Para responder en el hilo hace falta el identificador de Outlook del mensaje, no el Internet Message-ID. Ese identificador **cambia cuando el correo se mueve de carpeta**: el que sirve es el que devuelve la acción de mover. Si algún día no sirviera, E busca el mensaje por su Internet Message-ID dentro de la carpeta de procesados. |
| DF-05 | **El buzón es una environment variable**, `sanic_mppp_ev_buzoningesta`. Valor en Dev: `mppp@55xljh.onmicrosoft.com`. La carpeta de procesados es otra, `sanic_mppp_ev_carpetaprocesados`, porque su identificador es distinto en cada buzón. | Decisión del aprobador y BP-PP-123. **No está creada todavía**: la construcción sigue detenida; se crea con su playbook. |
| DF-06 | **C procesa de a una Solicitud por vez** (control de concurrencia del disparador en 1). | El "como máximo una vez" de cada comunicación depende de que dos ejecuciones no lean a la vez "todavía no iniciado". Con unos cientos de correos por mes, serializar no cuesta nada. |
| DF-07 | **Los adjuntos en línea no cuentan.** Firmas e imágenes incrustadas llegan como adjuntos con `isInline = true`; se descartan antes de contar. | Sin esto, un correo con firma con logo y la plantilla tendría "dos adjuntos" y fallaría la regla `UN_SOLO_EXCEL`. |

## 1. Mapa

| Flujo | Nombre | Disparador | Qué hace |
|---|---|---|---|
| A | `Cloud Flow - MPPP - A - Ingesta` | Llega un correo a la bandeja de entrada del buzón | Llama a I |
| I | `Cloud Flow - MPPP - I - Ingerir correo` | Hijo (manual) | Crea la Solicitud, sube archivos, mueve el correo, llama a la Custom API de validación |
| C | `Cloud Flow - MPPP - C - Comunicaciones` | Cambia `sanic_estadoprocesamiento` de una Solicitud | Llama a E |
| E | `Cloud Flow - MPPP - E - Enviar comunicación` | Hijo (manual) | Envía el acuse o la respuesta final, como máximo una vez |
| W | `Cloud Flow - MPPP - W - Vigilancia` | Cada 10 minutos | Recupera lo que quedó a medias, llamando a I y a E; levanta para revisión lo que no se puede reintentar |

Todos son propiedad de la **cuenta de servicio** (D-01, estándar regional de BAC; BP-PP-122 pide un service principal, y esa excepción ya está asentada en la definición). Todos usan dos connection references: `sanic_mppp_conr_outlook` y `sanic_mppp_conr_dataverse`. Ninguno lee filas, clientes ni planes: eso lo hace la Custom API (`04` §3).

## 2. A — Ingesta

- **Disparador**: *When a new email arrives in a shared mailbox (V2)*: el buzón es **compartido** (confirmado por el aprobador). Todas las acciones de Outlook de los cinco flujos son las de buzón compartido, o llevan la dirección del buzón como parámetro. Buzón = `sanic_mppp_ev_buzoningesta`; carpeta = Bandeja de entrada; **Include Attachments = No** (los trae I; así el disparador es liviano y no falla por tamaño).
- **Concurrencia del disparador**: activada, grado 5. Dos correos distintos no se pisan: cada uno tiene su propia clave.
- **Acción única**: *Run a Child Flow* → I, con `messageid` de Outlook.
- Sin condiciones ni lógica: todo lo que A sabe hacer lo tiene que saber hacer W.

## 3. I — Ingerir correo

Entrada: identificador de Outlook del mensaje. Salida: identificador de la Solicitud y resultado (`creada` · `ya_existia` · `error`).

| # | Acción | Detalle |
|---|---|---|
| 1 | *Get email (V2)* | Con adjuntos. Trae `internetMessageId`, remitente, asunto, fecha de recepción. |
| 2 | Componer la clave | `take(replace(replace(internetMessageId,'<',''),'>',''), 450)` (DD-03). |
| 3 | Filtrar adjuntos | `isInline` = false (DF-07). `cantidadadjuntos` = cuántos quedan. El Excel candidato es el único que termina en `.xlsx`; si hay cero o más de uno, no se sube ninguno y la regla correspondiente falla en la validación, que es donde tiene que fallar. |
| 4 | *Add a new row* → Solicitud | `sanic_messageid`, remitente, asunto, `sanic_fecharecibido` (la del correo), `sanic_fechaingresada` = `utcNow()`, estado = Ingresada, `sanic_cantidadadjuntos`. **Alta simple, nunca upsert por clave** (DD-03). |
| 4b | Si el alta falla por **clave duplicada** | La Solicitud ya existe (la creó otra ejecución). Se busca por `sanic_messageid` con *List rows* y filtro, se sigue desde el paso 7 con esa Solicitud, y el resultado es `ya_existia`. Cualquier **otro** error va al bloque de errores. |
| 5 | *Export email (V2)* → *Upload a file or an image* | El `.eml` a `sanic_correocrudo` (RF-10). |
| 6 | *Upload a file or an image* | El Excel a `sanic_exceloriginal`, si hay exactamente uno (D-31). |
| 7 | *Move email (V2)* | A `sanic_mppp_ev_carpetaprocesados`. **El correo cambia de identificador al moverse**: el nuevo es el que devuelve esta acción. |
| 7b | *Update a row* → Solicitud | **Acción propia, inmediatamente después de mover**: `sanic_outlookmessageid` = el identificador que devolvió el paso 7 (DF-04). La Solicitud se creó en el paso 4, antes de mover, así que sin esta acción el identificador nuevo no queda en ningún lado. Si esta acción falla, el flujo sigue: el correo ya está movido y la Solicitud existe; E encuentra el mensaje por su Internet Message-ID en la carpeta de procesados y completa la columna en ese momento. |
| 8 | *Perform an unbound action* → `sanic_mppp_capi_validarsolicitud` | Parámetro `solicitudid`. La respuesta trae estado y contadores. Política de reintento de la acción: **ninguna** (la API es idempotente, pero el reintento lo gobierna W, con su contador). |
| 9 | Bitácora | Evento "Ingresada", origen Flujo A o W según quién llamó, actor "Cuenta de servicio". |

**Orden deliberado**: el correo se mueve (7) **después** de tener la Solicitud y sus archivos, y **antes** de validar (8). Si I se cae antes del 7, el correo sigue en la bandeja de entrada y W lo reingresa; la clave única evita el duplicado. Si se cae entre 7 y 8, la Solicitud queda en Ingresada y W reintenta la validación.

**Errores**: los pasos 1 a 9 van dentro de un ámbito *Try*. Un ámbito *Catch* (configurado para correr si *Try* falla o agota el tiempo) escribe la Bitácora con el evento "Error" y el nombre de la acción que falló, **sin el cuerpo del correo ni datos de la plantilla**, y termina el flujo como fallido para que quede en el historial. No hay limpieza: todo lo que I deja a medias es recuperable por W.

## 4. C — Comunicaciones

- **Disparador**: *When a row is added, modified or deleted*, tabla Solicitud, cambio = Modified, **Select columns** = `sanic_estadoprocesamiento`, y **Filter rows** = `sanic_estadoprocesamiento eq <En proceso> or sanic_estadoprocesamiento eq <Rechazada> or sanic_estadoprocesamiento eq <Procesada>`. Así no corre en cada actualización de la Solicitud (D-24), y no se dispara con sus propias escrituras, que no tocan el estado… salvo el paso a Cerrada, que el filtro deja afuera.
- **Concurrencia del disparador**: grado 1 (DF-06).
- **Acción única**: *Run a Child Flow* → E, con el identificador de la Solicitud.

## 5. E — Enviar comunicación

Entrada: identificador de la Solicitud. Decide sola qué comunicación toca; por eso la pueden llamar C y W sin decirle nada más.

| Estado de la Solicitud | `fechaacuseenviado` | `fecharespuestafinalenviada` | Qué hace |
|---|---|---|---|
| En proceso o Rechazada | vacía | — | Envía el **acuse** con `sanic_acusecontenido` |
| Procesada | con fecha | vacía | Envía la **respuesta final** con `sanic_respuestafinalcontenido` |
| cualquier otro caso | | | No hace nada y termina bien |

Secuencia de un envío, idéntica para las dos comunicaciones (D-21):

| # | Acción | Detalle |
|---|---|---|
| 1 | Releer la Solicitud | Si la fecha de **iniciado** de esa comunicación ya tiene valor → **no envía**. Si además la de enviado está vacía, marca `sanic_requiererevision` con el motivo "envío iniciado sin confirmar" y termina. Nunca se reenvía ante la duda. |
| 2 | Marcar **iniciado** | `sanic_fechaacuseiniciado` (o `…respuestafinaliniciada`) = `utcNow()`. Bitácora "Acuse iniciado". |
| 3 | *Reply to email (V3)* | Sobre `sanic_outlookmessageid`, buzón = `sanic_mppp_ev_buzoningesta`, **responder solo al remitente**, nunca a quienes iban en copia (confirmado por el aprobador: es el único cuya autorización se verificó), cuerpo HTML = el contenido guardado, sin adjuntos. Si el identificador no sirve, se busca el mensaje en la carpeta de procesados por su Internet Message-ID y se reintenta una vez (DF-04). |
| 4 | Marcar **enviado** | La fecha de enviado = `utcNow()`. Bitácora "Acuse enviado". |
| 5 | Cerrar, si corresponde | Acuse de una **Rechazada** → estado Cerrada + `sanic_fechacerrada` (DD-09). Respuesta final de una **Procesada** → Cerrada + `sanic_fechacerrada`. Acuse de una En proceso → el estado no cambia. |

El cuerpo lo arma el código, nunca el flujo (DD-08): E no recorre filas ni conoce reglas. Si el paso 3 falla, la comunicación queda iniciada y sin enviar, y el paso 1 de la próxima ejecución la levanta para revisión humana: es el costo aceptado de garantizar que el cliente nunca reciba dos veces lo mismo.

## 6. W — Vigilancia

Disparador: recurrencia, cada 10 minutos. Un 2 % de ejecuciones con trabajo es lo esperable; el resto termina en segundos. Es un sondeo, pero contra nuestro propio estado y contra un buzón que no ofrece otro aviso de "correo que quedó sin procesar": no aplica BP-PP-059.

| # | Qué busca | Cómo | Qué hace |
|---|---|---|---|
| 1 | Correos que quedaron en la bandeja de entrada | *Get emails (V3)*, carpeta Bandeja de entrada, recibidos hace más de `vigilancia.minutos.sinvalidar`, tope 25 | I por cada uno |
| 2 | Solicitudes sin validar | Solicitud en Ingresada, con `sanic_fechaingresada` anterior al umbral y `sanic_requiererevision` = no | Si `sanic_reintentosvalidacion` < `vigilancia.reintentos.maximo`: suma uno y llama a la Custom API. Si no: `sanic_requiererevision` = sí, motivo "validación fallida N veces" |
| 3 | Comunicaciones sin enviar | En proceso o Rechazada con `fechaacuseiniciado` vacía, o Procesada con `fecharespuestafinaliniciada` vacía, más viejas que `vigilancia.minutos.sinresponder` | E por cada una |
| 4 | Envíos iniciados sin confirmar | Fecha de iniciado con valor, fecha de enviado vacía, más vieja que el umbral, `sanic_requiererevision` = no | **No reenvía.** Marca `sanic_requiererevision` = sí |

Los tres umbrales salen de la tabla de Parámetros (`vigilancia.*`), leídos al empezar cada ejecución.

## 7. Qué le agrega este diseño al resto

| Dónde | Cambio |
|---|---|
| `02` §3.1 Solicitud | Columna nueva `sanic_outlookmessageid` T(500) (DF-04) |
| `06` §11 | Cinco flujos en vez de cuatro: A, I, C, E, W. Desaparece B |
| `00` | Excepción E-15: desaparece Flow B; aparecen dos flujos hijos |
| `04` §3 | Sin cambios: el rol de la cuenta de servicio ya cubre todo esto |

## 8. Resuelto con el aprobador (2026-09-20)

1. El buzón es **compartido**.
2. El Dev actual (`55xljh.onmicrosoft.com`) es un **tenant de desarrollo propio del aprobador**; la solución pasa después al Dev de BAC. Consecuencias: el valor de las environment variables y las conexiones se cargan de nuevo allá; el publisher `Sistemas_Abiertos_Nicaragua` viaja con la solución, con su prefijo de opciones `15946`; y **hay que saber cuál es el idioma base del Dev de BAC antes de llevarla**, porque acá todas las etiquetas van bajo 1033 (`PENDIENTES.md`).
3. Las comunicaciones se responden **solo al remitente**.
4. Las respuestas automáticas **se filtran**; el cómo está propuesto en §9 y espera aprobación.

## 9. Propuesta pendiente de aprobación: solo se procesan correos nuevos

Regla del aprobador (2026-09-20), que reemplaza a la propuesta anterior de tres capas de detección: **solo se procesa un correo nuevo; una respuesta no se procesa nunca. Un reenvío sí se acepta.** Se decide **en el flujo de ingesta, antes de llamar al plugin**.

Por qué alcanza: una respuesta automática de "fuera de oficina" es, por construcción, una respuesta a algo que le mandamos; al no procesar respuestas, no se le contesta y el bucle no puede empezar. Cubre además lo que las cabeceras no cubrían: el cliente que contesta "gracias" a nuestro acuse, o que discute una fila en el mismo hilo. Un rebote llega de `postmaster` o `mailer-daemon`, que no es un remitente autorizado: ya caía en No reconocida, sin respuesta.

### Cómo se distingue

| Caso | Criterio | Qué se hace |
|---|---|---|
| **Nuevo** | El correo **no** trae las cabeceras `In-Reply-To` ni `References` | Se procesa |
| **Reenvío** | Trae esas cabeceras **y** el asunto empieza con un prefijo de reenvío (`FW:`, `FWD:`, `RV:`, `REENV:`; lista en el parámetro `correo.prefijos.reenvio`) | Se procesa |
| **Respuesta** | Trae esas cabeceras y el asunto no es de reenvío | **No se procesa** |

- **Reenvíos y respuestas no se distinguen por cabeceras**: en Outlook y en Gmail los dos llevan `In-Reply-To` y `References`, para mantenerse en la conversación. Lo único que los separa es el prefijo del asunto, que pone el programa de correo. Es una convención y no una garantía, por eso la lista de prefijos es un parámetro. **Esto es conocimiento general, no está verificado con correos reales**: al construir el flujo se prueba con un correo nuevo, una respuesta y un reenvío, desde Outlook y desde Gmail, contra el buzón de Dev, y se ajusta el criterio si hace falta.
- **Las cabeceras no vienen en la acción estándar *Get email*.** Se leen con la acción *Send an HTTP request* del mismo conector de Outlook, contra Graph: `GET /users/{buzón}/messages/{id}?$select=internetMessageHeaders`. Graph las expone y funciona sobre buzones compartidos (verificado en Learn); **falta comprobar al construir** que esa acción del conector admite esa ruta sobre un buzón compartido. No agrega ningún conector nuevo, así que la política DLP no cambia. Plan B si no se pudiera: el plugin las lee del `.eml` que ya guardamos, y la decisión se toma ahí.

### Qué pasa con el que no se procesa

Se registra igual que todo lo que llega (RF-10): se crea la Solicitud, se guarda el `.eml`, se mueve el correo. **No se llama a la validación y no se le responde al remitente.** Queda en la misma bandeja que hoy tienen los ejecutivos para los no reconocidos, con su motivo a la vista, y con los mismos botones: **Atendido** o **Descartar**.

| Pieza | Propuesta |
|---|---|
| Estado | Uno nuevo, **No es correo nuevo**, hermano de **No reconocida**. Dos estados y no uno, para poder contar cuántos de cada tipo llegan; la bandeja, los botones y el vencimiento son los mismos. |
| Bandeja | La entrada "No reconocidos" pasa a llamarse **Por clasificar** y muestra los dos estados, con una columna Motivo. |
| Vencimiento | Parámetro `clasificacion.dias.vencimiento`, inicial **30**. El flujo de vigilancia, una vez por día, pasa a un estado terminal nuevo, **Vencida**, todo lo que lleve más de esos días en la bandeja sin que nadie lo atienda ni lo descarte. **Vencida** y no Descartada, para que la trazabilidad distinga "alguien decidió ignorarlo" de "nadie lo miró". Queda en la Bitácora. |
| Aviso | Al llegar, el mismo aviso dentro de la app que hoy reciben los ejecutivos por un no reconocido. |

### Lo que esta regla le cuesta al cliente

Un cliente que corrige las filas rechazadas y **contesta nuestro acuse** adjuntando la plantilla arreglada no va a ser procesado: es una respuesta. Los textos del acuse y del rechazo (DD-08, DD-09) tienen que decirlo sin ambigüedad: *"Para reenviar la plantilla corregida, escriba un correo nuevo a esta dirección. No responda a este mensaje: las respuestas no se procesan."*

### Lo único que mantendría de la propuesta anterior

Un **cortacircuito por remitente**: si ya se le envió una comunicación a una dirección en los últimos N minutos y llega de ella otro correo nuevo y sin plantilla, no se le responde y queda para revisar (parámetro `comunicacion.minutos.entre.respuestas`). La regla de "solo nuevos" corta el bucle con cualquier autorrespondedor que conteste en el hilo, que son casi todos. No lo corta con un sistema que responde con un correo **nuevo** cada vez (algunas mesas de ayuda lo hacen: "recibimos su mensaje, caso n.º 123"). Es raro, pero una tormenta de correos con un cliente del banco es de lo peor que le puede pasar a esta solución, y el cortacircuito es la única defensa que no depende de cómo se porte el otro lado.
