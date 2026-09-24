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
    ///    escribe con SYSTEM: `03` §4), si quien inicia es una identidad de APLICACIÓN (`systemuser.applicationid` con valor:
    ///    el usuario del RPA) o si su UPN es el que declara el parámetro `servicio.cuenta` (la cuenta de servicio de los
    ///    cinco flujos). Cualquier otro es una persona;
    ///  - la identidad se consulta UNA vez por ejecución y solo cuando hace falta (profundidad 1); el parámetro se lee solo
    ///    si además no hay `applicationid`, que es el camino barato.
    /// </summary>
    public static class BaseDeStep
    {
        /// <summary>
        /// Parámetro que declara el UPN de la cuenta de servicio de los flujos.
        ///
        /// **Por qué existe.** `diseno/07-flujos.md` §33 declara una excepción a BP-PP-122: los cinco flujos son propiedad
        /// de una **cuenta de servicio**, que en BAC es un usuario, no un service principal. Un usuario no tiene
        /// `applicationid`, así que sin esta vía la lista blanca lo trata como persona y los flujos no pueden escribir sus
        /// propias marcas de envío. Se descubrió el 2026-09-23, cuando `MPPP-ENV` falló al escribir
        /// `sanic_fechaacuseiniciado`.
        ///
        /// **Por qué el UPN y no el GUID.** El identificador del usuario cambia de un entorno a otro; el UPN no. Un
        /// parámetro con un GUID habría que reescribirlo en cada despliegue, y quien lo revise no puede saber a quién
        /// nombra. `servicio.mppp@bac.com.ni` se lee.
        ///
        /// **Qué lo mantiene cerrado.** Sin el parámetro, o con el parámetro vacío, no exime a NADIE: el control queda
        /// exactamente como estaba. Y exime solo a quien coincide, uno. Quién puede escribir en la tabla de parámetros es
        /// lo que gobierna esta puerta (`diseno/04` §3): si eso se afloja, se afloja esto.
        /// </summary>
        public const string ParametroCuentaDeServicio = "servicio.cuenta";

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
                usuario = servicio.Retrieve(TablasNativas.Usuario, contexto.InitiatingUserId, new ColumnSet("applicationid", "domainname"));
            }
            catch (FaultException<OrganizationServiceFault>)
            {
                // Que el usuario no exista no puede tumbar un guardado (punto fino de la orden): se trata como persona.
                return false;
            }

            if (usuario.Contains("applicationid") && usuario["applicationid"] != null)
            {
                return true;
            }

            return EsLaCuentaDeServicio(servicio, usuario.GetAttributeValue<string>("domainname"));
        }

        /// <summary>
        /// `true` solo si el parámetro `servicio.cuenta` trae un UPN y es exactamente el de quien escribe. Un UPN no
        /// distingue mayúsculas, y un valor cargado a mano puede traer espacios al costado, así que se comparan recortados
        /// y sin distinguir caja. Cualquier ausencia —el usuario sin UPN, el parámetro sin cargar o vacío— devuelve
        /// `false`: esta puerta nunca se abre sola.
        ///
        /// **Por qué el `catch`.** `CatalogosDataverse.Parametro` no devuelve `null` cuando el valor está vacío: lanza
        /// `InvalidOperationException`, porque el resto de los parámetros del sistema SÍ son obligatorios. Sin este
        /// `catch`, alguien que cargara `servicio.cuenta` y le dejara el valor en blanco tumbaría TODO guardado de Fila y
        /// de Solicitud, para cualquier usuario, con un error que no nombra la causa. Lo encontró una prueba antes de que
        /// llegara al entorno. Vale acá el mismo principio que en el `Retrieve` del usuario, más arriba: un dato de
        /// configuración mal cargado degrada el control a "es una persona", nunca tumba la operación.
        /// </summary>
        private static bool EsLaCuentaDeServicio(IOrganizationService servicio, string upnDeQuienEscribe)
        {
            if (string.IsNullOrWhiteSpace(upnDeQuienEscribe))
            {
                return false;
            }

            string declarado;
            try
            {
                declarado = new CatalogosDataverse(servicio).Parametro(ParametroCuentaDeServicio)?.Valor;
            }
            catch (InvalidOperationException)
            {
                // El parámetro existe pero está vacío o ilegible: no declara a nadie.
                return false;
            }
            catch (FaultException<OrganizationServiceFault>)
            {
                // No se pudo consultar la tabla de parámetros: tampoco declara a nadie.
                return false;
            }

            if (string.IsNullOrWhiteSpace(declarado))
            {
                return false;
            }

            return string.Equals(declarado.Trim(), upnDeQuienEscribe.Trim(), StringComparison.OrdinalIgnoreCase);
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

            // SYSTEM, no quien llama (diseno/04 §1, textual: "los plugins leen los catálogos y graban ... con el
            // servicio de SYSTEM (`CreateOrganizationService(null)`), no con el usuario que llama").
            //
            // Con la identidad de quien llama NINGUNA persona podía transicionar una Fila: el step de transición lee
            // `rpa.puedeaprobar` de la tabla Parametro, sobre la que la matriz no le da lectura a nadie salvo al
            // administrador técnico (defecto encontrado el 2026-09-23; el servidor respondía
            // "is missing prvReadsanic_mppp_tbl_parametro"). Estuvo tres semanas escondido porque todo lo probado
            // hasta entonces corrió con una identidad sobre-privilegiada (el service principal, el administrador, y
            // los flujos, cuya cuenta de servicio hoy es provisoriamente la del administrador).
            //
            // Esto NO debilita el control: la seguridad de este diseño no descansa en los privilegios del llamador
            // dentro del plugin, sino en la lista blanca de columnas y en las verificaciones explícitas de rol y de
            // segregación. `EsCodigoDeServidor` sigue mirando el CONTEXTO (`Depth`, `InitiatingUserId`), no la
            // identidad del servicio, así que una persona sigue siendo una persona para la lista blanca.
            servicio = fabrica.CreateOrganizationService(null);

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
    /// nombre: se rechaza el guardado con el motivo. EXCEPCIÓN (revisión de código, 2026-09-21): si el `Target` de una Fila ya
    /// trae `sanic_nombre` y quien escribe es código de servidor, se respeta y NO se lee la Solicitud; así la Custom API de
    /// validación, que ya tiene el número en memoria, no provoca una lectura por fila (03 §1 paso 6). A una persona se le pisa
    /// siempre, en las tres tablas.
    /// </summary>
    public sealed class NombreCalculadoStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
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
                        // EXCEPCIÓN (revisión de código, 2026-09-21): si el Target ya trae sanic_nombre con contenido
                        // y quien escribe es código de servidor, se respeta y no se lee la Solicitud — así la Custom
                        // API de validación, que crea las filas una por una, no provoca un Retrieve por fila (03 §1
                        // paso 6). A una persona se le pisa siempre, igual que en Plan y AutorizacionPlan.
                        if (!TraeNombrePropio(target) || !BaseDeStep.EsCodigoDeServidor(contexto, servicio))
                        {
                            target["sanic_nombre"] = NombreDeFila(servicio, target);
                        }

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

        /// <summary>El Target ya trae un `sanic_nombre` con contenido (no nulo ni en blanco), sin mirar quién escribe.</summary>
        private static bool TraeNombrePropio(Entity target)
        {
            return target.Contains("sanic_nombre") && !string.IsNullOrWhiteSpace(target["sanic_nombre"] as string);
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
}
