# 05. Diseño de la app model-driven

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **borrador para revisión del aprobador**. Nada de esto está construido.

Reglas citadas: BP-PP-091, 093, 094, 095, 100, 186. Requisitos: RF-03, RF-11 a RF-14, RF-19, RNF-04. Decisiones: D-12, D-13, `02` DD-07, DD-14. Referencia estética: `anexos/referencia-dataverse-accelerator.md`.

Los **SUPUESTOS** marcados así son respuestas que puse yo a preguntas que siguen abiertas; están para que el aprobador las corrija.

## 0. Decisiones de este documento

| ID | Decisión | Motivo |
|---|---|---|
| DA-01 | **Enfoque híbrido** (aprobado 2026-09-20): model-driven nativa y limpia para todo, más **páginas custom solo donde la interfaz nativa no alcanza**. | La estética de la Dataverse Accelerator sale de no usar la interfaz genérica; pero cada página custom es tecnología canvas, cuesta mucho más que una vista, y exige resolver a mano accesibilidad y delegación (BP-PP-100). El plazo de la fase 1 es el cierre de septiembre. |
| DA-02 | **Las transiciones se disparan con botones propios en la barra de comandos de la grilla de Filas, sobre varias filas seleccionadas a la vez.** Los que no piden dato (Digitada, Aprobar) actúan directo; los que piden motivo (Rechazada en AS400, Anular, Devolver) abren un **diálogo**. | Son unas 7.500 filas por mes: abrir cada una para cambiarle el estado es inviable. El comando moderno con Power Fx recibe las filas seleccionadas (`Self.Selected.AllItems`), así que la acción masiva es nativa. |
| DA-03 | **El diálogo de motivo es una página custom pequeña, abierta como diálogo**: un texto, la lista de filas afectadas y dos botones. Es la **única** página custom de la fase 1. | La barra de comandos no tiene cómo pedir un texto. Una página custom en modo diálogo es el escalón que indica BP-PP-091 antes de JavaScript, y BP-PP-093 la prefiere a una canvas embebida. Es chica: no tiene listas grandes ni problemas de delegación. |
| DA-04 | **La "bandeja de trabajo" como página custom completa** —lista de solicitudes a la izquierda, filas a la derecha, detalle en panel lateral, al estilo de la Accelerator— **queda para la versión 1.1**, después de la fase 1. | Es donde más rinde una página custom, pero es también lo más caro de la app. La fase 1 sale con la grilla nativa y sus comandos, que ya resuelven la acción masiva. |
| DA-05 | **Controles modernos primero; Creator Kit solo si hace falta.** | El Creator Kit no tiene soporte oficial de Microsoft y obliga a instalar `CreatorKitCore` en Test y Prod antes que la solución. Para un diálogo de motivo alcanzan los controles modernos. |
| DA-06 | **Se ocultan todos los comandos genéricos que no se usan**, en cada tabla: Eliminar, Asignar, Compartir, Flujo, Enviar vínculo, Combinar, y "Nuevo" donde el alta no es de una persona (Solicitud, Fila, ResultadoRegla, Bitácora). | Es lo que más ensucia una model-driven y lo más barato de arreglar. Además, varios de esos comandos ofrecen acciones que la matriz de privilegios no permite. |
| DA-07 | **La lógica no vive en los botones.** Un botón solo cambia `sanic_estado` (y `sanic_mensaje`); que la transición sea válida, quién puede hacerla y la segregación de funciones los decide el plugin (`03` §4). | BP-PP-051. Un usuario que llame al Web API sin pasar por la app encuentra las mismas reglas. La visibilidad de cada botón según el rol es comodidad, no seguridad. |

## 1. La app

`MDA - MPPP - Mantenimiento PPP` (`sanic_mppp_mda_mantenimientoppp`). Una sola app para los cuatro perfiles (D-12); cada uno ve solo las entradas del sitemap cuyos datos puede leer.

## 2. Sitemap: un área, por tareas

