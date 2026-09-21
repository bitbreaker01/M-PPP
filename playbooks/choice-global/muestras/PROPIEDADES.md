# Choice global — propiedades observadas

Evidencia: `sanic_mppp_ch_moneda`, creado en Dev el 2026-09-20 con `herramientas/construir/choice_global.py` y exportado después. Dos muestras reales al lado de este archivo: `*.webapi.json` (lo que devuelve `GET GlobalOptionSetDefinitions`) y `*.solucion.xml` (el fragmento de `customizations.xml` de la solución unmanaged exportada). Nada de lo que hay acá es supuesto: es lo que devolvió la plataforma.

## 1. En el XML de la solución (`customizations.xml` → `<optionsets>`)

| Elemento o atributo | Valor observado | Quién lo puso | Texto visible |
|---|---|---|---|
| `<optionset Name>` | nombre lógico | nosotros (`Name`) | |
| `<optionset localizedName>` | igual al display name en el idioma base | plataforma (lo copia) | sí, duplicado |
| `<optionset description>` | igual a la descripción en el idioma base | plataforma (lo copia) | sí, duplicado |
| `<OptionSetType>` | `picklist` (minúscula; en el Web API es `Picklist`) | nosotros | |
| `<IsGlobal>` | `1` | nosotros | |
| `<IntroducedVersion>` | `1.0.0.0` = versión de la solución al crearlo | **plataforma** | |
| `<IsCustomizable>` | `1` | **plataforma** (no lo mandamos) | |
| `<displaynames><displayname description languagecode>` | una por idioma | nosotros | **sí — metadato** |
| `<Descriptions><Description description languagecode>` | una por idioma | nosotros | **sí — metadato** |
| `<option value>` | entero con el prefijo del publisher | nosotros | |
| `<option ExternalValue>` | `""` | **plataforma** | |
| `<option IsHidden>` | `0` | **plataforma** | |
| `<option><labels><label description languagecode>` | una por idioma | nosotros | **sí — metadato** |
| `<option><Descriptions><Description …>` | una por idioma | nosotros | **sí — metadato** |

En `solution.xml`: `<RootComponent type="9" schemaName="<nombre lógico>" behavior="0" />`. El tipo de componente de un choice global es **9**.

**Idiomas.** Todos los textos de un choice son **etiquetas de metadatos** (`languagecode` por etiqueta); no hay ninguno embebido fuera de ese esquema. Con 1033 alcanza: si el destino tiene otro idioma base, la plataforma usa estas (`01-convenciones.md` §0). Ojo con los dos atributos duplicados del elemento raíz (`localizedName`, `description`): si se edita el XML a mano hay que cambiarlos junto con su `<displayname>` / `<Description>`.

## 2. En el Web API (`GlobalOptionSetDefinitions`)

Mandamos 7 propiedades del choice (`@odata.type`, `Name`, `IsGlobal`, `OptionSetType`, `DisplayName`, `Description`, `Options`) y 3 por opción (`Value`, `Label`, `Description`). La plataforma devuelve 14 del choice y 11 por opción. Las que completó sola:

| Propiedad | Valor | Nota |
|---|---|---|
| `MetadataId` | guid | identidad del componente; con él se consulta `solutioncomponents` |
| `IsCustomOptionSet` | `true` | |
| `IsManaged` | `false` | |
| `IsCustomizable` | `{Value: true, CanBeChanged: true, ManagedPropertyLogicalName: "iscustomizable"}` | propiedad administrada, no un booleano |
| `IntroducedVersion` | `"1.0.0.0"` | |
| `HasChanged`, `ExternalTypeName`, `ParentOptionSetName` | `null` | |
| opción: `Color`, `Tag`, `MetadataId`, `HasChanged` | `null` | la opción no tiene `MetadataId` propio |
| opción: `IsManaged` `false`, `IsHidden` `false`, `ExternalValue` `""`, `ParentValues` `[]` | | |
| cada `Label`: `UserLocalizedLabel` | copia de la etiqueta en el idioma del usuario que consulta | depende de quién pregunta: **no usarla para verificar** |
| cada `LocalizedLabel`: `IsManaged`, `MetadataId`, `HasChanged` | | cada etiqueta tiene su propio `MetadataId` |

## 3. Comportamiento verificado

- `POST GlobalOptionSetDefinitions` con la cabecera de solución devuelve **204** sin cuerpo; el componente queda dentro de la solución (una fila en `solutioncomponents`).
- Segunda ejecución de la herramienta: `ya_existia`, sin escrituras. `--solo-verificar`: `ya_existia`.
- La validación estricta de forma (`exigir_forma`) pasó contra la respuesta real: ninguna propiedad que la herramienta lee llegó nula o con otro tipo. `Description` llegó como objeto con su etiqueta, no nula.
- Exportar con `pac solution export` falló en sesión sin escritorio (el perfil no puede renovar el token sin llavero); la acción **`ExportSolution` del Web API** funciona y es la vía de este proyecto.
