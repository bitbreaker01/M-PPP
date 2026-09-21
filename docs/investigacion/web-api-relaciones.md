# Web API de Dataverse: relaciones 1:N con su lookup

Investigación en Microsoft Learn del 2026-09-20 (agente de investigación, solo documentación). Es el insumo para el tipo de playbook `relacion`, su receta y su herramienta. **Nada de esto está ensayado todavía contra la plataforma**: lo marcado "NO DOCUMENTADO" se comprueba con tablas descartables antes de usarlo.

## Crear

`POST RelationshipDefinitions`, con la cabecera `MSCRM.SolutionUniqueName`. Respuesta `204` y `OData-EntityId`. **Hay que publicar después** (`PublishXml`).

```json
{
  "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
  "SchemaName": "<nombre de la relación, hasta 100 caracteres>",
  "ReferencedEntity": "<tabla del lado 1>",
  "ReferencedAttribute": "<su clave primaria>",
  "ReferencingEntity": "<tabla del lado N>",
  "CascadeConfiguration": { "Assign": "…", "Delete": "…", "Merge": "…", "Reparent": "…", "Share": "…", "Unshare": "…", "RollupView": "…" },
  "AssociatedMenuConfiguration": { "Behavior": "UseCollectionName", "Group": "Details", "Label": { … }, "Order": 10000 },
  "Lookup": {
    "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
    "AttributeType": "Lookup", "AttributeTypeName": { "Value": "LookupType" },
    "SchemaName": "<columna lookup>", "DisplayName": { … }, "Description": { … },
    "RequiredLevel": { "Value": "ApplicationRequired", "CanBeChanged": true, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings" }
  }
}
```

## Cascadas de cada comportamiento estándar

| Comportamiento | Assign | Delete | Merge | Reparent | Share | Unshare | RollupView |
|---|---|---|---|---|---|---|---|
| Parental | Cascade | Cascade | NoCascade | Cascade | Cascade | Cascade | NoCascade |
| Referencial (quitar vínculo) | NoCascade | RemoveLink | NoCascade | NoCascade | NoCascade | NoCascade | NoCascade |
| Referencial, borrado restringido | NoCascade | Restrict | NoCascade | NoCascade | NoCascade | NoCascade | NoCascade |

Valores de `CascadeType`: `NoCascade`, `Cascade`, `Active`, `UserOwned`, `RemoveLink`, `Restrict`. `Delete` admite solo `Cascade`, `RemoveLink`, `Restrict`; `Merge`, solo `Cascade` o `NoCascade`.

## Restricciones documentadas

- **Una sola relación parental por tabla relacionada**: no se puede crear una relación con alguna acción en cascada si la tabla del lado N ya es el lado N de otra relación que cascadea. En el modelo de MPPP se cumple: Fila, ResultadoRegla y Bitácora tienen cada una una sola parental, hacia Solicitud.
- Una tabla custom no puede ser el lado 1 de una relación que cascadea hacia una tabla del sistema.
- El comportamiento de cascada se puede cambiar después (`PUT` del objeto completo, no `PATCH`; con `MSCRM.MergeLabels`). El `SchemaName` de la relación y el del lookup, no.
- Borrar la relación **borra la columna lookup**. No se puede borrar si el lookup está en un formulario.
- **El lookup muestra el nombre primario del registro relacionado a cualquiera que vea el registro que lo contiene**, aunque no tenga permiso sobre el relacionado: la columna primaria no debe llevar datos sensibles.
- Tipo de componente en `solutioncomponents`: relación = **10**; atributo = 2.

## Leer para verificar

`GET RelationshipDefinitions(SchemaName='…')/Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata` → `ReferencedEntity`, `ReferencingEntity`, `ReferencingAttribute`, `IsCustomRelationship`, `IsManaged`, `CascadeConfiguration`, `MetadataId`.
`GET EntityDefinitions(LogicalName='<tabla N>')/Attributes(LogicalName='<lookup>')/Microsoft.Dynamics.CRM.LookupAttributeMetadata?$select=SchemaName,DisplayName,RequiredLevel,Targets`.

## No documentado (a ensayar)

- Si un lookup custom hacia `systemuser` tiene alguna restricción (los ejemplos nativos usan todo `NoCascade`).
- Si `RequiredLevel` del lookup se respeta al crear, o si la plataforma lo ignora como hace con la primaria de una tabla.
- Si `IsAuditEnabled` e `IsSecured` se pueden fijar en el `Lookup` embebido.
- Qué exige `AssociatedMenuConfiguration` como mínimo.

## Fuentes

- https://learn.microsoft.com/power-apps/developer/data-platform/webapi/create-update-entity-relationships-using-web-api
- https://learn.microsoft.com/power-apps/developer/data-platform/configure-entity-relationship-cascading-behavior
- https://learn.microsoft.com/power-apps/maker/data-platform/create-edit-1n-relationships-solution-explorer#edit-relationships
- https://learn.microsoft.com/power-apps/maker/data-platform/create-edit-entity-relationships#table-relationship-behavior
- https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/cascadeconfiguration
- https://learn.microsoft.com/power-apps/developer/data-platform/reference/entities/entityrelationship
- https://learn.microsoft.com/power-apps/developer/data-platform/reference/entities/solutioncomponent
