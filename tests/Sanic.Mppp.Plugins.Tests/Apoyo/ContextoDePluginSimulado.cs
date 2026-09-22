using System;
using System.Collections.Generic;
using Microsoft.Xrm.Sdk;

namespace Sanic.Mppp.Plugins.Tests.Apoyo
{
    /// <summary>
    /// El `IServiceProvider` que la plataforma le pasa a un `IPlugin`, simulado: contexto de ejecución, fábrica de servicio y
    /// trace. Lo que el plugin pida y no esté configurado se devuelve nulo (así se prueba un proveedor incompleto).
    /// </summary>
    public sealed class ContextoDePluginSimulado : IServiceProvider, IOrganizationServiceFactory
    {
        private readonly IOrganizationService _servicio;

        public ContextoDePluginSimulado(IOrganizationService servicio, DateTime operacionCreadaEn)
        {
            _servicio = servicio;
            Contexto = new ContextoDeEjecucionSimulado { OperationCreatedOn = operacionCreadaEn, UserId = Guid.NewGuid(), InitiatingUserId = Guid.NewGuid() };
        }

        public ContextoDeEjecucionSimulado Contexto { get; }

        public TraceSimulado Trace { get; } = new TraceSimulado();

        /// <summary>Qué servicios devuelve el proveedor. Sacar uno de acá simula un proveedor incompleto.</summary>
        public bool DaContexto { get; set; } = true;

        public bool DaFabrica { get; set; } = true;

        public bool DaTrace { get; set; } = true;

        /// <summary>Con qué id de usuario se pidió el servicio (el plugin tiene que usar `UserId`).</summary>
        public Guid? UsuarioDelServicio { get; private set; }

        public object GetService(Type serviceType)
        {
            if (serviceType == typeof(IPluginExecutionContext))
            {
                return DaContexto ? Contexto : null;
            }

            if (serviceType == typeof(IOrganizationServiceFactory))
            {
                return DaFabrica ? this : null;
            }

            if (serviceType == typeof(ITracingService))
            {
                return DaTrace ? (object)Trace : null;
            }

            return null;
        }

        public IOrganizationService CreateOrganizationService(Guid? userId)
        {
            UsuarioDelServicio = userId;
            return _servicio;
        }
    }

    /// <summary>Anota lo que el plugin deja en el trace.</summary>
    public sealed class TraceSimulado : ITracingService
    {
        public List<string> Lineas { get; } = new List<string>();

        public string Todo => string.Join("\n", Lineas);

        public void Trace(string format, params object[] args)
        {
            Lineas.Add(args == null || args.Length == 0 ? format : string.Format(format, args));
        }
    }

    /// <summary>`IPluginExecutionContext` con lo mínimo: lo que el plugin no usa queda en su valor por defecto.</summary>
    public sealed class ContextoDeEjecucionSimulado : IPluginExecutionContext
    {
        public ParameterCollection InputParameters { get; set; } = new ParameterCollection();

        public ParameterCollection OutputParameters { get; set; } = new ParameterCollection();

        public ParameterCollection SharedVariables { get; set; } = new ParameterCollection();

        public EntityImageCollection PreEntityImages { get; set; } = new EntityImageCollection();

        public EntityImageCollection PostEntityImages { get; set; } = new EntityImageCollection();

        public Guid UserId { get; set; }

        public Guid InitiatingUserId { get; set; }

        public DateTime OperationCreatedOn { get; set; }

        public string MessageName { get; set; } = "sanic_mppp_capi_clasificarcorreo";

        public int Stage { get; set; } = 30;

        public int Depth { get; set; } = 1;

        public int Mode { get; set; }

        public int IsolationMode { get; set; }

        public IPluginExecutionContext ParentContext { get; set; }

        public Guid BusinessUnitId { get; set; }

        public Guid CorrelationId { get; set; }

        public Guid InitiatingUserAgentId { get; set; }

        public bool IsExecutingOffline { get; set; }

        public bool IsInTransaction { get; set; } = true;

        public bool IsOfflinePlayback { get; set; }

        public Guid OperationId { get; set; }

        public Guid OrganizationId { get; set; }

        public string OrganizationName { get; set; }

        public EntityReference OwningExtension { get; set; }

        public string PrimaryEntityName { get; set; }

        public Guid PrimaryEntityId { get; set; }

        public Guid? RequestId { get; set; }

        public string SecondaryEntityName { get; set; }
    }
}
