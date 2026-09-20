# Orden de construcción: spike C-05, parte B (dentro de Dataverse)

## componente
Un paquete de plugin **descartable** con Open XML SDK como ensamblado dependiente, registrado en el entorno **Dev**, para responder si el lector de la plantilla puede correr dentro del sandbox de Dataverse. Es un spike: lo que vale es `CONCLUSIONES-B.md`. **Al terminar, Dev queda como estaba.**

## Preguntas que tiene que responder, con evidencia
1. **¿Open XML SDK 3.1.0 carga y funciona dentro del sandbox** como ensamblado dependiente de un paquete de plugin? En net462 el paquete se apoya en `WindowsBase` (ensamblado del framework) y en `System.IO.Packaging`: decir expresamente si el sandbox los resuelve. Es LA pregunta; si la respuesta es no, el resto no importa y se reporta de inmediato.
2. **¿Cuánto tarda de verdad** leer la plantilla real (25 filas) y una variante de 100 filas dentro del sandbox? Primera ejecución (en frío) y siguientes. El límite duro es 2 minutos; el objetivo de diseño es menos de 10 segundos.
3. **¿Cuánto pesa el paquete** `.nupkg` y lo acepta la plataforma?
4. **Atomicidad**: si el plugin de una Custom API crea registros y después lanza una excepción, ¿queda algo creado? (El diseño afirma que no: `diseno/03-contratos-custom-api.md` §1 paso 2.)
5. **Actor**: cuando el plugin de una Custom API hace un `Update` con el servicio de SYSTEM (`CreateOrganizationService(null)`), dentro del step PreOperation que dispara ese `Update`, ¿qué valen `UserId` e `InitiatingUserId`? El diseño necesita que `InitiatingUserId` siga siendo quien llamó a la API (`diseno/03` §4).
6. **Claves**: ¿una clave alternativa sobre una columna de texto distingue mayúsculas? (`ABC` y `abc`: ¿el segundo alta falla por duplicado?) La creación del índice de una clave es asíncrona y puede tardar; si en 10 minutos no está activa, reportarlo como **no concluyente** y seguir.

Fuera de alcance: el largo real de los Message-ID (no hay acceso al buzón), y cualquier cosa de la lógica de negocio.

## especificacion
- `diseno/01-convenciones.md` §5 (net462, prohibido usar APIs que no existan en net462) y §0 (publisher).
- `diseno/03-contratos-custom-api.md` §1 (atomicidad), §4 (actor) y §7 (lector: acá alcanza con abrir el libro, ubicar la hoja `Datos` y leer la ventana de filas; **no** hace falta implementar las reglas LP completas).
- Plantilla real: `datos/plantilla/Inclusiones_Exclusiones en PPP.xlsx` (26 KB). No la modifiques. El código de lectura de la parte A (`spikes/c05-parseo-excel/src/`) se puede reutilizar o simplificar.
- Para hacerle llegar el Excel al plugin en este spike alcanza con pasarlo en base64 como parámetro String de la Custom API. (En el producto se lee de una columna de archivo; no hace falta probarlo acá.)

## confianza_entradas
Confiable: el único archivo que se procesa es la plantilla del repositorio y variantes generadas por el propio spike.

## entorno
- Dev: `https://org36e60d9d.crm.dynamics.com/`. `verificador-entorno`: **ok** (2026-09-20): `pac` responde con `herramientas/pacx`, perfil `MPPP-DEV`; el Web API responde con `herramientas/dataverse_api.py`.
- Publisher: **`Sistemas_Abiertos_Nicaragua`** (prefijo `sanic`, prefijo de opciones `15946`). **Hay otro publisher con el mismo prefijo, "Sanic Corp" (unique name `sanic`): no usarlo nunca.** Buscar el publisher siempre por `uniquename`.

