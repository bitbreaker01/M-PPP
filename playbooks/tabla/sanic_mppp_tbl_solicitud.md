# Playbook: tabla · sanic_mppp_tbl_solicitud

## 1. Identidad

```json
{
  "tipo_playbook": "tabla",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "3.7",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
  "publisher": "Sistemas_Abiertos_Nicaragua",
  "prefijo": "sanic",
  "abrev": "mppp",
  "prefijo_opciones": 15946,
  "lcid": 1033
}
```

De dónde sale cada dato: `diseno/01-convenciones.md` §0 y §7, verificados contra Dev el 2026-09-20. La tabla está definida en `diseno/02-diccionario-datos.md` §3.1 y figura en `diseno/06-inventario-componentes.md` §3, renglón 3.7.

**`sanic_nombre` no va marcada obligatoria**, aunque siempre tenga valor: la genera la
plataforma (autonumérica). Si se marcara obligatoria quedaría `ApplicationRequired`, y el conector
de Dataverse exige un valor para TODA columna `ApplicationRequired` al crear una fila; el flujo
fallaría pidiendo un dato que nadie digita. Esto vive acá y no en la descripción de la columna: esa
descripción la lee un ejecutivo del banco en la interfaz, no quien construye.

Advertencias: en Dev existe otro publisher con el mismo prefijo de texto, "Sanic Corp", con otro unique name; no es el de este proyecto. El idioma base del entorno es inglés y es el único provisionado: las etiquetas van en español bajo ese LCID.

## 2. Qué se crea

