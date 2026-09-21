# Web API de Dataverse: claves alternativas

Investigación en Microsoft Learn del 2026-09-20 (agente de investigación, solo documentación). Insumo para el tipo de playbook `clave`. **Learn no trae un ejemplo HTTP de creación de claves**: el cuerpo de abajo sigue la convención documentada para tablas y columnas y se comprueba con tablas descartables antes de usarlo.

## Crear (a ensayar)

`POST EntityDefinitions(LogicalName='<tabla>')/Keys`, con `MSCRM.SolutionUniqueName`.

```json
{
  "@odata.type": "Microsoft.Dynamics.CRM.EntityKeyMetadata",
  "SchemaName": "<nombre de la clave>",
  "DisplayName": { "@odata.type": "Microsoft.Dynamics.CRM.Label", "LocalizedLabels": [ { "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": "…", "LanguageCode": 1033 } ] },
  "KeyAttributes": ["<columna>", "<lookup>"]
}
```

No documentado: código de respuesta, si hay que publicar, y si la cabecera de solución vale para claves.

## El índice se crea en segundo plano

`EntityKeyIndexStatus`: `Pending`, `InProgress`, `Active`, `Failed`. `AsyncJob` trae el trabajo del sistema. Una clave solo sirve cuando está `Active`. Si queda `Failed`: `POST ReactivateEntityKey` con `{"EntityLogicalName": "<tabla>", "EntityKeyLogicalName": "<clave>"}`. Borrar la clave mientras el índice se crea cancela el trabajo.

## Límites documentados

- Tipos admitidos: texto de una línea, entero, decimal, fecha y hora, **lookup** y choice. En `KeyAttributes` un lookup va con su nombre lógico (`sanic_clienteid`).
- Hasta **10 claves por tabla**, **16 columnas** y **900 bytes** por clave.
- Una columna con **seguridad de columna** no puede ir en una clave.
- **Con un valor nulo en una columna de la clave, la unicidad NO se exige.** Una clave solo protege si sus columnas siempre traen valor.
- Los caracteres `/ < > * % & : \ ? + #` en el valor impiden usar la clave en una URL (GET, PATCH, upsert); la unicidad sí se exige igual.
- No se documenta si `KeyAttributes` se puede cambiar después (se asume que no: se borra y se crea otra), ni el comportamiento con mayúsculas y acentos (en este proyecto se verificó en el spike C-05: no distingue mayúsculas).

## Leer, borrar, solución

- `GET EntityDefinitions(LogicalName='<tabla>')/Keys` y, por analogía con `Attributes`, `…/Keys(LogicalName='<clave>')`. Propiedades: `LogicalName`, `SchemaName`, `KeyAttributes`, `EntityKeyIndexStatus`, `AsyncJob`, `IsManaged`, `IsCustomizable`, `IntroducedVersion`, `EntityLogicalName`, `DisplayName`, `MetadataId`.
- Borrar (por analogía): `DELETE EntityDefinitions(LogicalName='<tabla>')/Keys(<MetadataId>)`.
- En `solutioncomponents`, una clave es el tipo **14** y, según la documentación de errores de importación, es un componente propio. **A comprobar en el ensayo**: con las relaciones la tabla de tipos también decía que eran un componente propio (10) y no lo son.

## Fuentes

- https://learn.microsoft.com/power-apps/developer/data-platform/define-alternate-keys-entity
- https://learn.microsoft.com/power-apps/maker/data-platform/define-alternate-keys-reference-records#limits-in-creating-alternate-keys
- https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/entitykeymetadata
- https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/entitykeyindexstatus
- https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/reactivateentitykey
- https://learn.microsoft.com/power-apps/developer/data-platform/use-alternate-key-reference-record
- https://learn.microsoft.com/troubleshoot/power-platform/dataverse/working-with-solutions/entitykey-selected-attributes-already-exists

## Comprobado en el ensayo del 2026-09-21 (tablas descartables en Dev)

- `GET …/Keys(LogicalName='<clave>')` funciona; **404** si no existe.
- Una clave **no es un componente propio** de la solución: cero filas en `solutioncomponents` (ni tipo 14 ni otro). Viaja dentro de su tabla. La pertenencia se comprueba por la tabla (tipo 1, `rootcomponentbehavior = 0`).
- El límite de **900 bytes no se comprueba al crear**: claves de 902 y 904 bytes quedaron `Active` con la tabla vacía. La herramienta lo bloquea igual.
- El índice tarda **~2 minutos** en pasar de `Pending` a `Active`, aun con la tabla vacía.
- `KeyAttributes` vuelve en **orden alfabético**, se mande como se mande.
- XML: `<EntityKeys>` dentro de la `<entity>`; la plataforma pone `IsCustomizable = 0`. El XML no trae el estado del índice.
- Borrar la tabla se lleva sus claves.
