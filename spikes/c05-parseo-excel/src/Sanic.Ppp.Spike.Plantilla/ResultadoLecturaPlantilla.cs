using System.Collections.Generic;

namespace Sanic.Ppp.Spike.Plantilla
{
    /// <summary>
    /// Resultado de leer una plantilla: nunca una excepcion por un problema de datos o de archivo
    /// (eso es una regla fallida, no un fallo del sistema - 03-contratos-custom-api.md #1).
    /// FilasRecorridas/FilasMaterializadas son diagnostico (sirven para la Bitacora) y evidencia
    /// de que LP-04/LP-05 funcionan: cuantas filas se vieron en total vs. cuantas caian en rango.
    /// </summary>
    public sealed class ResultadoLecturaPlantilla
    {
        public bool EsValido { get; private set; }
        public IList<string> Errores { get; private set; }
        public IList<FilaPlantilla> Filas { get; private set; }
        public IList<AdvertenciaLectura> Advertencias { get; private set; }
        public int FilasRecorridas { get; private set; }
        public int FilasMaterializadas { get; private set; }

        private ResultadoLecturaPlantilla(
            bool esValido,
            IList<string> errores,
            IList<FilaPlantilla> filas,
            IList<AdvertenciaLectura> advertencias,
            int filasRecorridas,
            int filasMaterializadas)
        {
            EsValido = esValido;
            Errores = errores;
            Filas = filas;
            Advertencias = advertencias;
            FilasRecorridas = filasRecorridas;
            FilasMaterializadas = filasMaterializadas;
        }

        public static ResultadoLecturaPlantilla ConFilas(
            IList<FilaPlantilla> filas, IList<AdvertenciaLectura> advertencias, int filasRecorridas, int filasMaterializadas)
        {
            return new ResultadoLecturaPlantilla(true, new List<string>(), filas, advertencias, filasRecorridas, filasMaterializadas);
        }

        public static ResultadoLecturaPlantilla ConError(string motivo)
        {
            return new ResultadoLecturaPlantilla(false, new List<string> { motivo }, new List<FilaPlantilla>(), new List<AdvertenciaLectura>(), 0, 0);
        }

        public static ResultadoLecturaPlantilla ConErrores(IList<string> motivos)
        {
            return new ResultadoLecturaPlantilla(false, motivos, new List<FilaPlantilla>(), new List<AdvertenciaLectura>(), 0, 0);
        }
    }
}