| Grupo | Entrada | Qué abre | Quién la ve |
|---|---|---|---|
| **Trabajo** | Por digitar | Vista de Filas en estado Validada | Ejecutivo |
| | Por aprobar | Vista de Filas en estado Digitada | Supervisor |
| | No reconocidos | Vista de Solicitudes en estado No reconocida | Ejecutivo |
| | Para revisar | Vista de Solicitudes con `sanic_requiererevision` = sí | Ejecutivo, Supervisor |
| **Consulta** | Solicitudes | Todas las Solicitudes | Ejecutivo, Supervisor |
| | Filas | Todas las Filas | Ejecutivo, Supervisor |
| **Catálogos** | Clientes · Planes · Autorizados | Sus vistas | Administrador de planes (Ejecutivo y Supervisor, solo lectura) |
| **Configuración** | Parámetros · Reglas | Sus vistas | Administrador técnico |

Un solo nivel, nombres de tarea y no de tabla, íconos Fluent en SVG (web resources `WR - MPPP - SVG - …`). Sin tableros en la fase 1. La entrada por defecto de cada perfil es su primera entrada de Trabajo.

## 3. Vistas

Columnas pensadas para digitar sin abrir el registro. Las protegidas (identificación y cuenta) se ven porque Ejecutivo y Supervisor están en el perfil de seguridad de columna.

| Vista (tabla) | Filtro | Columnas | Orden |
|---|---|---|---|
| **Mis clientes — por digitar** (Fila) · *por defecto del Ejecutivo* | Estado = Validada **y** Plan → Cliente → propietario = usuario actual (RF-19, D-13) | Solicitud, n.º de fila, Gestión, Clasificación, Plan, Referencia, Nombre, Tipo ID, Identificación, Cuenta, Moneda, Banco, Validada el | Solicitud, n.º de fila |
| Todos — por digitar (Fila) | Estado = Validada | las mismas + Cliente | ídem |
| **Por aprobar** (Fila) · *por defecto del Supervisor* | Estado = Digitada | las mismas + Digitada por, Digitada el | Digitada el |
| Mis clientes — devueltas (Fila) | Estado = Validada, con mensaje de devolución | + Mensaje | |
| Terminadas (Fila) | Estado terminal | + Estado, Mensaje, Aprobada por | más recientes primero |
| No reconocidos (Solicitud) | Estado = No reconocida | Recibido el, Remitente, Asunto, Adjuntos | más viejos primero |
| Para revisar (Solicitud) | `requiererevision` = sí | Número, Remitente, Estado, Motivo de revisión | |
| Solicitudes (Solicitud) | todas | Número, Recibido el, Remitente, Estado, Filas totales / válidas / rechazadas, Cerrada el | más recientes primero |
| Catálogos y configuración | activos | las de negocio de cada tabla | |

La vista "mis clientes" filtra por una relación de dos saltos (Fila → Plan → Cliente). Las vistas nativas lo admiten en su FetchXML; hay que comprobar al construir que el diseñador moderno no lo rompe al editarla.

## 4. Formularios

Uno principal por tabla, **una sola pestaña**, sin pestaña de "Relacionados" visible donde no aporta.

| Tabla | Secciones | Editable |
|---|---|---|
| **Fila** | Encabezado: Estado, Solicitud, n.º de fila. *Gestión* (los diez datos de la plantilla, más la referencia recibida). *Resultado* (Mensaje). *Trazabilidad* (validada, digitada por y cuándo, aprobada por y cuándo). | **Todo de solo lectura.** El estado se cambia con los botones; la lista blanca de columnas del plugin rechazaría cualquier otra edición (`04` §1). |
| **Solicitud** | Encabezado: Número, Estado, Remitente. *Correo* (recibido, asunto, archivos: correo original y Excel, para descargar). *Filas* (subgrilla con las filas y los mismos botones). *Reglas* (subgrilla de ResultadoRegla). *Comunicaciones* (acuse y respuesta final: cuándo y qué se dijo). *Bitácora* (subgrilla). | Solo lectura. |
| **Cliente** | Nombre, CIFBAC, CIFCOM, Ejecutivo asignado. Subgrillas: Planes, Autorizados. | Administrador de planes |
| **Plan** | Código, Cliente, Moneda, Tipo de formato. Subgrilla: Autorizaciones. | Administrador de planes |
| **Autorizado** | Correo, Cliente, Documento firmado, Fecha. Subgrilla: Planes autorizados. | Administrador de planes |
| **Parámetro** · **Regla** | Sus columnas; el valor JSON en un área de texto grande. | Administrador técnico |

