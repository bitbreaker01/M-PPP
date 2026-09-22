using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Api;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// 7.6b: el envoltorio `IPlugin` de la Custom API (diseno/03 §0). Traduce parámetros y no decide nada del negocio; lo que se
    /// prueba acá es el contrato con la plataforma y que un error real no le cuente nada a quien llama.
    /// </summary>
    public class ClasificarCorreoApiAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 21, 16, 0, 0, DateTimeKind.Utc);

        /// <summary>Un entorno mínimo y completo: reglas de correo, parámetro de prefijos, un autorizado con su plan, y la Solicitud.</summary>
        private static (ContextoDePluginSimulado ctx, OrganizationServiceEnMemoria svc, Guid solicitudId) Armar(string eml = "Subject: Inclusiones\r\n\r\ncuerpo", string remitente = "ana@acme.com")
        {
            var svc = new OrganizationServiceEnMemoria();
            Entity Activo(string tabla, params (string, object)[] atributos)
            {
                var e = new Entity(tabla) { ["statecode"] = new OptionSetValue(0) };
                foreach (var (a, v) in atributos)
                {
                    e[a] = v;
                }

                return e;
            }

            var cliente = svc.Sembrar(Activo(Tablas.Cliente, ("sanic_nombre", "ACME")));
            var plan = svc.Sembrar(Activo(Tablas.Plan, ("sanic_codigo", "000A"), ("sanic_tipoformato", new OptionSetValue((int)TipoDeFormatoDelPlan._06)), ("sanic_moneda", new OptionSetValue((int)Moneda.COR)), ("sanic_clienteid", new EntityReference(Tablas.Cliente, cliente))));
            var autorizado = svc.Sembrar(Activo(Tablas.Autorizado, ("sanic_nombre", "ana@acme.com"), ("sanic_clienteid", new EntityReference(Tablas.Cliente, cliente))));
            svc.Sembrar(Activo(Tablas.AutorizacionPlan, ("sanic_autorizadoid", new EntityReference(Tablas.Autorizado, autorizado)), ("sanic_planid", new EntityReference(Tablas.Plan, plan))));
            svc.Sembrar(Activo(Tablas.Parametro, ("sanic_nombre", ClasificarCorreo.ParametroPrefijosDeReenvio), ("sanic_version", 1), ("sanic_valor", @"[""FW:"",""RV:""]")));
            svc.Sembrar(Activo(Tablas.Regla, ("sanic_codigo", ReglasDelCorreo.EsCorreoNuevo), ("sanic_nivel", new OptionSetValue((int)NivelDeLaRegla.Correo)), ("sanic_orden", 10), ("sanic_efecto", new OptionSetValue((int)EfectoDeLaRegla.EnviaARevision))));
            svc.Sembrar(Activo(Tablas.Regla, ("sanic_codigo", ReglasDelCorreo.RemitenteReconocido), ("sanic_nivel", new OptionSetValue((int)NivelDeLaRegla.Correo)), ("sanic_orden", 20), ("sanic_dependede", ReglasDelCorreo.EsCorreoNuevo), ("sanic_efecto", new OptionSetValue((int)EfectoDeLaRegla.EnviaARevision))));

            // Un ejecutivo habilitado con su rol, para que el aviso de DA-08 tenga a quién ir.
            var rol = svc.Sembrar(new Entity(TablasNativas.Rol) { ["name"] = TablasNativas.RolEjecutivo });
            var usuario = svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = "Eje Cutivo", ["isdisabled"] = false });
            svc.Sembrar(new Entity(TablasNativas.UsuarioRol) { ["roleid"] = new EntityReference(TablasNativas.Rol, rol), ["systemuserid"] = new EntityReference(TablasNativas.Usuario, usuario) });

            var solicitudId = svc.Sembrar(new Entity(TablasHistorico.Solicitud)
            {
                ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)EstadoDeLaSolicitud.Ingresada),
                ["sanic_remitente"] = remitente, ["sanic_asunto"] = "Inclusiones", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
                ["sanic_correocrudo"] = Encoding.UTF8.GetBytes(eml),
            });

            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.InputParameters[ClasificarCorreoApi.ParametroSolicitudId] = solicitudId;
            return (ctx, svc, solicitudId);
        }

        private static void Ejecutar(ContextoDePluginSimulado ctx) => new ClasificarCorreoApi().Execute(ctx);

        // ------------------------------------------------------------------ el camino feliz
        [Fact]
        public void Devuelve_las_tres_salidas_con_sus_nombres_exactos_y_usa_el_usuario_y_la_fecha_del_contexto()
        {
            var (ctx, svc, _) = Armar();

            Ejecutar(ctx);

            Assert.Equal(true, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaProcesar]);
            Assert.Equal(Clasificaciones.Nuevo, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaClasificacion]);
            Assert.Equal(false, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaYaProcesada]);
            Assert.Equal(new[] { "procesar", "clasificacion", "yaprocesada" }, ctx.Contexto.OutputParameters.Keys.OrderBy(k => k == "procesar" ? 0 : k == "clasificacion" ? 1 : 2));
            Assert.Equal(ctx.Contexto.UserId, ctx.UsuarioDelServicio); // la cuenta de servicio, no quien inició
            Assert.NotEqual(ctx.Contexto.InitiatingUserId, ctx.UsuarioDelServicio);
            var evaluacion = svc.Registros(TablasHistorico.ResultadoRegla).First();
            Assert.Equal(Ahora, evaluacion["sanic_fechaevaluacion"]); // la fecha sale del contexto: el código no lee el reloj
        }

        [Fact]
        public void Una_fecha_del_contexto_sin_kind_se_trata_como_utc()
        {
            var svc = new OrganizationServiceEnMemoria();
            var (ctx, _, _) = Armar();
            ctx.Contexto.OperationCreatedOn = DateTime.SpecifyKind(Ahora, DateTimeKind.Unspecified);
            Ejecutar(ctx); // Dataverse entrega la fecha de la operación en UTC, sin Kind: no puede reventar
            Assert.Equal(Clasificaciones.Nuevo, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaClasificacion]);
        }

        [Fact]
        public void Un_correo_que_no_se_procesa_tambien_devuelve_las_tres_salidas_y_avisa_a_los_ejecutivos()
        {
            var (ctx, svc, solicitudId) = Armar(eml: "Subject: RE: Inclusiones\r\nIn-Reply-To: <a@b>\r\n\r\n");

            Ejecutar(ctx);

            Assert.Equal(false, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaProcesar]);
            Assert.Equal(Clasificaciones.Respuesta, ctx.Contexto.OutputParameters[ClasificarCorreoApi.SalidaClasificacion]);
            var aviso = Assert.Single(svc.Registros(TablasNativas.Notificacion));
            Assert.Contains("MPPP-00000123", (string)aviso["title"] + (string)aviso["body"]);
        }

        [Fact]
        public void El_trace_deja_rastro_del_principio_y_del_final_sin_volcar_el_correo()
        {
            var (ctx, _, solicitudId) = Armar(eml: "Subject: SECRETO DEL CLIENTE\r\nIn-Reply-To: <a@b>\r\n\r\ncuerpo secreto");

            Ejecutar(ctx);

            Assert.True(ctx.Trace.Lineas.Count >= 2);
            Assert.Contains(solicitudId.ToString(), ctx.Trace.Todo);
            Assert.Contains(Clasificaciones.Respuesta, ctx.Trace.Todo);
            Assert.DoesNotContain("SECRETO", ctx.Trace.Todo);
            Assert.DoesNotContain("cuerpo secreto", ctx.Trace.Todo);
        }

        // ------------------------------------------------------------------ parámetros de entrada
        public static IEnumerable<object[]> EntradasMalas()
        {
            yield return new object[] { null }; // sin el parámetro
            yield return new object[] { Guid.Empty };
            yield return new object[] { "no soy un guid" };
            yield return new object[] { 42 };
        }

        [Theory]
        [MemberData(nameof(EntradasMalas))]
        public void Una_entrada_que_no_es_un_identificador_util_es_un_error_que_dice_que_falta(object valor)
        {
            var (ctx, svc, _) = Armar();
            ctx.Contexto.InputParameters.Remove(ClasificarCorreoApi.ParametroSolicitudId);
            if (valor != null)
            {
                ctx.Contexto.InputParameters[ClasificarCorreoApi.ParametroSolicitudId] = valor;
            }

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => Ejecutar(ctx));
            Assert.Contains(ClasificarCorreoApi.ParametroSolicitudId, ex.Message);
            Assert.Empty(svc.Llamadas);
            Assert.Empty(ctx.Contexto.OutputParameters);
        }

        // ------------------------------------------------------------------ errores reales
        [Fact]
        public void Un_error_real_no_le_cuenta_nada_a_quien_llama_y_el_detalle_va_al_trace()
        {
            var (ctx, svc, solicitudId) = Armar();
            // Una regla activa sin evaluador: catálogo mal armado (D-13). El mensaje interno nombra la regla.
            svc.Sembrar(new Entity(Tablas.Regla)
            {
                ["statecode"] = new OptionSetValue(0), ["sanic_codigo"] = "REGLA_FANTASMA", ["sanic_nivel"] = new OptionSetValue((int)NivelDeLaRegla.Correo),
                ["sanic_orden"] = 30, ["sanic_efecto"] = new OptionSetValue((int)EfectoDeLaRegla.EnviaARevision),
            });

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => Ejecutar(ctx));

            Assert.Equal(ClasificarCorreoApi.MensajeDeErrorGenerico, ex.Message);
            Assert.DoesNotContain("REGLA_FANTASMA", ex.Message);
            Assert.Contains("REGLA_FANTASMA", ctx.Trace.Todo); // el detalle, solo para el equipo técnico
            Assert.Empty(ctx.Contexto.OutputParameters);
        }

        [Fact]
        public void Un_proveedor_incompleto_no_revienta_con_una_referencia_nula()
        {
            foreach (var quitar in new[] { "contexto", "fabrica", "trace" })
            {
                var (ctx, _, _) = Armar();
                ctx.DaContexto = quitar != "contexto";
                ctx.DaFabrica = quitar != "fabrica";
                ctx.DaTrace = quitar != "trace";
                var ex = Record.Exception(() => Ejecutar(ctx));
                Assert.IsType<InvalidPluginExecutionException>(ex);
            }

            Assert.Throws<InvalidPluginExecutionException>(() => new ClasificarCorreoApi().Execute(null));
        }
    }
}
