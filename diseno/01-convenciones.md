# 01. Convenciones de nombres y estructura

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **secciones 1 a 5 acordadas con el aprobador el 2026-09-18**

> Este documento **instancia** para este proyecto el estándar del estudio, que vive en `power-platform-practicas/references/convenciones-nombres.md` (reglas **BP-PP-181 a BP-PP-195**, origen `estandar`). Si algo de acá contradice al estándar y no figura como excepción en la sección 0, manda el estándar.

## 0. Parámetros de este proyecto

| Parámetro | Valor |
|---|---|
| Publisher | **Sistemas Abiertos Nicaragua**, unique name `Sistemas_Abiertos_Nicaragua` (verificado en Dev el 2026-09-20). **Cuidado: en Dev hay otro publisher con el mismo prefijo `sanic`, "Sanic Corp" (unique name `sanic`, prefijo de opciones 10000).** Todo componente se crea fijando el publisher por su unique name, nunca por el prefijo |
| Prefijo numérico de opciones | `15946` → los valores de choice son `159460001`, `159460002`… |
| Prefijo de publisher | `sanic` |
| Abreviatura de la solución | `MPPP` / `mppp` |
| Nombre completo | Mantenimiento PPP |
| Idioma base del entorno | **1033 (inglés)**, y es el único provisionado (verificado en Dev el 2026-09-20). Las etiquetas van **en español, bajo el LCID 1033**, como en las demás soluciones del publisher. Una etiqueta de metadatos **solo** en 3082 deja el componente sin nombre visible acá (verificado) |
| Idiomas del proyecto | **`idiomas: [1033, 3082]`**, ampliable (exigencia del aprobador, 2026-09-20: todo nace listo para varios idiomas). **Etiquetas de metadatos** (tablas, columnas, choices, vistas, formularios): en 1033; si el entorno destino tiene otro idioma base y la solución no trae etiquetas en él, la plataforma usa las del idioma base del origen (Learn, *Create solutions that support multiple languages*). **Etiquetas embebidas** en el XML del componente (títulos y descripciones del sitemap, textos de los comandos, y las que cada export real demuestre): **una por cada idioma de la lista**, porque ahí no hay sustitución. Se escriben desde Dev aunque solo tenga 1033 habilitado. Qué textos de cada tipo de componente son embebidos se asienta en la referencia del tipo, con el export real como evidencia |
| Excepciones al estándar | Ninguna |

## 1. Las tres reglas que gobiernan todo

1. **Display name**: `TIPO - ABREVIATURA - Nombre`. Ejemplo: `CH - MPPP - Estado de fila`.
2. **Nombre lógico / schema / unique name**: `prefijo_abreviatura_tipo_nombre`, un solo orden para todos los componentes. Ejemplo: `sanic_mppp_ch_estadofila`.
3. **Todo nombre lógico va en minúscula**, en español, sin tildes ni ñ, sin separadores dentro del nombre. Schema name y logical name quedan idénticos, y así desaparece una clase entera de errores: en Web API, `@odata.bind` y las propiedades de navegación respetan las mayúsculas del schema name. Para leer está el display name.

Si un componente **no tiene nombre lógico** en la plataforma, aplica solo la regla 1.

## 2. Tabla de componentes

