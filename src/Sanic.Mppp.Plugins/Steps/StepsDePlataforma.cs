using System;
using Microsoft.Xrm.Sdk;

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
            throw new NotImplementedException();
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
            throw new NotImplementedException();
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
            throw new NotImplementedException();
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
            throw new NotImplementedException();
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
            throw new NotImplementedException();
        }
    }
}
