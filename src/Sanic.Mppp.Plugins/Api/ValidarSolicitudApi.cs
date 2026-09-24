using System;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;

namespace Sanic.Mppp.Plugins.Api
{
    /// <summary>
    /// El envoltorio `IPlugin` de `sanic_mppp_capi_validarsolicitud` (diseno/03 §1): traduce parámetros y arma las piezas. NO
    /// tiene lógica de negocio: eso es <see cref="ValidarSolicitud"/>. Mismo contrato que
    /// <see cref="ClasificarCorreoApi"/> (lo fijan las pruebas `ValidarSolicitudApiAceptacion`):
    ///  - entrada `solicitudid` (Guid); ausente, de otro tipo o vacío → <see cref="InvalidPluginExecutionException"/>;
    ///  - salidas `estado` (int, el valor del choice), `yaprocesada` (bool), `filastotales`, `filasvalidas`, `filasrechazadas`
    ///    (int) y `resumen` (string), con esos nombres exactos y siempre las seis;
    ///  - el servicio se crea con <see cref="IPluginExecutionContext.UserId"/>; la fecha sale de `OperationCreatedOn` como UTC;
    ///  - deja rastro en el trace al empezar y al terminar, sin volcar datos del cliente;
    ///  - una <see cref="InvalidPluginExecutionException"/> de adentro se propaga; cualquier otra excepción se traza completa y
    ///    se vuelve a lanzar con un mensaje genérico (puede traer datos del Excel o del SDK; diseno/03 §1 "Errores").
    /// </summary>
    public sealed class ValidarSolicitudApi : IPlugin
    {
        public const string ParametroSolicitudId = "solicitudid";
        public const string SalidaEstado = "estado";
        public const string SalidaYaProcesada = "yaprocesada";
        public const string SalidaFilasTotales = "filastotales";
        public const string SalidaFilasValidas = "filasvalidas";
        public const string SalidaFilasRechazadas = "filasrechazadas";
        public const string SalidaResumen = "resumen";

        /// <summary>Lo único que se le dice a quien llama cuando algo se rompe de verdad. El detalle va al trace.</summary>
        public const string MensajeDeErrorGenerico = "No se pudo validar la solicitud. El equipo tecnico ya tiene el detalle.";

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
                trace.Trace($"ValidarSolicitud: empieza para la solicitud {solicitudId}.");

                // SYSTEM, no quien llama (diseno/04 §1 y §3). La cuenta de servicio que dispara esta API NO lee
                // filas, clientes, planes ni autorizados: "todo eso lo lee y lo escribe el plugin de la Custom API
                // con el servicio de SYSTEM, no con los privilegios de quien la llama" (04 §3). Con la identidad de
                // quien llama esto funcionaba solo porque la cuenta de servicio es provisoriamente la del
                // administrador (13.2 no existe); con la cuenta real habría fallado en la primera validación.
                var servicio = fabrica.CreateOrganizationService(null);
                var validar = new ValidarSolicitud(
                    new SolicitudesDataverse(servicio), new CatalogosDataverse(servicio), new ArchivosDataverse(servicio),
                    limites => new LectorOpenXml(limites));

                var ahoraUtc = DateTime.SpecifyKind(contexto.OperationCreatedOn, DateTimeKind.Utc);
                var resultado = validar.Ejecutar(solicitudId, ahoraUtc);

                contexto.OutputParameters[SalidaEstado] = (int)resultado.Estado;
                contexto.OutputParameters[SalidaYaProcesada] = resultado.YaProcesada;
                contexto.OutputParameters[SalidaFilasTotales] = resultado.FilasTotales;
                contexto.OutputParameters[SalidaFilasValidas] = resultado.FilasValidas;
                contexto.OutputParameters[SalidaFilasRechazadas] = resultado.FilasRechazadas;
                contexto.OutputParameters[SalidaResumen] = resultado.Resumen;

                trace.Trace($"ValidarSolicitud: termina. estado={resultado.Estado}, yaprocesada={resultado.YaProcesada}, filastotales={resultado.FilasTotales}, filasvalidas={resultado.FilasValidas}, filasrechazadas={resultado.FilasRechazadas}.");
            }
            catch (InvalidPluginExecutionException)
            {
                // Ya es el error que quien llama tiene que ver: se propaga tal cual.
                throw;
            }
            catch (Exception ex)
            {
                // Cualquier otra excepción puede traer datos del Excel o del SDK (diseno/03 §1 "Errores"): el detalle
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
