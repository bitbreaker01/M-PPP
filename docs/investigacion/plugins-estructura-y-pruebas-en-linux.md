# Plugins C#: estructura del proyecto y pruebas en Linux

Ensayo del 2026-09-21, en una carpeta descartable. Máquina: Linux, SDK de .NET 10.0.202, sin Windows ni Visual Studio.

## Lo comprobado

- Un proyecto de estilo SDK con `<TargetFramework>net462</TargetFramework>` **compila en Linux** si se le agrega el paquete `Microsoft.NETFramework.ReferenceAssemblies` (1.0.3). No hace falta Mono ni Windows.
- Un proyecto de pruebas **xunit en `net10.0`** puede referenciar ese ensamblado net462 y el SDK real (`Microsoft.CrmSdk.CoreAssemblies` 9.0.2.60). Corrieron en verde tres pruebas: una de dominio puro, y dos sobre un `IPlugin` real con `Entity`, `ParameterCollection`, `IPluginExecutionContext` implementado a mano e `InvalidPluginExecutionException`. **Sin FakeXrmEasy.**
- `dotnet test` restaura, compila y corre. Por decisión del aprobador (2026-09-21) cuenta como **correr pruebas**; `dotnet build`, `dotnet publish` y empaquetar no se hacen sin orden.

## Lo que dice Microsoft (Learn, verificado 2026-09-21)

- Un plugin **tiene que** apuntar a .NET Framework, de 4.6.2 a 4.8; .NET moderno solo vale para clientes del servicio web. https://learn.microsoft.com/power-apps/developer/data-platform/supported-customizations#support-for-net-framework-versions
- Todo proyecto cuyo ensamblado vaya en un paquete de plugins tiene que ser de **estilo SDK** con `net462`. https://learn.microsoft.com/power-apps/developer/data-platform/build-and-package#all-projects-must-use-the-sdk-style
- **Conviene usar paquete de plugins (ensamblados dependientes) desde el principio**: agregarlo después es mucho más difícil. Con paquete, **no hace falta firmar** los ensamblados. No se admite ILMerge. https://learn.microsoft.com/power-apps/developer/data-platform/build-and-package#dependent-assemblies
- `Microsoft.CrmSdk.CoreAssemblies` no se sube: ya está en el sandbox. **No depender de `System.Text.Json`** sin incluirlo explícitamente en el paquete: la versión del sandbox puede ser otra. (Afecta a `Plantilla/ConfiguracionPlantilla (JSON)` de `03` §8: hay que decidir con qué se lee el JSON.)
- El nombre y la versión de un paquete de plugins **no se pueden cambiar** una vez creado en el servidor.
- Una clase `IPlugin` se escribe **sin estado**: la plataforma cachea la instancia.

## Riesgo que queda abierto

Las pruebas corren sobre el runtime de .NET 10 y producción corre sobre .NET Framework 4.6.2. El comportamiento coincide en casi todo, pero no en todo (cultura en comparaciones y formato, expresiones regulares, y sobre todo la lectura del Excel). Mitigación: el código no depende de la cultura del hilo (siempre `CultureInfo.InvariantCulture` y comparaciones ordinales), y la pieza de lectura de Excel se prueba además dentro de Dataverse con archivos reales antes de darla por buena.
