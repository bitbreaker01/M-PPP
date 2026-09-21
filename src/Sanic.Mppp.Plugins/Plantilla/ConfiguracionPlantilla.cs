using System;
using System.Collections.Generic;
using System.Globalization;
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

            // Los campos se arman "en crudo" acá (solo se normaliza la columna a mayúscula, que es un dato de forma del
            // JSON, no una regla de validez) y se validan con Invalidez, la MISMA función que usa LectorOpenXml.Leer para
            // una configuración armada a mano (revisión de código, 2026-09-21: antes DesdeJson exigía más que
            // ValidarConfiguracion, y una configuración a mano con EncabezadoEsperado = null pasaba como válida).
            var campos = new List<CampoPlantilla>();
            if (dto.Campos != null)
            {
                foreach (CampoPlantillaDto campoDto in dto.Campos)
                {
                    if (campoDto == null)
                    {
                        campos.Add(null);
                        continue;
                    }

                    string columna = campoDto.Columna;
                    if (!string.IsNullOrWhiteSpace(columna))
                        columna = columna.Trim().ToUpperInvariant();

                    campos.Add(new CampoPlantilla
                    {
                        Nombre = campoDto.Nombre,
                        Columna = columna,
                        EncabezadoEsperado = campoDto.Encabezado,
                        LargoMinimo = campoDto.LargoMinimo,
                        LargoMaximo = campoDto.LargoMaximo,
                        // El `formato` es texto en el JSON pero el dominio lo tipa como enum: la conversión ocurre acá,
                        // al armar el campo (no en Invalidez, que también valida una ConfiguracionPlantilla armada a mano
                        // por LectorOpenXml, donde el campo ya nace con un FormatoDeCampo? válido o nulo, nunca con un
                        // texto que interpretar). Un texto que no sea exactamente uno de los tres valores es
                        // FormatException (D-18b): una expresión mal escrita no puede tumbar ni aflojar la validación.
                        Formato = ParsearFormato(campoDto.Nombre, campoDto.Formato)
                    });
                }
            }

            var configuracion = new ConfiguracionPlantilla
            {
                Hoja = dto.Hoja,
                FilaEncabezado = dto.FilaEncabezado,
                PrimeraFila = dto.PrimeraFila,
                CantidadFilas = dto.CantidadFilas,
                Campos = campos
            };

            string motivo = Invalidez(configuracion);
            if (motivo != null)
                throw new FormatException($"El parámetro de estructura de la plantilla {motivo}");

            return configuracion;
        }

        /// <summary>Convierte el `formato` de texto del JSON (D-18b) al enum del dominio. Nulo o ausente → sin formato
        /// (cualquier texto vale). Cualquier otro texto que no sea exactamente `texto`, `digitos` o `alfanumerico` es un
        /// parámetro mal cargado.</summary>
        private static FormatoDeCampo? ParsearFormato(string nombreDelCampo, string formato)
        {
            switch (formato)
            {
                case null:
                    return null;
                case "texto":
                    return FormatoDeCampo.Texto;
                case "digitos":
                    return FormatoDeCampo.Digitos;
                case "alfanumerico":
                    return FormatoDeCampo.Alfanumerico;
                default:
                    throw new FormatException($"El parámetro de estructura de la plantilla trae un formato inválido ('{formato}') en el campo '{nombreDelCampo}': tiene que ser 'texto', 'digitos' o 'alfanumerico'.");
            }
        }

        /// <summary>Filas máximas de una hoja de Excel (LP-08): la ventana (primeraFila .. primeraFila + cantidadFilas - 1)
        /// tiene que caber dentro de este límite.</summary>
        internal const int FilaMaximaHojaExcel = 1_048_576;

        /// <summary>
        /// True si la ventana definida por <paramref name="primeraFila"/> y <paramref name="cantidadFilas"/> cabe en una
        /// hoja de Excel (LP-08). La cuenta se hace en <c>long</c> para no desbordar cuando <paramref name="cantidadFilas"/>
        /// es grande (ej. <see cref="int.MaxValue"/>). La usan <see cref="DesdeJson"/> (traduce a <see cref="FormatException"/>)
        /// y <c>LectorOpenXml.Leer</c> (traduce a <see cref="ArgumentException"/>), para que la regla de LP-08 no se
        /// separe con el tiempo (revisión de código, 2026-09-21).
        /// </summary>
        internal static bool VentanaCabeEnHoja(int primeraFila, int cantidadFilas)
        {
            long ultimaFila = (long)primeraFila + (long)cantidadFilas - 1L;
            return ultimaFila <= FilaMaximaHojaExcel;
        }

        /// <summary>Letra(s) de columna válida: solo letras (LP-01/LP-08). Interna para que LectorOpenXml.Leer valide la
        /// misma regla antes de entrar al try del SDK, sin duplicar el patrón.</summary>
        internal static readonly Regex RegexColumna = new Regex("^[A-Za-z]+$", RegexOptions.Compiled);

        /// <summary>
        /// ÚNICA validación de una <see cref="ConfiguracionPlantilla"/> ya armada, la use quien la use: <see cref="DesdeJson"/>
        /// (la traduce a <see cref="FormatException"/>) o <c>LectorOpenXml.Leer</c> (la traduce a <see cref="ArgumentException"/>).
        /// Antes cada camino tenía sus propias reglas y DesdeJson exigía más que LectorOpenXml.ValidarConfiguracion (encabezado
        /// esperado, columnas repetidas, nombres repetidos): una configuración armada a mano con EncabezadoEsperado = null pasaba
        /// como válida (hallazgo de la re-revisión, 2026-09-21). Devuelve el motivo del primer problema encontrado, o null si la
        /// configuración es válida. Única diferencia a propósito entre los dos caminos: el <see cref="CampoPlantilla.Nombre"/> es
        /// opcional acá (lo es al armar la configuración a mano); si viene, no puede repetirse.
        /// </summary>
        internal static string Invalidez(ConfiguracionPlantilla configuracion)
        {
            if (configuracion.Campos == null || configuracion.Campos.Count == 0)
                return "no trae ningún campo.";

            if (string.IsNullOrWhiteSpace(configuracion.Hoja))
                return "no indica la hoja.";

            if (configuracion.FilaEncabezado < 1)
                return "tiene una fila de encabezado inválida: debe ser 1 o mayor.";

            if (configuracion.PrimeraFila <= configuracion.FilaEncabezado)
                return "tiene una primera fila inválida: tiene que ser posterior a la fila de encabezado.";

            if (configuracion.CantidadFilas < 1)
                return "tiene una cantidad de filas inválida: debe ser 1 o mayor.";

            if (!VentanaCabeEnHoja(configuracion.PrimeraFila, configuracion.CantidadFilas))
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "define una ventana que no cabe en una hoja de Excel (hasta la fila {0}).",
                    FilaMaximaHojaExcel);

            var columnasVistas = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var nombresVistos = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (CampoPlantilla campo in configuracion.Campos)
            {
                if (campo == null)
                    return "trae un campo nulo.";

                if (string.IsNullOrWhiteSpace(campo.Columna) || !RegexColumna.IsMatch(campo.Columna.Trim()))
                    return $"trae una columna inválida ('{campo.Columna}').";

                string columna = campo.Columna.Trim();
                if (!columnasVistas.Add(columna))
                    return $"repite la columna '{columna}'.";

                if (string.IsNullOrWhiteSpace(campo.EncabezadoEsperado))
                    return "trae un campo sin encabezado esperado.";

                if (!string.IsNullOrWhiteSpace(campo.Nombre) && !nombresVistos.Add(campo.Nombre))
                    return $"repite el nombre de campo '{campo.Nombre}'.";

                if (campo.LargoMinimo.HasValue && campo.LargoMinimo.Value < 0)
                    return $"trae un largo mínimo inválido ({campo.LargoMinimo.Value}) en el campo '{campo.Nombre}': no puede ser negativo.";

                if (campo.LargoMaximo.HasValue && campo.LargoMaximo.Value < 1)
                    return $"trae un largo máximo inválido ({campo.LargoMaximo.Value}) en el campo '{campo.Nombre}': tiene que ser 1 o mayor.";

                if (campo.LargoMinimo.HasValue && campo.LargoMaximo.HasValue && campo.LargoMinimo.Value > campo.LargoMaximo.Value)
                    return $"trae un largo mínimo ({campo.LargoMinimo.Value}) mayor que el máximo ({campo.LargoMaximo.Value}) en el campo '{campo.Nombre}'.";
            }

            return null;
        }

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

            [DataMember(Name = "largoMinimo")]
            public int? LargoMinimo { get; set; }

            [DataMember(Name = "largoMaximo")]
            public int? LargoMaximo { get; set; }

            [DataMember(Name = "formato")]
            public string Formato { get; set; }
        }
    }

    /// <summary>
    /// Formatos admitidos en `plantilla.estructura` (D-18b, aprobador 2026-09-21). En el JSON: `texto`, `digitos`, `alfanumerico`
    /// (exactos, en minúscula). `digitos`: solo 0-9 ASCII. `alfanumerico`: solo A-Z, a-z y 0-9 ASCII, sin espacios. Otro valor es
    /// parámetro mal cargado (<see cref="FormatException"/>): una expresión mal escrita no puede tumbar ni aflojar la validación.
    /// </summary>
    public enum FormatoDeCampo
    {
        Texto,
        Digitos,
        Alfanumerico,
    }

    public sealed class CampoPlantilla
    {
        /// <summary>Nombre del campo para el resto del código (`numeroPlan`). Opcional al armar la configuración a mano.</summary>
        public string Nombre { get; set; }

        /// <summary>Letra de la columna en el Excel (`D`, `AA`).</summary>
        public string Columna { get; set; }

        /// <summary>Texto que tiene que traer la fila de encabezado en esa columna (se compara sin espacios al inicio ni al final).</summary>
        public string EncabezadoEsperado { get; set; }

        /// <summary>`largoMinimo` (D-18b). Nulo = sin mínimo. Lo usa la regla LARGOS_Y_FORMATO; el lector no lo mira.</summary>
        public int? LargoMinimo { get; set; }

        /// <summary>`largoMaximo` (D-18b). Nulo = sin máximo.</summary>
        public int? LargoMaximo { get; set; }

        /// <summary>`formato` (D-18b): lista CERRADA, sin expresiones regulares. Nulo = cualquier texto.</summary>
        public FormatoDeCampo? Formato { get; set; }
    }
}
