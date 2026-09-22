using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization.Json;
using System.Text;
using Sanic.Mppp.Plugins.Correo;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Validacion;

namespace Sanic.Mppp.Plugins.Api
{
    /// <summary>Los valores del parámetro de salida `clasificacion` de `sanic_mppp_capi_clasificarcorreo` (diseno/03 §0). Exactos.</summary>
    public static class Clasificaciones
    {
        public const string Nuevo = "nuevo";
        public const string Reenvio = "reenvio";
        public const string Respuesta = "respuesta";
        public const string RemitenteNoReconocido = "remitente_no_reconocido";
        public const string Ilegible = "ilegible";
    }

    /// <summary>Las salidas de la Custom API (diseno/03 §0).</summary>
    public sealed class ResultadoDeClasificacion
    {
        public ResultadoDeClasificacion(bool procesar, string clasificacion, bool yaProcesada)
        {
            Procesar = procesar;
            Clasificacion = clasificacion;
            YaProcesada = yaProcesada;
        }

        public bool Procesar { get; }

        /// <summary>Uno de <see cref="Clasificaciones"/>; nulo cuando <see cref="YaProcesada"/>.</summary>
        public string Clasificacion { get; }

        public bool YaProcesada { get; }
    }

    /// <summary>Aviso dentro de la app a todos los ejecutivos (diseno/05 DA-08; diseno/03 §0 paso 5). La implementación sobre `appnotification` es de otra pieza.</summary>
    public interface IAvisos
    {
        void AvisarAEjecutivos(Guid solicitudId, string titulo, string cuerpo);
    }

    /// <summary>
    /// Lo que las reglas de nivel Correo miran (diseno/03 §0 paso 3). Sin SDK. Lo arma <see cref="ClasificarCorreo"/> con lo que
    /// leyó; la vista es de solo lectura.
    /// </summary>
    public sealed class CorreoEnValidacion
    {
        public CorreoEnValidacion(CabecerasLeidas cabeceras, IList<string> prefijosDeReenvio, ISet<Guid> planesAutorizadosDelRemitente)
        {
            Cabeceras = cabeceras ?? throw new ArgumentNullException(nameof(cabeceras));

            if (prefijosDeReenvio == null)
            {
                throw new ArgumentNullException(nameof(prefijosDeReenvio));
            }

            if (planesAutorizadosDelRemitente == null)
            {
                throw new ArgumentNullException(nameof(planesAutorizadosDelRemitente));
            }

            AsuntoEsDeReenvio = EmpiezaConAlgunPrefijo(cabeceras.Asunto, prefijosDeReenvio);
            PlanesAutorizados = planesAutorizadosDelRemitente.Count;
        }

        public CabecerasLeidas Cabeceras { get; }

        /// <summary>El asunto empieza (sin espacios a los lados, sin distinguir mayúsculas) con alguno de los prefijos de `correo.prefijos.reenvio`.</summary>
        public bool AsuntoEsDeReenvio { get; }

        /// <summary>Cuántos planes tiene autorizados el remitente con todo activo (D-42).</summary>
        public int PlanesAutorizados { get; }

