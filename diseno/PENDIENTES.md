# PENDIENTES — documento temporal

Se limpia a medida que se decide. **Cuando quede vacío, se elimina.**

Última actualización: 2026-09-20. Diseño `00` a `07` revisado por el aprobador; queda abierta una sola decisión de diseño: los idiomas (D-3).

## 0. Diseño que falta (bloquea construir esas partes, no el modelo de datos)

| # | Qué falta | Qué necesita |
|---|---|---|
| D-1 | **La app model-driven** (`05-app-model-driven.md`): sitemap, vistas por perfil, formularios, con qué gesto se dispara cada transición, cómo ve el supervisor la solicitud original. | Respuestas del aprobador a seis preguntas: unidad de trabajo del ejecutivo (bandeja de filas o por solicitud); acciones masivas sobre varias filas; qué necesita ver el supervisor; bandeja de no reconocidos y si hace falta el cuerpo del correo en texto; carga de catálogos uno a uno o por importación; avisos de trabajo nuevo. |
| D-2 | **Los cuatro flujos** (`07-flujos.md`): disparadores, acciones, expresiones, errores, reintentos, concurrencia. | Lo diseña el arquitecto; necesita del aprobador el nombre del buzón y cómo se envían las respuestas (desde el buzón dedicado, como respuesta al hilo o como correo nuevo). |

## 00. Construcción: DETENIDA por orden del aprobador (2026-09-20)

No se construye ningún componente hasta que el aprobador revise el diseño de la app (`05`) y de los flujos (`07`) y dé la orden. **Dev está vacío**: existe solo la solución `sanic_mppp_sol_mantenimientoppp`, sin componentes (el choice de prueba del ciclo 1 se borró el 2026-09-20 por orden del aprobador).

Las dos observaciones del revisor sobre `herramientas/construir/choice_global.py` quedaron **resueltas el 2026-09-20** (estado `error` frente a `bloqueado`, red de contención sin red), junto con lo que destaparon: toda respuesta del entorno se valida por tipo hasta el último nivel con `exigir_forma` (`_comun.py`). 105 pruebas sin red, comprobadas por mutación.

## 0. Diseño en revisión

| # | Documento | Qué necesita del aprobador |
|---|---|---|
| D-1 | `05-app-model-driven.md` | **Cerrado el 2026-09-20.** Decisiones DA-01 a DA-09 aprobadas y mockup revisado por el aprobador: pidió la navegación entre Cliente, Plan y correo Autorizado (ya está en el mockup y en `05`); "aparte de eso, lo miro todo bien". |
| D-2 | `07-flujos.md` | **Cerrado el 2026-09-20.** Flujos aprobados; el aprobador confirmó que el plugin liviano resuelva también `REMITENTE_RECONOCIDO`. |
| D-3 | **Idiomas** | El aprobador exige (2026-09-20) que todo nazca **listo para varios idiomas**. Regla (verificada en Learn y en Dev): las etiquetas de **metadatos** (tablas, columnas, choices, vistas, formularios) van en 1033 y la plataforma las usa en cualquier idioma base que no tenga las suyas; las etiquetas **embebidas** en el XML del componente (títulos del sitemap, textos de comandos y lo que cada export real demuestre) llevan **un título por idioma** de la lista del proyecto, 1033 y 3082 para empezar. **No hace falta habilitar español en Dev**: el aprobador ya lo hizo a mano desde un entorno en inglés. Falta: pasarlo a `01` §0 y al formato del playbook (`idiomas`), y probar temprano una importación en un entorno con base español. |
| D-4 | `02` §2.6, tabla Regla | **Cerrado el 2026-09-20.** La primaria de Regla es autonumérica y opcional, `REG-{SEQNUM:4}` (`02` DD-20). |
| D-5 | `02` §3.3 y §3.4 | **Cerrado el 2026-09-20.** Son opcionales a propósito, y además autonuméricas: `RES-{SEQNUM:10}` y `BIT-{SEQNUM:10}` (`02` DD-20). |
| D-6 | Relaciones 4.10 y 4.11 (BP-PP-188) | **Cerrado el 2026-09-20.** Aprobado: con más de una relación entre el mismo par de tablas, cada una lleva como sufijo el nombre de su lookup sin prefijo. Agregado a BP-PP-188 y a `01` §2. |
| D-7 | `02` §3.3 y §3.4 | **El lookup `sanic_solicitudid` de Resultado de regla y de Bitácora se construye opcional**, como dice el diccionario y como figuraba en la lista de relaciones que el aprobador aprobó el 2026-09-20. Queda la duda de si conviene requerido (son relaciones parentales); se cambia después sin costo. No frena nada. **2026-09-21**: el aprobador confirmó que la clave 5.10 se construye con el lookup opcional, tal como está; en la práctica nunca queda vacío porque el plugin siempre carga la solicitud. |
| D-8 | `04` §4 | **CERRADA (aprobador, 2026-09-21): por equipo.** El administrador crea un grupo de seguridad en Entra ID y su equipo de grupo en Power Platform, y a ese equipo se le asigna el perfil. Un perfil de solo lectura en fase 1 (`CSP - MPPP - Datos sensibles`); el de lectura y creación nace en fase 3. Pasado a `04` §4 e inventario 13.7. |
| D-9 | `03` y `04` §3 | **CERRADA (aprobador, 2026-09-21): `ExecutePrivilegeName = prvCreatesanic_mppp_tbl_solicitud`** para las dos Custom API de fase 1. Las de fase 2 se deciden al diseñar esa fase. Pasado a `03` (encabezado). |

## A. Para confirmar con negocio, sin apuro

La matriz de obligatoriedad arranca con **todo obligatorio salvo Referencia** (DD-16). Cuando se quiera flexibilizar, se cambia el parámetro `plantilla.obligatoriedad`; no hay código que tocar. El aprobador va a escribir la versión detallada. Lo ya respondido está en `02-diccionario-datos.md`, DD-12 a DD-17.

## B. Verificaciones contra el entorno

Todas hechas el 2026-09-20 y asentadas en `01-convenciones.md` §7. Queda una sola, que se cierra al construir el primer flujo: si Power Automate respeta la columna `uniquename` en un cloud flow.

## C. Spike C-05

**Cerrado.** Parte A y parte B terminadas; la condición C-05 de la definición está cumplida: Open XML SDK carga y lee la plantilla dentro del sandbox en milisegundos. Conclusiones en `spikes/c05-parseo-excel/CONCLUSIONES.md` y `CONCLUSIONES-B.md`. Quedó una sola cosa sin medir, porque necesita acceso al buzón: el largo real de los Message-ID que llegan (DD-03). Se mide al construir Flow A.
