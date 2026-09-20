# Licencias de componentes de terceros

Qué software de terceros se distribuye dentro de la solución, bajo qué licencia, y qué obliga. Se actualiza cada vez que se agrega una dependencia al paquete de plugins o a la herramienta de histórico. **Una dependencia no entra al producto sin su fila acá.**

## Dentro del paquete de plugins (`sanic_mppp_pkg_plugins`)

| Componente | Versión | Autor | Licencia | Fuente de la verificación |
|---|---|---|---|---|
| `DocumentFormat.OpenXml` (Open XML SDK) | 3.1.0 | Microsoft | **MIT** | Metadatos del propio paquete NuGet (`<license type="expression">MIT</license>`), firmado por Microsoft; y archivo `LICENSE` del repositorio oficial `github.com/dotnet/Open-XML-SDK` ("The MIT License (MIT) — Copyright (c) .NET Foundation and Contributors"). Verificado el 2026-09-20. |
| `DocumentFormat.OpenXml.Framework` | 3.1.0 | Microsoft | **MIT** | Ídem. Es dependencia del anterior. |
| `System.IO.Packaging` | 8.0.0 | Microsoft | **MIT** | Ídem; repositorio `github.com/dotnet/runtime`. Es dependencia del anterior. El paquete trae sus `LICENSE.TXT` y `THIRD-PARTY-NOTICES.TXT`. |

## Qué permite y qué obliga la licencia MIT

- **Permite el uso comercial, sin pago de licencia, regalías ni registro**, en una empresa de cualquier tamaño y rubro, banco incluido. Permite además modificar y redistribuir.
- **No exige publicar el código propio**: no es una licencia copyleft. El código de BAC que usa la librería sigue siendo de BAC.
- **Única obligación**: conservar el aviso de copyright y el texto de la licencia en las copias que se distribuyan. Se cumple incluyendo los archivos de licencia de estos paquetes junto al código fuente del proyecto; se agregan en `docs/licencias/` cuando la dependencia entre al producto.
- Se entrega **sin garantía**: Microsoft no da soporte comercial por esta librería. El soporte es el de la comunidad, en el repositorio.

Open XML SDK **no es Microsoft Office** ni lo necesita: es una librería que lee y escribe el formato de archivo abierto (ECMA-376 / ISO 29500). Usarla no requiere licencias de Office en el servidor, ni en Dataverse, ni en ningún puesto de trabajo.

## Herramientas de prueba: FakeXrmEasy NO es gratis para un banco

Verificado el 2026-09-20 en la página de licencias del propio producto (`dynamicsvalue.github.io/fake-xrm-easy-docs/licensing/license/`): las versiones **2.x y 3.x** de FakeXrmEasy son gratuitas solo para uso no comercial o para quien publique su código; **el uso comercial con código cerrado exige una licencia comercial paga**. Textual: *"If you wish to use the FakeXrmEasy Version 2 or later software libraries commercially without making available your source code, you may download and use them (with the appropriate payment) under the SOFTWARE LICENSE AND SERVICE AGREEMENT."*

No se distribuye con la solución, pero **se usa dentro de BAC para desarrollarla**, que es uso comercial. La definición del proyecto y las skills de construcción la daban por sentada. La versión 1.x tiene otra licencia, pero solo corre sobre .NET Framework, y el puesto de trabajo es Linux sin `mono`: no sirve acá.

**Decisión del aprobador (2026-09-20): FakeXrmEasy no se usa.** El diseño ya aísla `Dominio`, `Validacion`, `Plantilla` y `Respuesta` del SDK de Dataverse (`diseno/03` §8): esa es la mayor parte del código y se prueba con tests unitarios puros, sin ninguna librería de simulación. La capa fina que sí toca `IOrganizationService` (`Api`, `Steps`, `Datos`) se prueba con un doble propio en memoria, que vive en el proyecto de tests. Lo que un doble no puede probar —el pipeline real, la transacción, la seguridad— se prueba en Dev.

## Qué no cubre este documento

Las licencias de Power Platform, Dataverse y Azure son del tenant de BAC y se tratan en `factibilidad-tecnica.md`. Las demás herramientas del puesto de trabajo (`pac`, .NET SDK, xUnit) no se distribuyen con la solución y son de uso libre.
