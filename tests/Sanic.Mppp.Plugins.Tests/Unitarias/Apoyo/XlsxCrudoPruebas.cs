// Prueba del arquitecto sobre su propio ayudante: el archivo crudo tiene que ser un .xlsx que el Open XML SDK abre,
// y tiene que conservar el orden FÍSICO de filas y celdas tal como se le pidió (de eso dependen las pruebas de LP-05).
using System.IO;
using System.Linq;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using Xunit;
using static Sanic.Mppp.Plugins.Tests.Apoyo.XlsxCrudo;

namespace Sanic.Mppp.Plugins.Tests.Unitarias.Apoyo
{
    public class XlsxCrudoPruebas
    {
        [Fact]
        public void El_sdk_lo_abre_y_el_orden_fisico_se_conserva()
        {
            var bytes = ConFilas("Plantilla", Fila(500, Celda("C500", "x")), Fila(6, Celda("D6", "d"), Celda("C6", "c")), Fila(6, CeldaDanada("C6")));
            using (var doc = SpreadsheetDocument.Open(new MemoryStream(bytes), false))
            {
                var hoja = doc.WorkbookPart.Workbook.Descendants<Sheet>().Single();
                Assert.Equal("Plantilla", hoja.Name.Value);
                var parte = (WorksheetPart)doc.WorkbookPart.GetPartById(hoja.Id.Value);
                var filas = parte.Worksheet.Descendants<Row>().ToList();
                Assert.Equal(new uint[] { 500, 6, 6 }, filas.Select(f => f.RowIndex.Value));
                Assert.Equal(new[] { "D6", "C6" }, filas[1].Elements<Cell>().Select(c => c.CellReference.Value));
                Assert.Equal("d", filas[1].Elements<Cell>().First().InnerText);
            }
        }
    }
}
