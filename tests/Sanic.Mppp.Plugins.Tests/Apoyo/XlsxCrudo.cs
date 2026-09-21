using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;

namespace Sanic.Mppp.Plugins.Tests.Apoyo
{
    /// <summary>
    /// Arma un .xlsx mínimo escribiendo el XML de la hoja A MANO, para controlar exactamente el orden físico de filas y celdas,
    /// repetirlas o dañarlas. (ConstructorXlsxDePrueba pasa por el Open XML SDK, que ordena por su cuenta.) Textos como inlineStr.
    /// </summary>
    internal static class XlsxCrudo
    {
        public static string Celda(string referencia, string texto)
        {
            return $"<c r=\"{referencia}\" t=\"inlineStr\"><is><t>{texto}</t></is></c>";
        }

        /// <summary>Celda que apunta a un texto compartido que no existe: dentro de la ventana invalida el archivo.</summary>
        public static string CeldaDanada(string referencia)
        {
            return $"<c r=\"{referencia}\" t=\"s\"><v>999</v></c>";
        }

        /// <summary>Celda booleana (t="b") con el valor crudo que se le pida: "1", "0", o basura.</summary>
        public static string CeldaBooleana(string referencia, string valorCrudo)
        {
            return $"<c r=\"{referencia}\" t=\"b\"><v>{valorCrudo}</v></c>";
        }

        public static string Fila(int numero, params string[] celdas)
        {
            return $"<row r=\"{numero}\">{string.Concat(celdas)}</row>";
        }

        public static byte[] ConFilas(string nombreHoja, params string[] filasEnOrdenFisico)
        {
            const string ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
            const string rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
            var partes = new[]
            {
                ("[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                    + "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                    + "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
                    + "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>"),
                ("_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    + $"<Relationship Id=\"rId1\" Type=\"{rel}/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>"),
                ("xl/workbook.xml", $"<?xml version=\"1.0\" encoding=\"UTF-8\"?><workbook xmlns=\"{ns}\" xmlns:r=\"{rel}\"><sheets>"
                    + $"<sheet name=\"{nombreHoja}\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>"),
                ("xl/_rels/workbook.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    + $"<Relationship Id=\"rId1\" Type=\"{rel}/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>"),
                ("xl/worksheets/sheet1.xml", $"<?xml version=\"1.0\" encoding=\"UTF-8\"?><worksheet xmlns=\"{ns}\"><sheetData>{string.Concat(filasEnOrdenFisico)}</sheetData></worksheet>"),
            };
            using (var memoria = new MemoryStream())
            {
                using (var zip = new ZipArchive(memoria, ZipArchiveMode.Create, leaveOpen: true))
                {
                    foreach (var (ruta, xml) in partes)
                    {
                        using (var salida = zip.CreateEntry(ruta).Open())
                        {
                            var bytes = Encoding.UTF8.GetBytes(xml);
                            salida.Write(bytes, 0, bytes.Length);
                        }
                    }
                }

                return memoria.ToArray();
            }
        }
    }
}
