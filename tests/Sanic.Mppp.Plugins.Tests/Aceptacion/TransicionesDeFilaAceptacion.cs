// PRUEBAS DE ACEPTACIÓN de la pieza 7.1 (Dominio). Las escribe el arquitecto y fijan el comportamiento:
// salen de diseno/03-contratos-custom-api.md §4 (tabla de transiciones y "Cierre") y de la decisión D-25
// (Ejecutivo y Supervisor son excluyentes por usuario). EL CONSTRUCTOR NO MODIFICA ESTE ARCHIVO:
// si una prueba le parece equivocada, para y lo reporta con la cita del diseño.
using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Dominio;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    public class TransicionesDeFilaAceptacion
    {
        private static readonly Guid Ana = Guid.Parse("aaaaaaaa-0000-0000-0000-000000000001");
        private static readonly Guid Beto = Guid.Parse("bbbbbbbb-0000-0000-0000-000000000002");
        private static readonly Guid Bot = Guid.Parse("cccccccc-0000-0000-0000-000000000003");

        private static ResultadoDeTransicion Evaluar(EstadoDeLaFila desde, EstadoDeLaFila hacia, RolDeActor roles, Guid? quien = null,
                                                     string mensaje = null, Guid? digitadaPor = null, bool rpaPuedeAprobar = false)
        {
            return TransicionesDeFila.Evaluar(new PedidoDeTransicion
            {
                Desde = desde, Hacia = hacia, Actor = new Actor(quien ?? Ana, roles), Mensaje = mensaje, DigitadaPor = digitadaPor, RpaPuedeAprobar = rpaPuedeAprobar,
            });
        }

        private static void Permitida(ResultadoDeTransicion r, EfectoDeTransicion efecto, EventoDeBitacora evento)
        {
            Assert.True(r.Permitida, r.Motivo);
            Assert.Null(r.Motivo);
            Assert.Equal(efecto, r.Efecto);
            Assert.Equal(evento, r.Evento);
        }

        private static void Rechazada(ResultadoDeTransicion r, string fragmentoDelMotivo = null)
        {
            Assert.False(r.Permitida);
            Assert.False(string.IsNullOrWhiteSpace(r.Motivo));
            Assert.Equal(EfectoDeTransicion.Ninguno, r.Efecto);
            Assert.Null(r.Evento);
            if (fragmentoDelMotivo != null)
            {
                Assert.Contains(fragmentoDelMotivo, r.Motivo, StringComparison.OrdinalIgnoreCase);
            }
        }

        // ---- Validada -> Digitada: Ejecutivo o RPA ----
        [Theory]
        [InlineData(RolDeActor.Ejecutivo)]
        [InlineData(RolDeActor.Rpa)]
        public void Digitar_lo_hace_el_ejecutivo_o_el_rpa(RolDeActor rol)
        {
            Permitida(Evaluar(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada, rol), EfectoDeTransicion.RegistrarDigitacion, EventoDeBitacora.FilaDigitada);
        }

        [Fact]
        public void Digitar_no_lo_hace_el_supervisor()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada, RolDeActor.Supervisor));
        }

        // ---- Validada | Digitada -> Rechazada en AS400: quien digita, con mensaje ----
        [Theory]
        [InlineData(EstadoDeLaFila.Validada, RolDeActor.Ejecutivo)]
        [InlineData(EstadoDeLaFila.Digitada, RolDeActor.Ejecutivo)]
        [InlineData(EstadoDeLaFila.Validada, RolDeActor.Rpa)]
        [InlineData(EstadoDeLaFila.Digitada, RolDeActor.Rpa)]
        public void Rechazar_en_as400_lo_hace_quien_digita_y_con_mensaje(EstadoDeLaFila desde, RolDeActor rol)
        {
            Permitida(Evaluar(desde, EstadoDeLaFila.RechazadaEnAS400, rol, mensaje: "Cuenta cerrada en AS400"), EfectoDeTransicion.Ninguno, EventoDeBitacora.FilaRechazadaEnAS400);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void Rechazar_en_as400_sin_mensaje_no_se_permite(string mensaje)
        {
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.RechazadaEnAS400, RolDeActor.Ejecutivo, mensaje: mensaje), "mensaje");
        }

        [Fact]
        public void Rechazar_en_as400_no_lo_hace_el_supervisor()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.RechazadaEnAS400, RolDeActor.Supervisor, mensaje: "x"));
        }

        // ---- Validada | Digitada -> Anulada: SOLO el ejecutivo, con mensaje; el RPA nunca ----
        [Theory]
        [InlineData(EstadoDeLaFila.Validada)]
        [InlineData(EstadoDeLaFila.Digitada)]
        public void Anular_solo_el_ejecutivo_y_con_mensaje(EstadoDeLaFila desde)
        {
            Permitida(Evaluar(desde, EstadoDeLaFila.Anulada, RolDeActor.Ejecutivo, mensaje: "El cliente mandó mal la cuenta"), EfectoDeTransicion.Ninguno, EventoDeBitacora.FilaAnulada);
            Rechazada(Evaluar(desde, EstadoDeLaFila.Anulada, RolDeActor.Ejecutivo, mensaje: " "), "mensaje");
            Rechazada(Evaluar(desde, EstadoDeLaFila.Anulada, RolDeActor.Rpa, mensaje: "x"));
            Rechazada(Evaluar(desde, EstadoDeLaFila.Anulada, RolDeActor.Supervisor, mensaje: "x"));
        }

        // ---- Digitada -> Aprobada: supervisor distinto de quien digitó (segregación) ----
        [Fact]
        public void Aprobar_lo_hace_un_supervisor_que_no_digito()
        {
            Permitida(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Supervisor, quien: Beto, digitadaPor: Ana),
                      EfectoDeTransicion.RegistrarAprobacion, EventoDeBitacora.FilaAprobada);
        }

        [Fact]
        public void Nadie_aprueba_lo_que_digito()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Supervisor, quien: Ana, digitadaPor: Ana), "digit");
        }

        [Fact]
        public void Aprobar_no_lo_hace_el_ejecutivo()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Ejecutivo, quien: Beto, digitadaPor: Ana));
        }

        [Fact]
        public void Una_fila_digitada_sin_digitador_registrado_no_se_aprueba()
        {
            // Falla cerrado: sin saber quién digitó no se puede comprobar la segregación.
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Supervisor, quien: Beto, digitadaPor: null));
        }

        [Fact]
        public void El_rpa_aprueba_lo_que_el_mismo_digito_solo_si_el_parametro_lo_permite()
        {
            Permitida(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Rpa, quien: Bot, digitadaPor: Bot, rpaPuedeAprobar: true),
                      EfectoDeTransicion.RegistrarAprobacion, EventoDeBitacora.FilaAprobada);
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Rpa, quien: Bot, digitadaPor: Bot, rpaPuedeAprobar: false));
        }

        [Fact]
        public void El_parametro_del_rpa_no_le_abre_la_puerta_a_un_supervisor_que_digito()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, RolDeActor.Supervisor, quien: Ana, digitadaPor: Ana, rpaPuedeAprobar: true));
        }

        // ---- Digitada -> Validada: devolver, solo el supervisor, con mensaje ----
        [Fact]
        public void Devolver_lo_hace_el_supervisor_con_mensaje_y_limpia_la_digitacion()
        {
            Permitida(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada, RolDeActor.Supervisor, quien: Beto, mensaje: "La cuenta no coincide", digitadaPor: Ana),
                      EfectoDeTransicion.LimpiarDigitacion, EventoDeBitacora.FilaDevuelta);
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada, RolDeActor.Supervisor, quien: Beto, mensaje: null, digitadaPor: Ana), "mensaje");
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada, RolDeActor.Ejecutivo, mensaje: "x", digitadaPor: Ana));
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada, RolDeActor.Rpa, mensaje: "x", digitadaPor: Ana));
        }

        // ---- D-25: Ejecutivo y Supervisor son excluyentes por usuario ----
        [Fact]
        public void Un_usuario_con_los_dos_roles_no_puede_hacer_ninguna_transicion()
        {
            var ambos = RolDeActor.Ejecutivo | RolDeActor.Supervisor;
            Rechazada(Evaluar(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada, ambos), "rol");
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada, ambos, quien: Beto, digitadaPor: Ana), "rol");
            Rechazada(Evaluar(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada, ambos, quien: Beto, mensaje: "x", digitadaPor: Ana), "rol");
        }

        [Fact]
        public void Un_usuario_sin_ningun_rol_no_puede_hacer_ninguna_transicion()
        {
            Rechazada(Evaluar(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada, RolDeActor.Ninguno));
        }

        // ---- Todo lo que no está en la tabla ----
        public static IEnumerable<object[]> TodoLoQueNoEstaEnLaTabla()
        {
            var tabla = new HashSet<(EstadoDeLaFila, EstadoDeLaFila)>
            {
                (EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada), (EstadoDeLaFila.Validada, EstadoDeLaFila.RechazadaEnAS400), (EstadoDeLaFila.Digitada, EstadoDeLaFila.RechazadaEnAS400),
                (EstadoDeLaFila.Validada, EstadoDeLaFila.Anulada), (EstadoDeLaFila.Digitada, EstadoDeLaFila.Anulada), (EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada),
                (EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada),
            };
            var todos = Enum.GetValues(typeof(EstadoDeLaFila)).Cast<EstadoDeLaFila>().ToArray();
            return from desde in todos from hacia in todos where !tabla.Contains((desde, hacia)) select new object[] { desde, hacia };
        }

        [Theory]
        [MemberData(nameof(TodoLoQueNoEstaEnLaTabla))]
        public void Cualquier_otro_cambio_es_transicion_no_permitida_para_cualquier_rol(EstadoDeLaFila desde, EstadoDeLaFila hacia)
        {
            foreach (var rol in new[] { RolDeActor.Ejecutivo, RolDeActor.Supervisor, RolDeActor.Rpa })
            {
                var r = Evaluar(desde, hacia, rol, quien: Beto, mensaje: "x", digitadaPor: Ana, rpaPuedeAprobar: true);
                Assert.False(r.Permitida);
                Assert.Equal(TransicionesDeFila.NoPermitida, r.Motivo);
            }
        }

        [Fact]
        public void Un_pedido_nulo_o_sin_actor_es_un_error_de_programacion_no_un_rechazo()
        {
            Assert.Throws<ArgumentNullException>(() => TransicionesDeFila.Evaluar(null));
            Assert.Throws<ArgumentNullException>(() => TransicionesDeFila.Evaluar(new PedidoDeTransicion { Desde = EstadoDeLaFila.Validada, Hacia = EstadoDeLaFila.Digitada, Actor = null }));
        }

        // ---- Filas abiertas y cierre de la solicitud ----
        [Fact]
        public void Solo_validada_y_digitada_estan_abiertas()
        {
            foreach (EstadoDeLaFila e in Enum.GetValues(typeof(EstadoDeLaFila)))
            {
                Assert.Equal(e == EstadoDeLaFila.Validada || e == EstadoDeLaFila.Digitada, TransicionesDeFila.EstaAbierta(e));
            }
        }

        [Fact]
        public void La_solicitud_en_proceso_se_procesa_cuando_no_queda_ninguna_fila_abierta()
        {
            var cerradas = new[] { EstadoDeLaFila.Aprobada, EstadoDeLaFila.RechazadaEnAS400, EstadoDeLaFila.Anulada, EstadoDeLaFila.RechazadaEnValidacion, EstadoDeLaFila.SinAutorizacion };
            Assert.True(CierreDeSolicitud.CorrespondeProcesar(EstadoDeLaSolicitud.EnProceso, cerradas));
            Assert.False(CierreDeSolicitud.CorrespondeProcesar(EstadoDeLaSolicitud.EnProceso, cerradas.Concat(new[] { EstadoDeLaFila.Digitada })));
            Assert.False(CierreDeSolicitud.CorrespondeProcesar(EstadoDeLaSolicitud.EnProceso, new[] { EstadoDeLaFila.Validada }));
        }

        [Fact]
        public void Una_solicitud_que_no_esta_en_proceso_nunca_se_procesa()
        {
            var cerradas = new[] { EstadoDeLaFila.Aprobada };
            foreach (EstadoDeLaSolicitud e in Enum.GetValues(typeof(EstadoDeLaSolicitud)))
            {
                Assert.Equal(e == EstadoDeLaSolicitud.EnProceso, CierreDeSolicitud.CorrespondeProcesar(e, cerradas));
            }
        }

        [Fact]
        public void El_cierre_con_filas_nulas_es_un_error_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => CierreDeSolicitud.CorrespondeProcesar(EstadoDeLaSolicitud.EnProceso, null));
        }
    }
}