| Componente | Display name | Nombre lógico | Ejemplo |
|---|---|---|---|
| Solución | `SOL - MPPP - Nombre completo` | `sanic_mppp_sol_nombre` | `SOL - MPPP - Mantenimiento PPP` · `sanic_mppp_sol_mantenimientoppp` |
| Tabla | **Nombre limpio de negocio** (excepción a la regla 1) | `sanic_mppp_tbl_nombre` | `Solicitud` / `Solicitudes` · `sanic_mppp_tbl_solicitud` |
| Columna | Texto de negocio | `sanic_nombre` (sin abreviatura ni tipo: ya vive dentro de su tabla) | `Estado de procesamiento` · `sanic_estadoprocesamiento` |
| Lookup | Texto de negocio | `sanic_<destino>id` | `sanic_solicitudid`, `sanic_planid` |
| Choice global | `CH - MPPP - Nombre` | `sanic_mppp_ch_nombre` | `sanic_mppp_ch_estadofila` |
| Clave alternativa | `KEY - MPPP - Tabla - Campos` | `sanic_mppp_key_<tabla>_<campos>` | `sanic_mppp_key_fila_solicitud_numero` |
| Relación 1:N | no tiene | `sanic_mppp_<padre>_<hijo>`; con más de una relación entre el mismo par, sufijo con el lookup sin prefijo | `sanic_mppp_solicitud_fila` · `sanic_mppp_systemuser_fila_digitadapor` |
| Custom API | `CAPI - MPPP - Nombre` | `sanic_mppp_capi_nombre` | `CAPI - MPPP - Validar solicitud` · `sanic_mppp_capi_validarsolicitud` |
| Parámetro de entrada de Custom API | `CAPI_IP - MPPP - Nombre` | `uniquename` **corto**: `nombre` · `name`: `sanic_mppp_capiip_<api>_<nombre>` | `CAPI_IP - MPPP - Solicitud id` · `solicitudid` · `sanic_mppp_capiip_validarsolicitud_solicitudid` |
| Parámetro de salida de Custom API | `CAPI_OP - MPPP - Nombre` | `uniquename` corto · `name`: `sanic_mppp_capiop_<api>_<nombre>` | `filasvalidas` |
| Environment variable | `EV - MPPP - Nombre` | `sanic_mppp_ev_nombre` | `EV - MPPP - Buzón de ingesta` · `sanic_mppp_ev_buzoningesta` |
| Connection reference | `CONR - MPPP - Nombre` | `sanic_mppp_conr_nombre` | `CONR - MPPP - Outlook` · `sanic_mppp_conr_outlook` |
| Cloud flow | `Cloud Flow - MPPP - COD - Nombre`, donde `MPPP-COD` es su **identificador corto** de tres letras (BP-PP-196) | **no tiene**, salvo que Power Automate respete `uniquename` (§7); en ese caso `sanic_mppp_cloudflow_<cod>` | `Cloud Flow - MPPP - REC - Recibir correo nuevo` · ID `MPPP-REC` |
| Security role | `SR - MPPP - Nombre` | **no tiene** | `SR - MPPP - Ejecutivo` |
| Column security profile | `CSP - MPPP - Nombre` | **no tiene** | `CSP - MPPP - Datos sensibles` |
| App model-driven | `MDA - MPPP - Nombre` | `sanic_mppp_mda_nombre` | `MDA - MPPP - Mantenimiento PPP` · `sanic_mppp_mda_mantenimientoppp` |
| Site map | no aplica | `sanic_mppp_sm_nombre` | `sanic_mppp_sm_mantenimientoppp` |
| Vista | Texto de negocio en español | no tiene | `Mis clientes - Filas pendientes` |
| Formulario | `FRM - MPPP - Tabla - Tipo` | no tiene | `FRM - MPPP - Fila - Principal` |
| Regla de negocio | `BR - MPPP - Tabla - Nombre` | no tiene | |
| Dashboard / gráfico | `DASH - MPPP - Nombre` / `CHT - MPPP - Nombre` | no tiene | |
| Web resource | `WR - MPPP - TIPO - Nombre` | `sanic_mppp_wr_<tipo>_nombre` | `WR - MPPP - JS - Fila formulario` · `sanic_mppp_wr_js_filaformulario` |
| Paquete de plugins | no aplica | `sanic_mppp_pkg_plugins` | |
| Step de plugin | `STEP - MPPP - tabla - mensaje - etapa` | no tiene | `STEP - MPPP - fila - Update - PreOperation` |
| Usuario de aplicación | `APP - MPPP - Nombre` | no aplica | `APP - MPPP - RPA` |

**Por qué el parámetro de Custom API lleva `uniquename` corto**: es el nombre que viaja en cada llamada. Su alcance es su propia API (Learn: parámetros de APIs distintas pueden repetir `UniqueName`), así que prefijo y abreviatura no desambiguan nada y solo ensuciarían el contrato que consume el bot de RPA. La convención completa va en `name` y `displayname`, que es donde sirve para ordenar y buscar.

**Por qué la tabla lleva display name limpio**: es lo que ve el ejecutivo en el botón "Nuevo", los encabezados de formulario, los lookups y los mensajes de error. La app sí lleva `MDA - MPPP - …` por decisión del aprobador.

## 3. Versionado de la solución

`MAYOR.MENOR.PARCHE.BUILD`

