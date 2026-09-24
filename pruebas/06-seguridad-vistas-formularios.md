# 06 — Seguridad, sitemap, vistas y formularios

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

## G-00 · Los privilegios efectivos, antes de tocar la app

**Qué prueba.** Que cada usuario de prueba tenga **exactamente** las celdas de la matriz de `04`,
ni una menos ni una de más.

**Por qué va primero.** En Dataverse los privilegios se **suman**: los de los roles directos más los
de **cada equipo** al que el usuario pertenece. Un usuario reciclado de otro proyecto llega con los
roles de ese proyecto. Entonces, si en la app el usuario puede hacer algo que no debería, mirando la
pantalla **no se sabe quién se lo permitió**. Esto lo resuelve antes de empezar, y con nombre y
apellido del rol culpable.

**Cómo.**

```bash
python3 herramientas/pruebas/verificar_accesos.py User1 User2 User3
```

**Esperado.** `Coincide con la matriz, celda por celda.` para los tres. Sale con 0.

**Qué hacer con cada tipo de hallazgo.**

| Tipo | Qué significa | Qué hacer |
|---|---|---|
| `FALTA` | La matriz le da el privilegio y no lo tiene | El rol está mal construido: revisá su playbook y reimportalo |
| `ALCANCE` | Lo tiene, pero con otra profundidad | Ídem. Un `U` donde va `O` hace que el usuario solo vea sus propios registros |
| `SOBRA` | Lo tiene y la matriz no se lo da. **El detalle nombra el rol que se lo trajo** | Si el rol es de otro proyecto, sacalo del equipo antes de probar, o la prueba no vale |
| `COLUMNAS` | No alcanza el perfil de seguridad de columna | Ver G-05: sin eso, el ejecutivo no ve lo que tiene que digitar |

**Correr esto también después de cada cambio de roles.** Es lo único que detecta que un
`ImportSolution` pisó un privilegio.

---

## G-00b · El comportamiento de cada rol, contra el entorno

**Qué prueba.** La otra mitad de la pregunta. `verificar_accesos.py` responde *"¿qué privilegios
TIENE cada uno?"*; esta responde *"¿qué puede HACER?"*. Hacen falta las dos: un privilegio correcto
con un plugin que falla da un usuario bloqueado, y un plugin correcto con un privilegio de más da un
agujero.

**Por qué no alcanza con las pruebas de C#.** Las 800 pruebas usan un doble de
`IOrganizationService` que **no modela privilegios**: devuelve lo que se le pide, venga de quien
venga. Por eso ninguna vio el defecto del 2026-09-23 — los plugins leían la tabla Parametro con la
identidad de quien llamaba, y ningún rol de negocio tiene lectura ahí, así que **ninguna persona
podía transicionar una fila**. Eso solo se ve contra la plataforma y con un usuario de verdad.

**Cómo.**

```bash
python3 herramientas/pruebas/comportamiento_roles.py                   # 9 casos, NO escribe nada
python3 herramientas/pruebas/comportamiento_roles.py --con-escritura   # 16 casos, incluye el recorrido
```

Suplanta a cada usuario con la cabecera `MSCRMCallerID`, así que el plugin ve exactamente el mismo
contexto que si la persona hubiera entrado a la app. Sin `--con-escritura` solo corre los casos de
rechazo, donde el servidor frena antes de tocar el registro: **no deja rastro**, se puede correr
cuando sea. Con la bandera agrega el recorrido completo de dos filas de prueba (digitar → intentar
aprobar uno mismo → aprobar el supervisor; y digitar → devolver sin motivo → devolver con motivo).

**Esperado.** `0 fallas · 0 sin probar` en las dos modalidades.

Un caso `— sin probar` **no es un caso aprobado**: es un caso que no se pudo correr por falta de
datos (por ejemplo, ninguna Fila en Validada). Sale contado aparte justamente para que no se lea
como verde.

**Qué NO reemplaza.** Todo lo que sigue de G-01 en adelante: lo que la persona VE. La barra de
comandos, los íconos, el recorte del sitemap, las notificaciones y las columnas enmascaradas en
pantalla no se ven desde acá. Esto prueba las reglas; los casos de abajo prueban la experiencia.

---

## G-01 · El sitemap: 4 áreas y 13 entradas

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

## G-02 · Los íconos del sitemap

**Qué prueba.** Los 22 SVG de 12.1.

**Cómo.** Mirá el menú y la app.

