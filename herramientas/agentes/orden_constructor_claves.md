Sos el agente CONSTRUCTOR del proyecto M-PPP. Leé primero tu rol en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/agents/constructor-componente.md` y seguilo. Trabajás en `/home/gmaker/projects/M-PPP`. El aprobador ya dio la orden de construir.

## Tu entrada
Los playbooks de tipo `clave` (clave alternativa) que se te indican, en `playbooks/clave/`. Su formato está en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/skills/power-platform-especificar/references/clave.md` y la receta en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/skills/power-platform-construir/references/modelo-datos/patrones.md` (§1 contrato de herramientas y §2.4 "Clave alternativa"). Leé esos dos archivos una vez.

## Tu trabajo: las claves indicadas, DE A UNA y en el orden dado. No empieces una hasta terminar la anterior: el entorno admite una sola personalización a la vez.
Para cada clave `<K>`:
1. Comprobá el playbook `playbooks/clave/<K>.md` contra las "Reglas de completitud" (§4) de `clave.md` y contra el DISEÑO: `diseno/02-diccionario-datos.md` (la sección de la tabla, donde la columna dice **Clave**; DD-03 y DD-04), `diseno/06-inventario-componentes.md` §5 y `diseno/01-convenciones.md` §2 (nombre lógico y nombre visible de una clave). El playbook NO puede cambiar nada que el diseño decide y no puede contradecirse (sección 2 contra sección 5). Si el playbook advierte que una columna de la clave es opcional, comprobá contra el diccionario que de verdad lo es. Si algo no cierra, NO construyas esa clave: anotá la evidencia exacta y pasá a la siguiente.
2. `python3 herramientas/construir/clave.py playbooks/clave/<K>.md` (timeout de 10 minutos; el índice tarda unos dos minutos por clave; si avisa "espero 30 s y reintento" o "El índice de la clave está …; espero", es normal) → esperado `creado`.
3. El mismo comando otra vez → esperado `ya_existia`.
4. `python3 herramientas/construir/clave.py playbooks/clave/<K>.md --solo-verificar` → esperado `ya_existia`.
5. `python3 herramientas/construir/muestra_clave.py playbooks/clave/<K>.md --guardar` → esperado `OK`, 1 de 1.
6. La tabla sigue bien: `python3 herramientas/construir/tabla.py playbooks/tabla/<tabla>.md --solo-verificar` → esperado `ya_existia`.
Anotá la ÚLTIMA línea (el JSON) de cada comando, tal cual.

## Reglas duras
- **Si el sistema de permisos te bloquea o te niega un comando, NO lo reintentes**, ni igual ni con variantes: pará ahí mismo y reportá qué comando fue y el mensaje exacto. (Distinto son los avisos de espera de la propia herramienta: eso lo maneja ella sola.)
- NO escribas ni modifiques NINGÚN archivo: ni herramientas, ni pruebas, ni playbooks, ni skills, ni diseño. La única escritura permitida es la de `muestra_clave.py --guardar` en `playbooks/clave/muestras/`.
- Si una herramienta da `error`, `bloqueado` o `difiere`, o algo no coincide: NO la parchees, NO reintentes con variantes ni con otros flags, NO llames al Web API por tu cuenta para arreglarlo (tampoco `ReactivateEntityKey`), NO borres nada. Dejá ESA clave como está, anotá la evidencia exacta (comando y salida completa) y seguí con la siguiente, salvo que la falla sea del entorno entero (credenciales, red): en ese caso pará todo.
- No leas ni imprimas `local/pp_secrets.env`. No uses `pac`. No hagas commits. No uses cat/grep/find/sed/ls: usá Read/Grep/Glob o `rg`, `batcat`, `eza`.

## Qué devolvés (en español, conciso)
Una tabla con una fila por clave: clave · estado (completo | bloqueado | con problema) · MetadataId · resultado de cada uno de los 5 comandos en una palabra. Debajo, SOLO para las que no salieron limpias: el comando y su última línea real completa. Al final: `Desvíos y preguntas` · `Tropiezos candidatos` (separados: PLAYBOOK / skill de ESPECIFICAR / RECETA / HERRAMIENTA; o "Ninguno") · `skill_resolution: injected`.
