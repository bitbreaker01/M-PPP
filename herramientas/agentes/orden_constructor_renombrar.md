Sos el agente CONSTRUCTOR del proyecto M-PPP. Leé primero tu rol en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/agents/constructor-componente.md` y seguilo. Trabajás en `/home/gmaker/projects/M-PPP`.

## Qué pasó y qué se te pide
El aprobador decidió el 2026-09-21 que **ningún nombre visible lleva tildes ni ñ** (regla BP-PP-197; está en `diseno/01-convenciones.md` §7, "Nombres visibles"). Los playbooks ya se corrigieron (por ejemplo `Número` → `Numero`, `Autorización` → `Autorizacion`); las descripciones NO cambian, son prosa. Los componentes que se te indican ya están construidos en el entorno de desarrollo **con los nombres viejos**. Tu trabajo es mecánico: correr la herramienta de cada tipo con el flag que corrige SOLO nombres visibles. La herramienta decide sola si puede: si encuentra cualquier otra diferencia, no toca nada e informa `difiere`.

## Tu trabajo: los componentes indicados, DE A UNO y en el orden dado (el entorno admite una sola personalización a la vez)
Para un **choice** (`playbooks/choice-global/<C>.md`) o una **tabla** (`playbooks/tabla/<T>.md`), con `<H>` = `choice_global.py` o `tabla.py`:
1. `python3 herramientas/construir/<H> <playbook> --solo-verificar` → esperado `difiere`, y TODAS las diferencias son de nombres visibles (`DisplayName`, `DisplayCollectionName`, `<columna>.DisplayName`, `opciones[i].etiqueta`, `<columna>.etiqueta_si`/`etiqueta_no`), donde lo único que cambia entre "entorno" y "playbook" son tildes o ñ. Si aparece cualquier otra diferencia, o una diferencia de nombre que NO sea solo de tildes/ñ: NO sigas con ese componente, anotá la salida completa y pasá al siguiente.
2. `python3 herramientas/construir/<H> <playbook> --corregir-nombres` (timeout 10 minutos; si avisa "espero 30 s y reintento", es normal) → esperado `ya_existia`, con "se corrigieron N".
3. `python3 herramientas/construir/<H> <playbook> --solo-verificar` → esperado `ya_existia`.
4. `python3 herramientas/construir/muestra_choice.py <playbook> --guardar` o `python3 herramientas/construir/muestra_tabla.py <playbook> --guardar` → esperado `OK`, 1 de 1.
Para el **rol**: 1. `python3 herramientas/construir/rol.py <playbook> --solo-verificar` → esperado `error` ("no existe": está con el nombre viejo). 2. `python3 herramientas/construir/rol.py <playbook> "--renombrar-desde=<nombre anterior>"` → esperado `ya_existia`, con "se renombró". 3. `--solo-verificar` → `ya_existia`. 4. `python3 herramientas/construir/muestra_rol.py <playbook> --guardar` → `OK`.
Anotá la ÚLTIMA línea (el JSON) de cada comando, tal cual.

## Reglas duras
- **Si el sistema de permisos te bloquea o te niega un comando, NO lo reintentes**, ni igual ni con variantes: pará ahí mismo y reportá qué comando fue y el mensaje exacto.
- NO escribas ni modifiques NINGÚN archivo. La única escritura permitida es la de `muestra_*.py --guardar` en las carpetas `muestras/`.
- Si una herramienta da `error`, `bloqueado` o un `difiere` que no esperabas: NO la parchees, NO reintentes con variantes ni con otros flags, NO llames al Web API por tu cuenta para arreglarlo, NO borres nada. Dejá ESE componente como está, anotá la evidencia exacta y seguí con el siguiente, salvo que la falla sea del entorno entero (credenciales, red): en ese caso pará todo.
- No leas ni imprimas `local/pp_secrets.env`. No uses `pac`. No hagas commits. No uses cat/grep/find/sed/ls: usá Read/Grep/Glob o `rg`, `batcat`, `eza`.

## Qué devolvés (en español, conciso)
Una tabla con una fila por componente: componente · estado (completo | con problema) · cuántos nombres se corrigieron · resultado de cada comando en una palabra. Debajo, SOLO para los que no salieron limpios: el comando y su última línea real completa. Al final: `Desvíos y preguntas` · `Tropiezos candidatos` (o "Ninguno") · `skill_resolution: injected`.
