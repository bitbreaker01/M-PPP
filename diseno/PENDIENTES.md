# PENDIENTES — documento temporal

Se limpia a medida que se decide. **Cuando quede vacío, se elimina.** Nada de lo que hay acá frena la construcción.

Última actualización: 2026-09-20. El diseño detallado (`00` a `04`) está **revisado completo por el aprobador** y no tiene decisiones abiertas.

## 0. Diseño que falta (bloquea construir esas partes, no el modelo de datos)

| # | Qué falta | Qué necesita |
|---|---|---|
| D-1 | **La app model-driven** (`05-app-model-driven.md`): sitemap, vistas por perfil, formularios, con qué gesto se dispara cada transición, cómo ve el supervisor la solicitud original. | Respuestas del aprobador a seis preguntas: unidad de trabajo del ejecutivo (bandeja de filas o por solicitud); acciones masivas sobre varias filas; qué necesita ver el supervisor; bandeja de no reconocidos y si hace falta el cuerpo del correo en texto; carga de catálogos uno a uno o por importación; avisos de trabajo nuevo. |
| D-2 | **Los cuatro flujos** (`07-flujos.md`): disparadores, acciones, expresiones, errores, reintentos, concurrencia. | Lo diseña el arquitecto; necesita del aprobador el nombre del buzón y cómo se envían las respuestas (desde el buzón dedicado, como respuesta al hilo o como correo nuevo). |

## A. Para confirmar con negocio, sin apuro

La matriz de obligatoriedad arranca con **todo obligatorio salvo Referencia** (DD-16). Cuando se quiera flexibilizar, se cambia el parámetro `plantilla.obligatoriedad`; no hay código que tocar. El aprobador va a escribir la versión detallada. Lo ya respondido está en `02-diccionario-datos.md`, DD-12 a DD-17.

## B. Verificaciones contra el entorno

Todas hechas el 2026-09-20 y asentadas en `01-convenciones.md` §7. Queda una sola, que se cierra al construir el primer flujo: si Power Automate respeta la columna `uniquename` en un cloud flow.

## C. Spike C-05

**Cerrado.** Parte A y parte B terminadas; la condición C-05 de la definición está cumplida: Open XML SDK carga y lee la plantilla dentro del sandbox en milisegundos. Conclusiones en `spikes/c05-parseo-excel/CONCLUSIONES.md` y `CONCLUSIONES-B.md`. Quedó una sola cosa sin medir, porque necesita acceso al buzón: el largo real de los Message-ID que llegan (DD-03). Se mide al construir Flow A.
