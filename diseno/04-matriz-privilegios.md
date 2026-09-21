# 04. Matriz de privilegios

Proyecto: 2026-001-referencias-planes-pago · Etapa 3 · Estado: **revisado con el aprobador el 2026-09-18**

Reglas citadas: BP-PP-001, 002, 003, 004, 008. Una sola business unit (la raíz del entorno); sin sharing manual; sin teams, **con una única excepción**: el equipo que recibe el perfil de seguridad de columna (§4, D-8).

Notación: `C` crear · `R` leer · `W` escribir · `D` borrar · `Ap` append · `At` append to · `As` asignar. Alcance: **O** organización · **U** propio · `—` sin privilegio. **Todas las tablas son user-owned** (BP-PP-013), así que toda celda con privilegio lleva su alcance explícito, sin excepción.

User-owned es una decisión por BP-PP-013 (irreversibilidad de la propiedad), **no** por confidencialidad: alcance O no significa "cualquiera ve todo", significa "quien tiene el privilegio con ese alcance ve todas las filas". Quien no tiene asignado ningún rol `SR - MPPP` no ve nada en ningún caso, independientemente del alcance de las celdas de abajo.

## 1. Principio que ordena toda la matriz

**Los humanos casi no escriben; escribe el código.** La Custom API y los plugins **leen los catálogos y graban** Filas, ResultadoRegla y Bitácora con el servicio de **SYSTEM** (`CreateOrganizationService(null)`), no con el usuario que llama. Por eso ningún rol humano necesita `C` sobre la unidad histórica, y la cuenta de servicio tampoco. Es lo que hace que la trazabilidad no se pueda fabricar a mano.

El hueco que esto deja: el Ejecutivo y el Supervisor **necesitan `W` sobre Fila** para cambiar el estado, y `W` en Dataverse es sobre la fila entera: con ese privilegio podrían editar el número de cuenta. Se cierra con un control técnico, no con el formulario:

> **Lista blanca de columnas** (step PreOperation en `Update` de Fila, sin filtro de atributos): si quien llama no es SYSTEM ni una identidad de aplicación de la solución, el `Target` solo puede traer `sanic_estado` y `sanic_mensaje`. Cualquier otra columna → error. Un formulario de solo lectura es cosmética; esto es el control. Ya no existe `sanic_usuarioas400aprobador`: el usuario que marca Aprobada es el aprobador de AS400 (`03-contratos-custom-api.md` §4), así que no hace falta una columna extra en la lista blanca.

Mismo criterio en Solicitud para los humanos: solo `sanic_requiererevision` (el botón "Revisado", `05` §5) y `sanic_estadoprocesamiento` (No reconocida → Cerrada/Descartada).

**Dueños**: Cliente es propiedad del ejecutivo asignado (RF-19, D-23). Solicitud, Fila, ResultadoRegla y Bitácora son propiedad de la cuenta de servicio, salvo cuando el propio plugin las escribe como SYSTEM. Por eso Ejecutivo y Supervisor necesitan alcance **O** sobre Fila (y Solicitud, en lectura) para cubrir ausencias entre sí: ninguno de los dos es el dueño registral de esas filas.

## 2. Roles humanos

| Tabla | SR - MPPP - Ejecutivo | SR - MPPP - Supervisor | SR - MPPP - Administrador de planes | SR - MPPP - Administrador técnico |
|---|---|---|---|---|
| Cliente | R:O | R:O | C R W Ap At As : O | — |
| Plan | R:O | R:O | C R W Ap At : O | — |
| Autorizado | R:O | R:O | C R W Ap At : O | — |
| AutorizacionPlan | R:O | R:O | C R W Ap At : O | — |
| Parametro | — | — | — | C R W : O |
| Regla | R:O | R:O | R:O | C R W : O |
| Solicitud | R W At : O | R At : O | — | — |
| Fila | R W Ap : O | R W Ap : O | — | — |
| ResultadoRegla | R:O | R:O | — | — |
| Bitacora | R:O | R:O | — | — |
| CorridaHistorico (fase 3) | — | — | — | R:O |
| **Borrado** en cualquier tabla | — | — | — | — |

- **Nadie borra.** Los catálogos se desactivan (`W` alcanza para cambiar el estado); la unidad histórica solo la purga el job nativo (D-35).
- Ejecutivo y Supervisor tienen exactamente los mismos privilegios sobre Fila; lo que los distingue es **qué transición les deja hacer el plugin** según su rol. Son **mutuamente excluyentes por usuario** (D-25): el plugin rechaza toda transición de un usuario que tenga los dos roles.
- "Mis clientes" es una **vista**, no un permiso (RF-19, D-13): Fila → Plan → Cliente con `ownerid = usuario actual`. Todos leen todo a nivel O para cubrir ausencias.
- El Administrador de planes **no** ve Filas ni datos sensibles: administra catálogos, no gestiones (RF-11, D-37).
- El **Administrador técnico** solo toca lo técnico: Parámetros y Reglas. **No ve clientes, autorizados, solicitudes, filas, resultados de reglas ni bitácora**: eso es del negocio, y una Solicitud además trae el Excel crudo con cuentas e identificaciones. Para diagnosticar una solicitud que falló trabaja con lo que le muestre alguien de negocio o con el log de trazas del plugin, que no lleva datos sensibles. Se asigna a pedido y se retira al terminar (D-38); la asignación queda en la auditoría nativa de Dataverse: **hay que activar la auditoría sobre asignación de roles** en el entorno, coordinado con el administrador de Power Platform.
- Todos los roles se crean **copiando "App Opener"**, no "Basic User", para partir del mínimo. Cada uno incluye lectura de la app model-driven.

## 3. Identidades de aplicación

