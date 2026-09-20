# Spike C-05, parte A — Conclusiones

Alcance: solo lectura local con Open XML SDK, como librería .NET + banco de medición. No corre contra el sandbox de Dataverse (bloqueado por autenticación de `pac`, parte B).

> **Historial de revisión** (por eso el diseño de este lector tiene reglas explícitas, LP-01 a LP-08):
> - 1ª vuelta: rechazada, robustez básica frente a contenido corrupto (shared strings malformados, celdas de error, tope de tamaño ausente, comparación de hoja sensible a mayúsculas).
> - 2ª vuelta: rechazada, rendimiento con filas fuera de rango (corte de streaming que materializaba cada fila igual).
> - 3ª vuelta: rechazada, **el corte de streaming de la 2ª vuelta perdía filas útiles en silencio** cuando el archivo no venía ordenado. El problema de fondo era que la orden original no declaraba que el archivo es no confiable; se corrigió (`confianza_entradas: no confiable`) y el diseño pasó a estar fijado por escrito en `diseno/03-contratos-custom-api.md` §7 (reglas LP-01 a LP-08), no por parches sueltos.
>
> Los desvíos 1, 2 y 3 del primer informe del constructor, el manejo de shared strings corruptos, las advertencias de 16+ dígitos y de celdas de error, y la comparación de hoja sin distinguir mayúsculas quedan sin cambios: el revisor los verificó y están bien.

## 1. ¿Open XML SDK lee bien la plantilla REAL con una configuración parametrizada?

**Sí.** `LectorOpenXml` no tiene ninguna posición fija en el código: hoja, fila de encabezado, primera fila, cantidad de filas y, por campo, columna y encabezado esperado, entran todos por `ConfiguracionPlantilla`. Se probó contra una copia de `Inclusiones_Exclusiones en PPP.xlsx` (test `La_plantilla_real_pasa_la_validacion_de_estructura_con_sus_encabezados_reales`): valida los 10 encabezados reales (columnas B a K, fila 12) y confirma que la plantilla distribuible está en blanco (0 filas, como se espera — DD: filas totalmente vacías no generan Fila).

### Rarezas reales encontradas (y cómo se manejaron)

1. **Los encabezados "No. Plan" y "No. Cuenta" traen un espacio final en el propio shared string** (`"No. Plan "`, `"No. Cuenta "` — verificado inspeccionando `xl/sharedStrings.xml`). No es dato de usuario: es el archivo tal cual lo entrega Banca Privada. La comparación de estructura recorta (`Trim()`) ambos lados antes de comparar.
2. **La celda combinada está en la fila 11** (`F11:G11`), no en la fila de encabezado (12) ni en el rango de datos (13-37). No afecta la lectura.
3. **Columnas "No. Plan" y "No. Cuenta" están formateadas como Texto** (`numFmtId="49"`) en la plantilla real, no como Número: el riesgo de `1.2E+15` no se manifiesta hoy, pero el lector igual soporta celdas numéricas de forma robusta porque la configuración es parametrizable. Verificado con `"12.0"` → `"12"`, `"1.6E+16"` → `"16000000000000000"`, y 16 dígitos no triviales `"9.876543210123457E+15"` → `"9876543210123457"`.
4. **La hoja oculta `Listas`** tiene una celda con fórmula (`=UPPER("Atlantida")`, valor cacheado `ATLANTIDA`). El lector nunca la toca (solo abre la hoja `Datos`), y el patrón "usar el valor cacheado, nunca evaluar la fórmula" se prueba con un caso sintético.
5. Comentarios encadenados, `persons` y validaciones de datos con extensión `x14` están presentes y no interfieren.
6. `CellValues` en Open XML SDK 3.x **no es un `enum` de C#**: `switch`/`case` sobre sus miembros no compila (`CS9135`). Se compara con `==`.
7. **Excel solo garantiza 15 dígitos significativos en una celda con formato Número.** Una cuenta de 16 dígitos en una celda Número ya puede llegar redondeada al propio archivo; ningún lector puede recuperar un dígito que Excel ya perdió al guardar. Toda celda **numérica** (no de texto) con 16+ dígitos genera una `AdvertenciaLectura`, no un rechazo silencioso.

