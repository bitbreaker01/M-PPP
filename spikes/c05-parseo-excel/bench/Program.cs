using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using Sanic.Ppp.Spike.Plantilla;

namespace Sanic.Ppp.Spike.Plantilla.Bench
{
    /// <summary>
    /// Banco de medicion del spike C-05: responde las 3 preguntas de ORDEN.md con numeros reales.
    /// No toca ningun entorno; todo corre en memoria, contra copias de la plantilla real. La
    /// maquina es compartida: cada variante corre 10 veces y se reporta mediana ademas de
    /// promedio (el promedio baila con un vecino ruidoso, la mediana no).
    /// </summary>
    internal static class Program
    {
        private const int RepeticionesPorVariante = 10;

        private static void Main()
        {
            Console.WriteLine("=== Spike C-05 - banco de medicion ===");
            Console.WriteLine();

            ReportarVersionYTamano();
            Console.WriteLine();

            string rutaFixture = Path.Combine(AppContext.BaseDirectory, "Fixtures", "plantilla-real.xlsx");
            byte[] plantillaOriginal = File.ReadAllBytes(rutaFixture);
            Console.WriteLine($"Plantilla real: {rutaFixture} ({plantillaOriginal.Length / 1024.0:F1} KB)");
            Console.WriteLine();

            ConfiguracionPlantilla config25 = ConfiguracionReal(cantidadFilas: 25);
            ConfiguracionPlantilla config500 = ConfiguracionReal(cantidadFilas: 500);

            byte[] variante25 = GenerarVariante(plantillaOriginal, cantidadFilas: 25);
            byte[] variante500 = GenerarVariante(plantillaOriginal, cantidadFilas: 500);

            Console.WriteLine($"Variante 25 filas: {variante25.Length / 1024.0:F1} KB");
            Console.WriteLine($"Variante 500 filas: {variante500.Length / 1024.0:F1} KB");
            Console.WriteLine();

            MedirLecturaValida("25 filas", variante25, config25, filasEsperadas: 25);
            MedirLecturaValida("500 filas", variante500, config500, filasEsperadas: 500);

            Console.WriteLine();
            Console.WriteLine("--- LP-04/LP-05: filas fuera de rango, dentro y fuera del tope ---");

            byte[] variante25Mas4000Basura = GenerarVarianteConBasura(plantillaOriginal, filasUtiles: 25, filasBasura: 4000);
            Console.WriteLine($"Variante 25 utiles + 4.000 basura (dentro del tope de 5.000 filas recorridas): {variante25Mas4000Basura.Length / 1024.0:F1} KB");
            MedirLecturaValida("25 utiles + 4.000 basura", variante25Mas4000Basura, config25, filasEsperadas: 25);

            byte[] varianteSuperaTope = GenerarVarianteConBasura(plantillaOriginal, filasUtiles: 25, filasBasura: 5200);
            Console.WriteLine($"Variante que supera el tope de filas recorridas (1 encabezado + 25 utiles + 5.200 basura = 5.226 > 5.000): {varianteSuperaTope.Length / 1024.0:F1} KB");
            MedirRechazo("supera el tope de 5.000 filas recorridas (defecto)", varianteSuperaTope, config25);

            Console.WriteLine();
            Console.WriteLine("Presupuesto BP-PP-053: objetivo < 10 s para 25 filas (esto mide solo lectura, no reglas de negocio).");
        }

        private static void ReportarVersionYTamano()
        {
            Assembly ensamblado = typeof(SpreadsheetDocument).Assembly;
            AssemblyInformationalVersionAttribute versionInfo = ensamblado
                .GetCustomAttribute<AssemblyInformationalVersionAttribute>();
            Console.WriteLine("DocumentFormat.OpenXml — paquete NuGet referenciado: 3.1.0");
            Console.WriteLine($"DocumentFormat.OpenXml — version de ensamblado (net8.0, informativa): {versionInfo?.InformationalVersion ?? ensamblado.GetName().Version?.ToString()}");

            (string ruta, long bytes)[] dlls = LocalizarDllsNet462();
            if (dlls.Length == 0)
            {
                Console.WriteLine("net462: no se encontraron los binarios compilados. Corre primero:");
                Console.WriteLine("  dotnet build src/Sanic.Ppp.Spike.Plantilla -f net462");
                return;
            }

            long total = 0;
            Console.WriteLine("Tamano de DocumentFormat.OpenXml* para net462 (lo que suma al paquete del plugin):");
            foreach (var (ruta, bytes) in dlls)
            {
                Console.WriteLine($"  {Path.GetFileName(ruta)}: {bytes / 1024.0 / 1024.0:F2} MB");
                total += bytes;
            }
            Console.WriteLine($"  TOTAL: {total / 1024.0 / 1024.0:F2} MB");
        }