| Tabla | SR - MPPP - Servicio de ingesta (cuenta de servicio, los cinco flujos) | SR - MPPP - RPA (application user, fase 2) | SR - MPPP - Histórico (application user, fase 3) |
|---|---|---|---|
| Solicitud | C R W Ap At : O | R:O | C R W **D** Ap At : O |
| Fila | — | R:O | C R **D** Ap : O |
| ResultadoRegla | — | — | C R **D** Ap : O |
| Bitacora | C Ap : O | — | C R **D** Ap : O |
| Parametro | R:O (los `vigilancia.*` que lee `MPPP-VIG`) | — | R:O |
| Regla | — | — | R:O |
| Cliente, Plan | — | R:O | R:O |
| Autorizado, AutorizacionPlan | — | — | R:O |
| CorridaHistorico (fase 3) | — | — | C R W : O |
| Privilegios varios | Ejecutar flujos, leer environment variables y connection references | — | `prvBulkDelete` · `prvOverrideCreatedOnCreatedBy` (para `overriddencreatedon`, D-36) |
| Custom API | `sanic_mppp_capi_clasificarcorreo`, `sanic_mppp_capi_validarsolicitud` | `sanic_mppp_capi_obtenerfilaspendientes`, `sanic_mppp_capi_registrarresultadorpa` | — |

- El **RPA no escribe ninguna tabla**: todo pasa por su Custom API, que graba como SYSTEM. Rol mínimo de verdad (D-14, RNF-07).
- **Histórico es la única identidad con `D`** sobre la unidad histórica, y el código solo lo ejerce enviando el job nativo sobre Solicitudes marcadas y vencidas (D-35). `C` es para la reactivación.
- **La cuenta de servicio tiene su propio rol, `SR - MPPP - Servicio de ingesta`**, y es mínimo a propósito: crea y actualiza la Solicitud (alta, archivos, marcas de envío), escribe eventos en la Bitácora, lee los parámetros de vigilancia y ejecuta la Custom API de validación. **No lee filas, clientes, planes ni autorizados**: todo eso lo lee y lo escribe el plugin de la Custom API con el servicio de SYSTEM, no con los privilegios de quien la llama, y el contenido de los correos al cliente ya viene armado en la Solicitud. Si la credencial de la cuenta de servicio se filtrara, quien la tenga no podría leer un solo número de cuenta por esa vía. Además del rol, la cuenta necesita sus licencias de Power Apps y Power Automate (C-04) y los privilegios básicos para ejecutar flujos y leer environment variables y connection references.

## 4. Column security profile "CSP - MPPP - Datos sensibles"

Columnas: `sanic_mppp_tbl_fila.sanic_numeroidentificacion` y `sanic_mppp_tbl_fila.sanic_numerocuenta` (RNF-04, BP-PP-004).

**Cómo funciona en la plataforma** (verificado en Learn el 2026-09-21): un perfil de seguridad de columna se asigna a **usuarios o equipos, nunca a roles**, y sus permisos son **del perfil entero**, no de cada miembro. Por eso hay un perfil por nivel de acceso.

| Perfil | Leer | Crear | Actualizar | Quién necesita estar | Fase |
|---|---|---|---|---|---|
| `CSP - MPPP - Datos sensibles` | sí | no | no | Ejecutivos y Supervisores. El usuario de aplicación del RPA, en fase 2 | 1 |
| Un segundo perfil, de lectura **y creación** (se nombra al diseñar la fase 3) | sí | sí | no | El usuario de aplicación del Histórico | 3 |

Nadie más: ni la cuenta de servicio de ingesta, ni el Administrador de planes, ni el Administrador técnico.

**Cómo llegan las personas al perfil** (D-8, decisión del aprobador del 2026-09-21): **por equipo**. El administrador crea un **grupo de seguridad en Entra ID** y su **equipo de grupo** en Power Platform, y a ese equipo se le asigna el perfil. Es la única excepción a "sin teams" de esta matriz. El perfil y sus permisos viajan en la solución (inventario 6.1); **el grupo, el equipo y la asociación equipo ↔ perfil no viajan**: son una tarea de administración en cada entorno (inventario 13.7). Quien entra o sale del grupo de Entra gana o pierde la lectura de esas dos columnas sin tocar Dataverse.

- El Ejecutivo **tiene** que leerlas: son lo que digita en AS400. La protección es contra todos los demás y contra exportaciones.
- Histórico las lee para que el paquete no llegue con columnas vacías (RNF-09), y las crea al reactivar.
- SYSTEM (la Custom API) no necesita estar en ningún perfil.
- El `.eml` y el Excel originales contienen los mismos datos en crudo y **no** los cubre la seguridad de columna: los protege el registro padre. Por eso el Administrador de planes **no tiene lectura de Solicitud**: no la necesita para administrar catálogos y le daría el Excel crudo con cuentas e identificaciones. El Administrador técnico tampoco, por el mismo motivo.

## 5. Cómo se verifica

Un test por celda crítica, no por las 80: (1) un Ejecutivo no puede aprobar lo que digitó; (2) un usuario con ambos roles no puede transicionar nada; (3) el Supervisor devuelve una Fila Digitada → Validada y la fila reaparece con `digitadapor` vacío; (4) el usuario de aplicación del RPA no puede aprobar lo que él mismo digitó mientras `rpa.puedeaprobar` valga `no`; (5) un Ejecutivo no puede cambiar `sanic_numerocuenta` por Web API; (6) un Administrador de planes no ve `sanic_numerocuenta`; (7) ningún rol humano puede borrar una Solicitud; (8) el RPA no puede escribir una Fila por Web API directa. Los primeros cinco son tests de plugin con el doble propio de `IOrganizationService`; los últimos tres, prueba manual guiada en Dev con usuarios de prueba, documentada en `docs/`.