| Dígito | Sube cuando… | Al subir |
|---|---|---|
| **MAYOR** | Hay un rediseño que rompe compatibilidad (contratos de Custom API, modelo de datos). Arranca en `1`. | MENOR, PARCHE y BUILD vuelven a 0 |
| **MENOR** | Se entrega funcionalidad nueva a Prod. **No está atado a las fases**: una fase es una entrega, pero también lo es cualquier mejora posterior. | PARCHE y BUILD vuelven a 0 |
| **PARCHE** | Se corrige algo ya entregado, sin funcionalidad nueva. | BUILD vuelve a 0 |
| **BUILD** | Cada export desde Dev. | — |

Ejemplo: `1.0.0.14` es el export 14 camino a la primera entrega; `1.1.0.3` la segunda entrega funcional; `1.1.2.0` su segunda corrección. Lo que llega a Prod siempre queda etiquetado en git con su versión.

## 4. Idioma y forma

- Nombres lógicos: regla 3 de la sección 1. **Nombres visibles: en español, sin tildes ni ñ** (BP-PP-197, decisión del aprobador del 2026-09-21): tablas, columnas, choices y sus opciones, claves, lookups, roles, perfiles, y todo lo que venga después (flujos, vistas, formularios, steps, variables). Se escribe la palabra sin la tilde (`Numero`, `Autorizacion`). Las descripciones son prosa y sí llevan ortografía completa. Excepciones: solo las siete de D-10 (`PENDIENTES.md`), ya construidas y que el Web API no deja cambiar; ninguna más.
- Código C#: identificadores en inglés para lo técnico (`ValidationPipeline`, `IRowRule`) y en español para el dominio tal como lo nombra el negocio (`Solicitud`, `Fila`, `Gestion`). Nunca se traduce un término del glosario del panorama. El código C# sí usa PascalCase: la regla de minúsculas es solo para nombres lógicos de la plataforma.
- **Fechas de auditoría propias** (RNF-01, D-06): se llaman `sanic_fecha<evento>` (`sanic_fecharespondida`) y quién lo hizo `sanic_<evento>por` (`sanic_digitadapor`, lookup a `systemuser`). Toda columna de fecha y hora usa el comportamiento **Usuario local**: Dataverse guarda el instante en UTC y se lo muestra a cada persona en su hora. Es lo que permite restar dos fechas para medir el tiempo de ciclo y que el histórico en Azure quede en UTC sin ambigüedad. Ese comportamiento prácticamente no se puede cambiar después de crear la columna.
- **Columna primaria** de cada tabla: `sanic_nombre`. Nunca la digita una persona: la calcula un plugin o un flujo con el formato que indique el diccionario, o es **autonumérica** cuando el nombre tiene poca relevancia.

## 5. Ensamblados y código

| Elemento | Valor |
|---|---|
| Repositorio | este (`M-PPP`), rama `main` |
| Solución .NET | `src/Sanic.Mppp.sln` |
| Paquete de plugins (dependent assemblies, por Open XML SDK) | `Sanic.Mppp.Plugins` (.NET Framework 4.6.2, firmado); en Dataverse `sanic_mppp_pkg_plugins` |
| Namespace raíz | `Sanic.Mppp.Plugins` — **inmutable tras el primer registro** (renombrar tipos rompe el registro en silencio) |
| Frameworks de destino | Librerías: **`net462;net8.0`**. net462 es lo que ejecuta el sandbox de Dataverse; net8.0 existe solo para que los tests corran en el puesto de trabajo Linux, que no tiene `mono` (verificado 2026-09-18). Compilar net462 en Linux requiere `Microsoft.NETFramework.ReferenceAssemblies`. Prohibido usar APIs que no existan en net462. |
| Tests | `Sanic.Mppp.Plugins.Tests` (`net8.0`, xUnit, Strict TDD). **Sin FakeXrmEasy**: sus versiones 2.x y 3.x exigen licencia comercial paga (`docs/licencias-terceros.md`). El dominio se prueba con tests unitarios puros; la capa que toca `IOrganizationService` se prueba con un **doble propio en memoria**, que vive en el proyecto de tests |
| Herramienta de histórico (fase 3) | `Sanic.Mppp.Historico` (Azure Function, .NET 8 isolated) |
| Solución desempaquetada | `solution/` (`pac solution unpack`), sin binarios en git (BP-PP-130) |

