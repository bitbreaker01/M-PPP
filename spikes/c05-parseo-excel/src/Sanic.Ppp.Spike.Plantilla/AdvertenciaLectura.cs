namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Algo que no impide leer la fila (no es un error de archivo) pero que una regla de
    /// registro deberia poder rechazar con motivo: una celda numerica con 16+ digitos que
    /// Excel puede haber redondeado, o una celda con un valor de error de Excel (#REF!, #N/A...).
    /// </summary>
    public sealed class AdvertenciaLectura
    {
        public int NumeroFilaExcel { get; set; }
        public string Columna { get; set; }
        public string Motivo { get; set; }
    }
}
