using System.Collections.Generic;

namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Una fila leida de la plantilla, como texto tal cual lo escribio el cliente (DD-01).
    /// </summary>
    public sealed class FilaPlantilla
    {
        public int NumeroFilaExcel { get; set; }
        public int NumeroOrden { get; set; }

        /// <summary>Valor de cada campo, indexado por la letra de columna de <see cref="CampoPlantilla.Columna"/>.</summary>
        public IDictionary<string, string> Valores { get; set; }
    }
}