        // Primero busca el build real del proyecto (net462); si no corrio todavia, cae al cache
        // de NuGet como aproximacion (mismo contenido, misma version de paquete).
        private static (string ruta, long bytes)[] LocalizarDllsNet462()
        {
            string[] nombres = { "DocumentFormat.OpenXml.dll", "DocumentFormat.OpenXml.Framework.dll" };

            string[] candidatosBuild =
            {
                Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "src", "Sanic.Ppp.Spike.Plantilla", "bin", "Debug", "net462"),
                Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "src", "Sanic.Ppp.Spike.Plantilla", "bin", "Release", "net462"),
            };

            foreach (string carpeta in candidatosBuild)
            {
                string carpetaAbsoluta = Path.GetFullPath(carpeta);
                if (!Directory.Exists(carpetaAbsoluta)) continue;
                var encontrados = nombres
                    .Select(n => Path.Combine(carpetaAbsoluta, n))
                    .Where(File.Exists)
                    .Select(p => (p, new FileInfo(p).Length))
                    .ToArray();
                if (encontrados.Length == nombres.Length) return encontrados;
            }

            string cacheNuget = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".nuget", "packages");
            var candidatosCache = new[]
            {
                Path.Combine(cacheNuget, "documentformat.openxml", "3.1.0", "lib", "net46", "DocumentFormat.OpenXml.dll"),
                Path.Combine(cacheNuget, "documentformat.openxml.framework", "3.1.0", "lib", "net46", "DocumentFormat.OpenXml.Framework.dll"),
            };
            var encontradosCache = candidatosCache.Where(File.Exists).Select(p => (p, new FileInfo(p).Length)).ToArray();
            return encontradosCache;
        }

        private static ConfiguracionPlantilla ConfiguracionReal(int cantidadFilas)
        {
            return new ConfiguracionPlantilla
            {
                Hoja = "Datos",
                FilaEncabezado = 12,
                PrimeraFila = 13,
                CantidadFilas = cantidadFilas,
                Campos = new List<CampoPlantilla>
                {
                    new CampoPlantilla { Columna = "B", EncabezadoEsperado = "Gestión" },
                    new CampoPlantilla { Columna = "C", EncabezadoEsperado = "Clasificación" },
                    new CampoPlantilla { Columna = "D", EncabezadoEsperado = "No. Plan" },
                    new CampoPlantilla { Columna = "E", EncabezadoEsperado = "Nombre Colaborador / Proveedor" },
                    new CampoPlantilla { Columna = "F", EncabezadoEsperado = "Tipo ID" },
                    new CampoPlantilla { Columna = "G", EncabezadoEsperado = "No. Identificación" },
                    new CampoPlantilla { Columna = "H", EncabezadoEsperado = "Referencia" },
                    new CampoPlantilla { Columna = "I", EncabezadoEsperado = "No. Cuenta" },
                    new CampoPlantilla { Columna = "J", EncabezadoEsperado = "Moneda" },
                    new CampoPlantilla { Columna = "K", EncabezadoEsperado = "Banco" },
                }
            };
        }

        // Genera, a partir de la plantilla real (sin modificarla: todo corre sobre una copia en
        // memoria), una variante con N filas de datos sinteticos pero realistas: mismos
        // encabezados, mismo tipo de celda (texto/shared string) que usa la plantilla real.
        private static byte[] GenerarVariante(byte[] plantillaOriginal, int cantidadFilas)
        {
            string[] gestiones = { "INCLUSION", "EXCLUSION", "MODIFICACION" };
            string[] clasificaciones = { "BAC", "ACH", "CK" };
            string[] bancos = { "BAC", "BANPRO", "FICOHSA", "LAFISE" };
            string[] monedas = { "COR", "USD" };

            using (var stream = new MemoryStream())
            {
                stream.Write(plantillaOriginal, 0, plantillaOriginal.Length);
                stream.Position = 0;

                using (var documento = SpreadsheetDocument.Open(stream, isEditable: true))
                {
                    WorkbookPart workbookPart = documento.WorkbookPart;
                    Sheet hojaDatos = workbookPart.Workbook.Descendants<Sheet>()
                        .First(s => string.Equals(s.Name != null ? s.Name.Value : null, "Datos", StringComparison.Ordinal));
                    var worksheetPart = (WorksheetPart)workbookPart.GetPartById(hojaDatos.Id);
                    SheetData sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>();

                    SharedStringTablePart sstPart = workbookPart.SharedStringTablePart
                        ?? workbookPart.AddNewPart<SharedStringTablePart>();
                    if (sstPart.SharedStringTable == null) sstPart.SharedStringTable = new SharedStringTable();

                    var indiceCache = new Dictionary<string, int>(StringComparer.Ordinal);
                    int siguienteIndice = 0;
                    foreach (SharedStringItem item in sstPart.SharedStringTable.Elements<SharedStringItem>())
                    {
                        indiceCache[item.InnerText] = siguienteIndice;
                        siguienteIndice++;
                    }

                    Func<string, int> internar = texto =>
                    {
                        if (indiceCache.TryGetValue(texto, out int idxExistente)) return idxExistente;
                        int idx = siguienteIndice;
                        sstPart.SharedStringTable.AppendChild(new SharedStringItem(new Text(texto)));
                        indiceCache[texto] = idx;
                        siguienteIndice++;
                        return idx;
                    };

                    // Las filas 13-37 ya existen vacias en la plantilla distribuible: se sacan
                    // para no duplicar indices de fila al generar la variante.
                    foreach (Row filaVieja in sheetData.Elements<Row>()
                        .Where(r => r.RowIndex != null && r.RowIndex.Value >= 13).ToList())
                    {
                        filaVieja.Remove();
                    }

                    for (int i = 0; i < cantidadFilas; i++)
                    {
                        int numeroFila = 13 + i;
                        var fila = new Row { RowIndex = (uint)numeroFila };

                        AgregarCelda(fila, "B", numeroFila, internar(gestiones[i % gestiones.Length]));
                        AgregarCelda(fila, "C", numeroFila, internar(clasificaciones[i % clasificaciones.Length]));
                        AgregarCelda(fila, "D", numeroFila, internar((1000 + i).ToString(CultureInfo.InvariantCulture)));
                        AgregarCelda(fila, "E", numeroFila, internar("Proveedor de prueba " + i.ToString(CultureInfo.InvariantCulture)));
                        AgregarCelda(fila, "F", numeroFila, internar("CNA"));
                        AgregarCelda(fila, "G", numeroFila, internar((100000000 + i).ToString("D9", CultureInfo.InvariantCulture)));
                        AgregarCelda(fila, "H", numeroFila, internar("REF-" + i.ToString(CultureInfo.InvariantCulture)));
                        // 16 digitos, como cuenta bancaria real: la plantilla real la formatea
                        // como texto (numFmtId 49), por eso va como shared string y no como numero.
                        AgregarCelda(fila, "I", numeroFila, internar((1600000000000000L + i).ToString(CultureInfo.InvariantCulture)));
                        AgregarCelda(fila, "J", numeroFila, internar(monedas[i % monedas.Length]));
                        AgregarCelda(fila, "K", numeroFila, internar(bancos[i % bancos.Length]));

                        sheetData.AppendChild(fila);
                    }

                    worksheetPart.Worksheet.Save();
                    workbookPart.Workbook.Save();
                }

                return stream.ToArray();
            }
        }

        // Copia el resultado de GenerarVariante y le agrega filasBasura filas mas, todas fuera
        // del rango configurado (13..12+filasUtiles): para medir LP-04 (tope de filas
        // recorridas) y LP-05 (no materializar lo que esta fuera de rango).
        private static byte[] GenerarVarianteConBasura(byte[] plantillaOriginal, int filasUtiles, int filasBasura)
        {
            byte[] baseVariante = GenerarVariante(plantillaOriginal, filasUtiles);

            using (var stream = new MemoryStream())
            {
                stream.Write(baseVariante, 0, baseVariante.Length);
                stream.Position = 0;

                using (var documento = SpreadsheetDocument.Open(stream, isEditable: true))
                {
                    WorkbookPart workbookPart = documento.WorkbookPart;
                    Sheet hojaDatos = workbookPart.Workbook.Descendants<Sheet>()
                        .First(s => string.Equals(s.Name != null ? s.Name.Value : null, "Datos", StringComparison.Ordinal));
                    var worksheetPart = (WorksheetPart)workbookPart.GetPartById(hojaDatos.Id);
                    SheetData sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>();

                    SharedStringTablePart sstPart = workbookPart.SharedStringTablePart;
                    int indiceBasura = sstPart.SharedStringTable.Elements<SharedStringItem>().Count();
                    sstPart.SharedStringTable.AppendChild(new SharedStringItem(new Text("basura")));

                    int primeraFilaBasura = 13 + filasUtiles;
                    for (int i = 0; i < filasBasura; i++)
                    {
                        int numeroFila = primeraFilaBasura + i;
                        var fila = new Row { RowIndex = (uint)numeroFila };
                        AgregarCelda(fila, "C", numeroFila, indiceBasura);
                        sheetData.AppendChild(fila);
                    }

                    worksheetPart.Worksheet.Save();
                    workbookPart.Workbook.Save();
                }

                return stream.ToArray();
            }
        }

        private static void AgregarCelda(Row fila, string columna, int numeroFila, int indiceCompartido)
        {
            fila.AppendChild(new Cell
            {
                CellReference = columna + numeroFila.ToString(CultureInfo.InvariantCulture),
                DataType = CellValues.SharedString,
                CellValue = new CellValue(indiceCompartido.ToString(CultureInfo.InvariantCulture))
            });
        }

        private static void MedirLecturaValida(string etiqueta, byte[] xlsx, ConfiguracionPlantilla config, int filasEsperadas)
        {
            var lector = new LectorOpenXml();
            ResultadoLecturaPlantilla ultimo = null;
            MedicionRepetida medicion = Medir(() => ultimo = lector.Leer(xlsx, config));

            Console.WriteLine($"--- {etiqueta} ---");
            Console.WriteLine($"  EsValido: {ultimo.EsValido} | filas leidas: {ultimo.Filas.Count} (esperadas: {filasEsperadas}) | recorridas: {ultimo.FilasRecorridas} | materializadas: {ultimo.FilasMaterializadas}");
            ReportarMedicion(medicion);
        }

        private static void MedirRechazo(string etiqueta, byte[] xlsx, ConfiguracionPlantilla config)
        {
            var lector = new LectorOpenXml();
            ResultadoLecturaPlantilla ultimo = null;
            MedicionRepetida medicion = Medir(() => ultimo = lector.Leer(xlsx, config));

            Console.WriteLine($"--- {etiqueta} ---");
            Console.WriteLine($"  EsValido: {ultimo.EsValido} | motivo: {(ultimo.Errores.Count > 0 ? ultimo.Errores[0] : "(ninguno)")}");
            ReportarMedicion(medicion);
        }

        private static MedicionRepetida Medir(Action accion)
        {
            // Descartado: solo para forzar JIT/warm-up, no entra en la medicion.
            accion();

            var tiempos = new List<double>();
            var asignados = new List<long>();

            for (int i = 0; i < RepeticionesPorVariante; i++)
            {
                GC.Collect();
                GC.WaitForPendingFinalizers();
                GC.Collect();

                long asignadoAntes = GC.GetAllocatedBytesForCurrentThread();
                var cronometro = Stopwatch.StartNew();

                accion();

                cronometro.Stop();
                long asignadoDespues = GC.GetAllocatedBytesForCurrentThread();

                tiempos.Add(cronometro.Elapsed.TotalMilliseconds);
                asignados.Add(asignadoDespues - asignadoAntes);
            }

            return new MedicionRepetida { Tiempos = tiempos, Asignados = asignados };
        }

        private static void ReportarMedicion(MedicionRepetida medicion)
        {
            double promedioMs = medicion.Tiempos.Average();
            double medianaMs = Mediana(medicion.Tiempos);
            double minMs = medicion.Tiempos.Min();
            double maxMs = medicion.Tiempos.Max();
            double asignadoPromedioMb = medicion.Asignados.Average() / 1024.0 / 1024.0;
            double asignadoMedianaMb = Mediana(medicion.Asignados.Select(a => (double)a).ToList()) / 1024.0 / 1024.0;

            Console.WriteLine($"  Tiempo: mediana {medianaMs:F2} ms | promedio {promedioMs:F2} ms | min {minMs:F2} ms | max {maxMs:F2} ms (de {RepeticionesPorVariante} corridas)");
            Console.WriteLine($"  Memoria asignada por corrida: mediana {asignadoMedianaMb:F3} MB | promedio {asignadoPromedioMb:F3} MB");
        }

        private static double Mediana(List<double> valores)
        {
            List<double> ordenados = valores.OrderBy(v => v).ToList();
            int n = ordenados.Count;
            if (n % 2 == 1) return ordenados[n / 2];
            return (ordenados[n / 2 - 1] + ordenados[n / 2]) / 2.0;
        }

        private sealed class MedicionRepetida
        {
            public List<double> Tiempos { get; set; }
            public List<long> Asignados { get; set; }
        }
    }
}