**Esperado.** Cada entrada tiene **su** ícono (no el genérico), y la app tiene el suyo en la barra.
Los íconos se ven bien en **tema claro y oscuro** (usan `currentColor`).

---

## G-03 · Las 18 vistas existen y filtran

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

## G-04 · La cartera del ejecutivo (RF-19, D-13)

**Qué prueba.** Que **Mis clientes — por digitar** filtre por el propietario del Cliente.

**Cómo.**
1. Poné como propietario del Cliente `PR - Pruebas MPPP SA` a **otro** usuario.
2. Entrá como **Ejecutivo** (vos) y abrí **Por digitar**.

**Esperado.** Las filas de ese cliente **no aparecen** en *Mis clientes*, pero **sí** en
*Todos — por digitar*.

> Es comodidad, no seguridad: el ejecutivo **puede** ver todo si cambia de vista. Lo que prueba es
> que la vista por defecto le muestre su cartera.

---

## G-05 · Perfil de seguridad de columna

**Qué prueba.** 12 / P-06: identificación y cuenta son columnas protegidas.

**Cómo.** Entrá con el **Administrador de planes** (que NO está en el perfil) y abrí una Fila.

**Esperado.**

| Columna | Ejecutivo y Supervisor | Administrador de planes / técnico |
|---|---|---|
| `sanic_numeroidentificacion` | **ve el valor** | **ve `*******`** o el campo bloqueado |
| `sanic_numerocuenta` | **ve el valor** | **ve `*******`** |

**FALLA si** el Administrador de planes ve el número de cuenta. Es un dato bancario de una persona
real.

> **Bloqueante verificado el 2026-09-23.** Las dos columnas están protegidas de verdad
> (`IsSecured = true` en las dos), pero **`CSP - MPPP - Datos sensibles` no tiene ni un usuario ni
> un equipo asignado**. Hoy nadie lo alcanza salvo los System Administrator, que las leen por el
> perfil automático de la plataforma. Es decir: **el Ejecutivo y el Supervisor NO ven la
> identificación ni la cuenta**, que es justo lo que el ejecutivo tiene que digitar en AS400.
>
> No es un defecto de la solución: el perfil y sus permisos **viajan** en la solución (6.1), pero
> el grupo de Entra, el equipo de grupo y la asociación equipo ↔ perfil **no viajan** — son tarea de
> administración en cada entorno (inventario 13.7, `04` §4 D-8). Nunca se hizo en Dev.
>
> Hasta que se haga, G-05 da un falso positivo tranquilizador: el Administrador de planes no ve la
> cuenta… pero tampoco la ve nadie. La mitad derecha de la tabla pasa y la izquierda falla.

> Probalo también **en la vista**, no solo en el formulario: una columna protegida tiene que
> ocultarse en los dos lados.

---

## G-06 · Lo que cada rol NO puede

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

## G-07 · Cada rol entra donde debe

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

## G-08 · Los 9 formularios

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

## G-09 · La vista "Autorizaciones sin evidencia"

**Qué prueba.** D-42: la evidencia **no** condiciona la vigencia; es una lista de tareas del
administrador.

**Cómo.** Como Administrador de planes, abrí **Autorizaciones** y su vista *Sin evidencia*.

**Esperado.** Muestra las autorizaciones **sin** documento firmado — incluidas las que
`preparar_datos.py` creó.

**Y lo más importante**: esas autorizaciones **igual funcionan**. El caso C-01 pasó con
autorizaciones sin evidencia. Si en algún lado una autorización sin documento hace fallar
`AUTORIZACION_CORREO_PLAN`, es **FALLA** contra D-42.

---

## G-10 · La campana de notificaciones (DA-08)

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

## G-11 · Multiidioma de la app

**Qué prueba.** La convención: etiquetas en 1033 y en el idioma del cliente.

**Cómo.** Cambiá el idioma del usuario a inglés y recorré el sitemap y un par de formularios.

**Esperado.** Las etiquetas del sitemap, las vistas y las columnas cambian de idioma. Ninguna
queda con el texto del otro idioma ni con el nombre lógico crudo.

---

## G-12 · La app valida limpia

**Qué prueba.** Que la app no tenga componentes faltantes.

**Cómo.**

```bash
python3 herramientas/construir/app.py playbooks/app/mantenimientoppp.md --solo-verificar
```

**Esperado.** `"estado": "ya_existia"` con `11 tablas, 4 roles ... ValidateApp sin errores`.

---

## Resultados

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
