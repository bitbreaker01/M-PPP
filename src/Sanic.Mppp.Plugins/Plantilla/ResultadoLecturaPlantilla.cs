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
        private ResultadoLecturaPlantilla(bool esValido, IList<string> errores, IList<FilaPlantilla> filas, IList<AdvertenciaLectura> advertencias, string detalleTecnico = null)
        {
            EsValido = esValido;
            Errores = errores;
            Filas = filas;
            Advertencias = advertencias;
            DetalleTecnico = detalleTecnico;
        }

        public bool EsValido { get; }

        /// <summary>Motivos por los que el archivo es inválido, en texto para el cliente. Vacío si es válido.</summary>
        public IList<string> Errores { get; }

        public IList<FilaPlantilla> Filas { get; }

        public IList<AdvertenciaLectura> Advertencias { get; }

        /// <summary>
        /// Lo que dijo la librería que lee el Excel cuando no pudo abrirlo. Es para la traza del plugin (ITracingService), NUNCA para el cliente:
        /// <see cref="Errores"/> termina en un correo a una persona de fuera del banco y no lleva jerga de un SDK de terceros. `null` si no aplica.
        /// </summary>
        public string DetalleTecnico { get; }

        public static ResultadoLecturaPlantilla ConFilas(IList<FilaPlantilla> filas, IList<AdvertenciaLectura> advertencias)
        {
            return new ResultadoLecturaPlantilla(true, new List<string>(), filas, advertencias);
        }

        public static ResultadoLecturaPlantilla ConError(string motivo)
        {
            return new ResultadoLecturaPlantilla(false, new List<string> { motivo }, new List<FilaPlantilla>(), new List<AdvertenciaLectura>());
        }

        /// <summary>El archivo no se pudo abrir o recorrer: al cliente, un texto nuestro; a la traza, lo que dijo la librería.</summary>
        public static ResultadoLecturaPlantilla ConErrorTecnico(string motivoParaElCliente, string detalleTecnico)
        {
            return new ResultadoLecturaPlantilla(false, new List<string> { motivoParaElCliente }, new List<FilaPlantilla>(), new List<AdvertenciaLectura>(), detalleTecnico);
        }

        public static ResultadoLecturaPlantilla ConErrores(IList<string> motivos)
        {
            return new ResultadoLecturaPlantilla(false, motivos, new List<FilaPlantilla>(), new List<AdvertenciaLectura>());
        }
    }
}
