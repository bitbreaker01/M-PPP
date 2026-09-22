using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;
using Sanic.Mppp.Plugins.Respuesta;
using Sanic.Mppp.Plugins.Validacion;

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

        private readonly SolicitudesDataverse _solicitudes;
        private readonly CatalogosDataverse _catalogos;
        private readonly IArchivos _archivos;
        private readonly ILectorPlantilla _lector;

        public ValidarSolicitud(SolicitudesDataverse solicitudes, CatalogosDataverse catalogos, IArchivos archivos, ILectorPlantilla lector)
        {
            _solicitudes = solicitudes ?? throw new ArgumentNullException(nameof(solicitudes));
            _catalogos = catalogos ?? throw new ArgumentNullException(nameof(catalogos));
            _archivos = archivos ?? throw new ArgumentNullException(nameof(archivos));
            _lector = lector ?? throw new ArgumentNullException(nameof(lector));
        }

        public ResultadoDeValidacion Ejecutar(Guid solicitudId, DateTime ahoraUtc)
        {
            if (solicitudId == Guid.Empty)
            {
                throw new ArgumentException("El id de la solicitud no puede estar vacío.", nameof(solicitudId));
            }

            if (ahoraUtc.Kind != DateTimeKind.Utc)
            {
                throw new ArgumentException("La fecha tiene que venir en UTC (Kind = DateTimeKind.Utc).", nameof(ahoraUtc));
            }

            var solicitud = _solicitudes.Leer(solicitudId);

            // Paso 1 (diseno/03 §1): idempotencia. Fuera de Ingresada se devuelve lo guardado, sin tocar nada más: UNA
            // sola llamada a Dataverse en todo el camino (la Leer() de arriba).
            //
            // NOTA (tropiezo candidato, ver reporte): SolicitudLeida (Datos/Solicitudes.cs) no trae sanic_filastotales/
            // filasvalidas/filasrechazadas, así que acá no se pueden devolver esos tres contadores ya guardados sin una
            // segunda lectura (que rompería la regla de "una sola llamada" que fija la prueba de aceptación). Se devuelven
            // en cero: es lo único que se puede hacer sin tocar un archivo fuera del alcance de esta pieza.
            if (solicitud.Estado != EstadoDeLaSolicitud.Ingresada)
            {
                return new ResultadoDeValidacion(solicitud.Estado, true, 0, 0, 0,
                    string.Format(CultureInfo.InvariantCulture, "Solicitud {0}: ya procesada (estado {1}).", solicitud.Numero, solicitud.Estado));
            }

            // Paso 2 (diseno/03 §1 paso 3): los 4 parámetros, versión activa más alta. El que falta es un error REAL
            // (no una regla fallida) cuyo mensaje nombra el parámetro.
            var pEstructura = ParametroObligatorio(ParametroEstructura);
            var pListas = ParametroObligatorio(ParametroListas);
            var pObligatoriedad = ParametroObligatorio(ParametroObligatoriedad);
            var pLimites = ParametroObligatorio(ParametroLimites);

            var estructura = ConfiguracionPlantilla.DesdeJson(pEstructura.Valor);
            var listas = ListasPlantilla.DesdeJson(pListas.Valor);
            var obligatoriedad = ObligatoriedadPlantilla.DesdeJson(pObligatoriedad.Valor);
            var limites = LimitesLectura.DesdeJson(pLimites.Valor);

            // `lectura.limites` no entra en sanic_versionparametros: no cambia cómo se valida, solo cuánto se lee (diseno/03 §1 paso 3).
            var versionParametros = string.Format(
                CultureInfo.InvariantCulture, "estructura={0};listas={1};obligatoriedad={2}",
                pEstructura.Version, pListas.Version, pObligatoriedad.Version);

            // Paso 3 (diseno/03 §1 pasos 2 y 4): el sobre, con la plantilla leída A DEMANDA y una sola vez.
            var sobre = new SobreEnValidacion(solicitud.CantidadAdjuntos, solicitud.CantidadExcel,
                () => LeerPlantilla(solicitudId, limites, estructura));

            var reglasSolicitud = _catalogos.ReglasActivasConId(NivelDeLaRegla.Solicitud);
            var idsSolicitudPorCodigo = reglasSolicitud.ToDictionary(r => r.Definicion.Codigo, r => r.Id, StringComparer.Ordinal);
            var motorSobre = new MotorDeReglas<SobreEnValidacion>(ReglasDelSobre.Evaluadores());
            var resultadosSolicitud = motorSobre.Evaluar(reglasSolicitud.Select(r => r.Definicion), sobre);

            // Paso 4: si alguna regla de solicitud No cumplida tiene efecto Rechaza o Envía a revisión, el sobre no deja
            // seguir: no se leen filas. Advierte no bloquea (diseno/02 §1 "Efecto de regla").
            var sobreDejaSeguir = !resultadosSolicitud.Any(r =>
                r.Resultado == ResultadoDeLaRegla.NoCumplida && r.EfectoAplicado != EfectoDeLaRegla.Advierte);

            var filasParaGuardar = new List<FilaParaGuardar>();
            var filasParaRespuesta = new List<FilaParaRespuesta>();
            var estadosDeFilas = new List<EstadoDeLaFila>();

            if (sobreDejaSeguir)
            {
                ProcesarFilas(sobre, estructura, listas, obligatoriedad, solicitud.Remitente, ahoraUtc, filasParaGuardar, filasParaRespuesta, estadosDeFilas);
            }

            var estadoFinal = EstadosPorReglas.DeLaSolicitud(resultadosSolicitud, estadosDeFilas);

            // El historial del sobre se guarda SIEMPRE, pase lo que pase (diseno/03 §1 paso 4: "en los tres finales posibles").
            _solicitudes.GuardarResultados(solicitudId, resultadosSolicitud, idsSolicitudPorCodigo, ahoraUtc);

            if (filasParaGuardar.Count > 0)
            {
                _solicitudes.GuardarFilas(solicitudId, filasParaGuardar);
            }

            var filasValidas = estadosDeFilas.Count(e => e == EstadoDeLaFila.Validada);
            var filasRechazadas = filasParaGuardar.Count - filasValidas;

            var acuse = ArmarAcuse(solicitud, estadoFinal, resultadosSolicitud, filasParaRespuesta);

            _solicitudes.CerrarValidacion(solicitudId, new CierreDeValidacion
            {
                Estado = estadoFinal,
                FechaValidada = ahoraUtc,
                FilasTotales = filasParaGuardar.Count,
                FilasValidas = filasValidas,
                FilasRechazadas = filasRechazadas,
                AcuseContenido = acuse,
                VersionParametros = versionParametros,
            });

            var resumen = ArmarResumen(solicitud.Numero, estadoFinal, filasParaGuardar.Count, filasValidas, filasRechazadas);

            // Ningún camino termina sin Bitácora (diseno/03 §1 paso 7).
            _solicitudes.RegistrarEvento(solicitudId, ahoraUtc, EventoDeBitacora.ValidacionTerminada, OrigenDelEvento.CustomAPI, 0, null, resumen);

            return new ResultadoDeValidacion(estadoFinal, false, filasParaGuardar.Count, filasValidas, filasRechazadas, resumen);
        }

        /// <summary>Un parámetro ausente es un error real que nombra su código (diseno/03 §1 paso 3), nunca una regla fallida.</summary>
        private ParametroLeido ParametroObligatorio(string nombre)
        {
            var parametro = _catalogos.Parametro(nombre);
            if (parametro == null)
            {
                throw new InvalidOperationException($"Falta el parámetro '{nombre}', necesario para validar la solicitud.");
            }

            return parametro;
        }

        /// <summary>
        /// Baja el Excel de `sanic_exceloriginal` y lo lee. LP-02: un archivo más pesado que el límite NO revienta acá:
        /// vuelve como un resultado de lectura inválido, para que sea la regla ESTRUCTURA_PLANTILLA la que no se cumpla,
        /// con un motivo para el cliente (diseno/03 §7).
        /// </summary>
        private ResultadoLecturaPlantilla LeerPlantilla(Guid solicitudId, LimitesLectura limites, ConfiguracionPlantilla estructura)
        {
            byte[] excel;
            try
            {
                excel = _archivos.Descargar(TablasHistorico.Solicitud, solicitudId, ColumnaExcel, limites.TamanoMaximoBytesEntrada);
            }
            catch (ArchivoExcedeElMaximoException)
            {
                return ResultadoLecturaPlantilla.ConError(
                    "El archivo de Excel pesa más de lo permitido. Por favor, envíe un archivo más liviano.");
            }

            return _lector.Leer(excel, estructura);
        }

        /// <summary>
        /// Paso 5 y 6 (diseno/03 §1): evalúa las reglas de registro fila por fila. Los catálogos se cargan UNA vez: los
        /// planes de todos los números de plan de la plantilla en una sola consulta `In`, y las autorizaciones del
        /// remitente aparte.
        /// </summary>
        private void ProcesarFilas(
            SobreEnValidacion sobre, ConfiguracionPlantilla estructura, ListasPlantilla listas, ObligatoriedadPlantilla obligatoriedad,
            string remitente, DateTime ahoraUtc,
            List<FilaParaGuardar> filasParaGuardar, List<FilaParaRespuesta> filasParaRespuesta, List<EstadoDeLaFila> estadosDeFilas)
        {
            var filasDeLaVentana = sobre.Lectura.Filas;
            if (filasDeLaVentana == null || filasDeLaVentana.Count == 0)
            {
                return;
            }

            // Catálogo "vacío" solo para normalizar los números de plan (no hace falta la lista de planes para eso):
            // sirve para pedir los planes de una sola vez, con una única consulta `In` (diseno/03 §1 paso 6). Normalizar
            // dos veces es barato (el orden lo confirma la tarea): se vuelve a armar la fila con el catálogo real abajo.
            var catalogosParaNormalizar = new CatalogosDeValidacion(estructura, listas, obligatoriedad, new List<PlanDelCatalogo>(), new List<Guid>());
            var codigosDePlan = filasDeLaVentana
                .Select(f => new FilaEnValidacion(f, catalogosParaNormalizar).NumeroPlanNormalizado)
                .Where(codigo => codigo != null)
                .Distinct(StringComparer.Ordinal);

            var planesActivos = _catalogos.PlanesActivosPorCodigo(codigosDePlan);
            var planesAutorizados = _catalogos.PlanesAutorizadosDe(remitente);
            var catalogos = new CatalogosDeValidacion(estructura, listas, obligatoriedad, planesActivos, planesAutorizados);

            var reglasRegistro = _catalogos.ReglasActivasConId(NivelDeLaRegla.Registro);
            var definicionesRegistro = reglasRegistro.Select(r => r.Definicion).ToList();
            var motorFila = new MotorDeReglas<FilaEnValidacion>(ReglasDeRegistro.Evaluadores());

            foreach (var filaPlantilla in filasDeLaVentana)
            {
                var fila = new FilaEnValidacion(filaPlantilla, catalogos);
                var resultadosFila = motorFila.Evaluar(definicionesRegistro, fila);
                var estadoFila = EstadosPorReglas.DeLaFila(resultadosFila);
                var motivos = EstadosPorReglas.MotivosDeLaFila(resultadosFila);
                var mensaje = motivos.Count > 0 ? string.Join(" ", motivos) : null;

                estadosDeFilas.Add(estadoFila);

                var numeroCuenta = fila.Recibido(CamposDeFila.NumeroCuenta);
                var numeroIdentificacion = fila.Recibido(CamposDeFila.NumeroIdentificacion);
                var numeroPlan = fila.NumeroPlanNormalizado;

                filasParaGuardar.Add(new FilaParaGuardar
                {
                    NumeroFila = fila.NumeroFila,
                    Gestion = fila.Gestion,
                    Clasificacion = fila.Clasificacion,
                    Moneda = fila.Moneda,
                    TipoIdentificacion = fila.TipoIdentificacion,
                    Banco = fila.Banco,
                    NumeroPlan = numeroPlan,
                    PlanId = fila.Plan?.Id,
                    NombreBeneficiario = fila.Recibido(CamposDeFila.NombreBeneficiario),
                    NumeroIdentificacion = numeroIdentificacion,
                    NumeroCuenta = numeroCuenta,
                    Referencia = fila.ReferenciaQueRige,
                    ReferenciaRecibida = fila.ReferenciaRecibida,
                    Estado = estadoFila,
                    Mensaje = mensaje,
                    FechaValidada = ahoraUtc,
                });

                filasParaRespuesta.Add(new FilaParaRespuesta
                {
                    NumeroFila = fila.NumeroFila,
                    NumeroPlan = numeroPlan ?? fila.Recibido(CamposDeFila.NumeroPlan),
                    NombreBeneficiario = fila.Recibido(CamposDeFila.NombreBeneficiario),
                    NumeroCuenta = numeroCuenta,
                    NumeroIdentificacion = numeroIdentificacion,
                    Estado = estadoFila,
                    Mensaje = mensaje,
                });
            }
        }

        /// <summary>Arma el acuse (RF-04, DD-09). No reconocida no tiene acuse: no se le responde al cliente sin que la mire una persona (D-39).</summary>
        private static string ArmarAcuse(SolicitudLeida solicitud, EstadoDeLaSolicitud estado, IList<ResultadoDeRegla> resultadosSolicitud, IList<FilaParaRespuesta> filas)
        {
            if (estado == EstadoDeLaSolicitud.NoReconocida)
            {
                return null;
            }

            var motivosDelSobre = resultadosSolicitud
                .Where(r => r.Resultado == ResultadoDeLaRegla.NoCumplida)
                .OrderBy(r => r.Orden)
                .Select(r => r.Razon)
                .ToList();

            return ArmadorRespuesta.Acuse(new SolicitudParaRespuesta
            {
                Numero = solicitud.Numero,
                FechaRecibidoTexto = solicitud.FechaRecibido.ToString("dd/MM/yyyy HH:mm", CultureInfo.InvariantCulture),
                Estado = estado,
                MotivosDelSobre = motivosDelSobre,
                Filas = filas,
            });
        }

        /// <summary>Una línea para el run history (`Resumen`), sin datos del cliente (diseno/03 §1 "resumen").</summary>
        private static string ArmarResumen(string numero, EstadoDeLaSolicitud estado, int totales, int validas, int rechazadas)
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "Solicitud {0}: {1}. Filas totales: {2}, válidas: {3}, rechazadas: {4}.",
                numero, estado, totales, validas, rechazadas);
        }
    }
}
