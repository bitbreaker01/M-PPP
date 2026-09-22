using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Respuesta;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// Plomería común a los tres steps de esta pieza (diseno/03 §4 y §5): leer la imagen previa que trae la columna que
    /// hace falta, resolver los roles de negocio del actor con un número FIJO de consultas, leer `rpa.puedeaprobar` y el
    /// nombre de quien actuó para la Bitácora (D-21, `sanic_actortexto`).
    /// </summary>
    internal static class PlomeriaDeFila
    {
        private const string RolSupervisor = "sr_mppp_supervisor";
        // D-44: el usuario de aplicación del RPA tiene su propio rol, distinto del de la cuenta de servicio de los flujos.
        // Ese rol es de FASE 2 y todavía no existe en el entorno: hasta que se cree con este nombre, ninguna transición del RPA
        // es posible, que es lo correcto en fase 1.
        private const string RolRpa = "sr_mppp_rpa";

        /// <summary>La primera pre-image que trae `columna` (03 §4: "el estado de origen sale de la PRE-IMAGE, nunca del Target", sea cual sea la clave con la que la registraron).</summary>
        internal static Entity ImagenQueTrae(IPluginExecutionContext contexto, string columna)
        {
            foreach (var imagen in contexto.PreEntityImages.Values)
            {
                if (imagen != null && imagen.Contains(columna))
                {
                    return imagen;
                }
            }

            throw new InvalidPluginExecutionException($"Falta la imagen previa con la columna '{columna}'.");
        }

        /// <summary>
        /// Los roles de negocio del actor (Ejecutivo, Supervisor, RPA), con dos consultas fijas: los tres roles por
        /// `name`, y las asignaciones de ESE usuario entre esos tres (diseno/04 §2 y §3; orden del constructor).
        /// </summary>
        internal static RolDeActor DeterminarRoles(IOrganizationService servicio, Guid actorId)
        {
            var consultaRoles = new QueryExpression(TablasNativas.Rol) { ColumnSet = new ColumnSet("name") };
            consultaRoles.Criteria.AddCondition("name", ConditionOperator.In, TablasNativas.RolEjecutivo, RolSupervisor, RolRpa);
            var roles = servicio.RetrieveMultiple(consultaRoles).Entities;
            if (roles.Count == 0)
            {
                return RolDeActor.Ninguno;
            }

            var nombrePorRoleId = roles.ToDictionary(r => r.Id, r => r.GetAttributeValue<string>("name"));

            var consultaAsignaciones = new QueryExpression(TablasNativas.UsuarioRol) { ColumnSet = new ColumnSet("roleid") };
            consultaAsignaciones.Criteria.AddCondition("systemuserid", ConditionOperator.Equal, actorId);
            consultaAsignaciones.Criteria.AddCondition("roleid", ConditionOperator.In, nombrePorRoleId.Keys.Cast<object>().ToArray());
            var asignaciones = servicio.RetrieveMultiple(consultaAsignaciones).Entities;

            var resultado = RolDeActor.Ninguno;
            foreach (var asignacion in asignaciones)
            {
                var roleId = asignacion.GetAttributeValue<EntityReference>("roleid")?.Id;
                if (roleId.HasValue && nombrePorRoleId.TryGetValue(roleId.Value, out var nombre))
                {
                    resultado |= NombreARol(nombre);
                }
            }

            return resultado;
        }

        private static RolDeActor NombreARol(string nombre)
        {
            if (string.Equals(nombre, TablasNativas.RolEjecutivo, StringComparison.OrdinalIgnoreCase))
            {
                return RolDeActor.Ejecutivo;
            }

            if (string.Equals(nombre, RolSupervisor, StringComparison.OrdinalIgnoreCase))
            {
                return RolDeActor.Supervisor;
            }

            if (string.Equals(nombre, RolRpa, StringComparison.OrdinalIgnoreCase))
            {
                return RolDeActor.Rpa;
            }

            return RolDeActor.Ninguno;
        }

        /// <summary>`rpa.puedeaprobar` vale `si` (sin distinguir mayúsculas) para habilitar la excepción; ausente o cualquier otro valor, no (diseno/03 §4).</summary>
        internal static bool LeerRpaPuedeAprobar(IOrganizationService servicio)
        {
            var parametro = new CatalogosDataverse(servicio).Parametro(TransicionDeFilaStep.ParametroRpaPuedeAprobar);
            return parametro != null && string.Equals(parametro.Valor, "si", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>`sanic_actortexto` (D-21): el `fullname` de quien inicia, con una consulta.</summary>
        internal static string NombreDeQuienActua(IOrganizationService servicio, Guid usuarioId)
        {
            var usuario = servicio.Retrieve(TablasNativas.Usuario, usuarioId, new ColumnSet("fullname"));
            return usuario.GetAttributeValue<string>("fullname");
        }

        /// <summary>
        /// El usuario cuyos roles de negocio hay que resolver para autorizar la transición (revisión de código,
        /// 2026-09-21, spike C-05 parte B): si NO es código de servidor, o si es código de servidor sin anidar
        /// (identidad de aplicación en profundidad 1: es quien llama de verdad), es `InitiatingUserId`. Si es código
        /// de servidor ANIDADO (profundidad mayor que 1: la Custom API del RPA escribiendo como SYSTEM, donde
        /// `InitiatingUserId` vale SYSTEM en todos los niveles), se confía en la identidad que la Custom API ya
        /// grabó: `sanic_aprobadapor` del `Target` si la transición va a Aprobada, `sanic_digitadapor` del `Target`
        /// si va a Digitada, o el `sanic_digitadapor` de la PRE-IMAGE para cualquier otro caso. Si ahí tampoco hay
        /// nadie, `null`: no se asume ningún actor y la transición se rechaza sola por falta de rol.
        /// </summary>
        internal static Guid? ResolverIdentidadDelActor(IPluginExecutionContext contexto, bool esCodigoDeServidor, Entity target, Entity preImagen, EstadoDeLaFila hacia)
        {
            if (!esCodigoDeServidor || contexto.Depth <= 1)
            {
                return contexto.InitiatingUserId;
            }

            if (hacia == EstadoDeLaFila.Aprobada)
            {
                return target.GetAttributeValue<EntityReference>("sanic_aprobadapor")?.Id;
            }

            if (hacia == EstadoDeLaFila.Digitada)
            {
                return target.GetAttributeValue<EntityReference>("sanic_digitadapor")?.Id;
            }

            return preImagen.GetAttributeValue<EntityReference>("sanic_digitadapor")?.Id;
        }
    }

    /// <summary>
    /// 7.9, transición de estado de Fila: `Update` de Fila, PreOperation, síncrono, filtro `sanic_estado`, con pre-image
    /// (`sanic_estado`, `sanic_digitadapor`, `sanic_solicitudid`), orden 1 (diseno/03 §4, D-25). Contrato (lo fijan las pruebas
    /// `StepsDeFilaAceptacion`):
    ///  - el estado de origen sale de la PRE-IMAGE, nunca del `Target` (nadie puede decir de dónde venía);
    ///  - **quién actúa**: si escribe una persona, `sanic_digitadapor`, `sanic_aprobadapor` y sus fechas que vengan en el `Target`
    ///    se IGNORAN y se pisan con `InitiatingUserId` y la fecha del contexto; si escribe código de servidor, se confía en el
    ///    `Target` (es la Custom API del RPA, que ya puso al usuario del bot; `03` §4);
    ///  - **de quién se leen los roles** (revisión de código, 2026-09-21): si escribe una persona, de `InitiatingUserId`. Si
    ///    escribe código de servidor ANIDADO (profundidad mayor que 1, o sea la Custom API del RPA escribiendo como SYSTEM), de
    ///    `InitiatingUserId` NO se puede: el spike C-05 parte B probó que ahí vale SYSTEM en todos los niveles. Se leen de la
    ///    identidad que la Custom API ya grabó en el `Target`: `sanic_aprobadapor` para Aprobada, `sanic_digitadapor` para
    ///    Digitada, y para el resto el `sanic_digitadapor` de la pre-image (quien venía trabajando la fila). Si ahí tampoco hay
    ///    nadie, el actor queda sin roles y la transición se rechaza: nunca se asume un rol;
    ///  - los roles salen de los security roles de ese usuario, con un número fijo de consultas;
    ///  - la transición se evalúa SIEMPRE con <see cref="Dominio.TransicionesDeFila"/>, venga de quien venga, y si no está
    ///    permitida el guardado se rechaza con su motivo;
    ///  - `rpa.puedeaprobar` se lee del parámetro (`si` habilita la excepción; ausente o cualquier otra cosa = no);
    ///  - los efectos se escriben en el `Target`: Digitada pone `sanic_digitadapor`/`sanic_fechadigitada`; Aprobada pone
    ///    `sanic_aprobadapor`/`sanic_fechaaprobada`; Devolver limpia `sanic_digitadapor`/`sanic_fechadigitada`;
    ///  - un `Update` que no cambia el estado (el `Target` no trae `sanic_estado`) no hace nada.
    /// </summary>
    public sealed class TransicionDeFilaStep : IPlugin
    {
        public const string ParametroRpaPuedeAprobar = "rpa.puedeaprobar";

        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (!string.Equals(target.LogicalName, TablasHistorico.Fila, StringComparison.Ordinal) || !target.Contains("sanic_estado"))
            {
                // Filtering attributes = sanic_estado (03 §4): un Update que no cambia el estado no hace nada.
                return;
            }

            var preImagen = PlomeriaDeFila.ImagenQueTrae(contexto, "sanic_estado");
            var desde = (EstadoDeLaFila)preImagen.GetAttributeValue<OptionSetValue>("sanic_estado").Value;
            var hacia = (EstadoDeLaFila)target.GetAttributeValue<OptionSetValue>("sanic_estado").Value;
            var digitadaPorPrevio = preImagen.GetAttributeValue<EntityReference>("sanic_digitadapor")?.Id;

            var esCodigoDeServidor = BaseDeStep.EsCodigoDeServidor(contexto, servicio);
            // El actor para roles y para la segregación de funciones es el mismo usuario confiado, nunca SYSTEM
            // (revisión de código, 2026-09-21): ver el contrato arriba y PlomeriaDeFila.ResolverIdentidadDelActor.
            var actorId = PlomeriaDeFila.ResolverIdentidadDelActor(contexto, esCodigoDeServidor, target, preImagen, hacia);
            var roles = actorId.HasValue ? PlomeriaDeFila.DeterminarRoles(servicio, actorId.Value) : RolDeActor.Ninguno;
            var rpaPuedeAprobar = PlomeriaDeFila.LeerRpaPuedeAprobar(servicio);

            var pedido = new PedidoDeTransicion
            {
                Desde = desde,
                Hacia = hacia,
                Actor = new Actor(actorId ?? Guid.Empty, roles),
                Mensaje = target.Contains("sanic_mensaje") ? target["sanic_mensaje"] as string : null,
                DigitadaPor = digitadaPorPrevio,
                RpaPuedeAprobar = rpaPuedeAprobar,
            };

            var resultado = TransicionesDeFila.Evaluar(pedido);
            if (!resultado.Permitida)
            {
                throw new InvalidPluginExecutionException(resultado.Motivo);
            }

            AplicarEfecto(target, resultado.Efecto, contexto, esCodigoDeServidor);
        }

        /// <summary>Escribe quién y cuándo según el efecto (03 §4). A una persona nunca se le cree lo que mandó; al código de servidor se le confía lo que ya trae, y se completa solo lo que falte.</summary>
        private static void AplicarEfecto(Entity target, EfectoDeTransicion efecto, IPluginExecutionContext contexto, bool esCodigoDeServidor)
        {
            switch (efecto)
            {
                case EfectoDeTransicion.RegistrarDigitacion:
                    EscribirQuienYCuando(target, "sanic_digitadapor", "sanic_fechadigitada", contexto, esCodigoDeServidor);
                    break;
                case EfectoDeTransicion.RegistrarAprobacion:
                    EscribirQuienYCuando(target, "sanic_aprobadapor", "sanic_fechaaprobada", contexto, esCodigoDeServidor);
                    break;
                case EfectoDeTransicion.LimpiarDigitacion:
                    // Devolver: limpia explícitamente en el Target, poniendo null (no omitiendo la columna).
                    target["sanic_digitadapor"] = null;
                    target["sanic_fechadigitada"] = null;
                    break;
            }
        }

        private static void EscribirQuienYCuando(Entity target, string columnaUsuario, string columnaFecha, IPluginExecutionContext contexto, bool esCodigoDeServidor)
        {
            if (esCodigoDeServidor)
            {
                // 03 §4: "si quien llama ES SYSTEM ... el step confía en ese Target"; solo se completa lo que no vino.
                if (!target.Contains(columnaUsuario))
                {
                    target[columnaUsuario] = new EntityReference(TablasNativas.Usuario, contexto.InitiatingUserId);
                }

                if (!target.Contains(columnaFecha))
                {
                    target[columnaFecha] = contexto.OperationCreatedOn;
                }

                return;
            }

            // "Si quien llama NO es SYSTEM ... se ignoran y se pisan con InitiatingUserId y la hora actual" (03 §4).
            target[columnaUsuario] = new EntityReference(TablasNativas.Usuario, contexto.InitiatingUserId);
            target[columnaFecha] = contexto.OperationCreatedOn;
        }
    }

    /// <summary>
    /// 7.9, post-transición: `Update` de Fila, PostOperation, filtro `sanic_estado`, con pre-image (`sanic_estado`,
    /// `sanic_solicitudid`, `sanic_numerofila`) (diseno/03 §4 "Cierre"). Contrato:
    ///  - escribe la Bitácora del evento que corresponde a la transición (Fila digitada, aprobada, devuelta, rechazada en AS400,
    ///    anulada), con el número de fila y el nombre de quien actuó en texto;
    ///  - después mira las filas de esa Solicitud: si la Solicitud sigue En proceso y ya no queda ninguna en Validada ni en
    ///    Digitada (<see cref="Dominio.CierreDeSolicitud"/>), la pasa a **Procesada**, pone `sanic_fechaprocesada` y arma
    ///    `sanic_respuestafinalcontenido` con <see cref="Respuesta.ArmadorRespuesta.RespuestaFinal"/>. El paso a Cerrada NO es de
    ///    este plugin (lo hace `MPPP-ENV` al enviar);
    ///  - si la Solicitud no está En proceso, o todavía quedan filas abiertas, solo queda la Bitácora;
    ///  - todo con un número fijo de consultas: las filas de la Solicitud en UNA, y la Solicitud en otra.
    /// </summary>
    public sealed class PostTransicionDeFilaStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (!string.Equals(target.LogicalName, TablasHistorico.Fila, StringComparison.Ordinal) || !target.Contains("sanic_estado"))
            {
                return;
            }

            var preImagen = PlomeriaDeFila.ImagenQueTrae(contexto, "sanic_estado");
            var desde = (EstadoDeLaFila)preImagen.GetAttributeValue<OptionSetValue>("sanic_estado").Value;
            var hacia = (EstadoDeLaFila)target.GetAttributeValue<OptionSetValue>("sanic_estado").Value;
            var solicitudId = preImagen.GetAttributeValue<EntityReference>("sanic_solicitudid").Id;
            var numeroFila = preImagen.GetAttributeValue<int>("sanic_numerofila");

            // El evento de Bitácora es un dato fijo del par (Desde, Hacia): la pre-operación ya autorizó esta misma
            // transición, así que acá no hace falta resolver roles ni leer `rpa.puedeaprobar` de nuevo (revisión de
            // código, 2026-09-21; Dominio.TransicionesDeFila.EventoPara mira la misma tabla que Evaluar).
            var evento = TransicionesDeFila.EventoPara(desde, hacia);
            if (evento == null)
            {
                // La pre-operación ya validó esta misma transición: llegar acá sin evento es un error de programación.
                throw new InvalidPluginExecutionException("No se pudo determinar el evento de Bitácora de la transición.");
            }

            var solicitudes = new SolicitudesDataverse(servicio);
            var actorTexto = PlomeriaDeFila.NombreDeQuienActua(servicio, contexto.InitiatingUserId);
            solicitudes.RegistrarEvento(solicitudId, contexto.OperationCreatedOn, evento.Value, OrigenDelEvento.Plugin, numeroFila, actorTexto, null);

            // Consulta 1 (filas de la Solicitud): la fila que se acaba de transicionar todavía figura en la base con su
            // estado ANTERIOR en el doble de pruebas (no vuelve a aplicar el Update); se refleja el nuevo estado acá,
            // como ya lo tiene la plataforma real en PostOperation (diseno/03 §8).
            var filas = LeerFilasDeLaSolicitud(servicio, solicitudId, target.Id, hacia);

            var solicitud = solicitudes.Leer(solicitudId); // Consulta 2 (la Solicitud).
            if (!CierreDeSolicitud.CorrespondeProcesar(solicitud.Estado, filas.Select(f => f.Estado)))
            {
                return;
            }

            var respuesta = ArmadorRespuesta.RespuestaFinal(new SolicitudParaRespuesta
            {
                Numero = solicitud.Numero,
                Estado = EstadoDeLaSolicitud.Procesada,
                FechaRecibidoTexto = null,
                MotivosDelSobre = new List<string>(),
                Filas = filas.Select(ConvertirParaRespuesta).ToList(),
            });

            var entidadSolicitud = new Entity(TablasHistorico.Solicitud, solicitudId);
            entidadSolicitud["sanic_estadoprocesamiento"] = new OptionSetValue((int)EstadoDeLaSolicitud.Procesada);
            entidadSolicitud["sanic_fechaprocesada"] = contexto.OperationCreatedOn;
            entidadSolicitud["sanic_respuestafinalcontenido"] = respuesta;
            servicio.Update(entidadSolicitud);

            solicitudes.RegistrarEvento(solicitudId, contexto.OperationCreatedOn, EventoDeBitacora.Procesada, OrigenDelEvento.Plugin, 0, null, null);
        }

        private static IList<FilaParaCierre> LeerFilasDeLaSolicitud(IOrganizationService servicio, Guid solicitudId, Guid filaQueTransiciono, EstadoDeLaFila haciaLaFilaQueTransiciono)
        {
            var consulta = new QueryExpression(TablasHistorico.Fila)
            {
                ColumnSet = new ColumnSet("sanic_numerofila", "sanic_numeroplan", "sanic_nombrebeneficiario", "sanic_numerocuenta", "sanic_numeroidentificacion", "sanic_estado", "sanic_mensaje"),
            };
            consulta.Criteria.AddCondition("sanic_solicitudid", ConditionOperator.Equal, solicitudId);

            return servicio.RetrieveMultiple(consulta).Entities
                .Select(fila => new FilaParaCierre
                {
                    NumeroFila = fila.GetAttributeValue<int>("sanic_numerofila"),
                    NumeroPlan = fila.GetAttributeValue<string>("sanic_numeroplan"),
                    NombreBeneficiario = fila.GetAttributeValue<string>("sanic_nombrebeneficiario"),
                    NumeroCuenta = fila.GetAttributeValue<string>("sanic_numerocuenta"),
                    NumeroIdentificacion = fila.GetAttributeValue<string>("sanic_numeroidentificacion"),
                    // La plataforma ya escribió este cambio en la base cuando el step corre en PostOperation (diseno/03 §8: el
                    // doble de pruebas no vuelve a aplicar el Update, así que acá se refleja igual que en Dev).
                    Estado = fila.Id == filaQueTransiciono ? haciaLaFilaQueTransiciono : (EstadoDeLaFila)fila.GetAttributeValue<OptionSetValue>("sanic_estado").Value,
                    Mensaje = fila.GetAttributeValue<string>("sanic_mensaje"),
                })
                .ToList();
        }

        private static FilaParaRespuesta ConvertirParaRespuesta(FilaParaCierre fila) => new FilaParaRespuesta
        {
            NumeroFila = fila.NumeroFila,
            NumeroPlan = fila.NumeroPlan,
            NombreBeneficiario = fila.NombreBeneficiario,
            NumeroCuenta = fila.NumeroCuenta,
            NumeroIdentificacion = fila.NumeroIdentificacion,
            Estado = fila.Estado,
            Mensaje = fila.Mensaje,
        };

        /// <summary>Lo mínimo de una Fila para decidir el cierre y armar la respuesta final. Sin SDK hacia afuera.</summary>
        private sealed class FilaParaCierre
        {
            public int NumeroFila { get; set; }

            public string NumeroPlan { get; set; }

            public string NombreBeneficiario { get; set; }

            public string NumeroCuenta { get; set; }

            public string NumeroIdentificacion { get; set; }

            public EstadoDeLaFila Estado { get; set; }

            public string Mensaje { get; set; }
        }
    }

    /// <summary>
    /// 7.12, atender un correo por clasificar: `Update` de Solicitud, PreOperation, filtro `sanic_estadoprocesamiento`
    /// (diseno/03 §5; diseno/07 DF-09). Contrato:
    ///  - solo se admite salir de **No reconocida** o **No es correo nuevo**, y solo hacia **Cerrada** o **Descartada**;
    ///  - cualquier otro cambio de estado hecho por una PERSONA se rechaza con su motivo (el código de servidor no pasa por acá:
    ///    la Custom API y `MPPP-VIG` mueven los estados que les tocan);
    ///  - no completa ninguna columna propia: quién atendió y cuándo queda en la Bitácora, con `sanic_actortexto` (D-21).
    /// </summary>
    public sealed class AtenderPorClasificarStep : IPlugin
    {
        private static readonly HashSet<EstadoDeLaSolicitud> DesdeValidos = new HashSet<EstadoDeLaSolicitud>
        {
            EstadoDeLaSolicitud.NoReconocida,
            EstadoDeLaSolicitud.NoEsCorreoNuevo,
        };

        private static readonly HashSet<EstadoDeLaSolicitud> HaciaValidos = new HashSet<EstadoDeLaSolicitud>
        {
            EstadoDeLaSolicitud.Cerrada,
            EstadoDeLaSolicitud.Descartada,
        };

        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (!string.Equals(target.LogicalName, TablasHistorico.Solicitud, StringComparison.Ordinal) || !target.Contains("sanic_estadoprocesamiento"))
            {
                return;
            }

            if (BaseDeStep.EsCodigoDeServidor(contexto, servicio))
            {
                // 03 §5: la Custom API y MPPP-VIG mueven los estados que les tocan; este control no es asunto suyo.
                return;
            }

            var preImagen = PlomeriaDeFila.ImagenQueTrae(contexto, "sanic_estadoprocesamiento");
            var desde = (EstadoDeLaSolicitud)preImagen.GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value;
            var hacia = (EstadoDeLaSolicitud)target.GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value;

            if (!DesdeValidos.Contains(desde) || !HaciaValidos.Contains(hacia))
            {
                throw new InvalidPluginExecutionException(
                    $"No se puede cambiar el estado de '{desde}' a '{hacia}': solo se puede cerrar o descartar lo que está por clasificar.");
            }

            // "No reconocida atendida" cubre el cierre de los dos estados de origen (07 §6: "No reconocida → Cerrada (atendida)");
            // Descartada es el evento propio de esa transición.
            var evento = hacia == EstadoDeLaSolicitud.Cerrada ? EventoDeBitacora.NoReconocidaAtendida : EventoDeBitacora.Descartada;
            var actorTexto = PlomeriaDeFila.NombreDeQuienActua(servicio, contexto.InitiatingUserId);
            new SolicitudesDataverse(servicio).RegistrarEvento(target.Id, contexto.OperationCreatedOn, evento, OrigenDelEvento.Plugin, 0, actorTexto, null);
        }
    }
}
