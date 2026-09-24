using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Steps;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.9 y 7.12: transición de Fila, cierre de la Solicitud y atención de los correos por clasificar (diseno/03 §4 y §5).</summary>
    public class StepsDeFilaAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 21, 19, 0, 0, DateTimeKind.Utc);

        /// <summary>
        /// Los nombres de los roles son un CONTRATO CON EL ENTORNO, no un detalle interno: el
        /// plugin los usa para buscar en la tabla `role` por su columna `name`, y si no coinciden
        /// exactamente no encuentra nada y nadie puede hacer ninguna transición.
        ///
        /// Esta prueba no puede comprobar que el rol exista en el entorno — eso solo lo dice el
        /// entorno, y para eso está `herramientas/pruebas/verificar_roles.py`. Lo que sí hace es
        /// congelar el valor: cambiarlo tiene que ser un acto deliberado, no un descuido. El
        /// 2026-09-23 las constantes decían `sr_mppp_ejecutivo` (el nombre del ARCHIVO del
        /// playbook) mientras el entorno tenía `SR - MPPP - Ejecutivo`, y las 793 pruebas pasaban.
        /// </summary>
        [Theory]
        [InlineData("SR - MPPP - Ejecutivo")]
        [InlineData("SR - MPPP - Supervisor")]
        [InlineData("SR - MPPP - RPA")]
        public void Los_nombres_de_rol_son_los_que_declara_el_diseno(string esperado)
        {
            var declarados = new[] { TablasNativas.RolEjecutivo, TablasNativas.RolSupervisor, TablasNativas.RolRpa };
            Assert.Contains(esperado, declarados);
        }

        /// <summary>
        /// Que los roles NO ESTÉN en el entorno y que el usuario NO TENGA rol son dos problemas
        /// distintos y tienen que decirlo: el primero es una solución mal instalada y lo arregla
        /// un administrador en minutos; el segundo es una autorización denegada y está bien que
        /// ocurra. Hasta el 2026-09-23 los dos daban "El rol de quien llama no puede hacer esta
        /// transición", y por eso el defecto de los nombres nos mandó a buscar propagación de
        /// caché y asignaciones de permisos durante horas.
        /// </summary>
        [Fact]
        public void Si_los_roles_no_estan_instalados_el_error_lo_dice_en_vez_de_culpar_al_usuario()
        {
            var m = new Mundo(conRoles: false);

            var ex = Assert.Throws<InvalidPluginExecutionException>(
                () => m.Correr(new TransicionDeFilaStep(), m.Ejecutivo, EstadoDeLaFila.Digitada));

            Assert.Contains("no están instalados", ex.Message);
            Assert.Contains(TablasNativas.RolEjecutivo, ex.Message);
            Assert.DoesNotContain("El rol de quien llama", ex.Message);
        }

        private sealed class Mundo
        {
            public readonly OrganizationServiceEnMemoria Svc = new OrganizationServiceEnMemoria();
            public readonly ContextoDePluginSimulado Ctx;
            public Guid SolicitudId, FilaId, Ejecutivo, Supervisor, Rpa;

            public Mundo(EstadoDeLaFila estadoActual = EstadoDeLaFila.Validada, EstadoDeLaSolicitud estadoSolicitud = EstadoDeLaSolicitud.EnProceso, Guid? digitadaPor = null, string rpaPuedeAprobar = "no", bool conRoles = true)
            {
                // Los nombres salen de las CONSTANTES, nunca de literales repetidos acá.
                // Hasta el 2026-09-23 este doble sembraba "sr_mppp_ejecutivo" a mano, el mismo
                // string equivocado que usaba el código, así que la prueba se verificaba contra
                // sí misma y las 793 pasaban mientras en el entorno NINGUNA transición de Fila
                // se podía autorizar. Un literal repetido en la prueba no valida nada: confirma.
                Guid Rol(string nombre) => conRoles
                    ? Svc.Sembrar(new Entity(TablasNativas.Rol) { ["name"] = nombre })
                    : Guid.NewGuid();   // `conRoles: false` simula una solución mal instalada
                var rolEjecutivo = Rol(TablasNativas.RolEjecutivo);
                var rolSupervisor = Rol(TablasNativas.RolSupervisor);
                var rolRpa = Rol(TablasNativas.RolRpa); // D-44: rol propio del usuario de aplicación del RPA (fase 2), no el de la cuenta de servicio de los flujos

                Ejecutivo = Usuario("Eje Cutivo", rolEjecutivo);
                Supervisor = Usuario("Super Visor", rolSupervisor);
                Rpa = Usuario("Bot RPA", rolRpa, esAplicacion: true);

                Svc.Sembrar(new Entity(Tablas.Parametro) { ["statecode"] = new OptionSetValue(0), ["sanic_nombre"] = TransicionDeFilaStep.ParametroRpaPuedeAprobar, ["sanic_version"] = 1, ["sanic_valor"] = rpaPuedeAprobar });

                SolicitudId = Svc.Sembrar(new Entity(TablasHistorico.Solicitud)
                {
                    ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)estadoSolicitud),
                    ["sanic_remitente"] = "ana@acme.com", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
                });

                FilaId = Svc.Sembrar(Fila(1, estadoActual, digitadaPor));
                Ctx = new ContextoDePluginSimulado(Svc, Ahora);
                Ctx.Contexto.MessageName = "Update";
                Ctx.Contexto.PrimaryEntityName = TablasHistorico.Fila;
            }

            public Guid Usuario(string nombre, Guid rol, bool esAplicacion = false)
            {
                var u = new Entity(TablasNativas.Usuario) { ["fullname"] = nombre, ["isdisabled"] = false };
                if (esAplicacion)
                {
                    u["applicationid"] = Guid.NewGuid();
                }

                var id = Svc.Sembrar(u);
                // `systemuserroles` es una intersect entity: en Dataverse REAL sus columnas son
                // `Uniqueidentifier` crudos, no lookups. Este doble las sembraba como
                // `EntityReference` y por eso las pruebas no vieron que el código las leyera mal.
                // Un doble que modela algo distinto de la plataforma no prueba: consuela.
                Svc.Sembrar(new Entity(TablasNativas.UsuarioRol) { ["systemuserid"] = id, ["roleid"] = rol });
                return id;
            }

            public Entity Fila(int numero, EstadoDeLaFila estado, Guid? digitadaPor = null)
            {
                var f = new Entity(TablasHistorico.Fila)
                {
                    ["sanic_numerofila"] = numero, ["sanic_estado"] = new OptionSetValue((int)estado),
                    ["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, SolicitudId),
                    ["sanic_numerocuenta"] = "123456789", ["sanic_nombrebeneficiario"] = "Juan Perez", ["sanic_numeroplan"] = "0042",
                };
                if (digitadaPor.HasValue)
                {
                    f["sanic_digitadapor"] = new EntityReference(TablasNativas.Usuario, digitadaPor.Value);
                }

                return f;
            }

            /// <summary>Arma el `Target` y la pre-image como los manda la plataforma, y corre el step que se le pida.</summary>
            public Entity Correr(IPlugin step, Guid quienLlama, EstadoDeLaFila hacia, string mensaje = null, Action<Entity> ajustarTarget = null, EstadoDeLaFila? desde = null, Guid? digitadaPor = null)
            {
                var actual = Svc.Retrieve(TablasHistorico.Fila, FilaId, new ColumnSet(true));
                var target = new Entity(TablasHistorico.Fila, FilaId) { ["sanic_estado"] = new OptionSetValue((int)hacia) };
                if (mensaje != null)
                {
                    target["sanic_mensaje"] = mensaje;
                }

                ajustarTarget?.Invoke(target);

                var pre = new Entity(TablasHistorico.Fila, FilaId)
                {
                    ["sanic_estado"] = new OptionSetValue((int)(desde ?? (EstadoDeLaFila)actual.GetAttributeValue<OptionSetValue>("sanic_estado").Value)),
                    ["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, SolicitudId),
                    ["sanic_numerofila"] = actual["sanic_numerofila"],
                };
                var digitador = digitadaPor ?? actual.GetAttributeValue<EntityReference>("sanic_digitadapor")?.Id;
                if (digitador.HasValue)
                {
                    pre["sanic_digitadapor"] = new EntityReference(TablasNativas.Usuario, digitador.Value);
                }

                Ctx.Contexto.InitiatingUserId = quienLlama;
                Ctx.Contexto.UserId = quienLlama;
                Ctx.Contexto.InputParameters["Target"] = target;
                Ctx.Contexto.PreEntityImages["PreImage"] = pre;
                step.Execute(Ctx);
                return target;
            }

            public IList<Entity> Bitacora() => Svc.Registros(TablasHistorico.Bitacora);

            public Entity Solicitud() => Svc.Retrieve(TablasHistorico.Solicitud, SolicitudId, new ColumnSet(true));
        }

        // ------------------------------------------------------------------ 7.9 transición (Pre)
        [Fact]
        public void Un_ejecutivo_digita_una_fila_validada_y_el_plugin_pone_quien_y_cuando()
        {
            var m = new Mundo();

            var target = m.Correr(new TransicionDeFilaStep(), m.Ejecutivo, EstadoDeLaFila.Digitada);

            Assert.Equal(m.Ejecutivo, target.GetAttributeValue<EntityReference>("sanic_digitadapor").Id);
            Assert.Equal(Ahora, target["sanic_fechadigitada"]);
        }

        [Fact]
        public void Lo_que_una_persona_mande_en_quien_digito_se_pisa_nunca_se_le_cree()
        {
            var m = new Mundo();
            var inventado = Guid.NewGuid();

            var target = m.Correr(new TransicionDeFilaStep(), m.Ejecutivo, EstadoDeLaFila.Digitada, ajustarTarget: t =>
            {
                t["sanic_digitadapor"] = new EntityReference(TablasNativas.Usuario, inventado);
                t["sanic_fechadigitada"] = new DateTime(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            });

            Assert.Equal(m.Ejecutivo, target.GetAttributeValue<EntityReference>("sanic_digitadapor").Id);
            Assert.Equal(Ahora, target["sanic_fechadigitada"]);
        }

        [Fact]
        public void Un_supervisor_aprueba_lo_que_digito_otro_y_no_lo_que_digito_el()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            var target = m.Correr(new TransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);
            Assert.Equal(m.Supervisor, target.GetAttributeValue<EntityReference>("sanic_aprobadapor").Id);
            Assert.Equal(Ahora, target["sanic_fechaaprobada"]);

            var propia = new Mundo(EstadoDeLaFila.Digitada);
            var ex = Assert.Throws<InvalidPluginExecutionException>(() => propia.Correr(new TransicionDeFilaStep(), propia.Supervisor, EstadoDeLaFila.Aprobada, digitadaPor: propia.Supervisor));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        [Fact]
        public void Una_transicion_que_no_existe_o_sin_su_mensaje_se_rechaza()
        {
            var m = new Mundo();
            var ex = Assert.Throws<InvalidPluginExecutionException>(() => m.Correr(new TransicionDeFilaStep(), m.Ejecutivo, EstadoDeLaFila.Aprobada));
            Assert.Contains(TransicionesDeFila.NoPermitida, ex.Message);

            var sinMensaje = new Mundo();
            Assert.Throws<InvalidPluginExecutionException>(() => sinMensaje.Correr(new TransicionDeFilaStep(), sinMensaje.Ejecutivo, EstadoDeLaFila.Anulada));
            var conMensaje = new Mundo();
            conMensaje.Correr(new TransicionDeFilaStep(), conMensaje.Ejecutivo, EstadoDeLaFila.Anulada, mensaje: "Duplicada, la reenvían");
        }

        [Fact]
        public void El_estado_de_origen_sale_de_la_pre_image_no_de_lo_que_diga_quien_llama()
        {
            // La fila está Validada; alguien pretende aprobarla diciendo que venía de Digitada.
            var m = new Mundo();
            Assert.Throws<InvalidPluginExecutionException>(() => m.Correr(new TransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada, ajustarTarget: t => t["sanic_estadoanterior"] = new OptionSetValue((int)EstadoDeLaFila.Digitada)));
        }

        [Fact]
        public void Devolver_limpia_a_quien_habia_digitado()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            var target = m.Correr(new TransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Validada, mensaje: "Falta el nombre completo");
            Assert.True(target.Contains("sanic_digitadapor"));
            Assert.Null(target["sanic_digitadapor"]);
            Assert.Null(target["sanic_fechadigitada"]);
        }

        [Fact]
        public void El_rpa_aprueba_lo_suyo_solo_si_el_parametro_lo_habilita()
        {
            var no = new Mundo(EstadoDeLaFila.Digitada, rpaPuedeAprobar: "no");
            Assert.Throws<InvalidPluginExecutionException>(() => no.Correr(new TransicionDeFilaStep(), no.Rpa, EstadoDeLaFila.Aprobada, digitadaPor: no.Rpa));

            var si = new Mundo(EstadoDeLaFila.Digitada, rpaPuedeAprobar: "si");
            var target = si.Correr(new TransicionDeFilaStep(), si.Rpa, EstadoDeLaFila.Aprobada, digitadaPor: si.Rpa);
            Assert.Equal(si.Rpa, target.GetAttributeValue<EntityReference>("sanic_aprobadapor").Id);
        }

        // ------------------------------------------------------------------ revisión de código, 2026-09-21
        [Fact]
        public void Cuando_la_custom_api_del_rpa_escribe_como_system_los_roles_salen_del_target_no_de_system()
        {
            // 03 §4 y spike C-05 parte B: en un Update anidado con SYSTEM, `InitiatingUserId` vale SYSTEM en todos los niveles.
            // Si los roles se leyeran de ahí, el RPA no podría digitar nada: es su ÚNICO camino (04 §3, no tiene W sobre Fila).
            var m = new Mundo();
            m.Ctx.Contexto.Depth = 2;
            var system = m.Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "SYSTEM" }); // sin ningún rol

            var target = m.Correr(new TransicionDeFilaStep(), system, EstadoDeLaFila.Digitada, ajustarTarget: t =>
            {
                t["sanic_digitadapor"] = new EntityReference(TablasNativas.Usuario, m.Rpa);
                t["sanic_fechadigitada"] = Ahora;
            });

            Assert.Equal(m.Rpa, target.GetAttributeValue<EntityReference>("sanic_digitadapor").Id); // se respeta lo que puso la API
            Assert.Equal(Ahora, target["sanic_fechadigitada"]);
        }

        [Fact]
        public void Aprobando_como_system_el_rol_sale_de_quien_aprueba_y_la_segregacion_se_sigue_exigiendo()
        {
            // 03 §4: la excepción del RPA es para aprobar lo que ÉL MISMO digitó, con `rpa.puedeaprobar` en `si`.
            var m = new Mundo(EstadoDeLaFila.Digitada, rpaPuedeAprobar: "si");
            m.Ctx.Contexto.Depth = 2;
            var system = m.Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "SYSTEM" });

            var target = m.Correr(new TransicionDeFilaStep(), system, EstadoDeLaFila.Aprobada, digitadaPor: m.Rpa,
                ajustarTarget: t => t["sanic_aprobadapor"] = new EntityReference(TablasNativas.Usuario, m.Rpa));
            Assert.Equal(m.Rpa, target.GetAttributeValue<EntityReference>("sanic_aprobadapor").Id);

            // Y el RPA NO puede aprobar lo que digitó otro: no es supervisor.
            var deOtro = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid(), rpaPuedeAprobar: "si");
            deOtro.Ctx.Contexto.Depth = 2;
            var otroSystemMas = deOtro.Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "SYSTEM" });
            Assert.Throws<InvalidPluginExecutionException>(() => deOtro.Correr(new TransicionDeFilaStep(), otroSystemMas, EstadoDeLaFila.Aprobada,
                ajustarTarget: t => t["sanic_aprobadapor"] = new EntityReference(TablasNativas.Usuario, deOtro.Rpa)));

            // Sin nadie en el Target no se asume ningún rol: la transición se rechaza.
            var sinIdentidad = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            sinIdentidad.Ctx.Contexto.Depth = 2;
            var otroSystem = sinIdentidad.Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "SYSTEM" });
            Assert.Throws<InvalidPluginExecutionException>(() => sinIdentidad.Correr(new TransicionDeFilaStep(), otroSystem, EstadoDeLaFila.Aprobada));
        }

        [Fact]
        public void El_rpa_no_puede_aprobar_lo_que_digito_el_si_el_parametro_no_lo_habilita_aunque_escriba_como_system()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, rpaPuedeAprobar: "no");
            m.Ctx.Contexto.Depth = 2;
            var system = m.Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "SYSTEM" });
            Assert.Throws<InvalidPluginExecutionException>(() => m.Correr(new TransicionDeFilaStep(), system, EstadoDeLaFila.Aprobada,
                ajustarTarget: t => t["sanic_aprobadapor"] = new EntityReference(TablasNativas.Usuario, m.Rpa), digitadaPor: m.Rpa));
        }

        [Fact]
        public void El_evento_de_bitacora_sale_de_una_consulta_pura_sin_preguntar_roles()
        {
            Assert.Equal(EventoDeBitacora.FilaDigitada, TransicionesDeFila.EventoPara(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada));
            Assert.Equal(EventoDeBitacora.FilaAprobada, TransicionesDeFila.EventoPara(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada));
            Assert.Equal(EventoDeBitacora.FilaDevuelta, TransicionesDeFila.EventoPara(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada));
            Assert.Equal(EventoDeBitacora.FilaAnulada, TransicionesDeFila.EventoPara(EstadoDeLaFila.Validada, EstadoDeLaFila.Anulada));
            Assert.Equal(EventoDeBitacora.FilaRechazadaEnAS400, TransicionesDeFila.EventoPara(EstadoDeLaFila.Digitada, EstadoDeLaFila.RechazadaEnAS400));
            Assert.Null(TransicionesDeFila.EventoPara(EstadoDeLaFila.Validada, EstadoDeLaFila.Aprobada));

            // Y el Post no gasta consultas de roles ni del parámetro para saber qué evento escribir.
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            m.Svc.Sembrar(m.Fila(2, EstadoDeLaFila.Validada));
            var antes = m.Svc.Llamadas.Count;
            m.Correr(new PostTransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);
            // 6 desde el 2026-09-23: la sexta es el Update que toma el bloqueo de la Solicitud
            // (ver Los_datos_de_cierre_se_leen_DESPUES_de_tomar_el_bloqueo). Sigue sin preguntar roles.
            Assert.InRange(m.Svc.Llamadas.Count - antes, 1, 6);
        }

        /// <summary>
        /// El pre-lock sirve por el ORDEN, no por existir: si el `Update` que toma el bloqueo de la
        /// Solicitud se hiciera DESPUÉS de leer las filas, dos transacciones simultáneas volverían a
        /// leer las dos el mismo estado a medias y ninguna cerraría — exactamente el defecto que este
        /// patrón vino a arreglar (MPPP-00001008, 2026-09-23).
        ///
        /// Nada más en el código obliga a ese orden: son dos líneas seguidas que alguien puede
        /// reordenar sin que nada se queje. Por eso se fija acá.
        /// </summary>
        [Fact]
        public void Los_datos_de_cierre_se_leen_DESPUES_de_tomar_el_bloqueo()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            m.Svc.Sembrar(m.Fila(2, EstadoDeLaFila.Validada));
            var antes = m.Svc.Llamadas.Count;

            m.Correr(new PostTransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);

            var despues = m.Svc.Llamadas.Skip(antes).ToList();
            var bloqueo = despues.FindIndex(
                l => l.Operacion == "Update" && l.Entidad == TablasHistorico.Solicitud);
            var lecturaDeFilas = despues.FindIndex(
                l => l.Operacion == "RetrieveMultiple" && l.Entidad == TablasHistorico.Fila);

            Assert.True(bloqueo >= 0, "el step tiene que tomar el bloqueo de la Solicitud");
            Assert.True(lecturaDeFilas >= 0, "el step tiene que leer las filas de la Solicitud");
            Assert.True(bloqueo < lecturaDeFilas,
                $"el bloqueo se toma en la posición {bloqueo} y las filas se leen en la {lecturaDeFilas}: "
                + "leer antes de bloquear deja pasar la condición de carrera que el pre-lock evita.");
        }

        [Fact]
        public void Un_update_que_no_cambia_el_estado_no_hace_nada()
        {
            var m = new Mundo();
            var target = new Entity(TablasHistorico.Fila, m.FilaId) { ["sanic_mensaje"] = "solo un comentario" };
            m.Ctx.Contexto.InitiatingUserId = m.Ejecutivo;
            m.Ctx.Contexto.InputParameters["Target"] = target;
            new TransicionDeFilaStep().Execute(m.Ctx);
            Assert.False(target.Contains("sanic_digitadapor"));
        }

        // ------------------------------------------------------------------ 7.9 post-transición
        [Fact]
        public void La_post_transicion_deja_bitacora_y_no_cierra_si_quedan_filas_abiertas()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            m.Svc.Sembrar(m.Fila(2, EstadoDeLaFila.Validada)); // todavía queda una abierta

            m.Correr(new PostTransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);

            var evento = Assert.Single(m.Bitacora());
            Assert.Equal((int)EventoDeBitacora.FilaAprobada, evento.GetAttributeValue<OptionSetValue>("sanic_evento").Value);
            Assert.Equal(1, evento["sanic_numerofila"]);
            Assert.Contains("Super", (string)evento["sanic_actortexto"]);
            Assert.Equal(EstadoDeLaSolicitud.EnProceso, (EstadoDeLaSolicitud)m.Solicitud().GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value);
        }

        [Fact]
        public void Cuando_no_queda_ninguna_fila_abierta_la_solicitud_pasa_a_procesada_con_su_respuesta_final()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, digitadaPor: Guid.NewGuid());
            m.Svc.Sembrar(m.Fila(2, EstadoDeLaFila.RechazadaEnValidacion));

            m.Correr(new PostTransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);

            var solicitud = m.Solicitud();
            Assert.Equal((int)EstadoDeLaSolicitud.Procesada, solicitud.GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value);
            Assert.Equal(Ahora, solicitud["sanic_fechaprocesada"]);
            var respuesta = (string)solicitud["sanic_respuestafinalcontenido"];
            Assert.Contains("MPPP-00000123", respuesta);
            Assert.Contains("<table", respuesta);
            Assert.DoesNotContain("123456789", respuesta); // la cuenta va enmascarada
            Assert.Equal(2, m.Bitacora().Count); // la de la fila y la de Procesada
            Assert.Contains(m.Bitacora(), b => b.GetAttributeValue<OptionSetValue>("sanic_evento").Value == (int)EventoDeBitacora.Procesada);
        }

        [Fact]
        public void Si_la_solicitud_no_esta_en_proceso_la_post_transicion_solo_deja_bitacora()
        {
            var m = new Mundo(EstadoDeLaFila.Digitada, EstadoDeLaSolicitud.Rechazada, digitadaPor: Guid.NewGuid());
            m.Correr(new PostTransicionDeFilaStep(), m.Supervisor, EstadoDeLaFila.Aprobada);
            Assert.Single(m.Bitacora());
            Assert.Equal((int)EstadoDeLaSolicitud.Rechazada, m.Solicitud().GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value);
        }

        // ------------------------------------------------------------------ 7.12 atender por clasificar
        private static (ContextoDePluginSimulado ctx, OrganizationServiceEnMemoria svc, Guid id) Solicitud(EstadoDeLaSolicitud desde, EstadoDeLaSolicitud hacia, bool identidadDeAplicacion = false)
        {
            var svc = new OrganizationServiceEnMemoria();
            var usuario = new Entity(TablasNativas.Usuario) { ["fullname"] = "Eje Cutivo" };
            if (identidadDeAplicacion)
            {
                usuario["applicationid"] = Guid.NewGuid();
            }

            var usuarioId = svc.Sembrar(usuario);
            var id = svc.Sembrar(new Entity(TablasHistorico.Solicitud)
            {
                ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)desde),
                ["sanic_remitente"] = "ana@acme.com", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
            });
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = "Update";
            ctx.Contexto.InitiatingUserId = usuarioId;
            ctx.Contexto.UserId = usuarioId;
            ctx.Contexto.InputParameters["Target"] = new Entity(TablasHistorico.Solicitud, id) { ["sanic_estadoprocesamiento"] = new OptionSetValue((int)hacia) };
            ctx.Contexto.PreEntityImages["PreImage"] = new Entity(TablasHistorico.Solicitud, id) { ["sanic_estadoprocesamiento"] = new OptionSetValue((int)desde) };
            return (ctx, svc, id);
        }

        private static (ContextoDePluginSimulado ctx, OrganizationServiceEnMemoria svc, Guid id) SolicitudConRevision(
            bool estaba, bool queda, string motivo)
        {
            var svc = new OrganizationServiceEnMemoria();
            var usuarioId = svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "Ana Ejecutiva" });
            var id = svc.Sembrar(new Entity(TablasHistorico.Solicitud)
            {
                ["sanic_nombre"] = "MPPP-00000123",
                ["sanic_estadoprocesamiento"] = new OptionSetValue((int)EstadoDeLaSolicitud.EnProceso),
                [RevisionAtendidaStep.Marca] = estaba,
                [RevisionAtendidaStep.Motivo] = motivo,
            });
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = "Update";
            ctx.Contexto.InitiatingUserId = usuarioId;
            ctx.Contexto.UserId = usuarioId;
            ctx.Contexto.InputParameters["Target"] =
                new Entity(TablasHistorico.Solicitud, id) { [RevisionAtendidaStep.Marca] = queda };
            ctx.Contexto.PreEntityImages["PreImage"] = new Entity(TablasHistorico.Solicitud, id)
            {
                [RevisionAtendidaStep.Marca] = estaba,
                [RevisionAtendidaStep.Motivo] = motivo,
            };
            return (ctx, svc, id);
        }

        [Theory]
        [InlineData(EstadoDeLaSolicitud.NoReconocida, EstadoDeLaSolicitud.Cerrada)]
        [InlineData(EstadoDeLaSolicitud.NoReconocida, EstadoDeLaSolicitud.Descartada)]
        [InlineData(EstadoDeLaSolicitud.NoEsCorreoNuevo, EstadoDeLaSolicitud.Cerrada)]
        [InlineData(EstadoDeLaSolicitud.NoEsCorreoNuevo, EstadoDeLaSolicitud.Descartada)]
        public void Un_ejecutivo_puede_cerrar_o_descartar_lo_que_esta_por_clasificar(EstadoDeLaSolicitud desde, EstadoDeLaSolicitud hacia)
        {
            var (ctx, _, _) = Solicitud(desde, hacia);
            new AtenderPorClasificarStep().Execute(ctx);
        }

        /// <summary>
        /// El boton "Revisado" (`05` §5). Contrato: al apagar la marca, el motivo que habia escrito la
        /// MAQUINA queda en la Bitacora con quien y cuando, y la columna se limpia. El operador no escribe
        /// nada: `sanic_motivorevision` es lo que el LEE.
        /// </summary>
        [Fact]
        public void Apagar_la_marca_de_revision_deja_el_motivo_en_la_bitacora_y_limpia_la_columna()
        {
            var (ctx, svc, id) = SolicitudConRevision(estaba: true, queda: false,
                motivo: "Validacion fallida 3 veces.");

            new RevisionAtendidaStep().Execute(ctx);

            var evento = Assert.Single(svc.Registros(TablasHistorico.Bitacora));
            Assert.Equal((int)EventoDeBitacora.RevisionAtendida, evento.GetAttributeValue<OptionSetValue>("sanic_evento").Value);
            Assert.Equal("Validacion fallida 3 veces.", evento.GetAttributeValue<string>("sanic_detalle"));
            Assert.False(string.IsNullOrWhiteSpace(evento.GetAttributeValue<string>("sanic_actortexto")));

            var target = (Entity)ctx.Contexto.InputParameters["Target"];
            Assert.True(target.Contains(RevisionAtendidaStep.Motivo));
            Assert.Null(target[RevisionAtendidaStep.Motivo]);
            Assert.Equal(id, target.Id);
        }

        /// <summary>Prender la marca es asunto de los flujos, que ya escriben su propio evento: este step
        /// no tiene que meterse ni dejar un renglon de mas en la Bitacora.</summary>
        [Theory]
        [InlineData(false, true)]   // la prende un flujo
        [InlineData(true, true)]    // se guarda la solicitud sin cambiar la marca
        [InlineData(false, false)]
        public void Cualquier_otro_movimiento_de_la_marca_no_escribe_nada(bool estaba, bool queda)
        {
            var (ctx, svc, _) = SolicitudConRevision(estaba, queda, motivo: "Envio iniciado sin confirmar.");

            new RevisionAtendidaStep().Execute(ctx);

            Assert.Empty(svc.Registros(TablasHistorico.Bitacora));
            Assert.False(((Entity)ctx.Contexto.InputParameters["Target"]).Contains(RevisionAtendidaStep.Motivo));
        }

        [Theory]
        [InlineData(EstadoDeLaSolicitud.NoReconocida, EstadoDeLaSolicitud.EnProceso)]
        [InlineData(EstadoDeLaSolicitud.NoReconocida, EstadoDeLaSolicitud.Ingresada)]
        [InlineData(EstadoDeLaSolicitud.EnProceso, EstadoDeLaSolicitud.Cerrada)]
        [InlineData(EstadoDeLaSolicitud.Ingresada, EstadoDeLaSolicitud.Descartada)]
        [InlineData(EstadoDeLaSolicitud.Vencida, EstadoDeLaSolicitud.Cerrada)]
        public void Cualquier_otro_cambio_de_estado_hecho_por_una_persona_se_rechaza(EstadoDeLaSolicitud desde, EstadoDeLaSolicitud hacia)
        {
            var (ctx, _, _) = Solicitud(desde, hacia);
            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new AtenderPorClasificarStep().Execute(ctx));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        [Fact]
        public void El_codigo_de_servidor_mueve_los_estados_que_le_tocan_sin_pasar_por_este_control()
        {
            var (ctx, _, _) = Solicitud(EstadoDeLaSolicitud.Ingresada, EstadoDeLaSolicitud.EnProceso, identidadDeAplicacion: true);
            new AtenderPorClasificarStep().Execute(ctx);

            var (anidado, _, _) = Solicitud(EstadoDeLaSolicitud.EnProceso, EstadoDeLaSolicitud.Procesada);
            anidado.Contexto.Depth = 2;
            new AtenderPorClasificarStep().Execute(anidado);
        }

        [Fact]
        public void Un_proveedor_incompleto_no_revienta_con_una_referencia_nula()
        {
            foreach (IPlugin step in new IPlugin[] { new TransicionDeFilaStep(), new PostTransicionDeFilaStep(), new AtenderPorClasificarStep() })
            {
                Assert.Throws<InvalidPluginExecutionException>(() => step.Execute(null));
            }
        }
    }
}
