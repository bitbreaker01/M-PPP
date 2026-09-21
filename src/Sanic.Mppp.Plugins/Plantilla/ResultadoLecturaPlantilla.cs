using System.Collections.Generic;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>Una fila de datos de la ventana que trae al menos un valor. Las filas totalmente vacías no se devuelven.</summary>
    public sealed class FilaPlantilla
    {
        /// <summary>Número de fila en el Excel (la 12, la 13…).</summary>
        public int NumeroFilaExcel { get; set; }

        /// <summary>Posición dentro de la ventana, empezando en 1: la primera fila de datos configurada es la 1, tenga o no valores.</summary>
        public int NumeroOrden { get; set; }

        /// <summary>Valor de cada campo configurado, por LETRA DE COLUMNA. Un campo sin celda trae texto vacío.</summary>
        public IDictionary<string, string> Valores { get; set; }
    }

    /// <summary>Algo que el lector leyó pero no pudo interpretar con seguridad (LP-07: nada se pierde callado).</summary>
    public sealed class AdvertenciaLectura
    {
        public int NumeroFilaExcel { get; set; }

        public string Columna { get; set; }

        public string Motivo { get; set; }
    }

    public sealed class ResultadoLecturaPlantilla
    {
        private ResultadoLecturaPlantilla(bool esValido, IList<string> errores, IList<FilaPlantilla> filas, IList<AdvertenciaLectura> advertencias)
        {
            EsValido = esValido;
            Errores = errores;
            Filas = filas;
            Advertencias = advertencias;
        }

        public bool EsValido { get; }

        /// <summary>Motivos por los que el archivo es inválido, en texto para el cliente. Vacío si es válido.</summary>
        public IList<string> Errores { get; }

        public IList<FilaPlantilla> Filas { get; }

        public IList<AdvertenciaLectura> Advertencias { get; }

        public static ResultadoLecturaPlantilla ConFilas(IList<FilaPlantilla> filas, IList<AdvertenciaLectura> advertencias)
        {
            return new ResultadoLecturaPlantilla(true, new List<string>(), filas, advertencias);
        }

        public static ResultadoLecturaPlantilla ConError(string motivo)
        {
            return new ResultadoLecturaPlantilla(false, new List<string> { motivo }, new List<FilaPlantilla>(), new List<AdvertenciaLectura>());
        }

        public static ResultadoLecturaPlantilla ConErrores(IList<string> motivos)
        {
            return new ResultadoLecturaPlantilla(false, motivos, new List<FilaPlantilla>(), new List<AdvertenciaLectura>());
        }
    }
}
