# Pruebas funcionales de la fase 1

Proyecto: `2026-001-referencias-planes-pago` · Entorno: **Dev**

Los 170 componentes de la fase 1 están construidos y verificados **estructuralmente**: existen,
están bien formados y están en la solución. Lo que estas pruebas comprueban es otra cosa, la que
importa: **que hagan lo que el diseño dice que hacen**.

Ningún flujo se ejecutó nunca. Ningún comando de la barra se ejecutó nunca en un navegador.

---

## Cómo está organizado

| Archivo | Qué cubre | Casos |
|---|---|---|
| [`00-preparacion.md`](00-preparacion.md) | Datos, buzón, carpeta. **Se hace una sola vez** | 6 |
| [`01-clasificacion-del-correo.md`](01-clasificacion-del-correo.md) | `MPPP-REC`, `MPPP-ING`, el plugin liviano, reglas de nivel **Correo** | 8 |
| [`02-reglas-de-solicitud.md`](02-reglas-de-solicitud.md) | Reglas de nivel **Solicitud**: adjunto, Excel, estructura, filas | 7 |
| [`03-reglas-de-registro.md`](03-reglas-de-registro.md) | Reglas de nivel **Registro**: las 8 que deciden fila por fila | 14 |
| [`04-comunicaciones.md`](04-comunicaciones.md) | `MPPP-COM`, `MPPP-ENV`: acuse y respuesta final, "como máximo una vez" | 7 |
| [`05-app-y-comandos.md`](05-app-y-comandos.md) | Los 8 comandos de la barra y el diálogo de motivo | 13 |
| [`06-seguridad-vistas-formularios.md`](06-seguridad-vistas-formularios.md) | Roles, perfil de columnas, sitemap, 18 vistas, 9 formularios | 12 |
| [`07-vigilancia.md`](07-vigilancia.md) | `MPPP-VIG`: los 5 bloques de recuperación | 6 |
| [`08-integridad-y-plugins.md`](08-integridad-y-plugins.md) | Steps de plugin, catálogo de reglas, claves únicas | 9 |

**82 casos.** Cada uno trae: qué prueba, cómo hacerlo, **qué tiene que pasar** y cómo verificarlo.

---

## Antes de empezar

1. Corré **[`00-preparacion.md`](00-preparacion.md)** entero. Sin eso, la mitad de los casos no
   tiene sentido: citan planes y autorizaciones que hay que crear.
2. Tené a mano la herramienta de lectura, que evita andar clickeando para ver qué pasó:

   ```bash
   python3 herramientas/pruebas/ver_solicitud.py MPPP-00001234
   python3 herramientas/pruebas/ver_solicitud.py --ultima
   ```

   Muestra, de una sola vez: estado de la Solicitud, sus contadores, **cada regla con su
   resultado y su razón**, las filas con su estado y su mensaje, y la Bitácora completa.

---

## Cómo anotar los resultados

Cada archivo termina con una tabla para llenar. Poné:

- **OK** — pasó exactamente lo esperado
- **FALLA** — pasó otra cosa. Anotá qué pasó, con el número de solicitud
- **N/A** — no se pudo correr, y por qué

**Un caso que "casi" pasa es un FALLA.** Si el estado es el correcto pero el mensaje al cliente
dice otra cosa, es un FALLA: el mensaje lo lee el cliente del banco.

---

## Dos advertencias

**Esto escribe en Dev.** Los casos crean Solicitudes, Filas y Bitácora reales, y mandan correos
reales desde el buzón. Todo con datos ficticios y con planes `PR*` que se borran después
(`preparar_datos.py --limpiar`), pero el ruido en las tablas queda.

**El orden importa dentro de cada archivo.** Varios casos usan la Solicitud que dejó el anterior
(sobre todo en `04` y `05`). Cada caso dice de qué depende.

---

## Qué NO cubren estas pruebas

Para que no haya sorpresas después:

- **Rendimiento real.** `E14-volumen-100.xlsx` mira que 100 filas entren en el presupuesto de
  10 s (`03` §1), pero no es una prueba de carga: son 7.500 filas por mes en producción.
- **Concurrencia.** Dos correos exactamente simultáneos, o dos supervisores aprobando la misma
  fila, no se prueban acá. D-43 sigue abierta.
- **Migración desde SharePoint** (RF-16): es de Producción, no de Dev.
- **Fases 2 y 3** (RPA, histórico).
