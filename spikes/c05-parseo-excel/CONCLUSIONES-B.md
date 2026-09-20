# Spike C-05, parte B — Conclusiones (dentro de Dataverse)

Alcance: un paquete de plugin descartable con Open XML SDK 3.1.0 como ensamblado
dependiente, registrado y ejecutado de verdad contra el entorno Dev
(`https://org36e60d9d.crm.dynamics.com/`, publisher `Sistemas_Abiertos_Nicaragua`, prefijo
`sanic`). Todo lo creado vivió dentro de la solución propia del spike
`sanic_mppp_sol_zzspikec05` y llevaba `zz` en el nombre; se borró todo al terminar (ver
"Limpieza" al final). Código y scripts: `spikes/c05-parseo-excel/parte-b/`.

## 1. ¿Open XML SDK 3.1.0 carga y funciona dentro del sandbox como ensamblado dependiente?

**Sí.** Es la pregunta que decidía el resto del spike, y la respuesta es afirmativa con
evidencia directa: el paquete `sanic_mppp_pkg_zzspikec05` (net462, `DocumentFormat.OpenXml`
3.1.0 + `DocumentFormat.OpenXml.Framework` 3.1.0 como dependencias) se registró en Dev sin
error, y su plugin `SpikeApi` (modo `lector`) abrió la plantilla real con
`SpreadsheetDocument.Open`, ubicó la hoja `Datos` y leyó filas reales, devolviendo resultados
correctos en **todas** las corridas (ninguna `TypeLoadException`, `FileNotFoundException` ni
`MissingMethodException` — los errores típicos de un ensamblado que el sandbox no puede
resolver).

Salida real (`medir.py`, sección "Preguntas 1 y 2"):

```
corrida 0 (fria): lector OK: 25 filas leidas desde 'Datos' (fila 13 en adelante), 275 celdas tocadas -- 8 ms
corrida 1 (caliente): lector OK: 25 filas leidas desde 'Datos' (fila 13 en adelante), 275 celdas tocadas -- 10 ms
corrida 2 (caliente): lector OK: 25 filas leidas desde 'Datos' (fila 13 en adelante), 275 celdas tocadas -- 19 ms
corrida 3 (caliente): lector OK: 25 filas leidas desde 'Datos' (fila 13 en adelante), 275 celdas tocadas -- 20 ms
```

`WindowsBase` y `System.IO.Packaging` (de los que depende Open XML SDK en net462, ambos
ensamblados del framework, no paquetes NuGet) **se resolvieron sin declarar nada especial**:
no hicieron falta como dependencias explícitas del paquete — el sandbox los trae del GAC/del
framework host. `System.IO.Compression` sí necesitó la referencia explícita
`<Reference Include="System.IO.Compression" />` en el `.csproj` (igual que en la parte A),
pero eso es un detalle del build en Linux, no del runtime del sandbox.

**Corolario para el producto**: el diseño puede seguir con Open XML SDK como ensamblado
dependiente de `Sanic.Mppp.Plugins` (`01-convenciones.md` §5) sin riesgo de que el sandbox lo
rechace.

## 2. Tiempo de lectura: plantilla real (25 filas) y variante de 100 filas

**Muy por debajo del objetivo de diseño (<10 s) y del límite duro (2 min).**

| Variante | Corridas (ms) |
|---|---|
| Plantilla real, ventana de 25 filas (fila 13 en adelante) | 8, 10, 19, 20 |
| Variante sintética, ventana de 100 filas | 15, 10, 15, 13 |

No se observó una corrida "fría" claramente más lenta como en la parte A (local): la primera
invocación del spike sobre el paquete recién registrado sí tardó más (~982 ms, ver nota más
abajo), pero para cuando corrió `medir.py` el ensamblado ya estaba caliente en el sandbox de
Dev y las cuatro corridas de 25 filas dieron 8-20 ms. La única corrida realmente fría medida en
esta sesión (la primera llamada después de registrar el paquete) fue:

