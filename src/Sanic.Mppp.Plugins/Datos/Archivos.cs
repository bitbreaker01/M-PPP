using System;
using Microsoft.Xrm.Sdk;

namespace Sanic.Mppp.Plugins.Datos
{
    /// <summary>El archivo pesa más de lo que se admite (LP-02): quien llama lo convierte en una regla fallida, no en una excepción real.</summary>
    public sealed class ArchivoExcedeElMaximoException : Exception
    {
        public ArchivoExcedeElMaximoException(long tamanoBytes, long maximoBytes)
            : base($"El archivo pesa {tamanoBytes} bytes y el máximo admitido es {maximoBytes}.")
        {
            TamanoBytes = tamanoBytes;
            MaximoBytes = maximoBytes;
        }

        public long TamanoBytes { get; }

        public long MaximoBytes { get; }
    }

    /// <summary>Lectura de columnas de archivo (`sanic_exceloriginal`, `sanic_correocrudo`). Abstraída para que los plugins se prueben sin Dataverse.</summary>
    public interface IArchivos
    {
        /// <summary>
        /// El archivo completo. Si pesa más de <paramref name="maximoBytes"/>, <see cref="ArchivoExcedeElMaximoException"/> SIN descargar
        /// ningún bloque (el tamaño lo dice la inicialización). Sin archivo en la columna: se propaga la falla del servicio.
        /// </summary>
        byte[] Descargar(string tabla, Guid id, string columna, long maximoBytes);

        /// <summary>
        /// Solo el INICIO del archivo: a lo sumo <paramref name="maximoBytes"/> bytes, en un solo bloque (diseno/03 §0 paso 2: las
        /// cabeceras del `.eml`, tope 256 KB). Si el archivo es más chico, todo. Nunca falla por tamaño.
        /// </summary>
        byte[] DescargarInicio(string tabla, Guid id, string columna, int maximoBytes);
    }

    /// <summary>
    /// <see cref="IArchivos"/> sobre <see cref="IOrganizationService"/> con los mensajes de la plataforma (`InitializeFileBlocksDownload`
    /// + `DownloadBlock`). Contrato (lo fijan las pruebas `ArchivosDataverseAceptacion`): una inicialización por descarga; bloques de
    /// <see cref="TamanoDeBloque"/> bytes (el último, lo que falte) pedidos en orden con `Offset` y `BlockLength` exactos; el resultado
    /// tiene EXACTAMENTE `FileSizeInBytes` bytes (menos bytes que los anunciados es <see cref="InvalidOperationException"/>: un archivo
    /// truncado no se procesa); archivo de 0 bytes → arreglo vacío sin pedir bloques. Argumentos nulos o en blanco, id vacío, máximo
    /// no positivo: <see cref="ArgumentException"/> (o <see cref="ArgumentNullException"/> para el servicio).
    /// </summary>
    public sealed class ArchivosDataverse : IArchivos
    {
        /// <summary>4 MB: el máximo que admite `DownloadBlock` por pedido.</summary>
        public const int TamanoDeBloque = 4 * 1024 * 1024;

        public ArchivosDataverse(IOrganizationService servicio)
        {
            throw new NotImplementedException();
        }

        public byte[] Descargar(string tabla, Guid id, string columna, long maximoBytes)
        {
            throw new NotImplementedException();
        }

        public byte[] DescargarInicio(string tabla, Guid id, string columna, int maximoBytes)
        {
            throw new NotImplementedException();
        }
    }
}