```json
{
  "tipo": "tabla",
  "nombre": "sanic_mppp_tbl_solicitud",
  "displayname": "Solicitud",
  "displayname_plural": "Solicitudes",
  "descripcion": "Correo recibido en el buzón con su plantilla adjunta: es el sobre de la gestión. De ella cuelgan sus filas, los resultados de sus reglas y su bitácora.",
  "propiedad": "usuario",
  "notas": false,
  "actividades": false,
  "auditoria": false,
  "primaria": {
    "nombre": "sanic_nombre",
    "displayname": "Numero",
    "descripcion": "Número de la solicitud. Es lo que se le cita al cliente.",
    "largo": 100,
    "requerida": false,
    "autonumerico": "MPPP-{SEQNUM:8}"
  },
  "columnas": [
    {
      "nombre": "sanic_messageid",
      "displayname": "Message-ID",
      "descripcion": "Identificador del correo (cabecera Message-ID), recortado a 450. Es clave alternativa: garantiza que un correo se ingrese una sola vez.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 450
    },
    {
      "nombre": "sanic_outlookmessageid",
      "displayname": "Identificador en Outlook",
      "descripcion": "Identificador de Outlook del correo después de moverlo a la carpeta de procesados; permite responder en el hilo. Cambia si el correo se mueve.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 500
    },
    {
      "nombre": "sanic_remitente",
      "displayname": "Remitente",
      "descripcion": "Correo electrónico de quien envió la solicitud.",
      "tipo": "texto",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "largo": 320
    },
    {
      "nombre": "sanic_motivoclasificacion",
      "displayname": "Motivo de clasificacion",
      "descripcion": "Por qué el correo fue a Por clasificar. Vacía si se procesó.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 300
    },
    {
      "nombre": "sanic_asunto",
      "displayname": "Asunto",
      "descripcion": "Asunto del correo.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 400
    },
    {
      "nombre": "sanic_fecharecibido",
      "displayname": "Recibido el",
      "descripcion": "Fecha del correo en el buzón. Inicio del tiempo de ciclo.",
      "tipo": "fechahora",
      "requerida": true,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fechaingresada",
      "displayname": "Ingresada el",
      "descripcion": "Alta de la solicitud en Dataverse.",
      "tipo": "fechahora",
      "requerida": true,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_estadoprocesamiento",
      "displayname": "Estado",
      "descripcion": "Estado de procesamiento de la solicitud.",
      "tipo": "choice",
      "requerida": true,
      "protegida": false,
      "auditoria": false,
      "choice": "sanic_mppp_ch_estadosolicitud"
    },
    {
      "nombre": "sanic_fechavalidada",
      "displayname": "Validada el",
      "descripcion": "Cuándo terminó la validación.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fechaacuseiniciado",
      "displayname": "Acuse iniciado el",
      "descripcion": "Se marca antes de enviar el acuse. Si queda iniciado sin enviado, no se reenvía: se levanta para revisión.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fechaacuseenviado",
      "displayname": "Acuse enviado el",
      "descripcion": "Cuándo se envió el acuse al cliente.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_acusecontenido",
      "displayname": "Contenido del acuse",
      "descripcion": "Qué se le dijo al cliente en el acuse.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 1048576
    },
    {
      "nombre": "sanic_fechaprocesada",
      "displayname": "Procesada el",
      "descripcion": "Cuándo todas las filas llegaron a un estado terminal.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_bloqueodecierre",
      "displayname": "Bloqueo de cierre (tecnico)",
      "descripcion": "TECNICA, no es dato de negocio y no va en ningun formulario. El step de post-transicion la escribe ANTES de mirar las filas, para tomar el lock exclusivo de la Solicitud y que dos aprobaciones simultaneas no lean las dos el mismo estado a medias (patron 'pre-lock in a plug-in transaction', Microsoft Learn, Scalable Customization Design). Su VALOR no lo lee nadie; lo unico que importa es el lock que toma al escribirla. Queda fuera de la lista blanca a proposito: solo la escribe el servidor.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fecharespuestafinaliniciada",
      "displayname": "Respuesta final iniciada el",
      "descripcion": "Se marca antes de enviar la respuesta final; mismo mecanismo que el acuse.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_fecharespuestafinalenviada",
      "displayname": "Respuesta final enviada el",
      "descripcion": "Cuándo se envió la respuesta final al cliente.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_respuestafinalcontenido",
      "displayname": "Contenido de la respuesta final",
      "descripcion": "Qué se le dijo al cliente en la respuesta final.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 1048576
    },
    {
      "nombre": "sanic_fechacerrada",
      "displayname": "Cerrada el",
      "descripcion": "Fin del tiempo de ciclo e inicio del plazo de retención.",
      "tipo": "fechahora",
      "requerida": false,
      "protegida": false,
      "auditoria": false
    },
    {
      "nombre": "sanic_correocrudo",
      "displayname": "Correo original",
      "descripcion": "El correo tal como llegó, exportado en formato .eml.",
      "tipo": "archivo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "tamano_kb": 25600
    },
    {
      "nombre": "sanic_exceloriginal",
      "displayname": "Excel original",
      "descripcion": "La plantilla adjunta tal como llegó.",
      "tipo": "archivo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "tamano_kb": 10240
    },
    {
      "nombre": "sanic_cantidadadjuntos",
      "displayname": "Cantidad de adjuntos",
      "descripcion": "Cuántos archivos adjuntos traía el correo.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 1000
    },
    {
      "nombre": "sanic_cantidadexcel",
      "displayname": "Cantidad de Excel",
      "descripcion": "Cuántos de los archivos adjuntos son de Excel. La llena el flujo de ingreso; con ella las reglas del sobre distinguen \"no es Excel\" de \"más de un Excel\" (D-15).",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 1000
    },
    {
      "nombre": "sanic_filastotales",
      "displayname": "Filas totales",
      "descripcion": "Filas con datos leídas de la plantilla.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 100000
    },
    {
      "nombre": "sanic_filasvalidas",
      "displayname": "Filas validas",
      "descripcion": "Filas que pasaron la validación.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 100000
    },
    {
      "nombre": "sanic_filasrechazadas",
      "displayname": "Filas rechazadas",
      "descripcion": "Filas rechazadas en la validación o sin autorización.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 100000
    },
    {
      "nombre": "sanic_versionparametros",
      "displayname": "Version de parametros",
      "descripcion": "Versiones de los parámetros de plantilla usadas para validar esta solicitud.",
      "tipo": "texto",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 200
    },
    {
      "nombre": "sanic_reintentosvalidacion",
      "displayname": "Reintentos de validacion",
      "descripcion": "Veces que el flujo de vigilancia reintentó la validación.",
      "tipo": "entero",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "minimo": 0,
      "maximo": 1000
    },
    {
      "nombre": "sanic_requiererevision",
      "displayname": "Requiere revision",
      "descripcion": "Marca la solicitud para que la revise una persona: envío iniciado sin cerrar, máximo de reintentos o error de la validación.",
      "tipo": "sino",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "etiqueta_si": "Si",
      "etiqueta_no": "No",
      "defecto": false
    },
    {
      "nombre": "sanic_motivorevision",
      "displayname": "Motivo de revision",
      "descripcion": "Por qué la solicitud requiere revisión.",
      "tipo": "memo",
      "requerida": false,
      "protegida": false,
      "auditoria": false,
      "largo": 2000
    }
  ]
}
```