## 2. Tiempo y memoria (25, 500, y filas fuera de rango dentro/fuera del tope)

Banco: `dotnet run --project bench -c Release`, **10 corridas por variante** (descartando un warm-up), sobre variantes generadas por código a partir de una copia de la plantilla real. La máquina es compartida: se reporta mediana además de promedio, porque el promedio se deja arrastrar por un vecino ruidoso y la mediana no.

| Variante | Tiempo mediana | Tiempo promedio | Memoria mediana | Recorridas / materializadas |
|---|---|---|---|---|
| 25 filas | ~16.6-45.3 ms (ver nota) | ~18.9-134.9 ms | ~0.90 MB | 37 / 26 |
| 500 filas | ~183-723 ms (ver nota) | ~254-813 ms | ~6.8 MB | 512 / 501 |
| 25 útiles + 4.000 basura (dentro del tope de 5.000 filas recorridas) | ~69.7-94.9 ms | ~95.1-108.5 ms | ~3.6 MB | 4.037 / 26 |
| Supera el tope de 5.000 filas recorridas (rechazo) | ~35.7-37.9 ms | ~39.2-48.1 ms | ~4.2 MB | rechazado antes de terminar |

Nota: dos corridas completas del banco dieron medianas bien distintas para "25 filas" (16.6 ms vs 45.3 ms) y "500 filas" (183 ms vs 723 ms) — la máquina es compartida y hubo una corrida con un pico de 1.7 s en una sola repetición (el máximo de 10, no la mediana). El mínimo entre corridas ronda siempre 12-16 ms (25 filas) y 124-198 ms (500 filas): esa es la cota inferior real del código, no del vecino ruidoso. Los conteos de recorridas/materializadas son estables entre corridas (no dependen de la velocidad de la máquina).

Muy por debajo del presupuesto BP-PP-053 (< 10 s para 25 filas) — pero esto **solo mide el parseo del Excel**, no el pipeline completo de `ValidarSolicitud`. El presupuesto real hay que medirlo con Plugin Profiler sobre el conjunto de steps.

**"Recorridas / materializadas" es la prueba real de que LP-04/LP-05 funcionan**: con 4.000 filas basura fuera de rango, el lector las **recorre** todas (4.037 en total, dentro del tope) pero solo **materializa** (`LoadCurrentElement`, arma el DOM de la fila) las 26 que importan (encabezado + 25 útiles). Recorrer sin materializar es barato; materializar todo no lo es — con 200.000 filas basura materializadas igual (la versión rechazada en la 2ª vuelta), la misma operación tardaba **~1.2 segundos y asignaba ~177 MB** solo para descartarlas después.

### Qué pasó de verdad con el "corte de streaming" (por qué se eliminó, no se ajustó)

La 2ª vuelta agregó una optimización: cortar el recorrido del worksheet apenas se veía una fila fuera de rango, **asumiendo que las filas venían en orden ascendente**. `CONCLUSIONES.md` decía entonces que, si el archivo no venía ordenado, el lector "no cortaba: más lento, pero correcto". **Eso era falso.** La condición real del código no distinguía "no corto por las dudas" de "corto solo si until ahora vi orden ascendente" correctamente: con un archivo de 2 filas donde `<row r="500">` aparece **antes** que `<row r="6">` (la fila útil) en el XML, el corte se disparaba al ver la 500 y la fila 6 — la que importaba — **nunca se leía**. El resultado quedaba `EsValido=True, filas=0`, sin ningún error ni advertencia: la peor clase de bug, silenciosa.

