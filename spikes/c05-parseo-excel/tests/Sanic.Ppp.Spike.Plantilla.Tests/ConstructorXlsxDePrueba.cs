using System;
using System.Collections.Generic;
using System.IO;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;

namespace Sanic.Ppp.Spike.Plantilla.Tests
{
    /// <summary>
    /// Arma un .xlsx minimo en memoria, celda por celda, para no depender de archivos binarios
    /// fijos en git para cada variante de prueba. Solo para tests: nunca se usa contra un
    /// entorno real.
    /// </summary>
    internal sealed class ConstructorXlsxDePrueba
    {
        private readonly string _nombreHoja;
        private readonly Dictionary<string, CeldaDePrueba> _celdas = new Dictionary<string, CeldaDePrueba>(StringComparer.Ordinal);
        private readonly List<List<string>> _filasSinR = new List<List<string>>();
        private bool _conHojaOcultaExtra;
        private bool _idDeHojaInvalido;
        private int[] _ordenDeFilasExplicito;

        public ConstructorXlsxDePrueba(string nombreHoja)
        {
            _nombreHoja = nombreHoja;
        }

        public ConstructorXlsxDePrueba ConTexto(string referencia, string valor)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.SharedString, Valor = valor };
            return this;
        }

        public ConstructorXlsxDePrueba ConTextoEnLinea(string referencia, string valor)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.InlineString, Valor = valor };
            return this;
        }

        public ConstructorXlsxDePrueba ConNumero(string referencia, string valorCrudo)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.Number, Valor = valorCrudo };
            return this;
        }

        public ConstructorXlsxDePrueba ConFormulaTexto(string referencia, string formula, string valorCacheado)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.String, Valor = valorCacheado, Formula = formula };
            return this;
        }

        /// <summary>
        /// Celda t="s" con el &lt;v&gt; que se le pida tal cual, sin pasar por la tabla de
        /// shared strings: para simular un indice de texto compartido corrupto (no numerico,
        /// negativo, fuera de rango o vacio).
        /// </summary>
        public ConstructorXlsxDePrueba ConIndiceCompartidoCrudo(string referencia, string valorCrudoDeV)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.SharedString, Valor = valorCrudoDeV, EsIndiceCrudo = true };
            return this;
        }

        public ConstructorXlsxDePrueba ConError(string referencia, string textoError)
        {
            _celdas[referencia] = new CeldaDePrueba { Tipo = CellValues.Error, Valor = textoError };
            return this;
        }

        public ConstructorXlsxDePrueba ConHojaOcultaExtra()
        {
            _conHojaOcultaExtra = true;
            return this;
        }

        /// <summary>
        /// Fuerza el orden en que las filas quedan escritas en el XML, distinto del orden
        /// numerico de fila: para reproducir un &lt;row r="500"&gt; que aparece ANTES que
        /// &lt;row r="6"&gt; en el archivo (LP-05).
        /// </summary>
        public ConstructorXlsxDePrueba ConOrdenDeFilasExplicito(params int[] ordenDeFilas)
        {
            _ordenDeFilasExplicito = ordenDeFilas;
            return this;
        }

        /// <summary>
        /// Agrega una fila (en el orden en que se llama) SIN atributo r en la fila ni en
        /// ninguna de sus celdas: para probar la inferencia de posicion de LP-06. Cada valor
        /// se escribe como texto compartido. No se puede combinar con ConTexto/ConNumero/etc.
        /// en el mismo archivo (son mecanismos separados a proposito, para no mezclar filas
        /// con y sin "r" en un mismo test).
        /// </summary>
        public ConstructorXlsxDePrueba ConFilaSinR(params string[] valores)
        {
            _filasSinR.Add(new List<string>(valores));
            return this;
        }

        /// <summary>
        /// El &lt;sheet r:id="..."&gt; de workbook.xml apunta a una relacion que NO existe en
        /// workbook.xml.rels: reproduce el archivo del hallazgo D (GetPartById revienta).
        /// </summary>
        public ConstructorXlsxDePrueba ConIdDeHojaInvalido()
        {
            _idDeHojaInvalido = true;
            return this;
        }

        public byte[] Bytes()
        {
            using (var stream = new MemoryStream())
            {
                using (var documento = SpreadsheetDocument.Create(stream, SpreadsheetDocumentType.Workbook))
                {
                    var workbookPart = documento.AddWorkbookPart();
                    workbookPart.Workbook = new Workbook();

                    var sharedStringPart = workbookPart.AddNewPart<SharedStringTablePart>();
                    sharedStringPart.SharedStringTable = new SharedStringTable();
                    var indicesCompartidos = new Dictionary<string, int>(StringComparer.Ordinal);

                    var worksheetPart = workbookPart.AddNewPart<WorksheetPart>();
                    var sheetData = new SheetData();
                    worksheetPart.Worksheet = new Worksheet(sheetData);

                    if (_filasSinR.Count > 0)
                    {
                        // Modo separado a proposito (LP-06): ninguna fila ni celda trae "r".
                        foreach (List<string> valoresDeFila in _filasSinR)
                        {
                            var filaSinR = new Row(); // sin RowIndex
                            foreach (string valor in valoresDeFila)
                            {
                                if (!indicesCompartidos.TryGetValue(valor, out int indice))
                                {
                                    indice = indicesCompartidos.Count;
                                    indicesCompartidos[valor] = indice;
                                    sharedStringPart.SharedStringTable.AppendChild(new SharedStringItem(new Text(valor)));
                                }
                                filaSinR.AppendChild(new Cell // sin CellReference
                                {
                                    DataType = CellValues.SharedString,
                                    CellValue = new CellValue(indice.ToString())
                                });
                            }
                            sheetData.AppendChild(filaSinR);
                        }
                    }
                    else
                    {
                        var filas = new SortedDictionary<int, Row>();
                        foreach (var par in _celdas)
                        {
                            string referencia = par.Key;
                            CeldaDePrueba especificacion = par.Value;
                            int numeroFila = ObtenerNumeroFila(referencia);

                            if (!filas.TryGetValue(numeroFila, out Row fila))
                            {
                                fila = new Row { RowIndex = (uint)numeroFila };
                                filas[numeroFila] = fila;
                            }

                            var celda = new Cell { CellReference = referencia };

                            if (especificacion.Tipo == CellValues.SharedString && especificacion.EsIndiceCrudo)
                            {
                                celda.DataType = CellValues.SharedString;
                                if (especificacion.Valor != null) celda.CellValue = new CellValue(especificacion.Valor);
                            }
                            else if (especificacion.Tipo == CellValues.SharedString)
                            {
                                if (!indicesCompartidos.TryGetValue(especificacion.Valor, out int indice))
                                {
                                    indice = indicesCompartidos.Count;
                                    indicesCompartidos[especificacion.Valor] = indice;
                                    sharedStringPart.SharedStringTable.AppendChild(new SharedStringItem(new Text(especificacion.Valor)));
                                }
                                celda.DataType = CellValues.SharedString;
                                celda.CellValue = new CellValue(indice.ToString());
                            }
                            else if (especificacion.Tipo == CellValues.InlineString)
                            {
                                celda.DataType = CellValues.InlineString;
                                celda.InlineString = new InlineString(new Text(especificacion.Valor));
                            }
                            else if (especificacion.Tipo == CellValues.Number)
                            {
                                celda.CellValue = new CellValue(especificacion.Valor);
                            }
                            else if (especificacion.Tipo == CellValues.String)
                            {
                                celda.DataType = CellValues.String;
                                celda.CellFormula = new CellFormula(especificacion.Formula);
                                celda.CellValue = new CellValue(especificacion.Valor);
                            }
                            else if (especificacion.Tipo == CellValues.Error)
                            {
                                celda.DataType = CellValues.Error;
                                celda.CellValue = new CellValue(especificacion.Valor);
                            }

                            fila.AppendChild(celda);
                        }

                        if (_ordenDeFilasExplicito != null)
                        {
                            // LP-05: escribe las filas en el orden EXACTO pedido, no ascendente,
                            // para reproducir <row r="500"> antes que <row r="6"> en el archivo.
                            foreach (int numeroFila in _ordenDeFilasExplicito)
                                if (filas.TryGetValue(numeroFila, out Row fila))
                                    sheetData.AppendChild(fila);
                        }
                        else
                        {
                            foreach (var fila in filas.Values)
                                sheetData.AppendChild(fila);
                        }
                    }

                    var sheets = workbookPart.Workbook.AppendChild(new Sheets());
                    sheets.AppendChild(new Sheet
                    {
                        Id = _idDeHojaInvalido ? "rId999" : workbookPart.GetIdOfPart(worksheetPart),
                        SheetId = 1,
                        Name = _nombreHoja
                    });

                    if (_conHojaOcultaExtra)
                    {
                        var worksheetPartOculta = workbookPart.AddNewPart<WorksheetPart>();
                        worksheetPartOculta.Worksheet = new Worksheet(new SheetData());
                        sheets.AppendChild(new Sheet
                        {
                            Id = workbookPart.GetIdOfPart(worksheetPartOculta),
                            SheetId = 2,
                            Name = "Listas",
                            State = SheetStateValues.Hidden
                        });
                    }

                    workbookPart.Workbook.Save();
                }

                return stream.ToArray();
            }
        }

        private static int ObtenerNumeroFila(string referencia)
        {
            int i = 0;
            while (i < referencia.Length && !char.IsDigit(referencia[i])) i++;
            return int.Parse(referencia.Substring(i));
        }

        private sealed class CeldaDePrueba
        {
            public CellValues Tipo { get; set; }
            public string Valor { get; set; }
            public string Formula { get; set; }
            public bool EsIndiceCrudo { get; set; }
        }
    }
}
