Sos el agente CONSTRUCTOR del proyecto M-PPP. Leé primero tu rol en `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/agents/constructor-componente.md` y seguilo. Trabajás en `/home/gmaker/projects/M-PPP`. El aprobador ya dio la orden de agregar estas columnas; el entorno de desarrollo es el del playbook.

## Tu entrada
La tabla `{TABLA}` YA EXISTE en el entorno. Su playbook `playbooks/tabla/{TABLA}.md` ganó columnas nuevas: {COLUMNAS} (decisión {DECISION}). Formato del playbook: `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/skills/power-platform-especificar/references/tabla.md`. Receta: `/home/gmaker/projects/gmaker-plugins/plugins/plataforma-power-platform/skills/power-platform-construir/references/modelo-datos/patrones.md` §1 (contrato de herramientas) y §2.6 "Agregar columnas a una tabla ya construida". Leé esos tres archivos.

## Tu trabajo: carpintería, exactamente estos pasos
1. Comprobá las columnas NUEVAS del playbook contra el DISEÑO: `diseno/02-diccionario-datos.md` {DICCIONARIO} (nombre lógico letra por letra, tipo, requerida, protegida, auditoría según DD-18) y la regla de nombres visibles BP-PP-197 (sin tildes ni ñ; `diseno/01-convenciones.md`). Lo que el diccionario no trae (nombre visible, rango del entero) lo decide el playbook: comprobá que sea coherente con las columnas hermanas. Si algo no cierra, NO construyas: devolvé `bloqueado` con la evidencia exacta.
2. `python3 herramientas/construir/tabla.py playbooks/tabla/{TABLA}.md --solo-verificar` (timeout de 10 minutos). Tiene que dar `difiere` y su detalle tiene que ser EXACTAMENTE "falta la columna …" por cada columna nueva y nada más. Si dice cualquier otra cosa, pará y reportá.
3. `python3 herramientas/construir/tabla.py playbooks/tabla/{TABLA}.md --agregar-columnas`. Tiene que dar `ya_existia` con "se agregaron N columnas". Si aparece el aviso "El entorno tiene otra personalización en curso; espero 30 s y reintento", es normal: dejala trabajar.
4. Ejecutalo una segunda vez, igual: tiene que dar `ya_existia` con "no se modificó nada".
5. `python3 herramientas/construir/tabla.py playbooks/tabla/{TABLA}.md --solo-verificar` y `python3 herramientas/construir/muestra_tabla.py playbooks/tabla/{TABLA}.md --guardar` (la muestra anterior no trae la columna nueva).
6. Pegá en tu reporte la ÚLTIMA línea (el JSON) de cada ejecución, tal cual.

## Reglas duras
- **Si el sistema de permisos te bloquea o te niega un comando, NO lo reintentes**, ni igual ni con variantes: un bloqueo de permisos es una decisión, no una falla pasajera. Pará ahí mismo y reportá qué comando fue y el mensaje exacto del bloqueo. (Distinto es el aviso de la propia herramienta "espero 30 s y reintento": eso lo maneja ella sola.)
- NO escribas ni modifiques NINGÚN archivo. La única escritura permitida es la de `muestra_tabla.py --guardar` en `playbooks/tabla/muestras/`.
- Si una herramienta da `error`, `bloqueado`, o un `difiere` que no es el esperado: NO la parchees, NO reintentes con variantes ni con otros flags, NO llames al Web API por tu cuenta para arreglarlo, NO borres nada. Pará y reportá la evidencia exacta (comando y salida completa). Resolverlo es trabajo del arquitecto.
- No leas ni imprimas `local/pp_secrets.env`. No uses `pac`. No hagas commits. No uses cat/grep/find/sed/ls: usá Read/Grep/Glob o `rg`, `batcat`, `eza`.
- No toques ningún otro componente del entorno.

## Qué devolvés (en español, conciso)
- `Estado`: completo | parcial | bloqueado, y por qué en una línea.
- `Construido`: tabla, columnas agregadas y MetadataId de la tabla.
- `Verificación`: cada comando con su última línea real.
- `Desvíos y preguntas`.
- `Tropiezos candidatos`: separados en PLAYBOOK / skill de ESPECIFICAR / RECETA / HERRAMIENTA. Si no hubo, "Ninguno".
- `skill_resolution: injected`.
