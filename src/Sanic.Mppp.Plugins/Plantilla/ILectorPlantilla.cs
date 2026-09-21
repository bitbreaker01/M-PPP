using System.IO;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>
    /// Lee la ventana configurada de una plantilla Excel. El archivo es hostil hasta que demuestre lo contrario (diseno/03 §7):
    /// NUNCA lanza por culpa del archivo; todo problema del archivo vuelve como resultado inválido con su motivo.
    /// </summary>
    public interface ILectorPlantilla
    {
        ResultadoLecturaPlantilla Leer(Stream excel, ConfiguracionPlantilla configuracion);

        ResultadoLecturaPlantilla Leer(byte[] excel, ConfiguracionPlantilla configuracion);
    }
}
