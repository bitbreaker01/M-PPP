# Web API: security roles y column security profiles

Investigación en Microsoft Learn, 2026-09-21 (agente investigador, solo lectura). Lo marcado **a ensayar** no está documentado con precisión: se comprueba con componentes descartables antes de escribir la receta.

## A. Security role (tabla `role`)

**Crear**: `POST roles` con `MSCRM.SolutionUniqueName`:

```json
{ "name": "SR - MPPP - …", "businessunitid@odata.bind": "businessunits(<BU raíz>)" }
```

- `businessunitid` es obligatorio. La BU raíz sale de `WhoAmI` o de `businessunits?$filter=_parentbusinessunitid_value eq null`.
- Un rol recién creado **nace con ~9 privilegios por defecto** (mensajes del SDK, plugin type, etc.): la verificación tiene que saber cuáles son para no tratarlos como sobrantes. **A ensayar**: la lista exacta.
- `solutioncomponents`: **20 = Role**, 21 = Role Privilege. **A ensayar** (dos tipos ya contradijeron esta tabla: relación 10 y clave 14).
- Fuentes: https://learn.microsoft.com/power-apps/developer/data-platform/optional-parameters#associate-a-solution-component-with-a-solution · https://learn.microsoft.com/power-apps/developer/data-platform/webapi/web-api-functions-actions-sample#section-8-bound-action-addprivilegesrole

**Privilegios**: acción ligada `roles(<id>)/Microsoft.Dynamics.CRM.AddPrivilegesRole` (agrega) o `ReplacePrivilegesRole` (reemplaza todo):

```json
{ "Privileges": [ { "PrivilegeId": "<guid>", "Depth": "Global" } ] }
```

- `Depth`: `Basic` (usuario) · `Local` (BU) · `Deep` (BU e hijas) · `Global` (organización). En la matriz `04`: **O = Global**, **U = Basic**.
- El `privilegeid` sale de `privileges?$select=privilegeid,name&$filter=name eq 'prvCreatesanic_mppp_tbl_cliente'`. Nombres: `prvCreate`, `prvRead`, `prvWrite`, `prvDelete`, `prvAppend`, `prvAppendTo`, `prvAssign`, `prvShare` + nombre lógico de la tabla. **A ensayar**: `EntityDefinitions(LogicalName='…')?$expand=Privileges` como alternativa.
- Fuente: https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/roleprivilege

**Leer para verificar**: `RetrieveRolePrivilegesRole(RoleId=<id>)`, o `roles(<id>)/roleprivileges_association?$select=name`. La profundidad está en la intersección `roleprivileges` como máscara `privilegedepthmask`: 1 Basic · 2 Local · 4 Deep · 8 Global.
Fuentes: https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/retrieveroleprivilegesrole · https://learn.microsoft.com/power-apps/developer/data-platform/security-access-coding#retrieve-privileges-for-a-security-role

**"Copiar App Opener"** (lo que pide `04` §2): **no hay mensaje de Web API para copiar un rol**; solo la interfaz (admin center). Microsoft no publica la lista de privilegios de App Opener ni un `RoleTemplateId` para ubicarlo. Por API se arma a mano: leer `roleprivileges_association` del App Opener de la BU raíz (`roles?$filter=name eq 'App Opener' and _businessunitid_value eq <raíz>`) y reinyectar con `AddPrivilegesRole`. **A ensayar** que reproduce lo que hace "Copy Role". "min prv apps use" está en retiro.
Fuentes: https://learn.microsoft.com/power-platform/admin/copy-security-role · https://learn.microsoft.com/power-platform/admin/create-edit-security-role#minimum-privileges-for-common-tasks

**Privilegio para ejecutar una Custom API**: `customapi.executeprivilegename` nombra un `Privilege.Name` **ya existente**. **No se puede crear un privilegio a medida**: o se usa uno existente, o se crea una tabla y se usa uno de sus privilegios CRUD. Afecta al diseño de `03` y al rol de ingesta (inventario 6.6 y 8.1): hay que decidir qué privilegio existente gobierna cada Custom API.
Fuente: https://learn.microsoft.com/power-apps/developer/data-platform/custom-api#q-can-i-create-a-new-privilege-for-my-custom-api

**Rol ↔ app model-driven**: `POST appmodules(<id>)/appmoduleroles_association/$ref` con `{"@odata.id": "…/roles(<id>)"}`. Se lee con `appmodules(<id>)?$expand=appmoduleroles_association`. **A ensayar** si viaja con la app en la solución. Privilegio necesario para ver apps: `prvReadAppModule`.
Fuente: https://learn.microsoft.com/power-apps/developer/model-driven-apps/create-manage-model-driven-apps-using-code#manage-access-to-model-driven-app-using-security-roles

**BU y rol raíz**: un rol de la BU raíz se replica a las BU hijas (un registro `role` por BU). El `roleid` no es estable entre entornos. Un rol propio se busca por `name` + `_businessunitid_value` de la raíz; las réplicas apuntan a él con `_parentrootroleid_value`. (Este proyecto tiene una sola BU.)
Fuente: https://learn.microsoft.com/power-apps/developer/data-platform/security-roles

**XML exportado**: Learn no muestra el fragmento `<Roles><Role><RolePrivileges>`; remite al XSD. **A ensayar** exportando un rol descartable.

## B. Column security profile (`fieldsecurityprofile` + `fieldpermission`)

```json
POST fieldsecurityprofiles      { "name": "CSP - MPPP - …", "description": "…" }
POST fieldpermissions           { "entityname": "sanic_mppp_tbl_fila", "attributelogicalname": "sanic_numerocuenta",
                                  "canread": 4, "cancreate": 0, "canupdate": 0, "canreadunmasked": 0,
                                  "fieldsecurityprofileid@odata.bind": "fieldsecurityprofiles(<id>)" }
```

- `canread`/`cancreate`/`canupdate`: 0 no · 4 sí. `canreadunmasked`: 0 no · 1 un registro · 3 todos.
- `solutioncomponents`: 70 perfil, 71 permiso. **A ensayar.**
- **Miembros: usuarios (`systemuserprofiles_association`) o equipos (`teamprofiles_association`). No existe relación perfil ↔ rol.** Los permisos son del perfil, no de cada miembro. De ahí sale la decisión D-8 de `PENDIENTES.md`.
- **A ensayar**: si la asociación de usuarios viaja en la solución (por analogía con usuario ↔ rol, no).
- Fuentes: https://learn.microsoft.com/power-apps/developer/data-platform/column-level-security#provide-access-to-secured-columns · https://learn.microsoft.com/power-apps/developer/data-platform/reference/entities/fieldpermission#writable-columns-attributes · https://learn.microsoft.com/power-apps/developer/data-platform/reference/entities/fieldsecurityprofile#many-to-many-relationships