```
1er llamado tras registrar el paquete: 200, "lector OK: 25 filas leidas...", 982 ms
```

**Nota de diseño de este experimento**: la primera versión de `SpikeApi` no acotaba la
lectura a una ventana — recorría **todas** las filas con formato de la plantilla real (505
filas de `<row>`, no solo las 25 útiles: la plantilla distribuible trae formato hasta bien
más allá de la fila 37, aunque esté en blanco). Esa primera corrida dio 493 filas leídas en
vez de 25, contradiciendo la pregunta tal como está planteada ("leer la plantilla real, 25
filas"). Se corrigió agregando un parámetro `cantidadfilas` a la Custom API para que el
lector respete una ventana explícita (`PrimeraFila=13` fijo en código, `cantidadfilas`
configurable) — el mismo espíritu de LP-04 de `diseno/03` §7, aplicado aquí de forma mínima.
Esto es evidencia adicional, ya conocida de la parte A pero reconfirmada acá: **sin ventana
explícita, "leer la plantilla" y "recorrer todo el archivo con formato" son cosas muy
distintas**, y la plantilla real tiene mucho más contenido formateado del que tiene datos.

**Presupuesto de tiempo real de `ValidarSolicitud` (BP-PP-053)**: esto solo mide el parseo del
Excel dentro del sandbox, igual que la parte A medía el parseo local. Sigue faltando medir con
Plugin Profiler el pipeline completo (reglas de negocio incluidas) — no cambia por este spike.

## 3. Peso del paquete `.nupkg` y aceptación de la plataforma

**Aceptado sin problema.**

```
sanic_mppp_pkg_zzspikec05.1.0.0.nupkg: 1757.0 KB comprimido
  lib/net462/DocumentFormat.OpenXml.Framework.dll: 0.45 MB sin comprimir
  lib/net462/DocumentFormat.OpenXml.dll: 6.06 MB sin comprimir
  lib/net462/Sanic.Mppp.Plugins.Zzspikec05.dll: 0.02 MB sin comprimir
  TOTAL lib/ sin comprimir: 6.53 MB
```

Coincide con lo medido en la parte A (6.51 MB de `DocumentFormat.OpenXml*` para net462). El
`.nupkg` completo (comprimido, que es lo que efectivamente viaja como `content` en base64 al
Web API) pesa **1.72 MB**. Se registró — y más tarde se actualizó con `PATCH` — sin ningún
error de tamaño ni de la plataforma. No se encontró (ni hizo falta buscar) el límite exacto:
1.72 MB entra cómodo, y no hay indicio de estar cerca de un tope.

## 4. Atomicidad: ¿queda algo creado si la Custom API crea registros y después excepciona?

**No queda nada. Confirmado — coincide con lo que afirma `diseno/03-contratos-custom-api.md`
§1 paso 2.**

El plugin (modo `atomicidad`) crea un registro marcador en `sanic_mppp_tbl_zzspike` y, sin
capturar la excepción, la relanza deliberadamente. Salida real:

```
llamada: 400 {'error': "SPIKE atomicidad: excepcion deliberada tras crear el marcador
'zzatomicidad-aaccc897e3ca' (id 4d2fc5fc-0bb5-f111-aaad-000d3a350099). Si la transaccion es
atomica, este registro NO debe persistir."}
consulta post-excepcion del marcador 'zzatomicidad-aaccc897e3ca': 200 []
```

El `Create` reportó un id real (`4d2fc5fc-...`), pero la consulta posterior por ese mismo
nombre devuelve `[]`: el registro **no** quedó en la base. La Custom API corre dentro de la
transacción de Dataverse y una excepción sin capturar revierte todo lo hecho en esa
invocación, tal como asume el diseño. No hace falta ningún borrado de limpieza propio en el
producto para este camino.

## 5. Actor: `UserId` e `InitiatingUserId` en un `Update` anidado con el servicio de SYSTEM

**No se conserva. Esto contradice el supuesto de `diseno/03-contratos-custom-api.md` §4, y
confirma que hace falta el mecanismo de respaldo que el propio diseño ya anticipaba
(`SharedVariables`).**

Secuencia: se creó un registro de prueba directo (fuera del plugin), se llamó a la Custom API
en modo `actor` con ese id, la Custom API hizo
`serviceFactory.CreateOrganizationService(null)` (SYSTEM) y un `Update` sobre el registro; el
step `ActorCaptureStep` (PreOperation de `Update`, filtrado por `sanic_clave`) anotó
`context.UserId` y `context.InitiatingUserId` en el propio registro. Salida real (dos
corridas independientes, mismo resultado):

```
usuario de aplicacion que llama (WhoAmI): ffc778df-d287-f111-8075-70a8a5af5a32
capturado por el step: UserId=fc1957c4-d896-4ad5-b165-2814799fdd23;InitiatingUserId=fc1957c4-d896-4ad5-b165-2814799fdd23;Depth=2;MessageName=Update
quien es UserId (fc1957c4-d896-4ad5-b165-2814799fdd23): SYSTEM (isdisabled=True)
```

`CreateOrganizationService(null)` sí ejecuta como **SYSTEM** (confirmado contra
`systemusers`: `fullname = "SYSTEM"`, deshabilitado, sin `domainname` — el usuario de sistema
estándar de Dataverse). Pero dentro del `Update` anidado que ese servicio dispara,
**`InitiatingUserId` no vale el usuario de aplicación original que llamó a la Custom API**
(`ffc778df-...`): vale **lo mismo que `UserId`**, es decir, también SYSTEM. El pipeline
anidado no hereda quién inició la cadena externa; se reinicia con el actor del servicio que
disparó *esa* operación puntual.

**Impacto en el diseño**: `diseno/03` §4 dice "en ese `Update` anidado, `UserId` es SYSTEM
pero `InitiatingUserId` sigue siendo quien originó la llamada" y agrega textualmente "A
confirmar en la parte B del spike que `InitiatingUserId` se conserva en el pipeline anidado;
si no se conservara, la API le pasa el actor al step por `SharedVariables`". Este spike
confirma que **no se conserva** — y, como amplía la pregunta 5 bis más abajo, el mecanismo de
respaldo que el propio diseño proponía (`SharedVariables`) **tampoco funcionó** en las
pruebas. Esto es un cambio de diseño necesario en `diseno/03` §4, no un detalle de
implementación — se reporta como hallazgo, no se corrige acá (fuera del alcance del
constructor). Ver "Pregunta 5 bis" para la evidencia completa y la recomendación.

## Pregunta 5 bis: cómo identificar al actor de forma no falsificable

Ampliación pedida tras confirmar que el "plan A" (confiar en `InitiatingUserId` dentro del
`Update` anidado) falla. Se probaron dos hipótesis de "plan B" — la cadena de
`context.ParentContext` y `SharedVariables` — más una variante de control y una prueba de no
falsificación. Mismo mecanismo de captura que la pregunta 5: `ActorCaptureStep` (PreOperation
de `Update`, filtro `sanic_clave`) ahora recorre `context.ParentContext` hasta `null` y busca
la clave `"zz_actor"` en `SharedVariables` propio y de cada nivel padre, y lo deja todo en
`sanic_actordetalle` (columna `Memo` nueva) además del resumen en `sanic_actorcapturado`.
GUIDs abreviados a 8 caracteres: **`ffc778df`** = usuario de aplicación que llama (WhoAmI);
**`fc1957c4`** = SYSTEM (confirmado contra `systemusers`: `fullname = "SYSTEM"`, deshabilitado).

| Caso | Cómo se hizo el `Update` | `Depth` | `context.UserId` propio | `context.InitiatingUserId` propio | `ParentContext` | `zz_actor` en `SharedVariables` |
|---|---|---|---|---|---|---|
| 1. `modo=actor` (SYSTEM) | `CreateOrganizationService(null)` desde dentro de la Custom API | 2 | `fc1957c4` (SYSTEM) | `fc1957c4` (SYSTEM) — **no** `ffc778df` | 2 niveles: nivel 0 = mismo `Update`, `Stage=30`, `UserId`/`InitiatingUserId` = `fc1957c4` (SYSTEM); nivel 1 = `MessageName=sanic_mppp_capi_zzspikec05`, `Depth=1`, `UserId=ffc778df` (correcto) pero **`InitiatingUserId=fc1957c4`** (SYSTEM, incorrecto: debería ser `ffc778df`) | No aparece en ningún nivel |
| 4. `modo=actorusuario` (control, sin SYSTEM) | `CreateOrganizationService(context.UserId)` (el mismo usuario que llama) | 2 | `ffc778df` | `ffc778df` | 2 niveles, los tres (propio + 2 padres) con `UserId=InitiatingUserId=ffc778df`, consistente de punta a punta | No aparece en ningún nivel |
| 5. `Update` directo por Web API (sin Custom API) | `PATCH` directo a la fila, sin pasar por `sanic_mppp_capi_zzspikec05` | 1 | `ffc778df` (real, no falsificado) | `ffc778df` (real, no falsificado) | 2 niveles (`Update`→`Upsert`, mecánica interna del Web API), `MessageName` **nunca** menciona la Custom API — la ausencia de la API en la cadena es una señal correcta, pero no alcanza para identificar al actor cuando sí pasa por SYSTEM (ver caso 1) | No aplica: mandar `"SharedVariables": {...}` en el cuerpo da `400` (no es una propiedad real de la entidad); y el intento de pisar `sanic_actorcapturado` con un valor inventado ("YO SOY SYSTEM, CONFIEN EN MI") fue **sobrescrito por el step**, que solo escribe lo que lee de `context`, nunca lo que trae el `Target` de entrada |

**Lectura de la tabla**:

- **Punto 2 (`ParentContext`) falla**: la hipótesis era que algún nivel de `ParentContext`
  tuviera `MessageName = sanic_mppp_capi_zzspikec05` con su `InitiatingUserId` correcto. Esa
  entrada existe (nivel 1, caso 1) y el `MessageName` sí es el esperado, pero su
  `InitiatingUserId` **también quedó contaminado por SYSTEM** — comparando contra el caso de
  control (4), donde ese mismo nivel muestra `ffc778df` correctamente, la contaminación es
  atribuible específicamente a que **algún** punto de la cadena usó `CreateOrganizationService`
  con una identidad distinta (SYSTEM), no a un límite de profundidad ni al número de niveles.
- **Punto 3 (`SharedVariables`) falla, en los dos casos, no solo con SYSTEM**: la clave
  `"zz_actor"`, puesta en `context.SharedVariables` del contexto de la Custom API **antes**
  del `Update` (con o sin SYSTEM), no aparece en el `SharedVariables` propio del step ni en el
  de ningún nivel de su `ParentContext`. La propagación de `SharedVariables` documentada para
  varios steps del *mismo* mensaje no se sostuvo para un `Update` disparado dentro del plugin
  de una Custom API distinta — al menos no accediendo por `ParentContext` como se probó acá.
- **Punto 4 (control) aísla la causa**: sin SYSTEM, todo es consistente y correcto en todos
  los niveles. La corrupción del punto 2 aparece **solo** cuando el servicio usado para el
  `Update` anidado es SYSTEM, no es un problema general de anidamiento.
- **Punto 5 (no falsificación) se cumple, pero por un motivo distinto al esperado**: un
  cliente externo no puede fabricar `SharedVariables` (ni existe como propiedad del Web API) ni
  puede hacer que el step reporte algo distinto de lo que el propio `context` trae (el step
  nunca lee el `Target` entrante para esos datos, siempre calcula desde `context`). Pero eso
  solo prueba que **el step no puede ser engañado sobre quién ejecutó *ese* `Update`
  puntual** — no prueba que pueda distinguir, dentro de un `Update` ejecutado por SYSTEM, a
  qué usuario de aplicación representa. Ahí es donde siguen fallando los puntos 2 y 3.

**Ninguna de las dos vías propuestas por el diseño (`ParentContext` ni `SharedVariables`)
funciona una vez que el `Update` anidado corre con el servicio de SYSTEM.** Esto es un
resultado válido y cambia la arquitectura: `diseno/03-contratos-custom-api.md` §4 no puede
apoyarse en ninguna de las dos para que el step de transición conozca al actor real.

**Recomendación (una línea)**: el step del producto no debe leer identidad alguna del
`Update` anidado (ni `InitiatingUserId`, ni `ParentContext`, ni `SharedVariables`, todos
poco fiables una vez que interviene SYSTEM) — la Custom API tiene que capturar
`context.InitiatingUserId` en su **propio** contexto, antes de elevar a SYSTEM (ahí es
correcto y no falsificable, confirmado en el caso de control), y pasarlo como un **atributo
común del `Target`** del `Update` que ella misma arma (no como `SharedVariables`): los
atributos del `Target` sí llegaron siempre correctamente al step en las docenas de llamadas de
este spike (es el mecanismo estándar de entrega de datos de un plugin, no uno frágil como
`SharedVariables`/`ParentContext`), y ese atributo tiene que quedar fuera de la lista blanca de
columnas que un humano puede tocar directamente (`diseno/03` §5, "Lista blanca de columnas")
para que solo el camino elevado por SYSTEM pueda poblarlo. **Esta combinación (atributo en el
`Target` + exclusión de la lista blanca) no se construyó ni se probó en este spike** — es una
recomendación razonada a partir de la evidencia reunida, no un resultado verificado; queda
como el siguiente experimento si se necesita confirmarla antes de llevarla al diseño.

## 6. Clave alternativa sobre columna de texto: ¿distingue mayúsculas?

**No distingue.** El índice de `sanic_mppp_key_zzspike_clave` (sobre la columna de texto
`sanic_clave`) quedó **activo en menos de un minuto** (mucho antes del margen de 10 minutos
que preveía la orden — nada de "no concluyente" hizo falta). Con el índice activo:

```
alta con 'ZZABC896eb1e6': 204
alta con 'zzabc896eb1e6': 412 {'error': 'Entity Key KEY - MPPP - ZZ Spike C05 - Clave
violated. A record with the same value for Clave already exists. A duplicate record cannot
be created. Select one or more unique values and try again.'}
```

El segundo alta (mismo texto, minúsculas) fue rechazado por duplicado. Una clave alternativa
sobre una columna `String` estándar de Dataverse es **case-insensitive**: `ABC` y `abc`
colisionan. Cualquier clave de negocio del producto que dependa de distinguir mayúsculas
(no es el caso conocido de `02-diccionario-datos.md`, pero vale como advertencia general) no
puede apoyarse en una clave alternativa nativa sin normalizar antes.

## La receta que funcionó: compilar, empaquetar y registrar un paquete de plugin con
## dependencias desde Linux, paso a paso

Para que el producto la reutilice al construir `Sanic.Mppp.Plugins` de verdad.

### 1. Scaffolding

```bash
herramientas/pacx plugin init --outputDirectory <dir> --author "Sistemas Abiertos Nicaragua"
```

Genera `<dir>.csproj` (o el nombre del directorio), un `.snk` nuevo (nunca se versiona), y
`PluginBase.cs` / `Plugin1.cs` con el patrón `PluginBase : IPlugin` +
`ExecuteDataversePlugin(ILocalPluginContext)`. El namespace que genera es literalmente el
nombre del directorio pasado a `--outputDirectory`: si tiene guiones no compila (un namespace
de C# no admite `-`) — usar un nombre de directorio sin guiones, o renombrar el namespace
después a mano (lo segundo es lo que se hizo acá: `plugin/` scaffoldeado, renombrado a
`Sanic.Mppp.Plugins.Zzspikec05` en el `.csproj` y en los `.cs`).

### 2. Agregar la dependencia

En el `.csproj` generado (target `net462`, ya trae `Microsoft.CrmSdk.CoreAssemblies`,
`Microsoft.PowerApps.MSBuild.Plugin` y `Microsoft.NETFramework.ReferenceAssemblies`):

```xml
<PackageReference Include="DocumentFormat.OpenXml" Version="3.1.0" />
<Reference Include="System.IO.Compression" />
```

`Microsoft.PowerApps.MSBuild.Plugin` es la pieza clave: sus targets de MSBuild son los que
convierten el build en un `.nupkg` con `lib/net462/*.dll` incluyendo **todas** las
dependencias del proyecto (no solo el ensamblado propio) — es justamente el mecanismo de
"paquete de plugin con ensamblados dependientes".

### 3. Build

```bash
dotnet restore
dotnet build -c Release
```

Esto compila **y empaqueta** en un solo paso: además del `.dll` en
`bin/Release/net462/`, deja el `.nupkg` listo en `bin/Release/<PackageId>.<Version>.nupkg`.
**Tropiezo candidato**: tras cambiar el código (agregar un parámetro), `dotnet build`
recompiló el `.dll` (timestamp nuevo) pero **no regeneró el `.nupkg`** (quedó con el
timestamp viejo) — no cubierto por `references/dataverse/alm.md` ni `patrones.md`. Hubo que
borrar el `.nupkg` a mano (`rm bin/Release/*.nupkg`) y volver a `dotnet build` para que lo
regenerara. No se investigó la causa exacta (probablemente un target de MSBuild con
`Inputs`/`Outputs` mal calculados para el pack incremental); el workaround (borrar y
rebuildear) es confiable y barato.

### 4. Primer registro del paquete (Web API)

```
POST pluginpackages
Content-Type: application/json
MSCRM.SolutionUniqueName: <solucion>

{
  "name": "<uniquename>",
  "uniquename": "<uniquename>",
  "version": "1.0.0.0",
  "content": "<base64 del .nupkg>"
}
```

Al crear el `pluginpackage`, Dataverse **auto-descubre y crea** el `pluginassembly` y un
`plugintype` por cada clase que implementa `IPlugin` en el ensamblado — no hace falta
crearlos a mano ni declararlos en el `.nuspec`. Confirmado con los dos tipos del spike
(`Sanic.Mppp.Plugins.Zzspikec05.SpikeApi` y `...ActorCaptureStep`), ambos aparecieron en
`plugintypes` inmediatos después del `POST`.

### 5. Actualizar el contenido de un paquete ya registrado

```
PATCH pluginpackages(<id>)
{ "content": "<base64 del .nupkg nuevo>" }
```

Funciona **sin** cambiar la versión (se probó dejando `1.0.0.0` igual): el `PATCH` se aceptó,
y los `plugintypeid` de los tipos ya registrados **se mantuvieron estables** (mismo GUID antes
y después de actualizar el contenido) — importante porque el step y la Custom API ya estaban
enlazados a esos ids y no hubo que re-enlazar nada. No verificado: si esto sigue siendo cierto
si se **agrega o quita** un tipo `IPlugin` entre una versión y otra del contenido.

### 6. Enlazar la Custom API a su plugin type

```
PATCH customapis(<id>)
{ "PluginTypeId@odata.bind": "/plugintypes(<id>)" }
```

**Tropiezo candidato**: la propiedad de navegación es `PluginTypeId` (con esa capitalización
exacta) — probar `plugintypeid@odata.bind` (todo minúscula, como el nombre del atributo lógico
sugeriría) da `400`. Se confirmó consultando
`EntityDefinitions(LogicalName='customapi')/ManyToOneRelationships` y leyendo
`ReferencingEntityNavigationPropertyName`. No cubierto por `patrones.md` ni por
`references/dataverse/alm.md`.

### 7. Parámetros de la Custom API

```
POST customapirequestparameters
{
  "uniquename": "...", "name": "...", "displayname": "...",
  "type": 10,
  "isoptional": true,
  "CustomAPIId@odata.bind": "/customapis(<id>)"
}
```

Dos tropiezos candidatos más, ninguno cubierto por las referencias indicadas:

- **`type` es un entero (choice `CustomAPIFieldType`), no un string.** Enviar `"String"` da
  `400` con un error de OData bastante oscuro ("Cannot convert the literal 'String' to the
  expected type 'Edm.Int32'"). Los valores verificados contra el propio metadata de Dev:
  `0=Boolean, 1=DateTime, 2=Decimal, 3=Entity, 4=EntityCollection, 5=EntityReference,
  6=Float, 7=Integer, 8=Money, 9=Picklist, 10=String, 11=StringArray, 12=Guid`.
- **El binding al padre es `CustomAPIId@odata.bind`** (mismo patrón que el punto 6), no
  `customapiid@odata.bind`. Mismo error genérico de OData ("undeclared property... no
  property value") si se usa la capitalización equivocada.

Lo mismo aplica a `customapiresponseproperties` (mismo `type` entero, mismo
`CustomAPIId@odata.bind`).

### 8. Step de plugin (Update, PreOperation)

```
POST sdkmessageprocessingsteps
{
  "name": "...",
  "sdkmessageid@odata.bind": "/sdkmessages(<guid de Update>)",
  "sdkmessagefilterid@odata.bind": "/sdkmessagefilters(<guid del filtro Update+tabla>)",
  "eventhandler_plugintype@odata.bind": "/plugintypes(<id>)",
  "stage": 20,
  "mode": 0,
  "rank": 1,
  "filteringattributes": "sanic_clave"
}
```

**Tropiezo candidato**: el binding al plugin type del step **no** es
`plugintypeid@odata.bind` (esa propiedad de navegación existe en el metadata pero no es la
que hay que usar) sino **`eventhandler_plugintype@odata.bind`** — el atributo real que
Dataverse usa para el "manejador de evento" del step es `eventhandler` (un lookup
polimórfico a `plugintype` o `serviceendpoint`), y `eventhandler_plugintype` es su variante
de navegación específica para plugin types. No cubierto por `patrones.md` ni por
`references/dataverse/alm.md`. El `sdkmessagefilterid` correcto se obtiene filtrando
`sdkmessagefilters` por `primaryobjecttypecode eq '<tabla>'` y expandiendo `sdkmessageid` para
encontrar el que tiene `name eq 'Update'`.

## Qué quedó no concluyente

Nada de las 6 preguntas originales ni de la pregunta 5 bis. El único punto que la orden
marcaba como potencialmente no concluyente (el índice de la clave alternativa tardando hasta
10 minutos en activarse) se resolvió en menos de un minuto. La pregunta 5 bis sí tiene un
resultado negativo (ninguna de las dos vías propuestas funciona), pero negativo con evidencia
no es lo mismo que no concluyente: quedó perfectamente determinado qué no funciona y por qué.

## Limpieza

`parte-b/limpiar.py` borra, en orden de dependencia: steps de plugin con "zz" en el nombre,
parámetros y Custom APIs con "zz", plugin types y plugin packages con "Zzspikec05"/"zz",
claves alternativas y la tabla `sanic_mppp_tbl_zzspike`, y por último la solución
`sanic_mppp_sol_zzspikec05`. Es idempotente (tolera que algo ya no exista) y termina con la
misma comprobación de cuatro consultas que pide la orden. Se registró y limpió el entorno
**dos veces** en este spike: una para las preguntas 1 a 6 originales, y una segunda vuelta
completa (mismos scripts, nuevos GUIDs) para la pregunta 5 bis, agregada después de una
comprobación independiente de que la primera limpieza había dejado Dev limpio.

Corrida final real (segunda vuelta, la que deja Dev en el estado con el que se cierra este
documento):

```
-- Steps de plugin (sdkmessageprocessingsteps) --
  [FALLO] CustomApi 'sanic_mppp_capi_zzspikec05' implementation (ae84722e-...): 400 Invalid
  plug-in registration stage. Steps can only be modified in stages
  BeforeMainOperationOutsideTransaction, BeforeMainOperationInsideTransaction,
  AfterMainOperationInsideTransaction and AfterMainOperationOutsideTransaction.
  OK borrado: STEP - MPPP - zzspike - Update - PreOperation (859b4635-...)
-- Custom APIs (parametros + custom api) --
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiip.modo (61449618-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiip.excelbase64 (cd6e821f-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiip.zzspikeid (d36e821f-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiip.cantidadfilas (d96e821f-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiop.resultado (df6e821f-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.capiop.milisegundos (e56e821f-...)
  OK borrado: sanic_mppp_capi_zzspikec05 (51449618-...)
-- Plugin types y plugin packages (y sus plugin assemblies) --
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.ActorCaptureStep (73dcdb25-...)
  OK borrado: Sanic.Mppp.Plugins.Zzspikec05.SpikeApi (74dcdb25-...)
  [FALLO] Sanic.Mppp.Plugins.Zzspikec05 (72dcdb25-...): 400 Unable to delete plug-in assembly
  as it is part of plugin package
  OK borrado: sanic_mppp_pkg_zzspikec05 (70dcdb25-...)
-- Claves alternativas y tabla sanic_mppp_tbl_zzspike --
  OK borrada clave: sanic_mppp_key_zzspike_clave
  OK borrada tabla: sanic_mppp_tbl_zzspike
-- Solucion sanic_mppp_sol_zzspikec05 --
  OK borrado: sanic_mppp_sol_zzspikec05 (87a2f308-...)

=== Comprobacion final (todo debe dar vacio) ===
solutions: 200 []
customapis: 200 []
pluginpackages: 200 []
EntityDefinitions (sanic_mppp_tbl_zzspike): 200 []

LIMPIEZA COMPLETA Y VERIFICADA
```

Repetido aparte, después de `limpiar.py`, con las 4 consultas exactas de la orden (una por
una, no por el script): las cuatro devolvieron `"value": []`. `sanic_mppp_sol_mantenimientoppp`
se volvió a comprobar y sigue intacta (no se tocó en esta segunda vuelta tampoco).

Los dos `[FALLO]` son esperables y no dejan nada huérfano, confirmado por la comprobación
final: el step "implementation" es uno que Dataverse genera solo para la propia Custom API
(no se puede borrar a mano en la etapa "main operation" — se borra solo al borrar la Custom
API, que es el paso siguiente); el `pluginassembly` no se puede borrar directo porque
pertenece a un `pluginpackage` — se borra solo al borrar el `pluginpackage`, que también es
el paso siguiente. `limpiar.py` devuelve código de salida 1 por esos dos intentos
individuales aunque el estado final ya esté limpio; **quedó como tropiezo candidato para
`limpiar.py`**: no reintentar borrar assembly/step "implementation" a mano, confiar en el
borrado en cascada del paquete/Custom API.

Además, se repitió la comprobación de las 4 consultas exactas de la orden por separado,
después de correr `limpiar.py`, con el mismo resultado (`"value": []`) en las cuatro, y se
confirmó que `sanic_mppp_sol_mantenimientoppp` sigue existiendo intacta
(`version: "1.0.0.0"`, sin cambios).

**Confirmado: no queda ningún componente con "zz" en el nombre, ni la solución del spike, en
Dev.** `sanic_mppp_sol_mantenimientoppp` y el resto del entorno no se tocaron en ningún
momento de este spike (todas las llamadas que crearon o modificaron algo llevaron
`MSCRM.SolutionUniqueName: sanic_mppp_sol_zzspikec05`, o apuntaron a componentes ya
identificados como propios del spike).