## 5. Comandos

En la grilla principal de Filas, en la subgrilla de Filas de la Solicitud y en el formulario de Fila. Visibles según rol y estado; **la validación real es del plugin** (DA-07).

| Botón | Quién lo ve | Sobre filas en | Pide | Efecto |
|---|---|---|---|---|
| **Digitada** | Ejecutivo | Validada | confirmación con la cantidad | Estado → Digitada |
| **Rechazada en AS400** | Ejecutivo | Validada o Digitada | motivo (diálogo) | Estado → Rechazada en AS400 + mensaje |
| **Anular** | Ejecutivo | Validada o Digitada | motivo (diálogo) | Estado → Anulada + mensaje |
| **Aprobar** | Supervisor | Digitada | confirmación con la cantidad | Estado → Aprobada |
| **Devolver** | Supervisor | Digitada | motivo (diálogo) | Estado → Validada + mensaje |
| **Atendido** · **Descartar** | Ejecutivo | Solicitud No reconocida | confirmación | Estado → Cerrada · Descartada |
| **Revisado** | Ejecutivo, Supervisor | Solicitud con `requiererevision` | nota | Apaga `requiererevision` y deja la nota en la Bitácora |

Una acción masiva puede fallar en algunas filas y en otras no (por ejemplo, el supervisor intenta aprobar una fila que él mismo digitó): el botón informa cuántas se aplicaron y cuáles no y por qué, y no deja nada a medias dentro de una misma fila.

## 6. Supuestos sobre cómo trabaja la gente — a corregir por el aprobador

1. **SUPUESTO — Unidad de trabajo.** El ejecutivo trabaja una **lista plana de filas por digitar**, ordenada por solicitud, y no entra solicitud por solicitud. Tiene la Solicitud a un clic si quiere ver el correo.
2. **SUPUESTO — Acción masiva.** Selecciona varias filas y las marca juntas. El caso normal es "digité las 25 de esta plantilla".
3. **SUPUESTO — Verificación del supervisor.** Le alcanza con las filas que extrajimos, y si duda **descarga el Excel original** desde la Solicitud. No hay visor del Excel dentro de la app en la fase 1.
4. **SUPUESTO — No reconocidos.** Los ven **todos** los ejecutivos. Para decidir les alcanza con remitente, asunto y fecha, y si no, descargan el correo original. **Alternativa**: guardar también un extracto en texto del cuerpo (primeros 2.000 caracteres) en una columna nueva, para leerlo sin descargar. No lo agregué; decime si lo querés.
5. **SUPUESTO — Catálogos.** El Administrador de planes carga **uno por uno en formularios**, y para cargas grandes usa la importación nativa desde Excel de model-driven. La migración inicial desde SharePoint es aparte (RF-16).
6. **SUPUESTO — Avisos.** **No hay avisos** en la fase 1: la bandeja es la cola de trabajo. Las notificaciones dentro de la app son una mejora posterior barata.

## 7. Inventario que sale de este diseño (completa `06` §12)

| Tipo | Cantidad | Detalle |
|---|---|---|
| App y sitemap | 1 + 1 | |
| Vistas | ~16 | 5 de Fila, 3 de Solicitud, y activos + búsqueda de cada catálogo |
| Formularios | 9 | Uno por tabla con interfaz (ResultadoRegla y Bitácora solo se ven en subgrilla) |
| Comandos | 8 | Los de §5 |
| Página custom | 1 | Diálogo de motivo (DA-03) |
| Web resources | ~10 | Íconos SVG del sitemap y de los botones |
| Ocultamiento de comandos genéricos | 10 tablas | DA-06 |

**Aviso sobre cómo se construye.** Vistas, formularios, sitemap y comandos se pueden crear por Web API o por archivo de solución, así que entran al ciclo de playbooks. **La página custom no**: es un archivo canvas que se edita en Power Apps Studio. Se construye a mano siguiendo una guía de pantalla (para eso existe tu skill `powerapps-screen-guides`), o se explora empaquetarla con `pac canvas pack`. Es una sola y es chica, pero es el único componente de la fase 1 que un agente no puede crear solo.