```
M-PPP/
├── README.md          ← mapa del repositorio
├── diseno/            ← diseño detallado (00 a 04), diagrama y PENDIENTES
├── datos/             ← insumos versionados: plantilla del cliente, semillas de catálogos y parámetros. Sin datos reales de clientes
├── herramientas/      ← utilidades del puesto de trabajo: pacx, generar_er.py. Una sola carpeta
├── src/               ← C# (plugins, tests, histórico)
├── solution/          ← solución desempaquetada
├── spikes/            ← C-05, C-06: código descartable, conclusiones en md
├── docs/              ← procedimientos de operación
└── local/             ← NO versionado: secretos y documentos de contexto
```

## 6. Valores de choice

Los valores numéricos usan el prefijo de opciones del publisher + correlativo de 4 dígitos: `<prefijo>0001`, `<prefijo>0002`… El código C# **nunca** usa el literal: usa un `enum` generado a partir del diccionario. Los correlativos son estables y no se reordenan; una opción que deja de usarse se retira de las vistas, no se borra.

## 7. Verificado y pendiente de verificar

| Hecho | Estado |
|---|---|
| Nombre de step de plugin: máximo **256** caracteres | Verificado en Learn (tabla `SdkMessageProcessingStep`), 2026-09-18. El más largo previsto ronda los 65. |
| Schema name de relación: máximo **100** caracteres | Verificado en Learn (tabla `EntityRelationship`), 2026-09-18. |
| El `UniqueName` de un parámetro de Custom API puede repetirse entre APIs distintas; los parámetros se identifican por nombre | Verificado en Learn (`CustomAPI tables`), 2026-09-18. |
| Largo máximo del nombre lógico de **tabla** | Verificado en Dev el 2026-09-20: **95 caracteres** por identificador ("Identifiers cannot be more than 95 characters long"). Se crearon y borraron tablas de prueba de 51 y 65. La más larga del proyecto tiene 31. |
| Security role y column security profile no tienen nombre lógico | Verificado en los metadatos de Dev el 2026-09-20: `role` y `fieldsecurityprofile` solo tienen `name`. |
| Cloud flow | **Corrección**: la tabla `workflow` **sí** tiene una columna `uniquename`, y admite valor al crear. Falta comprobar, al construir el primer flujo, si Power Automate la respeta en un cloud flow; si la respeta, aplica el nombre lógico `sanic_mppp_cloudflow_<nombre>` que pedía el aprobador. Hasta entonces, solo display name. |
| Una connection reference creada por API conserva el nombre exacto, sin sufijo | Verificado en Dev el 2026-09-20 (`sanic_mppp_conr_zzdummy`, creada y borrada). Las connection references del proyecto se crean por API o por archivo de solución, no desde el maker portal. |
| El `uniquename` de un parámetro de Custom API **no** exige prefijo de publisher | Verificado en Dev el 2026-09-20: se aceptó `solicitudid` sin prefijo. |
| Open XML SDK 3.1.0 dentro del sandbox de Dataverse | Verificado en Dev el 2026-09-20 (spike C-05 parte B): carga como ensamblado dependiente, el paquete pesa 1,76 MB y la lectura tarda milisegundos. La Custom API es atómica. Las claves alternativas de texto no distinguen mayúsculas. **Bajo SYSTEM no se puede saber quién originó la llamada** (`03` §4). |
| La solución existe en Dev | Creada el 2026-09-20: `sanic_mppp_sol_mantenimientoppp`, «SOL - MPPP - Mantenimiento PPP», versión `1.0.0.0`, unmanaged, publisher `Sistemas_Abiertos_Nicaragua`. Vacía. |
| Unique name del publisher y prefijo numérico de opciones | Verificado en Dev el 2026-09-20: `Sistemas_Abiertos_Nicaragua`, `15946`. Existe un segundo publisher con prefijo `sanic` ("Sanic Corp", `10000`). |
| `pac` se cuelga sin error en una sesión sin escritorio | Resuelto el 2026-09-20: es el llavero de GNOME por D-Bus. Se usa `herramientas/pacx`, que aísla a `pac` del llavero; quitar solo `DBUS_SESSION_BUS_ADDRESS` no alcanza, porque D-Bus encuentra el bus por `XDG_RUNTIME_DIR`. Perfil del proyecto: `MPPP-DEV`. |