La corrección (LP-05) no fue "arreglar la condición de orden": fue **eliminar la idea de cortar por orden**. Ahora el lector:
- Recorre **todas** las filas del worksheet hasta el tope LP-04 (nunca se detiene antes suponiendo que "ya pasó todo lo que importa").
- Lee el atributo `r="..."` de cada `<row>` **antes** de materializarla (`OpenXmlReader.Attributes`, sin `LoadCurrentElement`) para decidir si está en rango — esa parte de la optimización de la 2ª vuelta sí era válida y se conservó.
- Solo materializa (`LoadCurrentElement`, arma cada `Cell`) las filas que **sí** caen en el rango.

Es decir: la optimización correcta no es "dejar de mirar", es "mirar liviano y materializar solo lo que hace falta". Verificado con el mutation test manual: revertir la condición de rango a la vieja lógica de corte hace fallar `LP05_no_pierde_una_fila_util_que_viene_despues_de_una_fuera_de_rango_en_el_archivo` exactamente con la misma pérdida silenciosa que encontró el revisor; se restauró enseguida.

**Bug adicional encontrado al implementar esto**: `OpenXmlReader` reporta `ElementType == typeof(Row)` tanto en el tag de apertura como en el de cierre de una fila con hijos que no se materializa (sin `LoadCurrentElement`, el recorrido "entra" a la fila para visitar sus celdas y vuelve a pasar por ella al salir). Sin filtrar por `reader.IsStartElement`, una fila fuera de rango se contaba dos veces en `FilasRecorridas`, y leer sus atributos en el tag de cierre tira `InvalidOperationException: The reader is now positioned at the end element tag`. Se agregó el filtro; es la causa de que este spike necesitara una vuelta más de ajuste después de la reescritura inicial de LP-01..08 (detectado por los propios tests nuevos, no por el revisor).

### LP-06: filas y celdas sin atributo `r`

El estándar OOXML permite omitir `r` en `<row>` y en `<c>`; la posición se infiere entonces como la anterior + 1 (primera = 1 para filas, "A" para columnas). El lector lo implementa con aritmética base-26 para columnas (`A=1, B=2, ..., Z=26, AA=27...`). Probado con un archivo donde **ninguna** fila ni celda trae `r` (`LP06_infiere_posicion_de_filas_y_celdas_sin_atributo_r`). No se encontró ningún generador real de `.xlsx` que omita `r` — es una garantía defensiva, no una necesidad observada en la plantilla real.

## 3. Versión de `DocumentFormat.OpenXml` para net462 y tamaño

- **Versión usada: `DocumentFormat.OpenXml` 3.1.0** (+ `DocumentFormat.OpenXml.Framework` 3.1.0). El build `dotnet build src/Sanic.Ppp.Spike.Plantilla -f net462` compila sin errores.
- **Tamaño real para net462**: `DocumentFormat.OpenXml.dll` 6.06 MB + `DocumentFormat.OpenXml.Framework.dll` 0.45 MB = **6.51 MB**.
- **No verificado en esta sesión**: el límite real de tamaño de ensamblado de Dataverse para decidir si 6.51 MB + el resto de `Sanic.Ppp.Plugins` entra cómodo.
- `System.IO.Compression` (LP-03, `ZipArchive`) existe en net462 pero el SDK-style csproj no la referencia por defecto para net4x: hubo que agregar `<Reference Include="System.IO.Compression" />` explícita en el `.csproj` para ese target.

## Reglas de diseño que salieron de este spike

Este spike es el origen directo de `diseno/03-contratos-custom-api.md` §7, "Lector de plantilla: el archivo es hostil hasta que demuestre lo contrario" (LP-01 a LP-08). Implementadas todas, cada una con al menos un test:

