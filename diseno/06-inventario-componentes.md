# 06. Inventario de componentes

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **borrador**. Completo. La app y los flujos ya están diseñados (`05-app-model-driven.md`, `07-flujos.md`), **en borrador y pendientes de la revisión del aprobador**; su parte de este inventario puede cambiar con esa revisión.

Todo lo que hay que crear, en el orden en que se puede crear. Cada componente se construye a partir de un **playbook**: una especificación en Markdown, cerrada y sin ambigüedad, que ejecuta un agente constructor y audita un agente revisor. La columna **Tipo de playbook** agrupa los componentes que comparten formato de especificación y receta de construcción: son **14 tipos**, y esa es la medida real del trabajo de escribir las skills.

Mecanismo de creación: **Web API de Dataverse**, con una herramienta versionada por tipo de playbook (`herramientas/construir/`). Esas herramientas construyen **solo en Dev**; a Test y a Prod llega la solución managed (BP-PP-121, BP-PP-125), no una re-ejecución. La excepción son los datos semilla, que se cargan en cada entorno. Estado: `hecho` · `pendiente` · `bloqueado por …`.

## Resumen

| Tipo de playbook | Cantidad fase 1 | Fase 2 | Fase 3 | Irreversible |
|---|---|---|---|---|
| P-01 Solución | 1 (`hecho`) | | | nombre |
| P-02 Choice global | 14 | | 1 | nombre; los valores no se renumeran |
| P-03 Tabla con sus columnas | 10 tablas, 84 columnas propias (sin lookups: esos nacen con las relaciones) | | 1 tabla | nombre, propiedad, tipo de cada columna |
| P-04 Relación | 11 | | | nombre, tipo |
| P-05 Clave alternativa | 10 | | 1 | nombre |
| P-06 Column security profile | 1 (2 columnas) | | | |
| P-07 Security role | 5 | 1 | 1 | |
| P-08 Código de plugins (C#, TDD) | 1 paquete, ~10 clases | +2 clases | | namespace y nombre de clase |
| P-09 Registro de Custom API y steps | 2 API (11 parámetros), ~17 steps | 2 API | | nombre de API y de parámetros |
| P-10 Datos semilla | 12 parámetros, 15 reglas | 1 parámetro | 2 parámetros | |
| P-11 Environment variable y connection reference | 2 + 2 | | +2 | nombre |
| P-12 Cloud flow | 5 (3 con disparador, 2 hijos) | | | |
| P-13 App model-driven: app, sitemap, ~19 vistas, 9 formularios, 8 comandos, ~10 íconos | ver §12 | | página custom de la bandeja (v1.1) | |
| P-15 Página custom (canvas, **no la construye un agente solo**) | 1: diálogo de motivo | | | |
| P-14 Identidades y puesta en marcha | cuenta de servicio, buzón | usuario de aplicación del RPA | usuario de aplicación e infraestructura Azure | |

## 1. Base

| # | Componente | Nombre | Tipo | Depende de | Estado |
|---|---|---|---|---|---|
| 1.1 | Solución | `sanic_mppp_sol_mantenimientoppp` | P-01 | publisher `Sistemas_Abiertos_Nicaragua` | **hecho** (2026-09-20) |

## 2. Choices globales — P-02

Sin dependencias entre sí; van primero porque las columnas los usan. Valores = `15946` + correlativo de 4 dígitos (`02` §1).

| # | Nombre lógico | Opciones | Fase |
|---|---|---|---|
| 2.1 | `sanic_mppp_ch_moneda` | 2 | 1 |
| 2.2 | `sanic_mppp_ch_gestion` | 3 | 1 |
| 2.3 | `sanic_mppp_ch_clasificacion` | 3 | 1 |
| 2.4 | `sanic_mppp_ch_tipoformatoplan` | 3 | 1 |
| 2.5 | `sanic_mppp_ch_tipoidentificacion` | 5 | 1 |
| 2.6 | `sanic_mppp_ch_banco` | 8 | 1 |
| 2.7 | `sanic_mppp_ch_estadosolicitud` | 9 | 1 |
| 2.8 | `sanic_mppp_ch_estadofila` | 7 | 1 |
| 2.9 | `sanic_mppp_ch_efectoregla` | 3 | 1 |
| 2.10 | `sanic_mppp_ch_nivelregla` | 3 | 1 |
| 2.11 | `sanic_mppp_ch_resultadoregla` | 3 | 1 |
| 2.12 | `sanic_mppp_ch_origenevento` | 8 | 1 (+2 opciones en fases 2 y 3) |
| 2.13 | `sanic_mppp_ch_eventobitacora` | 20 | 1 |
| 2.14 | `sanic_mppp_ch_tipoparametro` | 3 | 1 |
| 2.15 | estado de histórico | por definir | 3 |

## 3. Tablas con sus columnas — P-03

Todas user-owned. El orden respeta los lookups: una tabla se crea después de las que referencia. Las columnas lookup **no** se crean acá: nacen con la relación (sección 4).

| # | Tabla | Columnas propias | Archivo | Protegidas | Depende de | Fase |
|---|---|---|---|---|---|---|
| 3.1 | `sanic_mppp_tbl_cliente` | 3 | | | | 1 |
| 3.2 | `sanic_mppp_tbl_plan` | 4 | | | choices 2.1, 2.4 | 1 |
| 3.3 | `sanic_mppp_tbl_autorizado` | 1 | | | | 1 |
| 3.4 | `sanic_mppp_tbl_autorizacionplan` | 3 | 1 | | | 1 |
| 3.5 | `sanic_mppp_tbl_parametro` | 5 | | | choice 2.14 | 1 |
| 3.6 | `sanic_mppp_tbl_regla` | 7 | | | choices 2.9, 2.10 | 1 |
| 3.7 | `sanic_mppp_tbl_solicitud` | 29 | 2 | | choice 2.7 | 1 |
| 3.8 | `sanic_mppp_tbl_fila` | 18 | | 2 | choices 2.1–2.3, 2.5, 2.6, 2.8 | 1 |
| 3.9 | `sanic_mppp_tbl_resultadoregla` | 7 | | | choices 2.9, 2.11 | 1 |
| 3.10 | `sanic_mppp_tbl_bitacora` | 7 | | | choices 2.12, 2.13 | 1 |
| 3.11 | `sanic_mppp_tbl_corridahistorico` | por definir | | | | 3 |

## 4. Relaciones — P-04

Cada una crea su columna lookup. `P` = parental (borrado en cascada), `R` = referencial con borrado restringido.

| # | Relación | Lookup que crea | Tipo |
|---|---|---|---|
| 4.1 | cliente → plan | `plan.sanic_clienteid` | R |
| 4.2 | cliente → autorizado | `autorizado.sanic_clienteid` | R |
| 4.3 | autorizado → autorizacionplan | `autorizacionplan.sanic_autorizadoid` | R |
| 4.4 | plan → autorizacionplan | `autorizacionplan.sanic_planid` | R |
| 4.5 | solicitud → fila | `fila.sanic_solicitudid` | **P** |
| 4.6 | solicitud → resultadoregla | `resultadoregla.sanic_solicitudid` | **P** |
| 4.7 | solicitud → bitacora | `bitacora.sanic_solicitudid` | **P** |
| 4.8 | plan → fila | `fila.sanic_planid` | R |
| 4.9 | regla → resultadoregla | `resultadoregla.sanic_reglaid` | R |
| 4.10 | systemuser → fila | `fila.sanic_digitadapor` | R |
| 4.11 | systemuser → fila | `fila.sanic_aprobadapor` | R |

## 5. Claves alternativas — P-05

Después de las relaciones, porque varias incluyen un lookup. La activación del índice es asíncrona: el playbook tiene que esperar y verificar.

| # | Clave | Columnas |
|---|---|---|
| 5.1 | `sanic_mppp_key_cliente_cifbac` | cifbac |
| 5.2 | `sanic_mppp_key_cliente_cifcom` | cifcom |
| 5.3 | `sanic_mppp_key_plan_codigo` | codigo |
| 5.4 | `sanic_mppp_key_autorizado_cliente_nombre` | clienteid + nombre |
| 5.5 | `sanic_mppp_key_autorizacionplan_autorizado_plan` | autorizadoid + planid |
| 5.6 | `sanic_mppp_key_parametro_nombre_version` | nombre + version |
| 5.7 | `sanic_mppp_key_regla_codigo` | codigo |
| 5.8 | `sanic_mppp_key_solicitud_messageid` | messageid |
| 5.9 | `sanic_mppp_key_fila_solicitud_numerofila` | solicitudid + numerofila |
| 5.10 | `sanic_mppp_key_resultadoregla_solicitud_reglacodigo` | solicitudid + reglacodigo |

## 6. Seguridad — P-06 y P-07

| # | Componente | Nombre | Depende de | Fase |
|---|---|---|---|---|
| 6.1 | Column security profile | `CSP - MPPP - Datos sensibles` (`fila.sanic_numeroidentificacion`, `fila.sanic_numerocuenta`) | tabla 3.8 | 1 |
| 6.2 | Security role | `SR - MPPP - Ejecutivo` | todas las tablas | 1 |
| 6.3 | Security role | `SR - MPPP - Supervisor` | ídem | 1 |
| 6.4 | Security role | `SR - MPPP - Administrador de planes` | ídem | 1 |
| 6.5 | Security role | `SR - MPPP - Administrador tecnico` | ídem | 1 |
| 6.6 | Security role | `SR - MPPP - Servicio de ingesta` | ídem. Las Custom API 8.0 y 8.1 se ejecutan con un privilegio que este rol ya tiene (D-9): el rol no depende de ellas, ellas dependen del rol | 1 |
| 6.7 | Security role | `SR - MPPP - RPA` | Custom API de fase 2 | 2 |
| 6.8 | Security role | `SR - MPPP - Historico` | | 3 |

## 7. Código de plugins — P-08 (C#, TDD estricto, sin FakeXrmEasy)

Un solo paquete, `sanic_mppp_pkg_plugins` (`Sanic.Mppp.Plugins`). Se construye por capas, de adentro hacia afuera (`03` §8); las cuatro primeras no tocan Dataverse.

| # | Pieza | Qué hace | Fase |
|---|---|---|---|
| 7.1 | `Dominio/` | Estados, transiciones permitidas, actor | 1 |
| 7.2 | `Plantilla/` | Lector de la plantilla, reglas LP-01 a LP-08 | 1 |
| 7.3 | `Validacion/` | Motor de reglas con orden y dependencias; 5 reglas de solicitud y 8 de registro (eran 6 de solicitud hasta que E-16 movió `REMITENTE_RECONOCIDO` al nivel Correo, que vive en 7.6b); el motor es uno solo y genérico, y lo reutiliza el nivel Correo | 1 |
| 7.4 | `Respuesta/` | Arma el acuse y la respuesta final, con enmascarado | 1 |
| 7.5 | Doble de prueba `OrganizationServiceEnMemoria` | En el proyecto de tests | 1 |
| 7.6 | `Datos/` | Repositorios sobre `IOrganizationService` | 1 |
| 7.6b | `Correo/` y `Api/ClasificarCorreoApi` | Lector de cabeceras del `.eml` (entrada no confiable) y el **plugin liviano** que decide si el correo se procesa | 1 |
| 7.7 | `Api/ValidarSolicitudApi` | Plugin de la Custom API de validación | 1 |
| 7.8 | `Steps/` lista blanca de columnas (Fila y Solicitud) | | 1 |
| 7.9 | `Steps/` transición de Fila (Pre) y post-transición (Post) | | 1 |
| 7.10 | `Steps/` normalizar y validar (Cliente, Plan, Autorizado, Parametro, Regla) | En Regla: impide desactivar una regla de la que dependen otras activas (D-13); impide que `AUTORIZACION_CORREO_PLAN` tenga otro efecto que Rechaza (D-14); impide el efecto Envía a revisión fuera de las reglas del sobre —niveles Correo y Solicitud—, nunca en Registro (D-20) | 1 |
| 7.11 | `Steps/` nombre calculado (Plan, AutorizacionPlan) e integridad de AutorizacionPlan | | 1 |
| 7.12 | `Steps/` atender no reconocida | | 1 |
| 7.13 | `Api/ObtenerFilasPendientesApi`, `Api/RegistrarResultadoRpaApi` | | 2 |

## 8. Registro de Custom API y steps — P-09

| # | Componente | Nombre | Depende de | Fase |
|---|---|---|---|---|
| 8.0 | Custom API | `sanic_mppp_capi_clasificarcorreo` (1 parámetro de entrada, 3 de salida) | 7.6b | 1 |
| 8.1 | Custom API | `sanic_mppp_capi_validarsolicitud` (1 parámetro de entrada, 6 de salida) | 7.7 | 1 |
| 8.2 | Steps | Uno por cada mensaje y tabla de 7.8 a 7.12 (~17), con su etapa, orden, atributos de filtro e imágenes | paquete registrado | 1 |
| 8.3 | Custom API | `sanic_mppp_capi_obtenerfilaspendientes` | 7.13 | 2 |
| 8.4 | Custom API | `sanic_mppp_capi_registrarresultadorpa` | 7.13 | 2 |

## 9. Datos semilla — P-10

| # | Qué | Cantidad | Depende de |
|---|---|---|---|
| 9.1 | Parámetros: `correo.prefijos.reenvio`, `clasificacion.dias.vencimiento`, `plantilla.estructura`, `plantilla.listas`, `plantilla.obligatoriedad`, `lectura.limites`, `retencion.dias.*` (2), `vigilancia.*` (3), `rpa.puedeaprobar` | 12 | tabla 3.5 |
| 9.2 | Reglas de nivel Correo (2) y de nivel Solicitud (5) | 7 | tabla 3.6 |
| 9.3 | Reglas de nivel Registro | 8 | tabla 3.6 |
| 9.4 | Migración única desde SharePoint: clientes, planes, autorizados, autorizaciones (RF-16) | datos reales | tablas 3.1–3.4, y los datos revisados por Banca Privada |

## 10. Configuración entre entornos — P-11

| # | Componente | Nombre | Fase |
|---|---|---|---|
| 10.1 | Environment variable | `sanic_mppp_ev_buzoningesta` | 1 |
| 10.2 | Environment variable | `sanic_mppp_ev_carpetaprocesados` | 1 |
| 10.3 | Connection reference | `sanic_mppp_conr_outlook` | 1 |
| 10.4 | Connection reference | `sanic_mppp_conr_dataverse` | 1 |
| 10.5 | Environment variables del almacenamiento del histórico | por definir | 3 |

## 11. Flujos — P-12 (`07-flujos.md`)

| # | Flujo | Disparador | Depende de |
|---|---|---|---|
| 11.1 | `Cloud Flow - MPPP - ING - Ingerir y validar correo` | hijo | tabla 3.7, Custom API 8.0 y 8.1, 10.1–10.4 |
| 11.2 | `Cloud Flow - MPPP - REC - Recibir correo nuevo` | correo nuevo en el buzón | 11.1 |
| 11.3 | `Cloud Flow - MPPP - ENV - Enviar comunicación al cliente` | hijo | tabla 3.7 |
| 11.4 | `Cloud Flow - MPPP - COM - Detectar comunicación pendiente` | cambio de estado de la Solicitud | 11.3 |
| 11.5 | `Cloud Flow - MPPP - VIG - Vigilar pendientes` | cada 10 minutos | 11.1, 11.3, parámetros 9.1 |

Desaparece el Flow B de la definición (`07` DF-01). Los hijos se construyen antes que quienes los llaman.

## 12. App model-driven — P-13 y P-15 (`05-app-model-driven.md`)

| # | Componente | Cantidad | Depende de |
|---|---|---|---|
| 12.1 | Íconos SVG (web resources) | ~10 | |
| 12.2 | Vistas | ~19 | tablas y relaciones. Incluye las dos de AutorizacionPlan para subgrillas: "correos autorizados sobre un plan" y "planes que puede modificar un correo", más "Autorizaciones sin evidencia" (`05` §formularios) |
| 12.3 | Formularios principales | 9 | tablas, vistas (subgrillas) |
| 12.4 | Página custom: diálogo de motivo | 1 | tabla 3.8 · **se arma en Power Apps Studio** |
| 12.5 | Comandos propios | 8 | 12.4, plugin de transición 7.9 |
| 12.6 | Ocultamiento de comandos genéricos | 10 tablas | |
| 12.7 | Sitemap | 1 | 12.1, 12.2 |
| 12.8 | App `sanic_mppp_mda_mantenimientoppp` | 1 | 12.2, 12.3, 12.7, roles 6.2–6.5 |
| 12.9 | Página custom "bandeja de trabajo" | 1 | **versión 1.1**, fuera de la fase 1 |

## 13. Identidades y puesta en marcha — P-14

| # | Qué | Quién | Fase |
|---|---|---|---|
| 13.1 | Buzón dedicado, con carpeta de procesados | Administrador de Exchange | 1 |
| 13.2 | Cuenta de servicio licenciada, con su rol 6.6 y acceso exclusivo al buzón (C-04) | Administrador de Power Platform | 1 |
| 13.3 | Asignación de roles a ejecutivos, supervisores y administradores | Administrador de Power Platform | 1 |
| 13.4 | Auditoría sobre asignación de roles activada (D-38) | Administrador de Power Platform | 1 |
| 13.7 | Grupo de seguridad de Entra ID para quienes leen datos sensibles, su equipo de grupo en el entorno, y la asociación de ese equipo al perfil 6.1 (D-8, `04` §4) | Administrador de Azure y de Power Platform | 1 |
| 13.5 | Usuario de aplicación del RPA | | 2 |
| 13.6 | Usuario de aplicación del histórico e infraestructura Azure | Administrador de Azure | 3 |

## Orden de construcción de la fase 1

`2` choices → `3` tablas → `4` relaciones → `5` claves → `6.1` perfil de columna → `7.1–7.5` código sin Dataverse (**puede ir en paralelo con todo lo anterior**) → `7.6–7.12` → registro del paquete → `8.1–8.2` → `6.2–6.6` roles → `9.1–9.3` semillas → `10` configuración → `11` flujos → `12` app → `9.4` migración → `13` puesta en marcha.
