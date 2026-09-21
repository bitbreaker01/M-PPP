using System;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>
    /// Parámetro `lectura.limites` (diseno/03 §7 LP-02, LP-03 y LP-08). Los valores por defecto son los iniciales del diseño
    /// y valen solo si el parámetro falta. Ya NO existen topes de filas recorridas ni de celdas por fila: el costo lo acota la ventana.
    /// </summary>
    public sealed class LimitesLectura
    {
        /// <summary>Peso máximo del archivo comprimido. Por defecto 2 MB.</summary>
        public long TamanoMaximoBytesEntrada { get; set; } = 2L * 1024 * 1024;

        /// <summary>Peso máximo declarado del contenido descomprimido. Por defecto 20 MB.</summary>
        public long TamanoMaximoBytesDescomprimidos { get; set; } = 20L * 1024 * 1024;

        /// <summary>
        /// Lee {"maximoBytesComprimido":2097152,"maximoBytesDescomprimido":20971520}. Una clave que falta toma su valor por defecto;
        /// `null` o vacío devuelve todos los valores por defecto; un valor que no es un entero positivo es <see cref="FormatException"/>.
        /// </summary>
        public static LimitesLectura DesdeJson(string json)
        {
            var resultado = new LimitesLectura();

            // Ausente = "sin parámetro": todo por defecto (LP-08). Distinto de un parámetro CARGADO
            // pero mal formado, que es un error (ver DesdeJson de ConfiguracionPlantilla).
            if (string.IsNullOrWhiteSpace(json))
                return resultado;

            LimitesLecturaDto dto;
            try
            {
                dto = DeserializarJson<LimitesLecturaDto>(json);
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                throw new FormatException($"El parámetro de límites de lectura no es un JSON válido: {ex.Message}", ex);
            }

            if (dto == null)
                return resultado; // "{}" u objeto vacío: todo por defecto.

            if (dto.MaximoBytesComprimido.HasValue)
            {
                if (dto.MaximoBytesComprimido.Value <= 0)
                    throw new FormatException("El parámetro de límites de lectura tiene un tope de bytes comprimidos inválido: debe ser un entero positivo.");
                resultado.TamanoMaximoBytesEntrada = dto.MaximoBytesComprimido.Value;
            }

            if (dto.MaximoBytesDescomprimido.HasValue)
            {
                if (dto.MaximoBytesDescomprimido.Value <= 0)
                    throw new FormatException("El parámetro de límites de lectura tiene un tope de bytes descomprimidos inválido: debe ser un entero positivo.");
                resultado.TamanoMaximoBytesDescomprimidos = dto.MaximoBytesDescomprimido.Value;
            }

            return resultado;
        }

        internal static T DeserializarJson<T>(string json) where T : class
        {
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(json)))
            {
                var serializador = new DataContractJsonSerializer(typeof(T));
                return (T)serializador.ReadObject(stream);
            }
        }

        [DataContract]
        private sealed class LimitesLecturaDto
        {
            [DataMember(Name = "maximoBytesComprimido")]
            public long? MaximoBytesComprimido { get; set; }

            [DataMember(Name = "maximoBytesDescomprimido")]
            public long? MaximoBytesDescomprimido { get; set; }
        }
    }
}
