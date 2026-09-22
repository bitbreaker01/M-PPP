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
            throw new NotImplementedException();
        }
    }
}
