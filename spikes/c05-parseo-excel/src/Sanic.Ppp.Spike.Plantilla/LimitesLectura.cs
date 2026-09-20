namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// LIMITES_LECTURA (03-contratos-custom-api.md #7, LP-08): topes explicitos sobre lo que el
    /// lector recorre, no sobre lo que espera encontrar. Valores por defecto conservadores para
    /// cuando el parametro de Dataverse falta (RF-05). Valores iniciales propuestos por el diseno.
    /// </summary>
    public sealed class LimitesLectura
    {
        public long TamanoMaximoBytesEntrada { get; set; } = 10L * 1024 * 1024;
        public long TamanoMaximoBytesDescomprimidos { get; set; } = 50L * 1024 * 1024;
        public int MaximoFilasRecorridas { get; set; } = 5000;
        public int MaximoCeldasPorFila { get; set; } = 200;
    }
}
