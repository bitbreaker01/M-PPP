# PENDIENTES — documento temporal

Se limpia a medida que se decide. **Cuando quede vacío, se elimina.** Nada de lo que hay acá frena la construcción.

Última actualización: 2026-09-20. El diseño detallado (`00` a `04`) está **revisado completo por el aprobador** y no tiene decisiones abiertas.

## A. Para confirmar con negocio, sin apuro

La matriz de obligatoriedad arranca con **todo obligatorio salvo Referencia** (DD-16). Cuando se quiera flexibilizar, se cambia el parámetro `plantilla.obligatoriedad`; no hay código que tocar. El aprobador va a escribir la versión detallada. Lo ya respondido está en `02-diccionario-datos.md`, DD-12 a DD-17.

## B. Verificaciones contra el entorno

Todas hechas el 2026-09-20 y asentadas en `01-convenciones.md` §7. Queda una sola, que se cierra al construir el primer flujo: si Power Automate respeta la columna `uniquename` en un cloud flow.

## C. Parte B del spike C-05 (dentro de Dataverse)

La parte A quedó cerrada sin tercera revisión, por decisión del aprobador. Falta, ya con entorno:

- Open XML SDK como ensamblado dependiente dentro del sandbox, y cuánto tarda de verdad. En net462 el paquete se apoya en `WindowsBase`, un ensamblado del framework: comprobar que el sandbox lo tiene.
- Atomicidad de la Custom API: provocar una excepción después de crear filas y comprobar que no queda nada.
- Que `InitiatingUserId` se conserva en el `Update` anidado que hace el plugin como SYSTEM (si no, el actor viaja por `SharedVariables`).
- Que la comparación de claves alternativas no distingue mayúsculas.
- Largo real de los Message-ID que llegan al buzón.
