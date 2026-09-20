using System.IO;

namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Lee una plantilla Excel de referencias de planes de pago (03-contratos-custom-api.md #7,
    /// carpeta Plantilla/). La entrada nunca es una ruta de archivo: en el plugin real el Excel
    /// viene de una columna de Dataverse (sanic_ExcelOriginal).
    /// </summary>
    public interface ILectorPlantilla
    {
        ResultadoLecturaPlantilla Leer(Stream excel, ConfiguracionPlantilla configuracion);
        ResultadoLecturaPlantilla Leer(byte[] excel, ConfiguracionPlantilla configuracion);
    }
}
