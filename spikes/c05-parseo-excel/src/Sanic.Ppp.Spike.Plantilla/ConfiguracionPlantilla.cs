using System.Collections.Generic;

namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Configuracion parametrizada de una plantilla Excel: de donde leer, sin posiciones fijas
    /// en el codigo (diseno 02-diccionario-datos.md #2.5, parametro PLANTILLA).
    /// </summary>
    public sealed class ConfiguracionPlantilla
    {
        public string Hoja { get; set; }
        public int FilaEncabezado { get; set; }
        public int PrimeraFila { get; set; }
        public int CantidadFilas { get; set; }
        public IList<CampoPlantilla> Campos { get; set; }
    }
}
