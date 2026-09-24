# 08 — Integridad, plugins y claves

Cubre los **steps de plugin** que corren al guardar, y que son la red que impide dejar el sistema
en un estado imposible. Son los que protegen contra alguien que escribe por el Web API sin pasar
por la app.

Los ocho tipos registrados:

| Step | Qué protege |
|---|---|
| `NombreCalculadoStep` | el nombre de las tablas que no lo digita nadie |
| `NormalizarYValidarStep` | normaliza y valida al guardar |
| `ListaBlancaStep` | que solo se escriba lo que se puede escribir |
| `TransicionDeFilaStep` | que una transición de estado sea legal |
| `PostTransicionDeFilaStep` | los efectos posteriores (Bitácora, estado de la Solicitud) |
| `AtenderPorClasificarStep` | Atendido y Descartar |
| `IntegridadDeReglaStep` | que el catálogo de reglas sea coherente |
| `IntegridadAutorizacionPlanStep` | que una autorización tenga sentido |

**Cómo se prueban.** Casi todos se prueban **haciendo algo prohibido** y verificando que el sistema
se niegue con un mensaje claro. Un plugin que deja pasar lo prohibido es peor que no tenerlo.

---

## I-01 · El catálogo de reglas: una regla activa sin evaluador

**Qué prueba.** `IntegridadDeReglaStep` (D-13): una regla activa cuyo código no sabe evaluar.

**Cómo.** En **Configuración → Reglas**, creá una regla nueva:

- Código: `REGLA_QUE_NO_EXISTE`
- Nivel: Registro · Efecto: Rechaza · Orden: 90

**Esperado.** **No deja guardar.** El mensaje dice que esa regla no tiene evaluador programado
para su nivel.

**FALLA si** guarda. La próxima validación reventaría con una excepción y todas las Solicitudes
quedarían en Ingresada.

---

## I-02 · Una regla que depende de otra inactiva

**Qué prueba.** `IntegridadDeReglaStep`, segundo caso de D-13.

**Cómo.** Desactivá `PLAN_EXISTE` (que es de la que dependen cuatro reglas).

**Esperado.** **No deja desactivarla**, o no deja guardar la que queda colgando. El mensaje nombra
la dependencia rota.

> Acordate de dejar `PLAN_EXISTE` **activa** al terminar.

---

## I-03 · Una regla de nivel Registro con efecto "Envía a revisión"

**Qué prueba.** D-20: ese efecto solo tiene sentido a nivel Solicitud o Correo.

**Cómo.** Editá `MONEDA_DEL_PLAN` (nivel Registro) y ponele efecto **Envía a revisión**.

**Esperado.** **No deja guardar**, con un mensaje que explique por qué.

> Dejá `MONEDA_DEL_PLAN` con efecto **Rechaza** al terminar.

---

## I-04 · Una regla que depende de sí misma

**Qué prueba.** El defecto que encontró la revisión de código: la autodependencia se rechaza
**por el código**, antes de mirar ningún orden.

**Cómo.** Editá cualquier regla y poné en `sanic_dependede` **su propio código**.

**Esperado.** **No deja guardar**: *"No se puede guardar la regla 'X': no puede depender de sí
misma."*

> Probalo con una regla cuyo `orden` sea el mismo que tendría su "dependencia" — es el caso que una
> prueba mal escrita dejaba pasar por coincidencia.

---

## I-05 · Integridad de una autorización

**Qué prueba.** `IntegridadAutorizacionPlanStep`.

**Cómo.** En **Catálogos → Autorizaciones**, creá una autorización duplicada: el **mismo**
autorizado sobre el **mismo** plan que ya tiene (`TU-CORREO → PR11`).

**Esperado.** **No deja guardar** (clave alternativa o el plugin), con un mensaje entendible y
**no** un volcado técnico de la plataforma.

---

## I-06 · El nombre calculado

**Qué prueba.** `NombreCalculadoStep`.

**Cómo.** Creá una **Autorización** nueva (autorizado `TU-CORREO`, plan `PR06` si no existe ya) y
**no toques el campo Nombre**.

**Esperado.** Al guardar, el nombre queda calculado solo: **`correo → CODIGO`**.

Lo mismo con un **Plan**: el nombre se arma con su código y su cliente.

---

## I-07 · Lista blanca de escrituras

**Qué prueba.** `ListaBlancaStep`: que no se pueda escribir a mano lo que escribe el sistema.

**Cómo.** Abrí una **Fila** en la app e intentá editar a mano una columna que llena la validación
—por ejemplo `sanic_referencia`— y guardar.

**Esperado.** **No deja**, o el campo está de solo lectura en el formulario **y** el plugin lo
rechaza si se intenta por API.

> El formulario de solo lectura no alcanza: la prueba real es por el Web API. Si tenés cómo,
> probá un `PATCH` a esa columna.

---

## I-08 · Transición de estado ilegal

**Qué prueba.** `TransicionDeFilaStep`, que es lo que hace cierto DA-07.

**Cómo.** Sobre una fila en **Validada**, intentá ponerla directo en **Aprobada** (saltándose
Digitada). Hacelo desde el formulario, no con el botón.

**Esperado.** **No deja**: el mensaje dice que esa transición no es válida desde ese estado.

**Este es el caso que demuestra que la seguridad no está en el botón.** Si pasa, alguien con el
Web API puede aprobar lo que quiera.

---

## I-09 · El paquete de plugins está al día

**Qué prueba.** Que el ensamblado en el sandbox sea el del repositorio, y no una versión vieja.

**Cómo.**

```bash
python3 herramientas/construir/paquete_plugins.py playbooks/paquete-plugins/*.md --solo-verificar
```

**Esperado.** `"estado": "ya_existia"` con los **10 tipos** registrados.

> Cuidado con la trampa conocida: el sandbox puede seguir corriendo el binario viejo si no se
> subió el número de build. El síntoma es *"The plug-in type could not be found in the plug-in
> assembly"*, y la señal temprana es un `.nupkg` del mismo tamaño exacto que el anterior.

---

## Resultados

| Caso | Resultado | Notas |
|---|---|---|
| I-01 regla sin evaluador | | |
| I-02 dependencia inactiva | | |
| I-03 efecto inválido por nivel | | |
| I-04 autodependencia | | |
| I-05 autorización duplicada | | |
| I-06 nombre calculado | | |
| I-07 lista blanca | | |
| **I-08 transición ilegal** | | |
| I-09 paquete al día | | |

> Dejá el catálogo de **Reglas** como estaba: `PLAN_EXISTE` activa, `MONEDA_DEL_PLAN` con efecto
> Rechaza, y sin la regla inventada de I-01.
