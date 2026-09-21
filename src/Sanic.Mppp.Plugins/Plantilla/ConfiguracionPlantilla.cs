using System;
using System.Collections.Generic;

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
            throw new NotImplementedException();
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
