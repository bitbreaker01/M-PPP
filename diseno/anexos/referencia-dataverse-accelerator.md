# Anexo: cómo está hecha la Dataverse Accelerator App

Insumo para `05-app-model-driven.md`. Análisis del 2026-09-20, hecho **abriendo la app por dentro en Dev** (consultas de solo lectura) y contrastado con Microsoft Learn. No se vio la app en ejecución: la disposición de las pantallas se infiere de la documentación y de los componentes que usa.

## De qué está hecha (verificado en Dev)

| Pieza | Qué se encontró |
|---|---|
| App | `cat_DataverseCompanionApp`, model-driven. **Su único componente es el sitemap**: no incluye ninguna tabla, formulario ni vista. |
| Sitemap | Un área, un grupo, cuatro entradas: Home, Plugin monitor, API playground y un enlace externo. Íconos SVG de Fluent cargados como web resources (`cat_ic_fluent_flash_28_regular`). |
| Pantallas | **Las tres son custom pages** (`Page="cat_…"`, `canvasapptype = 2`): páginas canvas incrustadas en la app model-driven. |
| Controles | 50 controles PCF del publisher **PowerCAT** (prefijo `cat`): el **Creator Kit** (Fluent UI: `FluentDetailsList`, `CommandBar`, `Nav`, `Pivot`, `Breadcrumb`, `SearchBox`, `Card`, `Elevation`, `Shimmer`, `Spinner`, `SubwayNav`, `TagList`, `Icon`…) más controles hechos a medida para esta app (`DVFluentDetailsList`, `DVCommandBar`, `DVNav`, `DVCodeEditor`). |
| Librería | Una component library canvas, "Power CAT Component Library". |
| Soluciones | `DataverseAccelerator` y `CreatorKitCore` 1.0.20250310.1, managed, publisher PowerCAT. **El Creator Kit ya está instalado en Dev.** |

Microsoft la describe como "a web application built with low-code" y "a demonstration of our platform's powerful low-code capability". No usa nada que no esté al alcance de un proyecto.

## Por qué se ve bien

No es un tema ni un color: es que **no usa la interfaz genérica de model-driven**. De la app model-driven conserva el marco (encabezado, navegación lateral, seguridad, ALM) y reemplaza todo lo demás.

1. **Sin barra de comandos genérica.** Una vista o un formulario nativos traen Nuevo, Eliminar, Asignar, Compartir, Flujo, Exportar a Excel, Enviar vínculo… Una custom page trae un `CommandBar` con los tres o cuatro comandos que esa pantalla necesita.
2. **Sin el marco del formulario.** No hay encabezado de registro, pestañas, selector de vista ni pie de estado.
3. **Navegación plana y por tareas**, no por tablas: cuatro entradas, un solo nivel.
4. **Página de inicio con tarjetas** que llevan a hacer algo ("Crear…"), en vez de caer en una lista.
5. **El detalle se abre en un panel lateral**, sin navegar a otra pantalla: no se pierde el contexto de la lista.
6. **Estados cuidados**: esqueleto de carga (`Shimmer`), y estados vacíos que explican qué pasa y ofrecen el botón para resolverlo.
7. **Filtro en panel y caja de búsqueda**, en vez de selector de vistas y búsqueda avanzada.
8. **Un solo lenguaje visual**: Fluent UI, la misma tipografía, espaciado e íconos que el portal de Power Platform.

## Lo que cuesta, y lo que Microsoft advierte

- **Una custom page es tecnología canvas.** Se construye en Power Apps Studio, con Power Fx; hay que resolver a mano la delegación de consultas, la accesibilidad y los atajos de teclado, que en model-driven nativo vienen dados (Learn, *Recommendations for following design standards*).
- **El Creator Kit no tiene soporte oficial de Microsoft**: no se pueden abrir tickets; el soporte es por GitHub. Learn recomienda textualmente evaluar primero los **controles modernos** y usar el Creator Kit "only when no other options meet your needs". Parte de sus componentes se van a dar de baja a medida que los controles modernos los igualen.
- Los controles **Fluent UI v8 en custom pages están en desuso**; los reemplazan los controles modernos (Learn, *Design a custom page*).
- Si se usa el Creator Kit, `CreatorKitCore` tiene que estar instalado, managed, **en Test y en Prod antes que nuestra solución**: es una dependencia que hay que coordinar con el administrador.
- La propia Dataverse Accelerator está marcada por Microsoft como despriorizada. Sirve de inspiración, no de base.
- La licencia del repositorio del Creator Kit **no se pudo confirmar** en esta revisión; hay que verificarla antes de depender de él (`docs/licencias-terceros.md`).

## Qué se puede tomar sin custom pages

Buena parte de la sensación de limpieza se consigue en model-driven nativo: sitemap de un solo nivel y por tareas; íconos Fluent en SVG; **ocultar los comandos genéricos** que no se usan y dejar solo los propios; formularios de una sola pestaña con pocas secciones; tema de la app; el aspecto moderno (Fluent 2) que ya es el predeterminado.
