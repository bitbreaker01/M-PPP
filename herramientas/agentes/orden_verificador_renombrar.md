Sos el agente VERIFICADOR del proyecto M-PPP. Leé primero tu rol en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/agents/revisor-construccion.md` y seguilo. Trabajás en `/home/gmaker/projects/M-PPP`. Mandato ADVERSARIAL y de SOLO LECTURA: no le creas al constructor, comprobá vos.

## Qué se verifica
El aprobador decidió el 2026-09-21 que **ningún nombre visible lleva tildes ni ñ** (BP-PP-197; `diseno/01-convenciones.md` §7). Un agente constructor dice haber corregido en el entorno de desarrollo los nombres visibles de los componentes que se te indican, SIN cambiar nada más. Las **descripciones** son prosa: conservan sus tildes y NO tenían que cambiar.

## Tu trabajo
1. Por cada componente indicado, corré la herramienta de su tipo en solo lectura y la comprobación contra el XML exportado (SIN `--guardar`):
   - choice: `python3 herramientas/construir/choice_global.py playbooks/choice-global/<C>.md --solo-verificar` → esperado `ya_existia`.
   - tabla: `python3 herramientas/construir/tabla.py playbooks/tabla/<T>.md --solo-verificar` y `python3 herramientas/construir/muestra_tabla.py playbooks/tabla/<T>.md` → esperado `ya_existia` y `OK`.
   - rol: `python3 herramientas/construir/rol.py playbooks/rol/<R>.md --solo-verificar` y `python3 herramientas/construir/muestra_rol.py playbooks/rol/<R>.md` → esperado `ya_existia` y `OK`.
   Para los choices corré UNA vez `python3 herramientas/construir/muestra_choice.py` (procesa los 14) → esperado 14 de 14.
2. **Barrido independiente, por Web API crudo** (`python3 herramientas/dataverse_api.py GET "<ruta>"`), de lo que te toca. Buscás cualquier carácter fuera de ASCII (tildes, ñ, ü, comillas tipográficas, rayas) en un NOMBRE visible:
   - choices: `GlobalOptionSetDefinitions(Name='<C>')` → `DisplayName` y el `Label` de CADA opción. La `Description` puede llevar tildes.
   - tablas: `EntityDefinitions(LogicalName='<T>')?$select=DisplayName,DisplayCollectionName` y `EntityDefinitions(LogicalName='<T>')/Attributes?$select=LogicalName,DisplayName,IsCustomAttribute&$filter=IsCustomAttribute eq true` → el `DisplayName` de CADA columna propia (incluidos los lookups). Para cada columna sí/no, `…/Attributes(LogicalName='<col>')/Microsoft.Dynamics.CRM.BooleanAttributeMetadata?$select=LogicalName&$expand=OptionSet` → las etiquetas de `TrueOption` y `FalseOption`.
   - roles: `roles?$select=name&$filter=startswith(name,'SR - MPPP')` → el `name` exacto de cada uno. OJO: el filtro de Dataverse NO distingue tildes ni mayúsculas; mirá el `name` que vuelve, no te fíes de que la consulta "lo encontró".
   Para revisar muchas etiquetas sin equivocarte a ojo, podés pasar la salida por `python3 -c` y listar las que tengan algún carácter con código mayor a 126 (solo lectura; no escribas archivos).
3. Comprobá que **nada más cambió**: además de lo que ya cubre `--solo-verificar` (tipos, largos, requerida, auditoría, descripciones), elegí DOS columnas por tabla que te toque y compará a mano su `Description` y su `RequiredLevel` contra el playbook.
4. Excepción conocida, NO es un hallazgo: las claves alternativas (`EntityDefinitions(...)/Keys`) todavía tienen nombres visibles con tilde; la plataforma no deja cambiarlos por Web API y el aprobador está decidiendo qué hacer. No las toques ni las reportes como defecto; sí podés listar cuáles llevan tilde.

## Reglas duras
- **Si el sistema de permisos te bloquea o te niega un comando, NO lo reintentes**: pará y reportá el comando y el mensaje exacto.
- SOLO LECTURA: solo `GET`; nunca POST/PUT/PATCH/DELETE; las herramientas de construcción SIEMPRE con `--solo-verificar`; nunca `--guardar`, `--corregir-nombres`, `--renombrar-desde`, `--completar`, `--corregir-primaria`, `--publicar`. No modifiques ningún archivo. No leas `local/pp_secrets.env`. No uses `pac`. Sin commits. No uses cat/grep/find/sed/ls: usá Read/Grep/Glob o `rg`, `batcat`, `eza`.
- Si encontrás un defecto, NO lo arregles: reportalo con evidencia.

## Qué devolvés (en español, MUY conciso)
Una tabla con una fila por componente: componente · veredicto (aprobado | rechazado) · nombres visibles revisados (cantidad) · con caracteres fuera de ASCII (cantidad, y cuáles). Debajo: `Hallazgos` (solo si los hay, con evidencia) · `Verificación` (última línea real de cada comando, agrupada) · `Tropiezos candidatos` (o "Ninguno") · `skill_resolution: injected`.
