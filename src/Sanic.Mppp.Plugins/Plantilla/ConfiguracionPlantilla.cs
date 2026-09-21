using System;
using System.Collections.Generic;
using System.Runtime.Serialization;
using System.Text.RegularExpressions;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>
    /// La ventana que se lee de la plantilla (parámetro `plantilla.estructura`, diseno/03 §7 LP-04 y LP-08).
    /// Nada de la posición está fijo en el código: hoja, fila de encabezado, primera fila de datos, cantidad de filas y columna de cada campo.
    /// </summary>
    public sealed class ConfiguracionPlantilla
    {
        public string Hoja { get; set; }

        public int FilaEncabezado { get; set; }

        public int PrimeraFila { get; set; }

        public int CantidadFilas { get; set; }

        public IList<CampoPlantilla> Campos { get; set; }

        /// <summary>
        /// Lee el JSON del parámetro. Forma:
        /// {"hoja":"Plantilla","filaEncabezado":11,"primeraFila":12,"cantidadFilas":100,
        ///  "campos":[{"nombre":"numeroPlan","columna":"D","encabezado":"No. Plan"}]}
        /// Un JSON que no se puede leer, o con valores que no forman una ventana válida, es <see cref="FormatException"/>
        /// con el motivo: un parámetro mal cargado no puede terminar en una lectura "vacía pero válida".
        /// NO usa System.Text.Json (Microsoft advierte no depender de él en un plugin): DataContractJsonSerializer.
        /// </summary>
        public static ConfiguracionPlantilla DesdeJson(string json)
        {
            // A diferencia de LimitesLectura, acá NO hay "valor por defecto": la ventana de lectura
            // es obligatoria (LP-08). Un parámetro ausente o vacío es tan inválido como uno mal escrito.
            if (string.IsNullOrWhiteSpace(json))
                throw new FormatException("El parámetro de estructura de la plantilla está vacío.");

            ConfiguracionPlantillaDto dto;
            try
            {
                dto = LimitesLectura.DeserializarJson<ConfiguracionPlantillaDto>(json);
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                throw new FormatException($"El parámetro de estructura de la plantilla no es un JSON válido: {ex.Message}", ex);
            }

            if (dto == null)
                throw new FormatException("El parámetro de estructura de la plantilla no es un JSON válido.");

            if (string.IsNullOrWhiteSpace(dto.Hoja))
                throw new FormatException("El parámetro de estructura de la plantilla no indica la hoja.");

            if (dto.FilaEncabezado < 1)
                throw new FormatException("El parámetro de estructura de la plantilla tiene una fila de encabezado inválida: debe ser 1 o mayor.");

            if (dto.PrimeraFila <= dto.FilaEncabezado)
                throw new FormatException("El parámetro de estructura de la plantilla tiene una primera fila inválida: tiene que ser posterior a la fila de encabezado.");

            if (dto.CantidadFilas < 1)
                throw new FormatException("El parámetro de estructura de la plantilla tiene una cantidad de filas inválida: debe ser 1 o mayor.");

            if (dto.Campos == null || dto.Campos.Count == 0)
                throw new FormatException("El parámetro de estructura de la plantilla no trae ningún campo.");

            var campos = new List<CampoPlantilla>();
            var nombresVistos = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var columnasVistas = new HashSet<string>(StringComparer.Ordinal);

            foreach (CampoPlantillaDto campoDto in dto.Campos)
            {
                if (string.IsNullOrWhiteSpace(campoDto.Columna) || !RegexColumna.IsMatch(campoDto.Columna.Trim()))
                    throw new FormatException($"El parámetro de estructura de la plantilla trae una columna inválida ('{campoDto.Columna}').");

                if (string.IsNullOrWhiteSpace(campoDto.Encabezado))
                    throw new FormatException("El parámetro de estructura de la plantilla trae un campo sin encabezado esperado.");

                string columna = campoDto.Columna.Trim().ToUpperInvariant();
                if (!columnasVistas.Add(columna))
                    throw new FormatException($"El parámetro de estructura de la plantilla repite la columna '{columna}'.");

                if (!string.IsNullOrWhiteSpace(campoDto.Nombre) && !nombresVistos.Add(campoDto.Nombre))
                    throw new FormatException($"El parámetro de estructura de la plantilla repite el nombre de campo '{campoDto.Nombre}'.");

                campos.Add(new CampoPlantilla
                {
                    Nombre = campoDto.Nombre,
                    Columna = columna,
                    EncabezadoEsperado = campoDto.Encabezado
                });
            }

            return new ConfiguracionPlantilla
            {
                Hoja = dto.Hoja,
                FilaEncabezado = dto.FilaEncabezado,
                PrimeraFila = dto.PrimeraFila,
                CantidadFilas = dto.CantidadFilas,
                Campos = campos
            };
        }

        private static readonly Regex RegexColumna = new Regex("^[A-Za-z]+$", RegexOptions.Compiled);

        [DataContract]
        private sealed class ConfiguracionPlantillaDto
        {
            [DataMember(Name = "hoja")]
            public string Hoja { get; set; }

            [DataMember(Name = "filaEncabezado")]
            public int FilaEncabezado { get; set; }

            [DataMember(Name = "primeraFila")]
            public int PrimeraFila { get; set; }

            [DataMember(Name = "cantidadFilas")]
            public int CantidadFilas { get; set; }

            [DataMember(Name = "campos")]
            public List<CampoPlantillaDto> Campos { get; set; }
        }

        [DataContract]
        private sealed class CampoPlantillaDto
        {
            [DataMember(Name = "nombre")]
            public string Nombre { get; set; }

            [DataMember(Name = "columna")]
            public string Columna { get; set; }

            [DataMember(Name = "encabezado")]
            public string Encabezado { get; set; }
        }
    }

    public sealed class CampoPlantilla
    {
        /// <summary>Nombre del campo para el resto del código (`numeroPlan`). Opcional al armar la configuración a mano.</summary>
        public string Nombre { get; set; }

        /// <summary>Letra de la columna en el Excel (`D`, `AA`).</summary>
        public string Columna { get; set; }

        /// <summary>Texto que tiene que traer la fila de encabezado en esa columna (se compara sin espacios al inicio ni al final).</summary>
        public string EncabezadoEsperado { get; set; }
    }
}
