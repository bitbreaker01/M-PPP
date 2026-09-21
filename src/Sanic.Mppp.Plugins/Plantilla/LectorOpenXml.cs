using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>
    /// Lector sobre Open XML SDK 3.1.0. Reglas LP-01 a LP-08 de diseno/03 §7: el archivo es hostil hasta que demuestre lo
    /// contrario. Llega por correo desde fuera del banco; aunque el remitente esté autorizado, su cuenta puede estar
    /// comprometida.
    ///
    /// Reglas de este archivo:
    /// - Todo el trato con Open XML SDK y con System.IO.Compression (contenido hostil de terceros) vive dentro de un único
    ///   try con catch general (LP-01); la lógica propia (comparar encabezados, armar el resultado) queda SIEMPRE afuera,
    ///   para que un bug nuestro no se disfrace de archivo corrupto.
    /// - Solo se lee la ventana configurada (LP-04): la fila de encabezado y las filas de la ventana. Se deja de leer en la
    ///   primera fila más allá de la última configurada, y dentro de cada fila no se mira nada más allá de la última
    ///   columna configurada.
    /// - El orden se exige, no se supone (LP-05): filas y celdas estrictamente ascendentes en todo lo que se llega a
    ///   recorrer, o el archivo es inválido.
    /// - Todo lo que el lector no puede interpretar termina en error o advertencia, nunca en silencio (LP-07).
    /// </summary>
    public sealed class LectorOpenXml : ILectorPlantilla
    {
        /// <summary>
        /// Lo ÚNICO que se le dice al cliente cuando la librería no pudo abrir o recorrer el archivo (LP-01). El mensaje de la excepción
        /// va a <see cref="ResultadoLecturaPlantilla.DetalleTecnico"/>, no acá.
        /// </summary>
        public const string ArchivoIlegible = "El archivo adjunto no se pudo leer como una plantilla de Excel (.xlsx). Puede estar dañado o no ser un archivo de Excel.";

        private readonly LimitesLectura _limites;

        public LectorOpenXml()
            : this(new LimitesLectura())
        {
        }

        public LectorOpenXml(LimitesLectura limites)
        {
            _limites = limites ?? throw new ArgumentNullException(nameof(limites));
        }

        public ResultadoLecturaPlantilla Leer(Stream excel, ConfiguracionPlantilla configuracion)
        {
            if (excel == null) throw new ArgumentNullException(nameof(excel));
            if (configuracion == null) throw new ArgumentNullException(nameof(configuracion));
            ValidarConfiguracion(configuracion); // LP-01: config mal armada a mano es bug nuestro, no archivo inválido.

            // LP-02: tope de bytes de entrada con copia acotada. Nunca Stream.Length/CanSeek: un stream no seekable
            // (típico de una descarga) no los soporta de forma confiable.
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
            ValidarConfiguracion(configuracion); // LP-01: config mal armada a mano es bug nuestro, no archivo inválido.

            // Un byte[] ya está completo en memoria: su Length es un dato del CLR, no una promesa de un stream externo
            // que puede no cumplirse. No hace falta copia acotada.
            if (excel.LongLength > _limites.TamanoMaximoBytesEntrada)
                return ResultadoLecturaPlantilla.ConError(FormatoTamanoEntradaExcedido(excel.LongLength));

            return LeerDesdeBytesEnMemoria(excel, configuracion);
        }

        // LP-01: la configuración la arma código nuestro (a mano, o ConfiguracionPlantilla.DesdeJson). Una configuración
        // mal armada es un error de PROGRAMACIÓN, nunca "archivo inválido": por eso se valida ANTES del try que atrapa
        // las excepciones del SDK, y con ArgumentException (no con el resultado ConError). Usa la MISMA función que
        // ConfiguracionPlantilla.DesdeJson (revisión de código, 2026-09-21): antes tenía reglas propias, más laxas, y una
        // configuración armada a mano con EncabezadoEsperado = null pasaba como válida.
        private static void ValidarConfiguracion(ConfiguracionPlantilla configuracion)
        {
            string motivo = ConfiguracionPlantilla.Invalidez(configuracion);
            if (motivo != null)
                throw new ArgumentException($"La configuración de lectura {motivo}", nameof(configuracion));
        }

        // LP-02: lee como mucho máximo + 1 bytes a memoria. Si el stream tiene más, se corta ahí mismo: nunca se sigue
        // leyendo un stream hostil "a ver hasta dónde llega".
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
            // LP-03: tope de bytes descomprimidos, ANTES de intentar abrir con el SDK. Es su propio try:
            // System.IO.Compression también procesa contenido hostil y puede tirar excepciones propias.
            string errorZip, detalleZip;
            if (!TamanoDescomprimidoDentroDelTope(contenido, _limites.TamanoMaximoBytesDescomprimidos, out errorZip, out detalleZip))
            {
                // detalleZip != null: la librería no pudo ni abrir el zip para contar sus entradas (LP-01, no LP-03):
                // el cliente no puede terminar en un rechazo distinto según en qué punto exacto falló la lectura.
                return detalleZip != null
                    ? ResultadoLecturaPlantilla.ConErrorTecnico(ArchivoIlegible, detalleZip)
                    : ResultadoLecturaPlantilla.ConError(errorZip);
            }

            // Lógica propia (no toca el SDK): se calcula ANTES del try de LP-01 para que ese try no tenga más
            // responsabilidad que atrapar las excepciones del SDK (hallazgo de la revisión de código, 2026-09-21).
            int ultimaColumnaConfigurada = ColumnaMaximaConfigurada(configuracion);

            // LP-01: único try para TODO el trato con Open XML SDK (abrir, ubicar partes, recorrer). Cualquier excepción
            // se convierte en error del archivo, salvo las que no tiene sentido atrapar.
            DatosCrudosPlantilla datos;
            try
            {
                datos = LeerDatosCrudosConSdk(contenido, configuracion, ultimaColumnaConfigurada);
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                // Al cliente le llega SOLO la constante ArchivoIlegible: el tipo y el mensaje de la excepción (jerga del
                // SDK) van a DetalleTecnico, para la traza (ITracingService), nunca para un correo a alguien de fuera del
                // banco (hallazgo de la re-revisión, 2026-09-21).
                return ResultadoLecturaPlantilla.ConErrorTecnico(ArchivoIlegible, DetalleTecnicoDe(ex));
            }

            if (datos.Error != null)
                return ResultadoLecturaPlantilla.ConError(datos.Error);

            // A partir de acá: lógica propia, nada toca el SDK ni System.IO.Compression.
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

            return ResultadoLecturaPlantilla.ConFilas(filas, advertencias);
        }

        // LP-03: suma el tamaño DECLARADO (metadata del zip, sin inflar nada) de cada entrada. `detalle` sale distinto de
        // null únicamente cuando la librería no pudo ni abrir el zip (LP-01: mismo tratamiento que el try de más abajo,
        // el texto para el cliente es ArchivoIlegible y el de la excepción va a DetalleTecnico); cuando `error` es por el
        // tope de LP-03 (regla nuestra), `detalle` queda null.
        private static bool TamanoDescomprimidoDentroDelTope(byte[] contenido, long maximoBytesDescomprimidos, out string error, out string detalle)
        {
            error = null;
            detalle = null;
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
                error = ArchivoIlegible;
                detalle = DetalleTecnicoDe(ex);
                return false;
            }
        }

        // LP-01: lo que dijo la librería (tipo + mensaje), para ITracingService. Nunca se le muestra al cliente.
        private static string DetalleTecnicoDe(Exception ex) => $"{ex.GetType()}: {ex.Message}";

        // ---- Todo lo de acá para abajo hasta CapturarCeldaCruda toca el SDK: vive dentro del try de
        // LeerDesdeBytesEnMemoria (LP-01). Solo devuelve datos propios (CeldaCruda, strings, ints), nunca tipos de
        // Open XML, para que lo que sigue después del try sea indiscutiblemente lógica nuestra. ----

        private static DatosCrudosPlantilla LeerDatosCrudosConSdk(
            byte[] contenido, ConfiguracionPlantilla configuracion, int ultimaColumnaConfigurada)
        {
            using (var stream = new MemoryStream(contenido, writable: false))
            using (var documento = SpreadsheetDocument.Open(stream, isEditable: false))
            {
                WorkbookPart workbookPart = documento.WorkbookPart;
                if (workbookPart == null)
                    return DatosCrudosPlantilla.ConError("El archivo no tiene un WorkbookPart (no es un libro de Excel válido).");

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
                int ultimaFilaResuelta = 0; // LP-06: primera fila sin r = anterior(0) + 1 = 1

                using (OpenXmlReader reader = OpenXmlReader.Create(worksheetPart))
                {
                    while (reader.Read())
                    {
                        // OpenXmlReader.Read() reporta ElementType == typeof(Row) tanto en el tag de apertura como en el
                        // de cierre de una fila con hijos que no se materializó. Sin este filtro, una fila fuera de la
                        // ventana se contaba dos veces.
                        if (reader.ElementType != typeof(Row) || !reader.IsStartElement) continue;

                        // Se lee el atributo r ANTES de materializar (LoadCurrentElement): así no se paga el costo de
                        // armar la fila completa para una fila que después queda fuera de la ventana. LP-06: sin r, la
                        // posición es la de la fila anterior + 1.
                        int? indiceExplicito = LeerIndiceDeFila(reader.Attributes);
                        int indice = indiceExplicito ?? (ultimaFilaResuelta + 1);

                        // LP-05: el orden se exige sobre TODO lo que se llega a recorrer, incluidas las filas que están
                        // antes del encabezado o entre el encabezado y la ventana. Una fila que RETROCEDE o se REPITE
                        // invalida el archivo.
                        if (indice <= ultimaFilaResuelta)
                        {
                            return DatosCrudosPlantilla.ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "El archivo no está en orden: la fila {0} aparece después de la fila {1}.",
                                indice, ultimaFilaResuelta));
                        }
                        ultimaFilaResuelta = indice;

                        // LP-04 (aclaración D-12, diseno/PENDIENTES.md): una fila EN ORDEN pero más allá de la última
                        // fila de la ventana corta la lectura SIN invalidar nada -caso legítimo: pocas filas llenas y
                        // una nota al pie mucho más abajo-. Lo que venga después del corte no se mira: detectar un
                        // desorden ahí exigiría seguir leyendo, que es el costo no acotado que LP-04 elimina.
                        if (indice > filaHasta) break;

                        bool esEncabezado = indice == filaEncabezado;
                        bool esDeLaVentana = indice >= primeraFila && indice <= filaHasta;
                        if (!esEncabezado && !esDeLaVentana) continue; // fuera de lo que se interpreta: no se mira su contenido.

                        Row fila = (Row)reader.LoadCurrentElement();

                        var celdas = new Dictionary<string, CeldaCruda>(StringComparer.Ordinal);
                        int ultimaColumnaResuelta = 0;

                        foreach (Cell celda in fila.Elements<Cell>())
                        {
                            string columnaExplicita = ObtenerLetraColumna(celda.CellReference != null ? celda.CellReference.Value : null);
                            string columnaTexto = columnaExplicita ?? SiguienteColumna(ultimaColumnaResuelta); // LP-06
                            int columnaNumero = ColumnaANumero(columnaTexto);

                            // LP-05: el orden también se exige dentro de la fila. Una celda que RETROCEDE o se REPITE
                            // invalida el archivo.
                            if (columnaNumero <= ultimaColumnaResuelta)
                            {
                                return DatosCrudosPlantilla.ConError(string.Format(
                                    CultureInfo.InvariantCulture,
                                    "El archivo no está en orden: en la fila {0} la celda {1} aparece fuera de orden.",
                                    indice, columnaTexto + indice.ToString(CultureInfo.InvariantCulture)));
                            }
                            ultimaColumnaResuelta = columnaNumero;

                            // LP-04 (aclaración D-12): una celda EN ORDEN pero más allá de la última columna configurada
                            // corta ESTA fila sin invalidar nada -caso legítimo: trae C, no trae D, y después trae Z-.
                            // Los campos configurados que no llegaron a aparecer quedan como texto vacío.
                            if (columnaNumero > ultimaColumnaConfigurada) break;

                            celdas[columnaTexto] = CapturarCeldaCruda(
                                columnaTexto + indice.ToString(CultureInfo.InvariantCulture), celda);
                        }

                        celdasPorFila[indice] = celdas;
                    }
                }

                if (!celdasPorFila.ContainsKey(filaEncabezado))
                    return DatosCrudosPlantilla.ConError($"No se encontró la fila de encabezado (fila {filaEncabezado}).");

                return DatosCrudosPlantilla.ConDatos(celdasPorFila, textosCompartidos);
            }
        }

        private static int ColumnaMaximaConfigurada(ConfiguracionPlantilla configuracion)
        {
            int maximo = 0;
            foreach (CampoPlantilla campo in configuracion.Campos)
            {
                int numero = ColumnaANumero(campo.Columna);
                if (numero > maximo) maximo = numero;
            }
            return maximo;
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

                return null; // r presente pero no numérico: se trata igual que ausente (LP-06)
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

        // LP-06: columna anterior + 1, primera = A. Aritmética base-26 de columnas de Excel (A=1, B=2, ..., Z=26, AA=27...).
        private static string SiguienteColumna(int columnaAnteriorNumero)
        {
            return NumeroAColumna(columnaAnteriorNumero + 1);
        }

        private static int ColumnaANumero(string columna)
        {
            int resultado = 0;
            foreach (char c in columna)
                resultado = resultado * 26 + (char.ToUpperInvariant(c) - 'A' + 1);
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

        // ---- De acá para abajo: pura lógica propia, ningún tipo de Open XML SDK. Opera sobre CeldaCruda (nuestro),
        // nunca sobre Cell (del SDK). ----

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
                        "columna {0}{1}: se esperaba '{2}', se encontró '{3}'",
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

                orden++;
                if (!tieneAlgunValor) continue;

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
                // El índice ya se validó y resolvió a texto dentro del try de LP-01 (es el único lugar que conoce la
                // tabla de shared strings). Acá solo queda recortar.
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.InlineString)
            {
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.TextoFormula)
            {
                // Resultado de fórmula tipo texto: el valor cacheado ya vino en CellValue.
                return LecturaCelda.ConTexto((crudo ?? string.Empty).Trim());
            }

            if (celda.Tipo == TipoCeldaCruda.Boolean)
            {
                // LP-07: nada se pierde callado. Solo "1" y "0" son valores booleanos válidos; cualquier otro crudo
                // (vacío incluido) invalida el archivo nombrando la celda, igual que las demás celdas mal formadas.
                if (crudo == "1" || crudo == "0")
                    return LecturaCelda.ConTexto(crudo);

                return LecturaCelda.ConError(string.Format(
                    CultureInfo.InvariantCulture,
                    "celda {0}: valor booleano inválido ('{1}'); solo se acepta '1' o '0'", referencia, crudo));
            }

            if (celda.Tipo == TipoCeldaCruda.Error)
            {
                // #REF!, #N/A, #VALUE!... no es un fallo del lector: se devuelve tal cual y se marca como advertencia
                // para que una regla de registro la rechace con motivo.
                string textoError = (crudo ?? string.Empty).Trim();
                return LecturaCelda.ConTextoYAdvertencia(textoError, string.Format(
                    CultureInfo.InvariantCulture,
                    "celda {0}: tiene un valor de error de Excel ('{1}')", referencia, textoError));
            }

            // Numérico (default de Open XML), con o sin fórmula: el valor cacheado está igual en CellValue.
            string textoNumero = FormatearNumero(crudo).Trim();
            int digitos = ContarDigitos(textoNumero);
            if (digitos >= 16)
            {
                // Excel solo garantiza 15 dígitos significativos en una celda con formato Número: un valor de 16+
                // dígitos pudo haber llegado ya redondeado al archivo, y ningún lector puede recuperar lo que Excel ya
                // perdió.
                return LecturaCelda.ConTextoYAdvertencia(textoNumero, string.Format(
                    CultureInfo.InvariantCulture,
                    "celda {0}: {1} dígitos en una celda numérica (no de texto); Excel solo garantiza 15 dígitos significativos, puede venir redondeada",
                    referencia, digitos));
            }
            return LecturaCelda.ConTexto(textoNumero);
        }

        // Open XML puede serializar números grandes o resultados de fórmula en notación científica dentro del propio
        // XML (ej "1.6E+16"); nunca se muestra así. Con decimal (28-29 dígitos significativos), no con double (~15-17,
        // con redondeo real a partir de 2^53): un entero largo se pierde con double. Un valor entero en texto plano
        // (sin 'e'/'.') se devuelve tal cual, sin parsear nada.
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
            SharedStringResuelto, // índice ya validado y cambiado por su texto (ver DatosCrudosPlantilla.ConDatos)
            InlineString,
            TextoFormula,
            Boolean,
            Error,
            Numerico
        }

        /// <summary>Lo que se extrae de una <c>Cell</c> del SDK sin ningún tipo del SDK.</summary>
        private sealed class CeldaCruda
        {
            public string Referencia { get; set; }
            public TipoCeldaCruda Tipo { get; set; }
            public string ValorCrudo { get; set; }
        }

        /// <summary>Lo que sale del único try de LP-01: datos propios, o un motivo de error.</summary>
        private sealed class DatosCrudosPlantilla
        {
            public string Error { get; private set; }
            public Dictionary<int, Dictionary<string, CeldaCruda>> CeldasPorFila { get; private set; }

            public static DatosCrudosPlantilla ConError(string error)
            {
                return new DatosCrudosPlantilla { Error = error };
            }

            // Resuelve el índice de texto compartido a texto ACÁ (último lugar que conoce textosCompartidos, la tabla
            // que vino del SDK), para que lo que sale del try de LP-01 sean solo CeldaCruda con su texto final resuelto.
            // Contenido no confiable: TryParse siempre (LP-07) - índice no numérico, negativo, fuera de rango o ausente
            // es error del archivo, nunca un texto vacío silencioso.
            public static DatosCrudosPlantilla ConDatos(
                Dictionary<int, Dictionary<string, CeldaCruda>> celdasPorFila,
                string[] textosCompartidos)
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
                        {
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: hace referencia a texto compartido pero no trae índice", referencia));
                        }

                        int indice;
                        if (!int.TryParse(crudo, NumberStyles.Integer, CultureInfo.InvariantCulture, out indice))
                        {
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: índice de texto compartido inválido ('{1}')", referencia, crudo));
                        }

                        if (indice < 0 || indice >= textosCompartidos.Length)
                        {
                            return ConError(string.Format(
                                CultureInfo.InvariantCulture,
                                "celda {0}: índice de texto compartido fuera de rango ({1}, la tabla tiene {2})",
                                referencia, indice, textosCompartidos.Length));
                        }

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
                    CeldasPorFila = celdasPorFila
                };
            }
        }

        /// <summary>
        /// Resultado de interpretar una celda: texto normal, texto + advertencia (no fatal) o error (fatal, corta toda
        /// la lectura - contenido corrupto).
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