| Regla | Qué exige | Dónde vive en el código | Test |
|---|---|---|---|
| LP-01 | Único `try` para todo el trato con Open XML SDK; `catch (Exception)` general → error con motivo; lógica propia siempre afuera | `LeerDesdeBytesEnMemoria` (el único `try`), `LeerDatosCrudosConSdk` (todo lo que toca el SDK) | `LP01_hoja_con_relacion_inexistente_devuelve_error_sin_lanzar_excepcion` |
| LP-02 | Tope de bytes de entrada con copia acotada; nunca `Stream.Length`/`CanSeek` | `CopiarAcotado` | `LP02_tope_de_bytes_de_entrada_aplica_con_stream_no_seekable_cuyo_length_falla`, `LP02_stream_no_seekable_por_debajo_del_tope_se_lee_normalmente` |
| LP-03 | Tope de bytes descomprimidos, sumando el tamaño declarado del zip, antes de abrir con el SDK | `TamanoDescomprimidoDentroDelTope` | `LP03_rechaza_archivo_cuyo_tamano_descomprimido_declarado_supera_el_tope_chico_inyectado` |
| LP-04 | Tope de filas recorridas (no solo útiles) | contador `filasRecorridas` en `LeerDatosCrudosConSdk` | `LP04_rechaza_archivo_que_supera_el_tope_chico_de_filas_recorridas` (+ mutación manual verificada) |
| LP-05 | Prohibido cortar suponiendo orden; solo se materializa lo que cae en rango | bucle principal de `LeerDatosCrudosConSdk` | `LP05_no_pierde_una_fila_util_que_viene_despues_de_una_fuera_de_rango_en_el_archivo` (+ mutación manual verificada) |
| LP-06 | Fila/celda sin `r` = anterior + 1 | `LeerIndiceDeFila`, `SiguienteColumna` | `LP06_infiere_posicion_de_filas_y_celdas_sin_atributo_r` |
| LP-07 | Nada se pierde callado: error o advertencia, nunca silencio | `AdvertenciaLectura`, todos los `LecturaCelda.ConError` | cubierto transversalmente por todos los tests de celdas corruptas/advertencias |
| LP-08 | Tope de celdas por fila | contador `celdasEnFila` en `LeerDatosCrudosConSdk` | `LP08_rechaza_una_fila_que_supera_el_tope_chico_de_celdas_por_fila` |

Los 4 topes viven en `LimitesLectura` (bytes de entrada, bytes descomprimidos, filas recorridas, celdas por fila), inyectables por constructor, con los valores por defecto que propone el diseño (10 MB · 50 MB · 5.000 · 200).

## Incógnita explorada: ¿`ZipArchive` respeta el tamaño declarado cuando el zip miente?

Se armó un experimento local (net8.0, fuera del spike, no queda código): tomar un `.zip` válido creado con `System.IO.Compression.ZipArchive` y parchear a mano, en los bytes crudos, el campo de "tamaño sin comprimir" del *local file header* y del *central directory* (offsets 22 y 24 respectivamente desde la firma de cada uno), sin tocar los datos comprimidos reales.

- **Mintiendo ALTO** (declarar 50.000.000 bytes con un contenido real de 5 bytes): `ZipArchiveEntry.Length` reportó fielmente la mentira (50.000.000), pero al leer el contenido con `entry.Open()` solo salieron los 5 bytes reales. Conclusión: `.Length` es pura metadata, no se valida contra el contenido — **exactamente lo que LP-03 necesita**: sumar `.Length` sin inflar nada es una lectura honesta de lo que el archivo *dice* pesar, y un archivo que miente para arriba se rechaza correctamente (aunque el contenido real fuera inofensivo — falla cerrado, LP-07).
- **Mintiendo BAJO** (declarar 5 bytes con un contenido real de 2.000 bytes, comprimido con Deflate real): al leer con `entry.Open()`, el stream **se cortó en 5 bytes** — no devolvió los 2.000 reales. Esto sugiere que la implementación de `ZipArchiveEntry.Open()` en .NET 8 limita la lectura al tamaño declarado, no al contenido real inflado.