Decisiones que este playbook toma y el diccionario no traía:

| Decisión | Valor | Por qué |
|---|---|---|
| Nombre visible de la primaria | `Numero` | Es el número que se le cita al cliente (`MPPP-00000123`) |
| Nombres visibles de las columnas | los de la sección 2; las fechas se nombran con el hecho y "el" (`Recibido el`, `Cerrada el`) para que en una vista se lean solas | Texto de negocio (`02` DD-19) |
| Rango de las columnas enteras | cantidades de filas: 0 a 100000 (la ventana de lectura es de 100 filas; queda margen); adjuntos y reintentos: 0 a 1000 | El diccionario dice `E` sin rango; se fija uno amplio y sin negativos. Se puede ampliar después |
| Sí/No de `sanic_requiererevision` | `Si` / `No`, por defecto `No` | Una solicitud nace sin necesidad de revisión |
| Tamaño máximo de los archivos | `25600` KB y `10240` KB | 25 MB el correo y 10 MB el Excel (`02` §3.1) |

Viene del diseño, no lo decide este playbook: **auditoría nativa, notas y actividades** = desactivada · no · no (`02` DD-18: es parte de la unidad histórica, que ya lleva su trazabilidad en columnas propias y en la Bitácora).

## 3. Precondiciones

Las de la receta (`patrones.md` §2.2), con estos valores esperados:

| # | Qué tiene que cumplirse | Esperado |
|---|---|---|
| 1 | La solución existe, no es managed, y su publisher coincide en unique name, prefijo y prefijo de opciones | los de la sección 1 |
| 2 | El `lcid` es el idioma base y está provisionado | `1033` en los dos |
| 3 | Cada choice global que usa una columna existe | `sanic_mppp_ch_estadosolicitud` (construidos) |
| 4 | Todo lo que usa el playbook está verificado contra la plataforma | tipos archivo, autonumerico, choice, entero, fechahora, memo, sino, texto; primaria autonumérica: verificados en el ensayo del 2026-09-20 |

Si alguna falla: estado `bloqueado`, no se crea nada.

## 4. Cómo se construye

