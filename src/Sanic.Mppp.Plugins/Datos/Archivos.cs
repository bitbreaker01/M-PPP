using System;
using Microsoft.Crm.Sdk.Messages;
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

        private readonly IOrganizationService _servicio;

        public ArchivosDataverse(IOrganizationService servicio)
        {
            _servicio = servicio ?? throw new ArgumentNullException(nameof(servicio));
        }

        public byte[] Descargar(string tabla, Guid id, string columna, long maximoBytes)
        {
            ValidarObjetivo(tabla, id, columna);
            if (maximoBytes <= 0)
            {
                throw new ArgumentException("El máximo de bytes admitido tiene que ser positivo.", nameof(maximoBytes));
            }

            var inicio = Inicializar(tabla, id, columna);

            // El tamaño lo dice la inicialización: se controla ANTES de bajar ningún bloque (LP-02, diseno/03 §0 paso 2).
            if (inicio.FileSizeInBytes > maximoBytes)
            {
                throw new ArchivoExcedeElMaximoException(inicio.FileSizeInBytes, maximoBytes);
            }

            return DescargarPorBloques(inicio);
        }

        public byte[] DescargarInicio(string tabla, Guid id, string columna, int maximoBytes)
        {
            ValidarObjetivo(tabla, id, columna);
            if (maximoBytes <= 0)
            {
                throw new ArgumentException("El máximo de bytes admitido tiene que ser positivo.", nameof(maximoBytes));
            }

            var inicio = Inicializar(tabla, id, columna);
            if (inicio.FileSizeInBytes == 0)
            {
                return new byte[0];
            }

            // A lo sumo maximoBytes, en un solo bloque; si el archivo es más chico, todo. Nunca falla por tamaño.
            var largo = Math.Min((long)maximoBytes, inicio.FileSizeInBytes);
            return DescargarBloque(inicio.FileContinuationToken, 0, largo);
        }

        private static void ValidarObjetivo(string tabla, Guid id, string columna)
        {
            if (string.IsNullOrWhiteSpace(tabla))
            {
                throw new ArgumentException("La tabla no puede estar vacía.", nameof(tabla));
            }

            if (id == Guid.Empty)
            {
                throw new ArgumentException("El id del registro no puede estar vacío.", nameof(id));
            }

            if (string.IsNullOrWhiteSpace(columna))
            {
                throw new ArgumentException("La columna no puede estar vacía.", nameof(columna));
            }
        }

        private InitializeFileBlocksDownloadResponse Inicializar(string tabla, Guid id, string columna)
        {
            var pedido = new InitializeFileBlocksDownloadRequest
            {
                Target = new EntityReference(tabla, id),
                FileAttributeName = columna,
            };

            return (InitializeFileBlocksDownloadResponse)_servicio.Execute(pedido);
        }

        /// <summary>
        /// Baja el archivo entero en bloques de <see cref="TamanoDeBloque"/> (el último, lo que falte), en orden. Un bloque con menos
        /// bytes que los anunciados por la inicialización es un archivo truncado: entrada no confiable que no se procesa (diseno/03 §0 paso 2).
        /// </summary>
        private byte[] DescargarPorBloques(InitializeFileBlocksDownloadResponse inicio)
        {
            var tamano = inicio.FileSizeInBytes;
            if (tamano == 0)
            {
                return new byte[0];
            }

            var resultado = new byte[tamano];
            long offset = 0;
            while (offset < tamano)
            {
                var largo = Math.Min((long)TamanoDeBloque, tamano - offset);
                var datos = DescargarBloque(inicio.FileContinuationToken, offset, largo);
                if (datos.Length < largo)
                {
                    throw new InvalidOperationException(
                        $"El archivo anunció {tamano} bytes pero el bloque en el offset {offset} trajo solo {datos.Length}: es un archivo truncado y no se procesa.");
                }

                Array.Copy(datos, 0, resultado, offset, largo);
                offset += largo;
            }

            return resultado;
        }

        private byte[] DescargarBloque(string token, long offset, long largo)
        {
            var pedido = new DownloadBlockRequest
            {
                FileContinuationToken = token,
                Offset = offset,
                BlockLength = largo,
            };

            var respuesta = (DownloadBlockResponse)_servicio.Execute(pedido);
            return respuesta.Data;
        }
    }
}