Esto es alentador para LP-03, pero **queda como incógnita para la parte B, no una garantía**:
1. Se verificó en **.NET 8** con `System.IO.Compression.ZipArchive` llamado directamente por este spike. No se verificó en **net462** (el sandbox real de Dataverse), ni es una garantía documentada de Microsoft Learn — es comportamiento observado empíricamente en esta sesión, no una API contractual: podría cambiar entre versiones del runtime.
2. **No se verificó qué hace `DocumentFormat.OpenXml.Packaging.SpreadsheetDocument.Open` internamente** al descomprimir el paquete real — si usa el mismo camino de `ZipArchiveEntry.Open()` (heredando esta protección incidental) o una implementación de paquete OPC propia con otro comportamiento. LP-03 corre **antes** de `SpreadsheetDocument.Open` precisamente para no depender de esto: es una capa de defensa independiente, no una que asuma que el SDK también se protege solo.

## Qué queda por comprobar en la parte B (bloqueada por autenticación de `pac`)

1. Que `DocumentFormat.OpenXml` funcione igual como **ensamblado dependiente** dentro del sandbox real de Dataverse (aislamiento parcial, sin sistema de archivos): esta parte A corrió en un proceso de test/consola de confianza total, no en el sandbox.
2. Tiempo y memoria reales **dentro del sandbox** (no solo en el puesto de trabajo): el sandbox de Dataverse tiene su propio overhead y límites que este spike no reproduce.
3. La atomicidad de `ValidarSolicitud` (03-contratos-custom-api.md §1, paso 2): provocar una excepción real a mitad de la creación de Filas dentro de una Custom API y confirmar que Dataverse revierte todo.
4. El presupuesto de tiempo end-to-end (< 10 s, BP-PP-053) medido con Plugin Profiler sobre el mensaje completo, no solo el parseo.
5. Si 6.51 MB de `DocumentFormat.OpenXml*` más el resto del ensamblado `Sanic.Ppp.Plugins` respeta el límite real de tamaño de Dataverse para plugins con ensamblados dependientes.
6. Cómo se registra exactamente un ensamblado dependiente en el Plugin Registration Tool / `pac plugin push` — no cubierto por `references/dataverse/patrones.md` ni `rendimiento.md`.
7. Si `ZipArchive`/el reader interno de `DocumentFormat.OpenXml` limitan la descompresión real al tamaño declarado también en net462 y dentro del sandbox (ver incógnita arriba) — LP-03 no depende de que esto sea cierto, pero saberlo ayuda a calibrar qué tan redundante es esa capa.
8. Cómo debería reaccionar la regla de registro (`Validacion/IReglaRegistro`) ante una `AdvertenciaLectura` (16+ dígitos, celda de error, etc.) — este spike solo genera la señal, la decisión de rechazar la fila es de diseño, no de este lector.

## Nota del arquitecto (2026-09-18, posterior a la tercera vuelta)

La estrategia de recorrido de este spike quedó **superada por el diseño**. El aprobador corrigió las reglas LP-04, LP-05 y LP-08 de `diseno/03-contratos-custom-api.md` §7: el lector definitivo lee **solo la ventana configurada** en `plantilla.estructura` (hoja, fila de encabezado, primera fila, cantidad de filas, columnas) y deja de leer en la primera fila posterior a la ventana; para que ese corte sea seguro, **exige** orden estrictamente ascendente de filas y celdas y rechaza como inválido el archivo que no lo cumpla. Desaparecen el recorrido completo y los topes de filas recorridas y de celdas por fila; quedan como parámetros el peso comprimido y el descomprimido. Las conclusiones de este spike que siguen valiendo: Open XML SDK lee bien la plantilla real con sus rarezas; los tiempos y la memoria medidos para 25 y 500 filas; el peso de 6,5 MB en net462; las reglas LP-01, LP-02, LP-03, LP-06 y LP-07; las advertencias de celdas numéricas de 16 o más dígitos y de celdas con error. El código de este spike no se lleva al producto: el lector definitivo se construye de nuevo bajo las reglas corregidas.
