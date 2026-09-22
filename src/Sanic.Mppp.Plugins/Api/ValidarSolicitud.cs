using System;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;

namespace Sanic.Mppp.Plugins.Api
{
    /// <summary>Las salidas de `sanic_mppp_capi_validarsolicitud` (diseno/03 §1).</summary>
    public sealed class ResultadoDeValidacion
    {
        public ResultadoDeValidacion(EstadoDeLaSolicitud estado, bool yaProcesada, int filasTotales, int filasValidas, int filasRechazadas, string resumen)
        {
            Estado = estado;
            YaProcesada = yaProcesada;
            FilasTotales = filasTotales;
            FilasValidas = filasValidas;
            FilasRechazadas = filasRechazadas;
            Resumen = resumen;
        }

        public EstadoDeLaSolicitud Estado { get; }

        public bool YaProcesada { get; }

        public int FilasTotales { get; }

        public int FilasValidas { get; }

        public int FilasRechazadas { get; }

        /// <summary>Una línea para el run history del flujo. Nunca trae datos del cliente.</summary>
        public string Resumen { get; }
    }

    /// <summary>
    /// El plugin grande: abre la plantilla y valida la Solicitud entera (diseno/03 §1), sin el envoltorio `IPlugin` (que es
    /// <see cref="ValidarSolicitudApi"/>). Contrato (lo fijan las pruebas `ValidarSolicitudAceptacion`):
    ///  1. lee la Solicitud; si no está en Ingresada → `YaProcesada`, con los contadores y el estado ya guardados, sin tocar nada;
    ///  2. carga UNA vez los parámetros `plantilla.estructura`, `plantilla.listas`, `plantilla.obligatoriedad` y `lectura.limites`
    ///     (la versión activa más alta de cada uno); un parámetro que falta o está mal cargado es un error REAL, no una regla
    ///     fallida: sin él no se puede validar nada. `sanic_versionparametros` queda como `estructura=2;listas=3;obligatoriedad=1`
    ///     (en ese orden, con la versión de cada uno; `lectura.limites` no va: no cambia cómo se valida, solo cuánto se lee);
    ///  3. evalúa las reglas de nivel Solicitud con <see cref="ReglasDelSobre"/> y guarda un `ResultadoRegla` por cada una. El
    ///     Excel se abre UNA sola vez y solo si alguna regla lo necesita (el sobre corta antes si no hay adjunto);
    ///  4. si el sobre no deja seguir (alguna Rechaza no cumplida, o una que Envía a revisión: D-39), NO se leen filas: la
    ///     Solicitud queda Rechazada (o No reconocida), con el acuse armado, los contadores en cero y la Bitácora;
    ///  5. si el sobre pasa, por cada fila de la plantilla evalúa las reglas de nivel Registro con <see cref="ReglasDeRegistro"/>,
    ///     arma su estado y su `sanic_mensaje`, y guarda las filas. Los catálogos se cargan UNA vez: los planes de todos los
    ///     números de plan de la plantilla en una consulta, y las autorizaciones del remitente aparte (diseno/03 §1 paso 6);
    ///  6. estado final: Rechazada si ninguna fila quedó Validada (DD-09), si no En proceso. Escribe el acuse
    ///     (<see cref="Respuesta.ArmadorRespuesta"/>), los contadores, `sanic_fechavalidada` y la Bitácora "Validación terminada";
    ///  7. ningún camino termina sin Bitácora, y en ninguno se le responde al cliente desde acá (eso es `MPPP-ENV`).
    /// Nada lee el reloj: la fecha llega por parámetro y tiene que ser UTC. Una excepción real se propaga tal cual.
    /// </summary>
    public sealed class ValidarSolicitud
    {
        public const string ParametroEstructura = "plantilla.estructura";
        public const string ParametroListas = "plantilla.listas";
        public const string ParametroObligatoriedad = "plantilla.obligatoriedad";
        public const string ParametroLimites = "lectura.limites";

        /// <summary>`sanic_exceloriginal`, la columna de archivo de la que se lee la plantilla.</summary>
        public const string ColumnaExcel = "sanic_exceloriginal";

        public ValidarSolicitud(SolicitudesDataverse solicitudes, CatalogosDataverse catalogos, IArchivos archivos, ILectorPlantilla lector)
        {
            throw new NotImplementedException();
        }

        public ResultadoDeValidacion Ejecutar(Guid solicitudId, DateTime ahoraUtc)
        {
            throw new NotImplementedException();
        }
    }
}
