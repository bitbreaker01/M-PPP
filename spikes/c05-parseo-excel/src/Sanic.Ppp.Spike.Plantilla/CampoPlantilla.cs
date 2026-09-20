namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Un campo de la plantilla: en que columna vive y que encabezado se espera encontrar ahi.
    /// </summary>
    public sealed class CampoPlantilla
    {
        /// <summary>Letra de columna de Excel, ej. "B".</summary>
        public string Columna { get; set; }
        public string EncabezadoEsperado { get; set; }
    }
}
