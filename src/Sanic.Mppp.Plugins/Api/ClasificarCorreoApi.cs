using System;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Datos;

namespace Sanic.Mppp.Plugins.Api
{
    /// <summary>
    /// El envoltorio `IPlugin` de `sanic_mppp_capi_clasificarcorreo` (diseno/03 §0): traduce parámetros, arma las piezas y
    /// devuelve las salidas. NO tiene lógica de negocio: eso es <see cref="ClasificarCorreo"/>. Contrato (lo fijan las pruebas
    /// `ClasificarCorreoApiAceptacion`):
    ///  - entrada `solicitudid` (Guid); ausente, de otro tipo o vacío → <see cref="InvalidPluginExecutionException"/> con un
    ///    mensaje que dice qué falta, sin datos de la solicitud;
    ///  - salidas `procesar` (bool), `clasificacion` (string) y `yaprocesada` (bool), con esos nombres exactos y siempre las tres;
    ///  - el servicio se crea con <see cref="IPluginExecutionContext.UserId"/> (la cuenta de servicio que ejecuta la API), NO con
    ///    `InitiatingUserId`;
    ///  - la fecha sale de <see cref="IExecutionContext.OperationCreatedOn"/> tratada como UTC: el código nunca lee el reloj;
    ///  - deja rastro en <see cref="ITracingService"/> al empezar y al terminar (clasificación y si se procesa), sin volcar el
    ///    correo ni datos del cliente;
    ///  - una <see cref="InvalidPluginExecutionException"/> de adentro se propaga tal cual; cualquier OTRA excepción se traza
    ///    completa y se vuelve a lanzar como <see cref="InvalidPluginExecutionException"/> con un mensaje genérico que NO expone
    ///    el mensaje original (puede traer datos del correo o del SDK; diseno/03 §1 "Errores"). La transacción la revierte la
    ///    plataforma;
    ///  - un proveedor sin los servicios que necesita es <see cref="InvalidPluginExecutionException"/>, nunca
    ///    <see cref="NullReferenceException"/>.
    /// </summary>
    public sealed class ClasificarCorreoApi : IPlugin
    {
        public const string ParametroSolicitudId = "solicitudid";
        public const string SalidaProcesar = "procesar";
        public const string SalidaClasificacion = "clasificacion";
        public const string SalidaYaProcesada = "yaprocesada";

        /// <summary>Lo único que se le dice a quien llama cuando algo se rompe de verdad. El detalle va al trace.</summary>
        public const string MensajeDeErrorGenerico = "No se pudo clasificar el correo. El equipo tecnico ya tiene el detalle.";

        public void Execute(IServiceProvider serviceProvider)
        {
            if (serviceProvider == null)
            {
                throw new InvalidPluginExecutionException("No se recibió el proveedor de servicios del plugin.");
            }

            // Un proveedor sin lo que hace falta es un error de plataforma, nunca una referencia nula (contrato de la pieza).
            var contexto = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
            var fabrica = (IOrganizationServiceFactory)serviceProvider.GetService(typeof(IOrganizationServiceFactory));
            var trace = (ITracingService)serviceProvider.GetService(typeof(ITracingService));
            if (contexto == null || fabrica == null || trace == null)
            {
                throw new InvalidPluginExecutionException("Faltan servicios de la plataforma para ejecutar la Custom API.");
            }

            var solicitudId = LeerSolicitudId(contexto);

            try
            {
                trace.Trace($"ClasificarCorreo: empieza para la solicitud {solicitudId}.");

                // SYSTEM, no quien llama: mismo motivo que en `ValidarSolicitudApi` (diseno/04 §1 y §3). Este plugin
                // lee las autorizaciones del remitente, que la cuenta de servicio no tiene permiso de leer.
                var servicio = fabrica.CreateOrganizationService(null);
                var clasificar = new ClasificarCorreo(
                    new SolicitudesDataverse(servicio), new CatalogosDataverse(servicio), new ArchivosDataverse(servicio), new AvisosDataverse(servicio));

                var ahoraUtc = DateTime.SpecifyKind(contexto.OperationCreatedOn, DateTimeKind.Utc);
                var resultado = clasificar.Ejecutar(solicitudId, ahoraUtc);

                contexto.OutputParameters[SalidaProcesar] = resultado.Procesar;
                contexto.OutputParameters[SalidaClasificacion] = resultado.Clasificacion;
                contexto.OutputParameters[SalidaYaProcesada] = resultado.YaProcesada;

                trace.Trace($"ClasificarCorreo: termina. clasificacion={resultado.Clasificacion}, procesar={resultado.Procesar}, yaprocesada={resultado.YaProcesada}.");
            }
            catch (InvalidPluginExecutionException)
            {
                // Ya es el error que quien llama tiene que ver: se propaga tal cual.
                throw;
            }
            catch (Exception ex)
            {
                // Cualquier otra excepción puede traer datos del correo o del SDK (diseno/03 §1 "Errores"): el detalle
                // completo va SOLO al trace, y quien llama recibe un mensaje genérico. La plataforma revierte la transacción.
                trace.Trace(ex.ToString());
                throw new InvalidPluginExecutionException(MensajeDeErrorGenerico);
            }
        }

        /// <summary>`solicitudid`: tiene que estar, ser un `Guid` y no estar vacío. No toca el servicio ni el trace: es
        /// el primer chequeo, antes de que exista nada que revertir.</summary>
        private static Guid LeerSolicitudId(IPluginExecutionContext contexto)
        {
            if (!contexto.InputParameters.Contains(ParametroSolicitudId) || !(contexto.InputParameters[ParametroSolicitudId] is Guid solicitudId) || solicitudId == Guid.Empty)
            {
                throw new InvalidPluginExecutionException($"Falta el parámetro '{ParametroSolicitudId}' o no es un identificador válido.");
            }

            return solicitudId;
        }
    }
}
