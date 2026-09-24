using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Api;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.7: el envoltorio `IPlugin` de la Custom API de validación (diseno/03 §1). Traduce parámetros; no decide nada del negocio.</summary>
    public class ValidarSolicitudApiAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 22, 9, 0, 0, DateTimeKind.Utc);

        /// <summary>Una Solicitud que YA NO está en Ingresada: el camino idempotente, que no necesita Excel ni parámetros.</summary>
        private static (ContextoDePluginSimulado ctx, OrganizationServiceEnMemoria svc, Guid id) Armar(EstadoDeLaSolicitud estado = EstadoDeLaSolicitud.EnProceso)
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Sembrar(new Entity(TablasHistorico.Solicitud)
            {
                ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)estado),
                ["sanic_remitente"] = "ana@acme.com", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
                ["sanic_filastotales"] = 7, ["sanic_filasvalidas"] = 5, ["sanic_filasrechazadas"] = 2,
            });
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = "sanic_mppp_capi_validarsolicitud";
            ctx.Contexto.InputParameters[ValidarSolicitudApi.ParametroSolicitudId] = id;
            return (ctx, svc, id);
        }

        /// <summary>
        /// Esta prueba se llamaba `..._usa_el_usuario_del_contexto` y exigía `CreateOrganizationService(contexto.UserId)`.
        /// Fijaba como contrato lo contrario de lo que manda `diseno/04` §1 y §3: el plugin lee y graba con SYSTEM,
        /// porque la cuenta de servicio que llama a esta API NO puede leer filas, clientes, planes ni autorizados.
        /// Corregida el 2026-09-23, con el defecto ya visto en el entorno.
        /// </summary>
        [Fact]
        public void Devuelve_las_seis_salidas_con_sus_nombres_exactos_y_trabaja_como_system()
        {
            var (ctx, _, _) = Armar();

            new ValidarSolicitudApi().Execute(ctx);

            var salidas = ctx.Contexto.OutputParameters;
            Assert.Equal((int)EstadoDeLaSolicitud.EnProceso, salidas[ValidarSolicitudApi.SalidaEstado]);
            Assert.Equal(true, salidas[ValidarSolicitudApi.SalidaYaProcesada]);
            Assert.Equal(7, salidas[ValidarSolicitudApi.SalidaFilasTotales]);
            Assert.Equal(5, salidas[ValidarSolicitudApi.SalidaFilasValidas]);
            Assert.Equal(2, salidas[ValidarSolicitudApi.SalidaFilasRechazadas]);
            Assert.False(string.IsNullOrWhiteSpace((string)salidas[ValidarSolicitudApi.SalidaResumen]));
            Assert.Equal(6, salidas.Count);
            // `null` = SYSTEM: ni el usuario del contexto ni quien inició la llamada.
            Assert.Null(ctx.UsuarioDelServicio);
            Assert.True(ctx.Trace.Lineas.Count >= 2);
        }

        public static IEnumerable<object[]> EntradasMalas()
        {
            yield return new object[] { null };
            yield return new object[] { Guid.Empty };
            yield return new object[] { "no soy un guid" };
        }

        [Theory]
        [MemberData(nameof(EntradasMalas))]
        public void Una_entrada_que_no_es_un_identificador_util_es_un_error_que_dice_que_falta(object valor)
        {
            var (ctx, svc, _) = Armar();
            ctx.Contexto.InputParameters.Remove(ValidarSolicitudApi.ParametroSolicitudId);
            if (valor != null)
            {
                ctx.Contexto.InputParameters[ValidarSolicitudApi.ParametroSolicitudId] = valor;
            }

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new ValidarSolicitudApi().Execute(ctx));
            Assert.Contains(ValidarSolicitudApi.ParametroSolicitudId, ex.Message);
            Assert.Empty(svc.Llamadas);
            Assert.Empty(ctx.Contexto.OutputParameters);
        }

        [Fact]
        public void Un_error_real_no_le_cuenta_nada_a_quien_llama_y_el_detalle_va_al_trace()
        {
            // Una Solicitud en Ingresada sin ningún parámetro cargado: error real de configuración.
            var (ctx, _, _) = Armar(EstadoDeLaSolicitud.Ingresada);

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new ValidarSolicitudApi().Execute(ctx));

            Assert.Equal(ValidarSolicitudApi.MensajeDeErrorGenerico, ex.Message);
            Assert.Contains("plantilla.", ctx.Trace.Todo); // el detalle, solo para el equipo técnico
            Assert.DoesNotContain("plantilla.", ex.Message);
            Assert.Empty(ctx.Contexto.OutputParameters);
        }

        [Fact]
        public void Un_proveedor_incompleto_no_revienta_con_una_referencia_nula()
        {
            Assert.Throws<InvalidPluginExecutionException>(() => new ValidarSolicitudApi().Execute(null));
            foreach (var quitar in new[] { "contexto", "fabrica", "trace" })
            {
                var (ctx, _, _) = Armar();
                ctx.DaContexto = quitar != "contexto";
                ctx.DaFabrica = quitar != "fabrica";
                ctx.DaTrace = quitar != "trace";
                Assert.Throws<InvalidPluginExecutionException>(() => new ValidarSolicitudApi().Execute(ctx));
            }
        }
    }
}