Receta: `power-platform-construir`, `references/modelo-datos/patrones.md` §2.2 "Tabla con sus columnas". Herramienta del proyecto: `herramientas/construir/tabla.py`.

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_solicitud.md
```

## 5. Verificación

```
python3 herramientas/construir/tabla.py playbooks/tabla/sanic_mppp_tbl_solicitud.md --solo-verificar
python3 herramientas/construir/muestra_tabla.py playbooks/tabla/sanic_mppp_tbl_solicitud.md --guardar
```

| # | Comprobación | Esperado |
|---|---|---|
| 1 | `GET EntityDefinitions(LogicalName='sanic_mppp_tbl_solicitud')` | 200 · `OwnershipType = UserOwned` · `IsManaged = false` · `IsCustomEntity = true` · `HasNotes = false` · `HasActivities = false` · `IsAuditEnabled = false` · `PrimaryNameAttribute = sanic_nombre` |
| 2 | Nombre, plural y descripción en 1033 | los de la sección 2; ninguna etiqueta en otro idioma |
| 3 | Columnas (30): tipo, requerida, protegida, auditoría, nombre visible, descripción y lo propio de su tipo | `sanic_nombre` autonumérico `MPPP-{SEQNUM:8}` (largo 100) requerida · `sanic_messageid` texto 450 requerida · `sanic_outlookmessageid` texto 500 opcional · `sanic_remitente` texto 320 requerida · `sanic_motivoclasificacion` texto 300 opcional · `sanic_asunto` texto 400 opcional · `sanic_fecharecibido` fecha y hora (usuario local) requerida · `sanic_fechaingresada` fecha y hora (usuario local) requerida · `sanic_estadoprocesamiento` choice `sanic_mppp_ch_estadosolicitud` requerida · `sanic_fechavalidada` fecha y hora (usuario local) opcional · `sanic_fechaacuseiniciado` fecha y hora (usuario local) opcional · `sanic_fechaacuseenviado` fecha y hora (usuario local) opcional · `sanic_acusecontenido` multilínea 1048576 opcional · `sanic_fechaprocesada` fecha y hora (usuario local) opcional · `sanic_fecharespuestafinaliniciada` fecha y hora (usuario local) opcional · `sanic_fecharespuestafinalenviada` fecha y hora (usuario local) opcional · `sanic_respuestafinalcontenido` multilínea 1048576 opcional · `sanic_fechacerrada` fecha y hora (usuario local) opcional · `sanic_correocrudo` archivo hasta 25600 KB opcional · `sanic_exceloriginal` archivo hasta 10240 KB opcional · `sanic_cantidadadjuntos` entero 0–1000 opcional · `sanic_cantidadexcel` entero 0–1000 opcional · `sanic_filastotales` entero 0–100000 opcional · `sanic_filasvalidas` entero 0–100000 opcional · `sanic_filasrechazadas` entero 0–100000 opcional · `sanic_versionparametros` texto 200 opcional · `sanic_reintentosvalidacion` entero 0–1000 opcional · `sanic_requiererevision` sí/no (por defecto False) opcional · `sanic_motivorevision` multilínea 2000 opcional · `sanic_bloqueodecierre` fecha y hora (usuario local) opcional, técnica; ninguna auditada |
| 4 | Ninguna columna propia de más | salvo lookups, que nacen con su relación |
| 5 | Pertenece a la solución de la sección 1 | una fila en `solutioncomponents` (tipo de componente 1) |
| 6 | Segunda ejecución sin `--solo-verificar` | estado `ya_existia`, código de salida 0 |
| 7 | Comprobación independiente contra el XML exportado (`muestra_tabla.py`) | `OK`, y la muestra queda en `playbooks/tabla/muestras/` |

## 6. Si ya existe

Se hacen todas las comprobaciones de la sección 5. Si todas pasan: `ya_existia`. Si alguna no: `difiere`, con la diferencia exacta, **sin tocar nada**.

## 7. Reversa

`DELETE EntityDefinitions(LogicalName='sanic_mppp_tbl_solicitud')`, posible mientras la tabla esté vacía y nada la referencie. **Irreversible desde que se crea**: el nombre lógico de la tabla y el de cada columna, el tipo de propiedad (`usuario`), el tipo de cada columna, a qué choice global apunta cada una. Los largos se pueden ampliar después; achicarlos, no.

## 8. Fuera de alcance

- La clave alternativa `sanic_mppp_key_solicitud_messageid`: inventario 5.8.
- Las relaciones parentales hacia Fila, ResultadoRegla y Bitácora: inventario 4.5 a 4.7.
- Las columnas del histórico (archivada, ruta del paquete, reactivada, estado): fase 3.
- La lista blanca de columnas que una persona puede modificar: plugin, inventario 7.8.
- Vistas, formulario y seguridad de la tabla: inventario 12 y 6.
