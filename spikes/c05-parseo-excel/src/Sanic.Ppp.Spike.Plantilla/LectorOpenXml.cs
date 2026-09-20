using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;

namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Lee una plantilla Excel con Open XML SDK. El archivo es hostil hasta que demuestre lo
    /// contrario (03-contratos-custom-api.md #7, LP-01 a LP-08): llega por correo desde fuera
    /// del banco, y aunque el remitente este autorizado su cuenta puede estar comprometida.
    ///
    /// Reglas de este archivo:
    /// - Todo lo que viene del contenido del .xlsx se parsea con TryParse, nunca con Parse.
    /// - Todo el trato con una libreria de terceros que procesa el contenido hostil (Open XML
    ///   SDK, System.IO.Compression) vive dentro de un unico try con catch general (LP-01); la
    ///   logica propia (validar encabezados, armar el resultado, contar advertencias) queda
    ///   SIEMPRE afuera de esos try, para que un bug nuestro no se disfrace de archivo corrupto.
    /// - Nada se pierde callado: o es error del archivo, o es advertencia con celda y motivo
    ///   (LP-07). Nunca se optimiza suponiendo algo sobre el contenido (LP-05).
    /// </summary>
    public sealed class LectorOpenXml : ILectorPlantilla
    {
        private readonly LimitesLectura _limites;

        public LectorOpenXml() : this(new LimitesLectura()) { }

        public LectorOpenXml(LimitesLectura limites)
        {
            _limites = limites ?? throw new ArgumentNullException(nameof(limites));
        }

        public ResultadoLecturaPlantilla Leer(Stream excel, ConfiguracionPlantilla configuracion)
        {
            if (excel == null) throw new ArgumentNullException(nameof(excel));
            if (configuracion == null) throw new ArgumentNullException(nameof(configuracion));

            // LP-02: tope de bytes de entrada con copia acotada. Nunca Stream.Length/CanSeek:
            // un stream no seekable (tipico de una descarga) no los soporta de forma confiable.
            byte[] contenido;
            string errorTamano;
            if (!CopiarAcotado(excel, _limites.TamanoMaximoBytesEntrada, out contenido, out errorTamano))
                return ResultadoLecturaPlantilla.ConError(errorTamano);

            return LeerDesdeBytesEnMemoria(contenido, configuracion);
        }

        public ResultadoLecturaPlantilla Leer(byte[] excel, ConfiguracionPlantilla configuracion)
        {
            if (excel == null) throw new ArgumentNullException(nameof(excel));
            if (configuracion == null) throw new ArgumentNullException(nameof(configuracion));

            // Un byte[] ya esta completo en memoria: su Length es un dato del CLR, no una
            // promesa de un stream externo que puede no cumplirse. No hace falta copia acotada.
            if (excel.LongLength > _limites.TamanoMaximoBytesEntrada)
                return ResultadoLecturaPlantilla.ConError(FormatoTamanoEntradaExcedido(excel.LongLength));

            return LeerDesdeBytesEnMemoria(excel, configuracion);
        }

        // LP-02: lee como mucho maximo + 1 bytes a memoria. Si el stream tiene mas, se corta ahi
        // mismo: nunca se sigue leyendo un stream hostil "a ver hasta donde llega".
        private static bool CopiarAcotado(Stream origen, long maximoBytes, out byte[] contenido, out string error)
        {
            contenido = null;
            error = null;

            using (var destino = new MemoryStream())
            {
                byte[] buffer = new byte[65536];
                long totalLeido = 0;
                int leidos;

                while ((leidos = origen.Read(buffer, 0, buffer.Length)) > 0)
                {
                    totalLeido += leidos;
                    if (totalLeido > maximoBytes)
                    {
                        error = FormatoTamanoEntradaExcedidoStream(maximoBytes);
                        return false;
                    }
                    destino.Write(buffer, 0, leidos);
                }

                contenido = destino.ToArray();
                return true;
            }
        }

        private static string FormatoTamanoEntradaExcedido(long bytesReales)
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "El archivo pesa {0} bytes, supera el tope configurado de bytes de entrada.",
                bytesReales);
        }

        private static string FormatoTamanoEntradaExcedidoStream(long maximoBytes)
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "El archivo supera el tope configurado de {0} bytes de entrada.",
                maximoBytes);
        }

        private ResultadoLecturaPlantilla LeerDesdeBytesEnMemoria(byte[] contenido, ConfiguracionPlantilla configuracion)
        {
            // LP-03: tope de bytes descomprimidos, ANTES de intentar abrir con el SDK. El
            // tamano comprimido del zip no protege de nada (una plantilla de pocos MB puede
            // inflar a GB de XML). Es su propio try: System.IO.Compression tambien procesa
            // contenido hostil y puede tirar excepciones que no nos interesa enumerar.
            string errorZip;
            if (!TamanoDescomprimidoDentroDelTope(contenido, _limites.TamanoMaximoBytesDescomprimidos, out errorZip))
                return ResultadoLecturaPlantilla.ConError(errorZip);

            // LP-01: unico try para TODO el trato con Open XML SDK (abrir, ubicar partes,
            // recorrer). Cualquier excepcion se convierte en error del archivo, salvo las que
            // no tiene sentido atrapar (memoria agotada, stack overflow, thread abortado).
            DatosCrudosPlantilla datos;
            try
            {
                datos = LeerDatosCrudosConSdk(contenido, configuracion, _limites);
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                return ResultadoLecturaPlantilla.ConError($"archivo invalido: {ex.Message}");
            }

            if (datos.Error != null)
                return ResultadoLecturaPlantilla.ConError(datos.Error);

            // A partir de aca: logica propia, nada toca el SDK ni System.IO.Compression.
            string errorCelda;
            List<string> erroresEncabezado = ValidarEncabezados(configuracion, datos.CeldasPorFila, out errorCelda);
            if (errorCelda != null)
                return ResultadoLecturaPlantilla.ConError(errorCelda);
            if (erroresEncabezado.Count > 0)
                return ResultadoLecturaPlantilla.ConErrores(erroresEncabezado);

            List<AdvertenciaLectura> advertencias;
            List<FilaPlantilla> filas = LeerFilasDeDatos(configuracion, datos.CeldasPorFila, out errorCelda, out advertencias);
            if (errorCelda != null)
                return ResultadoLecturaPlantilla.ConError(errorCelda);

            return ResultadoLecturaPlantilla.ConFilas(filas, advertencias, datos.FilasRecorridas, datos.FilasMaterializadas);
        }

        // LP-03: suma el tamano DECLARADO (metadata del zip, sin inflar nada) de cada entrada.
        private static bool TamanoDescomprimidoDentroDelTope(byte[] contenido, long maximoBytesDescomprimidos, out string error)
        {
            error = null;
            try
            {
                using (var stream = new MemoryStream(contenido, writable: false))
                using (var zip = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    long totalDeclarado = 0;
                    foreach (ZipArchiveEntry entrada in zip.Entries)
                    {
                        totalDeclarado += entrada.Length;
                        if (totalDeclarado > maximoBytesDescomprimidos)
                        {
                            error = string.Format(
                                CultureInfo.InvariantCulture,
                                "El archivo supera el tope de {0} bytes descomprimidos (declarado en el zip).",
                                maximoBytesDescomprimidos);
                            return false;
                        }
                    }
                }
                return true;
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                error = $"archivo invalido: {ex.Message}";
                return false;
            }
        }

        // ---- Todo lo de aca para abajo hasta CapturarCeldaCruda toca el SDK: vive dentro del
        // try de LeerDesdeBytesEnMemoria (LP-01). Solo devuelve datos propios (CeldaCruda,
        // strings, ints), nunca tipos de Open XML, para que lo que sigue despues del try sea
        // indiscutiblemente logica nuestra. ----

        private static DatosCrudosPlantilla LeerDatosCrudosConSdk(byte[] contenido, ConfiguracionPlantilla configuracion, LimitesLectura limites)
        {
            using (var stream = new MemoryStream(contenido, writable: false))
            using (var documento = SpreadsheetDocument.Open(stream, isEditable: false))
            {
                WorkbookPart workbookPart = documento.WorkbookPart;
                if (workbookPart == null)
                    return DatosCrudosPlantilla.ConError("El archivo no tiene un WorkbookPart (no es un libro de Excel valido).");

                string hojaBuscada = (configuracion.Hoja ?? string.Empty).Trim();
                Sheet hoja = workbookPart.Workbook.Descendants<Sheet>()
                    .FirstOrDefault(s => string.Equals(ObtenerNombreHoja(s), hojaBuscada, StringComparison.OrdinalIgnoreCase));
                if (hoja == null)
                    return DatosCrudosPlantilla.ConError($"No existe la hoja '{configuracion.Hoja}' en el archivo.");

                var worksheetPart = workbookPart.GetPartById(hoja.Id) as WorksheetPart;
                if (worksheetPart == null)
                    return DatosCrudosPlantilla.ConError($"La hoja '{configuracion.Hoja}' no tiene contenido de worksheet.");

                string[] textosCompartidos = ObtenerTextosCompartidos(workbookPart);

                int filaEncabezado = configuracion.FilaEncabezado;
                int primeraFila = configuracion.PrimeraFila;
                int filaHasta = configuracion.PrimeraFila + configuracion.CantidadFilas - 1;

                var celdasPorFila = new Dictionary<int, Dictionary<string, CeldaCruda>>();
                int filasRecorridas = 0;
                int filasMaterializadas = 0;
                int ultimaFilaResuelta = 0; // LP-06: primera fila sin r = anterior(0) + 1 = 1

                using (OpenXmlReader reader = OpenXmlReader.Create(worksheetPart))
                {
                    // LP-05: se recorren TODAS las filas hasta el tope LP-04. Nunca se corta
                    // suponiendo que, al ver una fuera de rango, ya no queda ninguna util: eso
                    // perdia en silencio una fila que venia despues en el archivo.
                    while (reader.Read())
                    {
                        // OpenXmlReader.Read() reporta ElementType == typeof(Row) tanto en el
                        // tag de apertura como en el de cierre de una fila con hijos que no se
                        // materializo (LoadCurrentElement consume hasta el cierre; sin eso, el
                        // recorrido "entra" a la fila y vuelve a pasar por ella al salir). Sin
                        // este filtro, una fila fuera de rango se contaba dos veces y leer sus
                        // atributos en el cierre tira InvalidOperationException.
                        if (reader.ElementType != typeof(Row) || !reader.IsStartElement) continue;

                        filasRecorridas++;
                        if (filasRecorridas > limites.MaximoFilasRecorridas)
                        {
                            return DatosCrudosPlantilla.ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "El archivo supera el tope de {0} filas recorridas.", limites.MaximoFilasRecorridas));
                        }

                        // Se lee el atributo r ANTES de materializar (LoadCurrentElement): asi
                        // no se paga el costo de armar la fila completa cuando esta fuera de
                        // rango. LP-06: sin r, la posicion es la de la fila anterior + 1.
                        int? indiceExplicito = LeerIndiceDeFila(reader.Attributes);
                        int indice = indiceExplicito ?? (ultimaFilaResuelta + 1);
                        ultimaFilaResuelta = indice;

                        bool dentroDeRango = indice == filaEncabezado || (indice >= primeraFila && indice <= filaHasta);
                        if (!dentroDeRango) continue;

                        Row fila = (Row)reader.LoadCurrentElement();
                        filasMaterializadas++;

                        var celdas = new Dictionary<string, CeldaCruda>(StringComparer.Ordinal);
                        string ultimaColumnaResuelta = null;
                        int celdasEnFila = 0;

                        foreach (Cell celda in fila.Elements<Cell>())
                        {
                            celdasEnFila++;
                            if (celdasEnFila > limites.MaximoCeldasPorFila)
                            {
                                return DatosCrudosPlantilla.ConError(string.Format(
                                    CultureInfo.InvariantCulture,
                                    "La fila {0} supera el tope de {1} celdas por fila.", indice, limites.MaximoCeldasPorFila));
                            }

                            string columnaExplicita = ObtenerLetraColumna(celda.CellReference != null ? celda.CellReference.Value : null);
                            string columna = columnaExplicita ?? SiguienteColumna(ultimaColumnaResuelta); // LP-06
                            ultimaColumnaResuelta = columna;

                            celdas[columna] = CapturarCeldaCruda(
                                columna + indice.ToString(CultureInfo.InvariantCulture), celda);
                        }

                        celdasPorFila[indice] = celdas;
                    }
                }

                return DatosCrudosPlantilla.ConDatos(celdasPorFila, textosCompartidos, filasRecorridas, filasMaterializadas);
            }
        }

        private static string ObtenerNombreHoja(Sheet sheet)
        {
            string nombre = sheet.Name != null ? sheet.Name.Value : null;
            return (nombre ?? string.Empty).Trim();
        }

        private static string[] ObtenerTextosCompartidos(WorkbookPart workbookPart)
        {
            SharedStringTablePart parte = workbookPart.SharedStringTablePart;
            if (parte == null || parte.SharedStringTable == null)
                return Array.Empty<string>();

            return parte.SharedStringTable.Elements<SharedStringItem>()
                .Select(item => item.InnerText)
                .ToArray();
        }

        private static int? LeerIndiceDeFila(IEnumerable<OpenXmlAttribute> atributos)
        {
            foreach (OpenXmlAttribute atributo in atributos)
            {
                if (!string.Equals(atributo.LocalName, "r", StringComparison.Ordinal)) continue;

                int valor;
                if (int.TryParse(atributo.Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out valor))
                    return valor;

                return null; // r presente pero no numerico: se trata igual que ausente (LP-06)
            }

            return null; // r ausente
        }

        private static CeldaCruda CapturarCeldaCruda(string referencia, Cell celda)
        {
            TipoCeldaCruda tipo;
            string valorCrudo;

            if (celda.DataType != null && celda.DataType.Value == CellValues.SharedString)
            {
                tipo = TipoCeldaCruda.SharedString;
                valorCrudo = celda.CellValue != null ? celda.CellValue.Text : null;
            }
            else if (celda.DataType != null && celda.DataType.Value == CellValues.InlineString)
            {
                tipo = TipoCeldaCruda.InlineString;
                valorCrudo = celda.InlineString != null
                    ? (celda.InlineString.Text != null ? celda.InlineString.Text.Text : celda.InlineString.InnerText)
                    : null;
            }
            else if (celda.DataType != null && celda.DataType.Value == CellValues.String)
            {
                tipo = TipoCeldaCruda.TextoFormula;
                valorCrudo = celda.CellValue != null ? celda.CellValue.Text : null;
            }
            else if (celda.DataType != null && celda.DataType.Value == CellValues.Boolean)
            {
                tipo = TipoCeldaCruda.Boolean;
                valorCrudo = celda.CellValue != null ? celda.CellValue.Text : null;
            }
            else if (celda.DataType != null && celda.DataType.Value == CellValues.Error)
            {
                tipo = TipoCeldaCruda.Error;
                valorCrudo = celda.CellValue != null ? celda.CellValue.Text : null;
            }
            else
            {
                tipo = TipoCeldaCruda.Numerico;
                valorCrudo = celda.CellValue != null ? celda.CellValue.Text : null;
            }

            return new CeldaCruda { Referencia = referencia, Tipo = tipo, ValorCrudo = valorCrudo };
        }

        private static string ObtenerLetraColumna(string referenciaCelda)
        {
            if (string.IsNullOrEmpty(referenciaCelda)) return null;

            int i = 0;
            while (i < referenciaCelda.Length && !char.IsDigit(referenciaCelda[i])) i++;
            return i > 0 ? referenciaCelda.Substring(0, i) : null;
        }

        // LP-06: columna anterior + 1, primera = A. Aritmetica base-26 de columnas de Excel
        // (A=1, B=2, ..., Z=26, AA=27...).
        private static string SiguienteColumna(string columnaAnterior)
        {
            int valor = string.IsNullOrEmpty(columnaAnterior) ? 0 : ColumnaANumero(columnaAnterior);
            return NumeroAColumna(valor + 1);
        }

        private static int ColumnaANumero(string columna)
        {
            int resultado = 0;
            foreach (char c in columna)
                resultado = resultado * 26 + (c - 'A' + 1);
            return resultado;
        }

        private static string NumeroAColumna(int numero)
        {
            var letras = new System.Text.StringBuilder();
            while (numero > 0)
            {
                int resto = (numero - 1) % 26;
                letras.Insert(0, (char)('A' + resto));
                numero = (numero - 1) / 26;
            }
            return letras.ToString();
        }

        // ---- De aca para abajo: pura logica propia, ningun tipo de Open XML SDK. Opera sobre
        // CeldaCruda (nuestro), nunca sobre Cell (del SDK). ----

        private static List<string> ValidarEncabezados(
            ConfiguracionPlantilla configuracion,
            Dictionary<int, Dictionary<string, CeldaCruda>> celdasPorFila,
            out string errorCelda)
        {
            errorCelda = null;
            var errores = new List<string>();
            celdasPorFila.TryGetValue(configuracion.FilaEncabezado, out Dictionary<string, CeldaCruda> encabezados);

            foreach (CampoPlantilla campo in configuracion.Campos)
            {
                CeldaCruda celda = null;
                if (encabezados != null) encabezados.TryGetValue(campo.Columna, out celda);

                LecturaCelda lectura = InterpretarCelda(celda);
                if (lectura.Error != null)
                {
                    errorCelda = lectura.Error;
                    return errores;
                }

                string encontrado = lectura.Texto.Trim();
                string esperado = (campo.EncabezadoEsperado ?? string.Empty).Trim();

                if (!string.Equals(encontrado, esperado, StringComparison.Ordinal))
                {
                    errores.Add(string.Format(
                        CultureInfo.InvariantCulture,
                        "columna {0}{1}: se esperaba '{2}', se encontro '{3}'",
                        campo.Columna, configuracion.FilaEncabezado, esperado, encontrado));
                }
            }

            return errores;
        }

        private static List<FilaPlantilla> LeerFilasDeDatos(
            ConfiguracionPlantilla configuracion,
            Dictionary<int, Dictionary<string, CeldaCruda>> celdasPorFila,
            out string errorCelda,
            out List<AdvertenciaLectura> advertencias)
        {
            errorCelda = null;
            advertencias = new List<AdvertenciaLectura>();
            var filas = new List<FilaPlantilla>();
            int orden = 0;
            int filaHasta = configuracion.PrimeraFila + configuracion.CantidadFilas - 1;

            for (int indice = configuracion.PrimeraFila; indice <= filaHasta; indice++)
            {
                celdasPorFila.TryGetValue(indice, out Dictionary<string, CeldaCruda> celdasFila);

                var valores = new Dictionary<string, string>(StringComparer.Ordinal);
                bool tieneAlgunValor = false;

                foreach (CampoPlantilla campo in configuracion.Campos)
                {
                    CeldaCruda celda = null;
                    if (celdasFila != null) celdasFila.TryGetValue(campo.Columna, out celda);

                    LecturaCelda lectura = InterpretarCelda(celda);
                    if (lectura.Error != null)
                    {
                        errorCelda = lectura.Error;
                        return new List<FilaPlantilla>();
                    }

                    if (lectura.Advertencia != null)
                    {
                        advertencias.Add(new AdvertenciaLectura
                        {
                            NumeroFilaExcel = indice,
                            Columna = campo.Columna,
                            Motivo = lectura.Advertencia
                        });
                    }

                    valores[campo.Columna] = lectura.Texto;
                    if (!string.IsNullOrEmpty(lectura.Texto)) tieneAlgunValor = true;
                }

                if (!tieneAlgunValor) continue;

                orden++;
                filas.Add(new FilaPlantilla { NumeroFilaExcel = indice, NumeroOrden = orden, Valores = valores });
            }

            return filas;
        }

        private static LecturaCelda InterpretarCelda(CeldaCruda celda)
        {
            if (celda == null) return LecturaCelda.ConTexto(string.Empty);

            string referencia = celda.Referencia ?? "?";
            string crudo = celda.ValorCrudo;

            if (celda.Tipo == TipoCeldaCruda.SharedStringResuelto)
            {
                // El indice ya se valido y resolvio a texto dentro del try de LP-01 (es el
                // unico lugar que conoce la tabla de shared strings). Aca solo queda recortar.
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.InlineString)
            {
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.TextoFormula)
            {
                // Resultado de formula tipo texto: el valor cacheado ya vino en CellValue.
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.Boolean)
            {
                return LecturaCelda.ConTexto(crudo == "1" ? "1" : "0");
            }

            if (celda.Tipo == TipoCeldaCruda.Error)
            {
                // #REF!, #N/A, #VALUE!... no es un fallo del lector: se devuelve tal cual y se
                // marca como advertencia para que una regla de registro la rechace con motivo.
                string textoError = (crudo ?? string.Empty).Trim();
                return LecturaCelda.ConTextoYAdvertencia(textoError, string.Format(
                    CultureInfo.InvariantCulture,
                    "celda {0}: tiene un valor de error de Excel ('{1}')", referencia, textoError));
            }

            // Numerico (default de Open XML), con o sin formula: el valor cacheado esta igual
            // en CellValue.
            string textoNumero = FormatearNumero(crudo).Trim();
            int digitos = ContarDigitos(textoNumero);
            if (digitos >= 16)
            {
                // Excel solo garantiza 15 digitos significativos en una celda con formato
                // Numero: un valor de 16+ digitos pudo haber llegado ya redondeado al archivo,
                // y ningun lector puede recuperar lo que Excel ya perdio (ver CONCLUSIONES.md).
                return LecturaCelda.ConTextoYAdvertencia(textoNumero, string.Format(
                    CultureInfo.InvariantCulture,
                    "celda {0}: {1} digitos en una celda numerica (no de texto); Excel solo garantiza 15 digitos significativos, puede venir redondeada",
                    referencia, digitos));
            }
            return LecturaCelda.ConTexto(textoNumero);
        }

        // Open XML puede serializar numeros grandes o resultados de formula en notacion
        // cientifica dentro del propio XML (ej "1.6E+16"); nunca se muestra asi (comportamiento
        // requerido de la orden). Con decimal (28-29 digitos significativos), no con double
        // (~15-17, con redondeo real a partir de 2^53): un entero largo se pierde con double.
        // Un valor entero en texto plano (sin 'e'/'.') se devuelve tal cual, sin parsear nada.
        private static string FormatearNumero(string crudo)
        {
            if (string.IsNullOrEmpty(crudo)) return string.Empty;

            if (crudo.IndexOfAny(new[] { 'e', 'E', '.' }) < 0)
                return crudo;

            decimal valor;
            if (!decimal.TryParse(crudo, NumberStyles.Float, CultureInfo.InvariantCulture, out valor))
                return crudo;

            return valor.ToString("0.###############", CultureInfo.InvariantCulture);
        }

        private static int ContarDigitos(string texto)
        {
            if (string.IsNullOrEmpty(texto)) return 0;

            int contador = 0;
            for (int i = 0; i < texto.Length; i++)
                if (char.IsDigit(texto[i])) contador++;
            return contador;
        }

        /// <summary>Tipo de celda, sin depender de <c>DocumentFormat.OpenXml.Spreadsheet.CellValues</c>.</summary>
        private enum TipoCeldaCruda
        {
            SharedString,
            SharedStringResuelto, // indice ya validado y cambiado por su texto (ver DatosCrudosPlantilla.ConDatos)
            InlineString,
            TextoFormula,
            Boolean,
            Error,
            Numerico
        }

        /// <summary>Lo que se extrae de una <c>Cell</c> del SDK sin ningun tipo del SDK.</summary>
        private sealed class CeldaCruda
        {
            public string Referencia { get; set; }
            public TipoCeldaCruda Tipo { get; set; }
            public string ValorCrudo { get; set; }
        }

        /// <summary>Lo que sale del unico try de LP-01: datos propios, o un motivo de error.</summary>
        private sealed class DatosCrudosPlantilla
        {
            public string Error { get; private set; }
            public Dictionary<int, Dictionary<string, CeldaCruda>> CeldasPorFila { get; private set; }
            public int FilasRecorridas { get; private set; }
            public int FilasMaterializadas { get; private set; }

            public static DatosCrudosPlantilla ConError(string error)
            {
                return new DatosCrudosPlantilla { Error = error };
            }

            // Resuelve el indice de texto compartido a texto ACA (ultimo lugar que conoce
            // textosCompartidos, la tabla que vino del SDK), para que lo que sale del try de
            // LP-01 sean solo CeldaCruda con su texto final resuelto. Contenido no confiable:
            // TryParse siempre (LP-07) - indice no numerico, negativo, fuera de rango o
            // ausente es error del archivo, nunca un texto vacio silencioso.
            public static DatosCrudosPlantilla ConDatos(
                Dictionary<int, Dictionary<string, CeldaCruda>> celdasPorFila,
                string[] textosCompartidos,
                int filasRecorridas,
                int filasMaterializadas)
            {
                foreach (var fila in celdasPorFila.Values)
                {
                    foreach (string columna in fila.Keys.ToList())
                    {
                        CeldaCruda celda = fila[columna];
                        if (celda.Tipo != TipoCeldaCruda.SharedString) continue;

                        string referencia = celda.Referencia ?? "?";
                        string crudo = celda.ValorCrudo;

                        if (string.IsNullOrEmpty(crudo))
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: hace referencia a texto compartido pero no trae indice", referencia));

                        int indice;
                        if (!int.TryParse(crudo, NumberStyles.Integer, CultureInfo.InvariantCulture, out indice))
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: indice de texto compartido invalido ('{1}')", referencia, crudo));

                        if (indice < 0 || indice >= textosCompartidos.Length)
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: indice de texto compartido fuera de rango ({1}, la tabla tiene {2})",
                                referencia, indice, textosCompartidos.Length));

                        fila[columna] = new CeldaCruda
                        {
                            Referencia = referencia,
                            Tipo = TipoCeldaCruda.SharedStringResuelto,
                            ValorCrudo = textosCompartidos[indice]
                        };
                    }
                }

                return new DatosCrudosPlantilla
                {
                    CeldasPorFila = celdasPorFila,
                    FilasRecorridas = filasRecorridas,
                    FilasMaterializadas = filasMaterializadas
                };
            }
        }

        /// <summary>
        /// Resultado de interpretar una celda: texto normal, texto + advertencia (no fatal) o
        /// error (fatal, corta toda la lectura - contenido corrupto).
        /// </summary>
        private sealed class LecturaCelda
        {
            public string Texto { get; private set; }
            public string Error { get; private set; }
            public string Advertencia { get; private set; }

            private LecturaCelda(string texto, string error, string advertencia)
            {
                Texto = texto;
                Error = error;
                Advertencia = advertencia;
            }

            public static LecturaCelda ConTexto(string texto) => new LecturaCelda(texto, null, null);
            public static LecturaCelda ConTextoYAdvertencia(string texto, string advertencia) => new LecturaCelda(texto, null, advertencia);
            public static LecturaCelda ConError(string error) => new LecturaCelda(null, error, null);
        }
    }
}
