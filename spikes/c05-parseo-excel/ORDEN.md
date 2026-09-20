# Orden de construcción: spike C-05, parte A (local)

## componente
Lector de la plantilla Excel con Open XML SDK, como librería .NET, más un banco de medición. Es un **spike**: código descartable, conclusiones que quedan. No es el plugin ni toca ningún entorno.

La parte B (correr esto dentro del sandbox de Dataverse como ensamblado dependiente y medir contra el límite de 2 minutos) queda fuera de esta orden: está bloqueada por la autenticación de `pac`.

## Pregunta que el spike tiene que responder
1. ¿Open XML SDK lee bien la plantilla REAL, con sus rarezas, usando una configuración parametrizada (RF-05)?
2. ¿Cuánto tarda y cuánta memoria usa con 25 filas y con 500 filas?
3. ¿Qué versión de `DocumentFormat.OpenXml` sirve para **net462**, y cuántos MB suma con sus dependencias? (el paquete de plugin tiene tope de tamaño)

## especificacion
- `diseno/02-diccionario-datos.md` §2.5 (parámetro `PLANTILLA`, largos vigentes) y §3.2 (campos de la Fila, DD-01: se guarda el texto tal cual lo escribió el cliente).
- `diseno/03-contratos-custom-api.md` §1 y §8 (carpeta `Plantilla/`: `ILectorPlantilla`, `LectorOpenXml`, `ConfiguracionPlantilla`).
- **`diseno/03-contratos-custom-api.md` §7, reglas LP-01 a LP-08: obligatorias.** Agregadas tras dos rechazos del revisor.

## confianza_entradas
**No confiable.** El Excel llega por correo desde fuera del banco. El lector falla cerrado, nunca pierde datos callado, y su tiempo y memoria están acotados por topes explícitos (LP-02, LP-03, LP-04), no por suposiciones sobre el contenido.
- `diseno/01-convenciones.md` §3 y §4 (idioma, `net462;net8.0`, prohibido usar APIs que no existan en net462).
- Plantilla real: `Inclusiones_Exclusiones en PPP.xlsx` (raíz del repo). **No la modifiques**; copiala para generar variantes.

Hechos ya verificados de la plantilla: hoja `Datos`, encabezados en la fila 12 (columnas B a K: Gestión, Clasificación, No. Plan, Nombre Colaborador / Proveedor, Tipo ID, No. Identificación, Referencia, No. Cuenta, Moneda, Banco), datos en las filas 13 a 37, columna A con el número de fila, una celda combinada, comentarios encadenados en los encabezados, validaciones de datos con extensión x14, y una hoja **oculta** `Listas` que tiene una celda con fórmula (`=UPPER("Atlantida")`).

## Comportamiento requerido (un test por cada punto, como mínimo)
- La configuración (hoja, fila de encabezado, primera fila, cantidad de filas, y por campo: letra de columna y encabezado esperado) entra como objeto; **nada de posiciones fijas en el código**.
- Devuelve las filas como texto, con su número de fila de Excel y su número de orden. Las filas totalmente vacías no se devuelven.
- Lee bien: texto compartido (shared strings), texto en línea, números guardados como número (un plan `12` o una cuenta de 16 dígitos **no** pueden salir como `1.2E+15` ni con decimales), celdas con fórmula (usa el valor en caché), celdas vacías en medio de una fila, espacios al inicio o al final (se recortan), ceros a la izquierda en celdas de texto (se conservan).
- Verifica la estructura: si un encabezado no coincide con el esperado, informa cuál y en qué celda, sin lanzar excepción.
- Archivo que no es un xlsx, xlsx corrupto, hoja inexistente: resultado de error con motivo, **sin excepción** (en el diseño eso es una regla fallida, no un fallo del sistema).
- Entrada por `Stream` o `byte[]`, nunca por ruta: en el plugin el archivo viene de una columna de Dataverse.

## referencias
De `power-platform-construir`: `references/dataverse/patrones.md` (solo lo relativo a ensamblados dependientes) y `references/dataverse/rendimiento.md`. Si no cubren paquetes de plugin con dependencias ni Open XML, declaralo como tropiezo candidato.

## destino
Solo dentro de `spikes/c05-parseo-excel/`:
- `src/Sanic.Ppp.Spike.Plantilla/` (librería `net462;net8.0`)
- `tests/Sanic.Ppp.Spike.Plantilla.Tests/` (`net8.0`, xUnit)
- `bench/` (consola `net8.0` que mide tiempo y memoria; genera por código la variante de 500 filas a partir de la plantilla real)
- `CONCLUSIONES.md`

## modo_tdd
estricto

## verificacion
```
cd spikes/c05-parseo-excel && dotnet test --nologo -v q 2>&1 | tail -15
cd spikes/c05-parseo-excel && dotnet build src/Sanic.Ppp.Spike.Plantilla -f net462 --nologo -v q 2>&1 | tail -5
cd spikes/c05-parseo-excel && dotnet run --project bench -c Release 2>&1 | tail -20
```
Correr tests y banco es parte de este spike: medir es su razón de ser.

## Qué debe decir CONCLUSIONES.md
Respuesta a las 3 preguntas con números reales, versión exacta del paquete y tamaño en MB de sus DLL para net462, rarezas de la plantilla que encontraste, y qué queda por comprobar en la parte B.
