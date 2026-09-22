using System;
using System.ServiceModel;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Datos;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// Lo común a todos los steps: sacar del proveedor el contexto, el servicio y el trace, y decidir si quien escribe es
    /// código de servidor o una persona. Contrato (lo fijan las pruebas `StepsDePlataformaAceptacion`):
    ///  - un proveedor incompleto o nulo es <see cref="InvalidPluginExecutionException"/>, nunca <see cref="NullReferenceException"/>;
    ///  - `Target` que no es una `Entity`, o que no es de la tabla que el step espera, se ignora en silencio (el step no se
    ///    registró bien, pero no es asunto de quien está guardando): el step no hace nada;
    ///  - **quién escribe**: es código de servidor si la profundidad es mayor que 1 (nuestro propio plugin o Custom API, que
    ///    escribe con SYSTEM: `03` §4) o si quien inicia es una identidad de APLICACIÓN (`systemuser.applicationid` con valor:
    ///    la cuenta de servicio de los flujos y el usuario del RPA). Cualquier otro es una persona;
    ///  - la identidad de aplicación se consulta UNA vez por ejecución y solo cuando hace falta (profundidad 1).
    /// </summary>
    public static class BaseDeStep
    {
        public static bool EsCodigoDeServidor(IPluginExecutionContext contexto, IOrganizationService servicio)
        {
            if (contexto.Depth > 1)
            {
                // Nuestro propio plugin o Custom API, que ya escribe con SYSTEM (03 §4): no hace falta preguntar nada.
                return true;
            }

            Entity usuario;
            try
            {
                usuario = servicio.Retrieve(TablasNativas.Usuario, contexto.InitiatingUserId, new ColumnSet("applicationid"));
            }
            catch (FaultException<OrganizationServiceFault>)
            {
                // Que el usuario no exista no puede tumbar un guardado (punto fino de la orden): se trata como persona.
                return false;
            }

            return usuario.Contains("applicationid") && usuario["applicationid"] != null;
        }
    }

    /// <summary>
    /// Plomería común a los cuatro steps de esta pieza: extrae contexto, fábrica de servicio y trace del proveedor, y el
    /// `Target` cuando es una `Entity` utilizable. Un proveedor incompleto es <see cref="InvalidPluginExecutionException"/>;
    /// un `Target` ausente o que no es `Entity` hace que <see cref="Preparar"/> devuelva `false` (el step no hace nada).
    /// </summary>
    internal static class PlomeriaDePlataforma
    {
        public static bool Preparar(IServiceProvider serviceProvider, out IPluginExecutionContext contexto, out IOrganizationService servicio, out Entity target)
        {
            if (serviceProvider == null)
            {
                throw new InvalidPluginExecutionException("No se recibió el proveedor de servicios del plugin.");
            }

            contexto = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
            var fabrica = (IOrganizationServiceFactory)serviceProvider.GetService(typeof(IOrganizationServiceFactory));
            var trace = (ITracingService)serviceProvider.GetService(typeof(ITracingService));
            if (contexto == null || fabrica == null || trace == null)
            {
                throw new InvalidPluginExecutionException("Faltan servicios de la plataforma para ejecutar el step.");
            }

            servicio = fabrica.CreateOrganizationService(contexto.UserId);

            target = contexto.InputParameters.Contains("Target") && contexto.InputParameters["Target"] is Entity entidad
                ? entidad
                : null;

            return target != null;
        }
    }

    /// <summary>
    /// 7.8, lista blanca de columnas: `Update` de Fila y de Solicitud, PreOperation, sin filtro de atributos, orden 0
    /// (diseno/03 §5, diseno/04 §1). Si quien escribe es una persona y el `Target` trae una columna que no está permitida, el
    /// guardado se rechaza con <see cref="InvalidPluginExecutionException"/> y un mensaje que NOMBRA las columnas (quien lo lee
    /// es un ejecutivo del banco, no un cliente). Si quien escribe es código de servidor, no se controla nada.
    /// </summary>
    public sealed class ListaBlancaStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (BaseDeStep.EsCodigoDeServidor(contexto, servicio))
            {
                // 04 §1: el código de servidor no pasa por la lista blanca.
                return;
            }

            // ColumnasNoPermitidas ya devuelve vacío para una tabla que este step no controla (04 §1).
            var noPermitidas = ListaBlancaDeColumnas.ColumnasNoPermitidas(target.LogicalName, target.Attributes.Keys);
            if (noPermitidas.Count > 0)
            {
                throw new InvalidPluginExecutionException(
                    $"No se puede guardar: la(s) columna(s) {string.Join(", ", noPermitidas)} no está(n) permitida(s) para este usuario.");
            }
        }
    }

    /// <summary>
    /// 7.10, normalizar y validar: `Create` y `Update` de Cliente, Plan, Autorizado y Parametro, PreOperation (diseno/03 §5).
    /// Por cada columna que el `Target` trae, escribe de vuelta el valor normalizado (<see cref="Normalizacion"/>); un valor que
    /// no cumple su formato rechaza el guardado con el motivo. Una columna que no viene en el `Target` no se toca (en un `Update`
    /// parcial no se inventa nada). Corre para todos, también para el código de servidor: los catálogos los carga una persona y
    /// una migración no puede meter un código mal formado.
    /// </summary>
    public sealed class NormalizarYValidarStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out _, out _, out var target))
            {
                return;
            }

            switch (target.LogicalName)
            {
                case Tablas.Cliente:
                    NormalizarColumna(target, "sanic_cifbac", Normalizacion.CifBac);
                    NormalizarColumna(target, "sanic_cifcom", Normalizacion.CifCom);
                    break;
                case Tablas.Plan:
                    NormalizarColumna(target, "sanic_codigo", Normalizacion.CodigoDePlan);
                    break;
                case Tablas.Autorizado:
                    NormalizarColumna(target, "sanic_nombre", Normalizacion.CorreoAutorizado);
                    break;
                case Tablas.Parametro:
                    NormalizarColumna(target, "sanic_nombre", Normalizacion.NombreDeParametro);
                    break;
            }
        }

        private static void NormalizarColumna(Entity target, string columna, Func<string, string> normalizar)
        {
            if (!target.Contains(columna))
            {
                // En un Update parcial no se inventa nada (diseno/03 §5).
                return;
            }

            try
            {
                target[columna] = normalizar(target[columna] as string);
            }
            catch (ArgumentException ex)
            {
                throw new InvalidPluginExecutionException($"La columna '{columna}' no tiene un valor válido: {ex.Message}");
            }
        }
    }

    /// <summary>
    /// 7.11, nombre calculado: `Create` PreOperation de Plan, AutorizacionPlan y Fila (diseno/03 §5; en las demás tablas la
    /// primaria es autonumérica o es la clave de negocio). Completa `sanic_nombre` con <see cref="NombreCalculado"/>, pisando lo
    /// que venga. Lo que necesita y no está en el `Target` lo lee del registro relacionado, con una consulta por lookup y solo
    /// si hace falta: el nombre del Cliente para el Plan; el correo del Autorizado y el código del Plan para la AutorizacionPlan;
    /// el `sanic_nombre` de la Solicitud para la Fila. Si falta el dato imprescindible (el lookup no viene), no se inventa un
    /// nombre: se rechaza el guardado con el motivo.
    /// </summary>
    public sealed class NombreCalculadoStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out _, out var servicio, out var target))
            {
                return;
            }

            try
            {
                switch (target.LogicalName)
                {
                    case Tablas.Plan:
                        target["sanic_nombre"] = NombreDePlan(servicio, target);
                        break;
                    case Tablas.AutorizacionPlan:
                        target["sanic_nombre"] = NombreDeAutorizacionPlan(servicio, target);
                        break;
                    case TablasHistorico.Fila:
                        target["sanic_nombre"] = NombreDeFila(servicio, target);
                        break;
                }
            }
            catch (ArgumentException ex)
            {
                // NombreCalculado (Dominio) valida con ArgumentException; acá se traduce a lo que el step tiene que lanzar.
                throw new InvalidPluginExecutionException($"No se pudo calcular 'sanic_nombre': {ex.Message}");
            }
        }

        private static string NombreDePlan(IOrganizationService servicio, Entity target)
        {
            var clienteRef = LookupObligatorio(target, "sanic_clienteid", "el cliente del plan");
            var codigo = target.GetAttributeValue<string>("sanic_codigo");

            var cliente = servicio.Retrieve(Tablas.Cliente, clienteRef.Id, new ColumnSet("sanic_nombre"));
            var nombreDelCliente = cliente.GetAttributeValue<string>("sanic_nombre");

            return NombreCalculado.DePlan(codigo, nombreDelCliente);
        }

        private static string NombreDeAutorizacionPlan(IOrganizationService servicio, Entity target)
        {
            var autorizadoRef = LookupObligatorio(target, "sanic_autorizadoid", "el autorizado de la autorización");
            var planRef = LookupObligatorio(target, "sanic_planid", "el plan de la autorización");

            var autorizado = servicio.Retrieve(Tablas.Autorizado, autorizadoRef.Id, new ColumnSet("sanic_nombre"));
            var plan = servicio.Retrieve(Tablas.Plan, planRef.Id, new ColumnSet("sanic_codigo"));

            var correo = autorizado.GetAttributeValue<string>("sanic_nombre");
            var codigoDePlan = plan.GetAttributeValue<string>("sanic_codigo");

            return NombreCalculado.DeAutorizacionPlan(correo, codigoDePlan);
        }

        private static string NombreDeFila(IOrganizationService servicio, Entity target)
        {
            var solicitudRef = LookupObligatorio(target, "sanic_solicitudid", "la solicitud de la fila");
            if (!target.Contains("sanic_numerofila") || !(target["sanic_numerofila"] is int numeroDeFila))
            {
                throw new InvalidPluginExecutionException("No se puede calcular el nombre de la fila: falta el número de fila ('sanic_numerofila').");
            }

            var solicitud = servicio.Retrieve(TablasHistorico.Solicitud, solicitudRef.Id, new ColumnSet("sanic_nombre"));
            var numeroDeSolicitud = solicitud.GetAttributeValue<string>("sanic_nombre");

            return NombreCalculado.DeFila(numeroDeSolicitud, numeroDeFila);
        }

        /// <summary>El lookup que hace falta para calcular el nombre. Si no viene, no se inventa nada: se rechaza el guardado (diseno/03 §5).</summary>
        private static EntityReference LookupObligatorio(Entity target, string columna, string motivo)
        {
            if (target.Contains(columna) && target[columna] is EntityReference referencia)
            {
                return referencia;
            }

            throw new InvalidPluginExecutionException($"No se puede calcular el nombre: falta {motivo} ('{columna}').");
        }
    }

    /// <summary>
    /// 7.11, integridad de AutorizacionPlan: `Create` y `Update` PreOperation (diseno/03 §5; diseno/02 §2.4). El Cliente del Plan
    /// tiene que ser el mismo Cliente del Autorizado. En un `Update` que solo cambia uno de los dos lookups, el otro se lee del
    /// registro. Si no coinciden, se rechaza el guardado con un mensaje que lo explica.
    /// </summary>
    public sealed class IntegridadAutorizacionPlanStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (!string.Equals(target.LogicalName, Tablas.AutorizacionPlan, StringComparison.Ordinal))
            {
                return;
            }

            var traeAutorizado = target.Contains("sanic_autorizadoid");
            var traePlan = target.Contains("sanic_planid");

            if (!traeAutorizado && !traePlan)
            {
                // El Target no trae ninguno de los dos lookups: no hay nada que comprobar (diseno/03 §5).
                return;
            }

            EntityReference autorizadoRef;
            EntityReference planRef;

            if (traeAutorizado && traePlan)
            {
                autorizadoRef = (EntityReference)target["sanic_autorizadoid"];
                planRef = (EntityReference)target["sanic_planid"];
            }
            else if (string.Equals(contexto.MessageName, "Update", StringComparison.Ordinal))
            {
                // Trae uno solo, y es un Update: el otro se lee del registro existente (diseno/03 §5).
                var existente = servicio.Retrieve(Tablas.AutorizacionPlan, target.Id, new ColumnSet("sanic_autorizadoid", "sanic_planid"));
                autorizadoRef = traeAutorizado ? (EntityReference)target["sanic_autorizadoid"] : existente.GetAttributeValue<EntityReference>("sanic_autorizadoid");
                planRef = traePlan ? (EntityReference)target["sanic_planid"] : existente.GetAttributeValue<EntityReference>("sanic_planid");
            }
            else
            {
                // Create con un solo lookup: los dos son requeridos por la plataforma: no es asunto de este step.
                return;
            }

            var plan = servicio.Retrieve(Tablas.Plan, planRef.Id, new ColumnSet("sanic_clienteid"));
            var autorizado = servicio.Retrieve(Tablas.Autorizado, autorizadoRef.Id, new ColumnSet("sanic_clienteid"));

            var clienteDelPlan = plan.GetAttributeValue<EntityReference>("sanic_clienteid")?.Id;
            var clienteDelAutorizado = autorizado.GetAttributeValue<EntityReference>("sanic_clienteid")?.Id;

            if (clienteDelPlan != clienteDelAutorizado)
            {
                throw new InvalidPluginExecutionException("No se puede guardar la autorización: el plan pertenece a una empresa distinta de la del autorizado.");
            }
        }
    }
}
