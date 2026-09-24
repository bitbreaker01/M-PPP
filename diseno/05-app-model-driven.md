# 05. Diseño de la app model-driven

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **decisiones DA-01 a DA-09 y los seis supuestos aprobados por el aprobador el 2026-09-20; mockup revisado y aprobado ese mismo día** (`PENDIENTES.md` D-1: pidió la navegación entre Cliente, Plan y correo Autorizado, ya incorporada; "aparte de eso, lo miro todo bien"). Nada de esto está construido. *(Corregido el 2026-09-22: esta línea decía "falta su opinión sobre el mockup", que contradecía a D-1.)*

Reglas citadas: BP-PP-091, 093, 094, 095, 100, 186. Requisitos: RF-03, RF-11 a RF-14, RF-19, RNF-04. Decisiones: D-12, D-13, `02` DD-07, DD-14. Referencia estética: `anexos/referencia-dataverse-accelerator.md`.

## 0. Decisiones de este documento

| ID | Decisión | Motivo |
|---|---|---|
| DA-01 | **Enfoque híbrido** (aprobado 2026-09-20): model-driven nativa y limpia para todo, más **páginas custom solo donde la interfaz nativa no alcanza**. | La estética de la Dataverse Accelerator sale de no usar la interfaz genérica; pero cada página custom es tecnología canvas, cuesta mucho más que una vista, y exige resolver a mano accesibilidad y delegación (BP-PP-100). El plazo de la fase 1 es el cierre de septiembre. |
| DA-02 | **Las transiciones se disparan con botones propios en la barra de comandos de la grilla de Filas, sobre varias filas seleccionadas a la vez.** Los que no piden dato (Digitada, Aprobar) actúan directo; los que piden motivo (Rechazada en AS400, Anular, Devolver) abren un **diálogo**. | Son unas 7.500 filas por mes: abrir cada una para cambiarle el estado es inviable; el comando recibe las filas seleccionadas y la acción masiva es nativa. **Corregido el 2026-09-22 (aprobador):** los botones son **clásicos, con un web resource JavaScript**, no modernos con Power Fx. Motivo: un comando moderno **no se puede crear por API** — Learn solo documenta el diseñador visual —, y eso sacaba 18 de los 56 componentes del ciclo de construcción. Con `RibbonDiffXml` + JS se construyen por `ImportSolution` y quedan versionados en el repo. La acción masiva no se pierde: JavaScript recibe las filas seleccionadas por `SelectedControlSelectedItemIds`, igual que Power Fx por `Self.Selected.AllItems`. |
| DA-03 | **El diálogo de motivo es el formulario de creación rápida de una tabla técnica**, `sanic_mppp_tbl_motivoaccion`: un texto obligatorio y los botones nativos de guardar y cancelar. El comando lo abre con `Xrm.Navigation.navigateTo({pageType:"entityrecord", entityName:"sanic_mppp_tbl_motivoaccion"}, {target:2})`, lee el motivo del registro que devuelve y lo aplica a TODAS las filas seleccionadas. **No hay ninguna página custom en la fase 1.** | **Corregida el 2026-09-22 con evidencia de Learn.** Decía "una página custom pequeña abierta como diálogo", y eso **no puede funcionar con acción masiva**: (1) `navigateTo` a una página custom resuelve el promise **sin ningún valor** al cerrar el diálogo — *"An object is passed only if the `pageType` = `entityRecord` and you opened the form in create mode"* ([navigateTo](https://learn.microsoft.com/power-apps/developer/model-driven-apps/clientapi/reference/xrm-navigation/navigateto)) —, así que la página no tiene cómo devolverle el motivo al comando; y (2) el `pageInput` de una página custom solo admite `entityName` y `recordId`, y `recordId` **debe ser un GUID** porque viaja en la URL: no hay forma de pasarle las 25 filas seleccionadas. DA-02 (acción masiva) y la página custom eran **incompatibles entre sí**. En cambio `pageType: "entityrecord"` en modo create **sí** devuelve `savedEntityReference[0]` con `id` y `name`, y admite `data` para prellenar columnas. Además saca de la fase 1 el único componente que no se podía construir por API. |
| DA-04 | **La "bandeja de trabajo" como página custom completa** —lista de solicitudes a la izquierda, filas a la derecha, detalle en panel lateral, al estilo de la Accelerator— **queda para la versión 1.1**, después de la fase 1. | Es donde más rinde una página custom, pero es también lo más caro de la app. La fase 1 sale con la grilla nativa y sus comandos, que ya resuelven la acción masiva. |
| DA-05 | **Solo controles modernos. El Creator Kit no se usa para nada.** | Decisión del aprobador: **ninguna dependencia externa** por ahora. El Creator Kit no tiene soporte oficial de Microsoft y obligaría a instalar `CreatorKitCore` en Test y Prod antes que la solución. |
| DA-06 | **Se ocultan todos los comandos genéricos que no se usan**, en cada tabla: Eliminar, Asignar, Compartir, Flujo, Enviar vínculo, Combinar, y "Nuevo" donde el alta no es de una persona (Solicitud, Fila, ResultadoRegla, Bitácora). | Es lo que más ensucia una model-driven y lo más barato de arreglar. Además, varios de esos comandos ofrecen acciones que la matriz de privilegios no permite. |
| DA-08 | **Notificaciones dentro de la app desde la fase 1** (campana de la model-driven, tabla nativa `appnotification`). Las crea el código de servidor, no los botones: la Custom API de validación y el plugin posterior a la transición. **Una por solicitud y por tanda, nunca una por fila.** | Decisión del aprobador. Avisos: al ejecutivo del cliente, cuando una solicitud suya deja filas por digitar; a los supervisores, cuando una solicitud pasa a tener filas por aprobar; al ejecutivo que digitó, cuando le devuelven filas; a todos los ejecutivos, cuando un correo va a Por clasificar; a ejecutivos y supervisores, cuando una solicitud queda para revisar. Cada aviso abre la vista o la solicitud que corresponde. Es nativo: no agrega dependencias ni licencias. |
| DA-09 | **Toda pantalla se valida primero en un mockup HTML 100 % funcional** (`diseno/mockups/`), con datos ficticios, antes de construir nada. | Estándar del aprobador para cualquier Power App (BP-PP-102): probar la interfaz y dar opinión cuesta minutos en un mockup y días en la plataforma. |
| DA-07 | **La lógica no vive en los botones.** Un botón solo cambia `sanic_estado` (y `sanic_mensaje`); que la transición sea válida, quién puede hacerla y la segregación de funciones los decide el plugin (`03` §4). | BP-PP-051. Un usuario que llame al Web API sin pasar por la app encuentra las mismas reglas. La visibilidad de cada botón según el rol es comodidad, no seguridad. |

## 1. La app

`MDA - MPPP - Mantenimiento PPP` (`sanic_mppp_mda_mantenimientoppp`). Una sola app para los cuatro perfiles (D-12); cada uno ve solo las entradas del sitemap cuyos datos puede leer.

## 2. Sitemap: un área, por tareas

| Grupo | Entrada | Qué abre | Quién la ve |
|---|---|---|---|
| **Trabajo** | Por digitar | Vista de Filas en estado Validada | Ejecutivo |
| | **Devueltas** | Vista de Filas que el Supervisor devolvió (Validada con mensaje de devolución) | Ejecutivo |
| | Por aprobar | Vista de Filas en estado Digitada | Supervisor |
| | **Por clasificar** | Vista de Solicitudes en estado No reconocida o No es correo nuevo, con su motivo | Ejecutivo |
| | Para revisar | Vista de Solicitudes con `sanic_requiererevision` = sí | Ejecutivo, Supervisor |
| **Consulta** | Solicitudes | Todas las Solicitudes | Ejecutivo, Supervisor |
| | Filas | Todas las Filas | Ejecutivo, Supervisor |
| **Catálogos** | Clientes · Planes · Autorizados · Autorizaciones | Sus vistas. Autorizaciones (AutorizacionPlan) trae la vista **"Sin evidencia"**: el respaldo que el Administrador de planes tiene pendiente de cargar. Es una lista de tareas suya, **no** una lista de autorizaciones inválidas: esas autorizaciones ya valen (D-42) | Administrador de planes (Ejecutivo y Supervisor, solo lectura) |
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
| **Por clasificar** (Solicitud) | Estado = No reconocida o No es correo nuevo | Recibido el, Remitente, Asunto, **Motivo**, Adjuntos, Vence el | más viejos primero |
| Para revisar (Solicitud) | `requiererevision` = sí | Número, Remitente, Estado, Motivo de revisión | |
| Solicitudes (Solicitud) | todas | Número, Recibido el, Remitente, Estado, Filas totales / válidas / rechazadas, Cerrada el | más recientes primero |
| Catálogos y configuración | activos | las de negocio de cada tabla | |

### Lista cerrada de las 17 vistas (inventario 12.2)

Cerrada el 2026-09-22 con el aprobador. Antes el inventario decía "~19" y la fórmula del párrafo de abajo daba 16: ninguno de los dos números se podía reconstruir. **Cada tabla de catálogo lleva UNA sola vista, "Activos".** La vista de búsqueda rápida (Quick Find) no se cuenta: toda tabla la trae y no hay nada que diseñar en ella.

| # | Vista | Tabla | Para qué |
|---|---|---|---|
| 1 | Mis clientes — por digitar | Fila | entrada de sitemap "Por digitar" (Ejecutivo) |
| 2 | Todos — por digitar | Fila | la misma pantalla, sin el filtro de cartera |
| 3 | Por aprobar | Fila | entrada de sitemap "Por aprobar" (Supervisor) |
| 4 | Mis clientes — devueltas | Fila | entrada de sitemap "Devueltas" (agregada el 2026-09-22) |
| 5 | Terminadas | Fila | consulta |
| 6 | Por clasificar | Solicitud | entrada de sitemap |
| 7 | Para revisar | Solicitud | entrada de sitemap |
| 8 | Solicitudes | Solicitud | entrada de sitemap "Solicitudes" |
| 9 | Clientes activos | Cliente | entrada de sitemap "Clientes" |
| 10 | Planes activos | Plan | entrada de sitemap "Planes" |
| 11 | Autorizados activos | Autorizado | entrada de sitemap "Autorizados" |
| 12 | Autorizaciones activas | AutorizacionPlan | entrada de sitemap "Autorizaciones" |
| 13 | Parámetros activos | Parametro | entrada de sitemap "Parámetros" |
| 14 | Reglas activas | Regla | entrada de sitemap "Reglas" |
| 15 | Autorizaciones sin evidencia | AutorizacionPlan | pendientes del Administrador de planes. **No** son autorizaciones inválidas (D-42) |
| 16 | Correos autorizados sobre este plan | AutorizacionPlan | subgrilla del formulario de Plan |
| 17 | Planes que puede modificar | AutorizacionPlan | subgrilla del formulario de Autorizado |

Las 16 y 17 son la misma tabla vista desde cada lado, como dice la nota de navegación de abajo.

**Vista por defecto de cada tabla** (la que usa la plataforma en subgrillas y lookups cuando nadie elige otra): Fila → *Mis clientes — por digitar*; Solicitud → *Solicitudes*; AutorizacionPlan → *Autorizaciones activas*; y cada catálogo, su propia "Activos".

La vista "mis clientes" filtra por una relación de dos saltos (Fila → Plan → Cliente). Las vistas nativas lo admiten en su FetchXML; hay que comprobar al construir que el diseñador moderno no lo rompe al editarla.

## 4. Formularios

Uno principal por tabla, **una sola pestaña**, sin pestaña de "Relacionados" visible donde no aporta.

| Tabla | Secciones | Editable |
|---|---|---|
| **Fila** | Encabezado: Estado, Solicitud, n.º de fila. *Gestión* (los diez datos de la plantilla, más la referencia recibida). *Resultado* (Mensaje). *Trazabilidad* (validada, digitada por y cuándo, aprobada por y cuándo). | **Todo de solo lectura.** El estado se cambia con los botones; la lista blanca de columnas del plugin rechazaría cualquier otra edición (`04` §1). |
| **Solicitud** | Encabezado: Número, Estado, Remitente. *Correo* (recibido, asunto, archivos: correo original y Excel, para descargar). *Filas* (subgrilla con las filas y los mismos botones). *Reglas* (subgrilla de ResultadoRegla). *Comunicaciones* (acuse y respuesta final: cuándo y qué se dijo). *Bitácora* (subgrilla). | Solo lectura. |
| **Cliente** | Nombre, CIFBAC, CIFCOM, Ejecutivo asignado. Subgrilla **Planes del cliente** (código, moneda, tipo de formato, cantidad de correos autorizados, estado). *(La subgrilla **Correos autorizados del cliente** se quitó el 2026-09-24: un correo ya no pertenece a un cliente.)* | Administrador de planes |
| **Plan** | Código, Cliente (el lookup lleva al cliente), Moneda, Tipo de formato. Subgrilla **Correos autorizados sobre este plan** (correo, evidencia, fecha del documento, estado), sobre AutorizacionPlan; cada renglón abre esa autorización. | Administrador de planes |
| **Autorizado** | Correo, Cliente (el lookup lleva al cliente). Subgrilla **Planes que puede modificar** (plan, moneda, tipo de formato, evidencia, fecha del documento, estado), sobre AutorizacionPlan; cada renglón abre esa autorización. Desde ahí el Administrador de planes agrega una autorización nueva (solo planes del mismo cliente) o la desactiva; no se borra. **El Autorizado ya no lleva evidencia propia** (E-17). | Administrador de planes |
| **Autorización** (AutorizacionPlan) | Correo, Plan y Cliente (los tres lookups navegables). Sección **Evidencia de la autorización**: Documento firmado (`sanic_documentofirmado`, control nativo de archivo: cargar, descargar, reemplazar y quitar; un archivo, hasta 10 MB) y Fecha del documento. **La evidencia NO condiciona la vigencia** (D-42, aprobador 2026-09-21; `02` §2.4): una autorización vale con el Autorizado, el Plan, el Cliente y la propia AutorizacionPlan activos, tenga o no el documento cargado. La evidencia es el respaldo que el administrador de planes tiene que subir, y el formulario se lo muestra pendiente con una notificación, pero **al cliente no se lo afecta porque el banco no cargó un papel**. El archivo solo se puede cargar después de guardar el registro (así funciona una columna de archivo), así que toda autorización nace "sin evidencia" y eso es normal. *(Corregido el 2026-09-22: esta celda decía "la evidencia es obligatoria" y que la autorización "no vale" hasta cargarla, que es justo la validación que D-42 mandó sacar.)* Ejecutivo y Supervisor la pueden descargar, no cambiar (`04` §1). | Administrador de planes |
| **Parámetro** · **Regla** | Sus columnas; el valor JSON en un área de texto grande. | Administrador técnico |

**Navegación entre catálogos** (pedido del aprobador sobre el mockup, 2026-09-20). Desde un Cliente se ven sus planes y sus correos autorizados; desde un Plan se viaja a su cliente y se ven los correos autorizados sobre él; desde un Autorizado se ven los planes que puede modificar. Desde una Fila, el Plan y el Cliente son enlaces. Todo con lo nativo: lookups y subgrillas; "Volver" regresa al registro anterior, no a la lista. La subgrilla de un Plan y la de un Autorizado muestran la misma tabla, AutorizacionPlan, vista desde cada lado: hacen falta dos vistas de esa tabla, una por lado (`06`).

## 5. Comandos

En la grilla principal de Filas, en la subgrilla de Filas de la Solicitud y en el formulario de Fila. Visibles según rol y estado; **la validación real es del plugin** (DA-07).

| Botón | Quién lo ve | Sobre filas en | Pide | Efecto |
|---|---|---|---|---|
| **Digitada** | Ejecutivo | Validada | confirmación con la cantidad | Estado → Digitada |
| **Rechazada en AS400** | Ejecutivo | Validada o Digitada | motivo (diálogo) | Estado → Rechazada en AS400 + mensaje |
| **Anular** | Ejecutivo | Validada o Digitada | motivo (diálogo) | Estado → Anulada + mensaje |
| **Aprobar** | Supervisor | Digitada | confirmación con la cantidad | Estado → Aprobada |
| **Devolver** | Supervisor | Digitada | motivo (diálogo) | Estado → Validada + mensaje |
| **Atendido** · **Descartar** | Ejecutivo | Solicitud No reconocida o No es correo nuevo | confirmación | Estado → Cerrada · Descartada. Lo que nadie clasifica en 30 días pasa solo a Vencida (`07` DF-09) |
| **Revisado** | Ejecutivo, Supervisor | Solicitud con `requiererevision` | confirmación | Apaga `requiererevision`. El step `RevisionAtendidaStep` deja el **motivo que había escrito la máquina** en la Bitácora, con quién y cuándo, y limpia `sanic_motivorevision` |

> **Corregido el 2026-09-23.** Esta fila decía que Revisado pide una **nota**, y el comando la pedía y la escribía en `sanic_motivorevision`. Dos cosas estaban mal. La primera: esa columna **no es del operador** — la escriben `MPPP-VIG` y `MPPP-ENV` para explicar por qué hace falta revisar ("Validación fallida 3 veces", "Envío iniciado sin confirmar"), y es lo que el operador **lee** en la vista *Para revisar*; la nota se la habría comido. La segunda: la lista blanca de `04` §1 no admite esa columna de una persona, así que el botón **fallaba siempre**, y el plugin que esta tabla daba por hecho ("deja la nota en la Bitácora") **no existía**. Se resolvió como el **mockup aprobado el 2026-09-20**, que no pide texto. Evento nuevo de Bitácora: `Revision atendida` (159460021).

Una acción masiva puede fallar en algunas filas y en otras no (por ejemplo, el supervisor intenta aprobar una fila que él mismo digitó): el botón informa cuántas se aplicaron y cuáles no y por qué, y no deja nada a medias dentro de una misma fila.

## 6. Cómo trabaja la gente — confirmado por el aprobador el 2026-09-20

1. **Unidad de trabajo.** El ejecutivo trabaja una **lista plana de filas por digitar**, ordenada por solicitud, y no entra solicitud por solicitud. Tiene la Solicitud a un clic si quiere ver el correo.
2. **Acción masiva.** Selecciona varias filas y las marca juntas. El caso normal es "digité las 25 de esta plantilla". La grilla ofrece además **"Seleccionar todas" y "Desmarcar todas"** como comandos visibles, no solo la casilla del encabezado.
3. **Verificación del supervisor.** Le alcanza con las filas que extrajimos, y si duda **descarga el Excel original** desde la Solicitud. No hay visor del Excel dentro de la app en la fase 1.
4. **Por clasificar** (correos no reconocidos y correos que no son nuevos). Los ven **todos** los ejecutivos. Para decidir les alcanza con remitente, asunto y fecha, y si no, descargan el correo original.
5. **Catálogos.** El Administrador de planes carga **uno por uno en formularios**, y para cargas grandes usa la importación nativa desde Excel de model-driven. La migración inicial desde SharePoint es aparte (RF-16).
6. **Avisos.** **Notificaciones dentro de la app desde la fase 1** (DA-08).

## 7. Inventario que sale de este diseño (completa `06` §12)

| Tipo | Cantidad | Detalle |
|---|---|---|
| App y sitemap | 1 + 1 | |
| Vistas | ~16 | 5 de Fila, 3 de Solicitud, y activos + búsqueda de cada catálogo |
| Formularios | 9 | Uno por tabla con interfaz (ResultadoRegla y Bitácora solo se ven en subgrilla) |
| Comandos | 8 | Los de §5 |
| Tabla técnica + su creación rápida | 1 + 1 | `sanic_mppp_tbl_motivoaccion`: el diálogo de motivo (DA-03 corregida) |
| Web resources | ~10 | Íconos SVG del sitemap y de los botones |
| Ocultamiento de comandos genéricos | 10 tablas | DA-06 |

**Aviso sobre cómo se construye.** Vistas, formularios, sitemap y comandos se crean por Web API o por archivo de solución, así que **toda la fase 1 entra al ciclo de playbooks**. *(Corregido el 2026-09-22: acá decía que la página custom era el único componente que un agente no podía crear solo. Con DA-03 corregida ya no hay ninguna página custom, así que no queda ningún componente de la fase 1 fuera del ciclo. La bandeja de trabajo de DA-04 sigue siendo página custom, pero es versión 1.1.)*