### Límites duros en el entorno (no negociables)
- Todo lo que crees va dentro de una solución **propia del spike**: `sanic_mppp_sol_zzspikec05` («SOL - MPPP - ZZ Spike C05»). Creala vos. **No toques `sanic_mppp_sol_mantenimientoppp`** (la solución del proyecto, hoy vacía) ni ninguna otra solución, tabla o componente que no hayas creado vos en esta orden.
- Todos los nombres de lo que crees llevan `zz`: tabla `sanic_mppp_tbl_zzspike`, Custom API `sanic_mppp_capi_zzspikec05`, paquete `sanic_mppp_pkg_zzspikec05`, etc. Minúsculas, según `01-convenciones.md`.
- **Nunca imprimas, registres ni escribas en ningún archivo el secreto ni el token.** No abras `local/pp_secrets.env` para leerlo: usá `herramientas/dataverse_api.py` (como librería o como comando) y `herramientas/pacx`. Todo `pac` va por `herramientas/pacx` (trae `timeout`); `pac` a secas **se cuelga para siempre** en esta máquina.
- No borres nada que no hayas creado. No importes soluciones managed. No cambies configuración del entorno ni privilegios de usuarios.
- **Limpieza obligatoria al final**, pase lo que pase: borrar steps, Custom API y sus parámetros, el paquete de plugin (y su ensamblado y tipos), la tabla, y por último la solución del spike. Verificar con consultas que no quedó nada con `zz` ni la solución. Si algo no se deja borrar, decirlo con el nombre exacto.
- Tope de intentos: si registrar el paquete falla **cinco veces** por causas distintas, parar, limpiar y reportar `parcial` con los errores textuales. Un "no se puede" bien documentado es un resultado válido del spike.

### Pistas (no verificadas: comprobalas)
- Un paquete de plugin con dependencias es un `.nupkg`. `herramientas/pacx plugin init --outputDirectory <dir> --author "Sistemas Abiertos Nicaragua"` genera un proyecto preparado para eso; hay que agregarle `DocumentFormat.OpenXml` 3.1.0. En Linux, compilar `net462` requiere el paquete `Microsoft.NETFramework.ReferenceAssemblies` (la parte A ya lo hace).
- El primer registro de un paquete se puede hacer por Web API creando un registro `pluginpackages` con `name`, `uniquename`, `version` y `content` (el `.nupkg` en base64), con la cabecera de solución; la plataforma crea el `pluginassembly` y los `plugintypes`. Después: `customapis` con `PluginTypeId@odata.bind`, sus parámetros, y un `sdkmessageprocessingsteps` para el step de `Update` de la tabla del spike.
- El usuario con el que corre todo es un usuario de aplicación; para la pregunta 5 él es "quien llamó a la API".
- La cabecera `MSCRM.SolutionUniqueName` mete lo creado en la solución; `dataverse_api.py` la pone con el argumento `solucion=`.

## referencias
De `power-platform-construir`: `references/dataverse/patrones.md`, `references/dataverse/alm.md` y `references/dataverse/errores-frecuentes.md`. Ya se sabe que **no cubren** ensamblados dependientes ni Open XML SDK: no lo reportes de nuevo como hallazgo; sí anotá como tropiezo candidato todo lo que aprendas del registro de paquetes, con los comandos o llamadas exactas que funcionaron.

## destino
Solo dentro de `spikes/c05-parseo-excel/parte-b/` (código, scripts de registro, de medición y de limpieza) y `spikes/c05-parseo-excel/CONCLUSIONES-B.md`. Nada de binarios ni `.nupkg` versionados.

## modo_tdd
No aplica: es un spike de integración contra un entorno. Sí aplica reportar con salida real.

## verificacion
1. Un script `parte-b/medir.py` que invoque la Custom API en cada modo y muestre los resultados; pegá su salida real.
2. Un script `parte-b/limpiar.py` y, después de correrlo, esta comprobación con salida real, que tiene que dar todo vacío:
```
python3 herramientas/dataverse_api.py GET "solutions?$select=uniquename&$filter=contains(uniquename,'zzspike')"
python3 herramientas/dataverse_api.py GET "customapis?$select=uniquename&$filter=contains(uniquename,'zz')"
python3 herramientas/dataverse_api.py GET "pluginpackages?$select=uniquename&$filter=contains(uniquename,'zz')"
python3 herramientas/dataverse_api.py GET "EntityDefinitions?$select=LogicalName&$filter=LogicalName eq 'sanic_mppp_tbl_zzspike'"
```

## Qué debe decir CONCLUSIONES-B.md
Respuesta a las 6 preguntas, cada una con su evidencia (salida real, números, mensajes de error textuales). La receta exacta que funcionó para compilar, empaquetar y registrar un paquete de plugin con dependencias desde Linux, paso a paso, para que el producto la reutilice. Qué quedó no concluyente y por qué. Confirmación de la limpieza.
