# PENDIENTES — documento temporal

Se limpia a medida que se decide. **Cuando quede vacío, se elimina.** Nada de lo que hay acá frena la construcción.

Última actualización: 2026-09-20. El diseño detallado (`00` a `04`) está **revisado completo por el aprobador** y no tiene decisiones abiertas.

## A. Para confirmar con negocio, sin apuro

La matriz de obligatoriedad arranca con **todo obligatorio salvo Referencia** (DD-16). Cuando se quiera flexibilizar, se cambia el parámetro `plantilla.obligatoriedad`; no hay código que tocar. El aprobador va a escribir la versión detallada. Lo ya respondido está en `02-diccionario-datos.md`, DD-12 a DD-17.

## B. Verificaciones contra el entorno

`pac` ya funciona desde la sesión remota con `herramientas/pacx` (perfil `MPPP-DEV`). Verificado: publisher `Sistemas_Abiertos_Nicaragua`, prefijo de opciones `15946`; hay un segundo publisher con prefijo `sanic` ("Sanic Corp") que no se debe usar.

Falta comprobar, al crear los primeros componentes:

- Largo máximo del nombre lógico de tabla (`sanic_mppp_tbl_` ya gasta 15 caracteres).
- Que security role, column security profile y cloud flow no tienen nombre lógico.
- Si una connection reference creada por archivo de solución conserva el nombre exacto, sin sufijo.
- Si el `uniquename` de un parámetro de Custom API exige prefijo de publisher.

## C. Parte B del spike C-05 (dentro de Dataverse)

La parte A quedó cerrada sin tercera revisión, por decisión del aprobador. Falta, ya con entorno:

- Open XML SDK como ensamblado dependiente dentro del sandbox, y cuánto tarda de verdad.
- Atomicidad de la Custom API: provocar una excepción después de crear filas y comprobar que no queda nada.
- Que `InitiatingUserId` se conserva en el `Update` anidado que hace el plugin como SYSTEM (si no, el actor viaja por `SharedVariables`).
- Que la comparación de claves alternativas no distingue mayúsculas.
- Largo real de los Message-ID que llegan al buzón.