        private static bool EmpiezaConAlgunPrefijo(string asunto, IEnumerable<string> prefijos)
        {
            var recortado = (asunto ?? string.Empty).Trim();
            foreach (var prefijo in prefijos)
            {
                if (string.IsNullOrEmpty(prefijo))
                {
                    continue;
                }

                if (recortado.StartsWith(prefijo.Trim(), StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }
    }

    /// <summary>
    /// Los evaluadores de las dos reglas semilla de nivel Correo (diseno/02 §2.6; diseno/03 §0 paso 3). Sueltos fallan cerrado.
    ///  - `ES_CORREO_NUEVO`: se cumple si las cabeceras son legibles y (no traen referencias a otro correo, o las traen y el asunto
    ///    es de reenvío). Ilegibles o respuesta → no se cumple. Marcador `valor` = el asunto citado.
    ///  - `REMITENTE_RECONOCIDO`: se cumple si el remitente tiene al menos un plan autorizado.
    /// Los textos de estas reglas NO llegan al cliente (no se le responde): son para la bandeja Por clasificar.
    /// </summary>
    public static class ReglasDelCorreo
    {
        public const string EsCorreoNuevo = "ES_CORREO_NUEVO";
        public const string RemitenteReconocido = "REMITENTE_RECONOCIDO";

        public static IList<IEvaluador<CorreoEnValidacion>> Evaluadores()
        {
            return new List<IEvaluador<CorreoEnValidacion>>
            {
                new EsCorreoNuevoEvaluador(),
                new RemitenteReconocidoEvaluador(),
            };
        }

        private static CorreoEnValidacion Requerido(CorreoEnValidacion correo)
        {
            if (correo == null)
            {
                throw new ArgumentNullException(nameof(correo));
            }

            return correo;
        }

        private static IDictionary<string, string> MarcadorValor(string asunto)
        {
            return new Dictionary<string, string> { ["valor"] = asunto ?? string.Empty };
        }

        /// <summary>
        /// `03` §0 paso 3: nuevo (no trae referencias) o reenvío (trae referencias y el asunto es de reenvío) cumplen; ilegible o
        /// respuesta, no.
        /// </summary>
        private sealed class EsCorreoNuevoEvaluador : IEvaluador<CorreoEnValidacion>
        {
            public string Codigo => EsCorreoNuevo;

            public Veredicto Evaluar(CorreoEnValidacion correo)
            {
                correo = Requerido(correo);

                if (!correo.Cabeceras.Legibles)
                {
                    return Veredicto.NoCumplida("No se pudieron leer las cabeceras del correo.", MarcadorValor(correo.Cabeceras.Asunto), null);
                }

                if (!correo.Cabeceras.TraeReferenciasAOtroCorreo || correo.AsuntoEsDeReenvio)
                {
                    return Veredicto.Cumplida();
                }

                return Veredicto.NoCumplida("El correo es una respuesta a otro correo.", MarcadorValor(correo.Cabeceras.Asunto), null);
            }
        }

        /// <summary>`02` §2.4, D-42: el remitente tiene al menos una autorización vigente sobre algún plan.</summary>
        private sealed class RemitenteReconocidoEvaluador : IEvaluador<CorreoEnValidacion>
        {
            public string Codigo => RemitenteReconocido;

            public Veredicto Evaluar(CorreoEnValidacion correo)
            {
                correo = Requerido(correo);

                if (correo.PlanesAutorizados >= 1)
                {
                    return Veredicto.Cumplida();
                }

                return Veredicto.NoCumplida("El remitente no tiene ningún plan autorizado.");
            }
        }
    }

    /// <summary>
    /// El plugin liviano, sin el envoltorio de `IPlugin` (que es `ClasificarCorreoApi`, pieza 7.6b, y solo traduce parámetros):
    /// "¿este correo merece procesarse?" (diseno/03 §0). Contrato (lo fijan las pruebas `ClasificarCorreoAceptacion`):
    ///  1. lee la Solicitud; si no está en Ingresada → `YaProcesada`, `Procesar` = false, sin tocar nada;
    ///  2. baja SOLO el inicio de `sanic_correocrudo` (tope <see cref="LectorDeCabeceras.TopeBytes"/>) y lee las cabeceras;
    ///  3. lee `correo.prefijos.reenvio` (JSON: lista de textos; ausente o ilegible → error real), las reglas activas de nivel Correo y
    ///     los planes autorizados del remitente (número fijo de consultas); evalúa con el motor y guarda un ResultadoRegla por regla;
    ///  4. decide: cabeceras ilegibles → `ilegible`; `ES_CORREO_NUEVO` no cumplida → `respuesta`; `REMITENTE_RECONOCIDO` no cumplida →
    ///     `remitente_no_reconocido`; si no, `nuevo` o `reenvio` según el asunto. `ilegible` y `respuesta` → estado No es correo nuevo;
    ///     `remitente_no_reconocido` → No reconocida; en los tres, `sanic_motivoclasificacion` con el motivo, Bitácora "Correo
    ///     clasificado" (origen Custom API) y un aviso a los ejecutivos; `Procesar` = false. `nuevo`/`reenvio` → la Solicitud sigue en
    ///     Ingresada, `Procesar` = true, y también Bitácora "Correo clasificado" (ningún camino termina sin rastro);
    ///  5. no abre el Excel, no carga planes por código, no arma ninguna comunicación al remitente;
    ///  6. una excepción real (catálogo mal armado, servicio) se propaga tal cual: la transacción la revierte la plataforma.
    /// Nada de acá lee el reloj: la fecha llega por parámetro (el plugin la toma del contexto) y tiene que ser UTC.
    /// </summary>
    public sealed class ClasificarCorreo
    {
        public const string ParametroPrefijosDeReenvio = "correo.prefijos.reenvio";

        private const string ColumnaCorreoCrudo = "sanic_correocrudo";

        private readonly SolicitudesDataverse _solicitudes;
        private readonly CatalogosDataverse _catalogos;
        private readonly IArchivos _archivos;
        private readonly IAvisos _avisos;

        public ClasificarCorreo(SolicitudesDataverse solicitudes, CatalogosDataverse catalogos, IArchivos archivos, IAvisos avisos)
        {
            _solicitudes = solicitudes ?? throw new ArgumentNullException(nameof(solicitudes));
            _catalogos = catalogos ?? throw new ArgumentNullException(nameof(catalogos));
            _archivos = archivos ?? throw new ArgumentNullException(nameof(archivos));
            _avisos = avisos ?? throw new ArgumentNullException(nameof(avisos));
        }

        public ResultadoDeClasificacion Ejecutar(Guid solicitudId, DateTime ahoraUtc)
        {
            if (solicitudId == Guid.Empty)
            {
                throw new ArgumentException("El id de la solicitud no puede estar vacío.", nameof(solicitudId));
            }

            if (ahoraUtc.Kind != DateTimeKind.Utc)
            {
                throw new ArgumentException("La fecha tiene que venir en UTC (Kind = DateTimeKind.Utc).", nameof(ahoraUtc));
            }

            // Paso 1: idempotencia (BP-PP-055). Si no está en Ingresada, no se toca nada más.
            var solicitud = _solicitudes.Leer(solicitudId);
            if (solicitud.Estado != EstadoDeLaSolicitud.Ingresada)
            {
                return new ResultadoDeClasificacion(false, null, true);
            }

            // Paso 2: SOLO el inicio del .eml; entrada no confiable, el cuerpo nunca se mira.
            var inicioDelArchivo = _archivos.DescargarInicio(TablasHistorico.Solicitud, solicitudId, ColumnaCorreoCrudo, LectorDeCabeceras.TopeBytes);
            var cabeceras = LectorDeCabeceras.Leer(inicioDelArchivo);

            // Paso 3: catálogos. Si el parámetro de prefijos o el catálogo de reglas están mal, es un error real
            // ANTES de escribir nada (nada queda a medias).
            var prefijos = LeerPrefijosDeReenvio();
            var planesAutorizados = _catalogos.PlanesAutorizadosDe(solicitud.Remitente);
            var reglasActivas = _catalogos.ReglasActivas(NivelDeLaRegla.Correo);

            var contexto = new CorreoEnValidacion(cabeceras, prefijos, planesAutorizados);
            var motor = new MotorDeReglas<CorreoEnValidacion>(ReglasDelCorreo.Evaluadores());
            var resultados = motor.Evaluar(reglasActivas, contexto);

            // `Envía a revisión` es el único efecto válido en el nivel Correo (02 §2.6): cualquier otro es catálogo mal
            // armado y el motor falla cerrado, igual que con una regla de Registro con efecto Rechaza (D-14, D-20).
            foreach (var resultado in resultados)
            {
                if (resultado.EfectoAplicado != EfectoDeLaRegla.EnviaARevision)
                {
                    throw new ConfiguracionDeReglasInvalidaException(
                        resultado.Codigo, $"La regla de nivel Correo '{resultado.Codigo}' tiene el efecto '{resultado.EfectoAplicado}': en Correo solo vale 'Envía a revisión'.");
                }
            }

            var resultadoNuevo = resultados.FirstOrDefault(r => string.Equals(r.Codigo, ReglasDelCorreo.EsCorreoNuevo, StringComparison.Ordinal));
            var resultadoReconocido = resultados.FirstOrDefault(r => string.Equals(r.Codigo, ReglasDelCorreo.RemitenteReconocido, StringComparison.Ordinal));
            if (resultadoNuevo == null || resultadoReconocido == null)
            {
                // Sin las dos reglas semilla de nivel Correo activas nadie decide: no se procesa a ciegas (02 §2.6).
                throw new ConfiguracionDeReglasInvalidaException(
                    null, $"El catálogo de reglas de nivel Correo no tiene activas '{ReglasDelCorreo.EsCorreoNuevo}' y '{ReglasDelCorreo.RemitenteReconocido}'.");
            }

            // Paso 4: decisión.
            string clasificacion;
            bool procesar;
            EstadoDeLaSolicitud estadoFinal = EstadoDeLaSolicitud.Ingresada;
            string motivo = null;

            if (!cabeceras.Legibles)
            {
                clasificacion = Clasificaciones.Ilegible;
                procesar = false;
                estadoFinal = EstadoDeLaSolicitud.NoEsCorreoNuevo;
                motivo = "No se pudieron leer las cabeceras del correo.";
            }
            else if (resultadoNuevo.Resultado != ResultadoDeLaRegla.Cumplida)
            {
                clasificacion = Clasificaciones.Respuesta;
                procesar = false;
                estadoFinal = EstadoDeLaSolicitud.NoEsCorreoNuevo;
                motivo = "El correo es una respuesta a otro correo: no se procesa (solo se procesan correos nuevos o reenvíos).";
            }
            else if (resultadoReconocido.Resultado != ResultadoDeLaRegla.Cumplida)
            {
                clasificacion = Clasificaciones.RemitenteNoReconocido;
                procesar = false;
                estadoFinal = EstadoDeLaSolicitud.NoReconocida;
                motivo = "El remitente no tiene ninguna autorización vigente sobre un plan.";
            }
            else
            {
                clasificacion = cabeceras.TraeReferenciasAOtroCorreo ? Clasificaciones.Reenvio : Clasificaciones.Nuevo;
                procesar = true;
            }

            // Un ResultadoRegla por cada una, en los dos finales (se procese o no procese).
            //
            // TROPIEZO DE FIRMAS (diseno/03 §0 paso 3, "el catálogo la trae"): CatalogosDataverse.ReglasActivas devuelve
            // DefinicionDeRegla, que NO trae el id de la regla (a diferencia de PlanDelCatalogo, que sí trae Guid Id). Sin ese id
            // no se puede armar el diccionario código -> id que pide GuardarResultados, así que acá queda vacío y
            // `sanic_reglaid` NO se completa. Se reporta como tropiezo en vez de tocar `Datos/Catalogos.cs` o
            // `Validacion/MotorDeReglas.cs`, que quedan fuera de los archivos permitidos para esta pieza.
            var idsDeReglaPorCodigo = new Dictionary<string, Guid>(StringComparer.Ordinal);
            _solicitudes.GuardarResultados(solicitudId, resultados, idsDeReglaPorCodigo, ahoraUtc);

            if (!procesar)
            {
                _solicitudes.Clasificar(solicitudId, new ClasificacionDelCorreo { Estado = estadoFinal, Motivo = motivo });
            }

            // Ningún camino termina sin rastro: Bitácora "Correo clasificado" también cuando sigue en Ingresada.
            _solicitudes.RegistrarEvento(solicitudId, ahoraUtc, EventoDeBitacora.CorreoClasificado, OrigenDelEvento.CustomAPI, 0, null, null);

            if (!procesar)
            {
                // No se arma ninguna comunicación para el remitente: el aviso es SOLO interno, a los ejecutivos.
                _avisos.AvisarAEjecutivos(solicitudId, TituloAviso(solicitud.Numero), CuerpoAviso(solicitud.Numero, motivo));
            }

            return new ResultadoDeClasificacion(procesar, clasificacion, false);
        }

        private static string TituloAviso(string numeroSolicitud) => $"Correo sin procesar: solicitud {numeroSolicitud}";

        private static string CuerpoAviso(string numeroSolicitud, string motivo) => $"La solicitud {numeroSolicitud} no se procesó automáticamente. Motivo: {motivo}";

        /// <summary>`correo.prefijos.reenvio`: JSON con una lista de textos. Ausente, ilegible, con un elemento vacío o que no es
        /// texto: error real (nunca `NullReferenceException`).</summary>
        private IList<string> LeerPrefijosDeReenvio()
        {
            var parametro = _catalogos.Parametro(ParametroPrefijosDeReenvio);
            if (parametro == null)
            {
                throw new InvalidOperationException($"Falta el parámetro '{ParametroPrefijosDeReenvio}' (sin ninguna versión activa).");
            }

            // `DataContractJsonSerializer` es más laxo de lo que pide el contrato: a un `List<string>` le acepta "{}" como
            // lista VACÍA (sin lanzar) y convierte un número JSON en texto sin quejarse. Se valida a mano, sin expresiones
            // regulares, que sea un arreglo y que cada elemento esté entre comillas ANTES de confiarle el resto (comillas
            // escapadas, unicode, etc.) al serializador.
            ValidarQueEsArregloDeTextosJson(parametro.Valor);

            List<string> prefijos;
            try
            {
                using (var flujo = new MemoryStream(Encoding.UTF8.GetBytes(parametro.Valor ?? string.Empty)))
                {
                    var serializador = new DataContractJsonSerializer(typeof(List<string>));
                    prefijos = (List<string>)serializador.ReadObject(flujo);
                }
            }
            catch (Exception ex) when (!(ex is OutOfMemoryException || ex is StackOverflowException || ex is System.Threading.ThreadAbortException))
            {
                throw new InvalidOperationException($"El parámetro '{ParametroPrefijosDeReenvio}' no es una lista de textos JSON válida: {ex.Message}", ex);
            }

            if (prefijos == null)
            {
                throw new InvalidOperationException($"El parámetro '{ParametroPrefijosDeReenvio}' no es una lista de textos JSON válida.");
            }

            foreach (var prefijo in prefijos)
            {
                if (string.IsNullOrWhiteSpace(prefijo))
                {
                    throw new InvalidOperationException($"El parámetro '{ParametroPrefijosDeReenvio}' tiene un elemento vacío.");
                }
            }

            return prefijos;
        }

        /// <summary>Estructura mínima de un arreglo JSON de textos (sin expresiones regulares): empieza con `[` y termina con
        /// `]`, y cada elemento de primer nivel empieza y termina con `"`. No interpreta escapes: eso lo hace el serializador
        /// después, ya sobre un elemento que se sabe que es una cadena.</summary>
        private void ValidarQueEsArregloDeTextosJson(string json)
        {
            var texto = (json ?? string.Empty).Trim();
            if (texto.Length < 2 || texto[0] != '[' || texto[texto.Length - 1] != ']')
            {
                throw new InvalidOperationException($"El parámetro '{ParametroPrefijosDeReenvio}' tiene que ser un arreglo JSON de textos.");
            }

            var contenido = texto.Substring(1, texto.Length - 2);
            foreach (var elemento in SepararElementosDeArregloJson(contenido))
            {
                var recortado = elemento.Trim();
                if (recortado.Length < 2 || recortado[0] != '"' || recortado[recortado.Length - 1] != '"')
                {
                    throw new InvalidOperationException($"El parámetro '{ParametroPrefijosDeReenvio}' tiene un elemento que no es texto.");
                }
            }
        }

        /// <summary>Separa por comas de primer nivel, sin partir una coma que esté DENTRO de un texto entre comillas.</summary>
        private static IList<string> SepararElementosDeArregloJson(string contenido)
        {
            var elementos = new List<string>();
            if (string.IsNullOrWhiteSpace(contenido))
            {
                return elementos;
            }

            var inicio = 0;
            var dentroDeTexto = false;
            for (var i = 0; i < contenido.Length; i++)
            {
                var c = contenido[i];
                if (c == '"' && (i == 0 || contenido[i - 1] != '\\'))
                {
                    dentroDeTexto = !dentroDeTexto;
                }
                else if (c == ',' && !dentroDeTexto)
                {
                    elementos.Add(contenido.Substring(inicio, i - inicio));
                    inicio = i + 1;
                }
            }

            elementos.Add(contenido.Substring(inicio));
            return elementos;
        }
    }
}
