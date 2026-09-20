# Mantenimiento PPP

Automatización de inclusiones, exclusiones y modificaciones de referencias en planes de pago de planilla y proveedores (PPP), para BAC Credomatic Nicaragua. Proyecto `2026-001-referencias-planes-pago`, sobre Power Platform con Dataverse.

Solución: `SOL - MPPP - Mantenimiento PPP` (`sanic_mppp_sol_mantenimientoppp`), publisher `Sistemas_Abiertos_Nicaragua`, prefijo `sanic`.

## Mapa del repositorio

| Carpeta | Qué hay |
|---|---|
| `diseno/` | El diseño detallado de la etapa 3. Empezar por `00-excepciones-a-la-definicion.md`; después `01` convenciones, `02` diccionario de datos (con su diagrama), `03` contratos de Custom API y plugins, `04` matriz de privilegios. `PENDIENTES.md` es temporal. |
| `datos/` | Insumos versionados: la plantilla Excel que llenan los clientes (`datos/plantilla/`) y, más adelante, las semillas de catálogos y parámetros. **Nunca datos reales de clientes.** |
| `herramientas/` | Utilidades del puesto de trabajo. `pacx`: corre `pac` sin colgarse en una sesión sin escritorio. `generar_er.py`: regenera el diagrama del modelo de datos. |
| `spikes/` | Pruebas de concepto exigidas por las condiciones de la definición (C-05, C-06). Código descartable; lo que vale es su `CONCLUSIONES.md`. |
| `src/` | Código C#: plugins, tests, herramienta de histórico. *(todavía vacío)* |
| `solution/` | La solución de Dataverse desempaquetada. *(todavía vacío)* |
| `docs/` | Procedimientos de operación. *(todavía vacío)* |
| `local/` | **No se versiona.** Secretos (`pp_secrets.env`) y documentos de contexto (definición, ficha, factibilidad, panoramas), cuyos originales viven en el repositorio de conocimiento. |

## Convenciones

Commits convencionales. Los nombres de todo componente siguen `diseno/01-convenciones.md`. El publisher se fija siempre por su unique name: en Dev hay otro publisher con el mismo prefijo `sanic`.
