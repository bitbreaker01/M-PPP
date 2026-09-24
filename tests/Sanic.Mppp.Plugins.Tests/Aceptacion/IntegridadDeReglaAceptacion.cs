using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Steps;
using Sanic.Mppp.Plugins.Validacion;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// 7.10, integridad del catálogo de Reglas: el control PREVENTIVO al guardar. El motor ya falla cerrado en tiempo de
    /// ejecución; lo que se prueba acá es que un catálogo mal armado no llegue siquiera a guardarse, para que quien lo edita
    /// se entere en el momento y no cuando dejan de procesarse las solicitudes.
    /// </summary>
    public class IntegridadDeReglaAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 22, 9, 0, 0, DateTimeKind.Utc);

        private const string Codigo = "sanic_codigo";
        private const string Nivel = "sanic_nivel";
        private const string Orden = "sanic_orden";
        private const string DependeDe = "sanic_dependede";
        private const string Efecto = "sanic_efecto";
        private const string Estado = "statecode";

        private static Entity Regla(string codigo, NivelDeLaRegla nivel, int orden, string dependeDe = null,
            EfectoDeLaRegla efecto = EfectoDeLaRegla.Rechaza, int estado = 0, Guid? id = null)
        {
            var e = new Entity(Tablas.Regla)
            {
                [Codigo] = codigo,
                [Nivel] = new OptionSetValue((int)nivel),
                [Orden] = orden,
                [Efecto] = new OptionSetValue((int)efecto),
                [Estado] = new OptionSetValue(estado),
            };
            if (dependeDe != null)
            {
                e[DependeDe] = dependeDe;
            }

            if (id.HasValue)
            {
                e.Id = id.Value;
            }

            return e;
        }

        private sealed class Mundo
        {
            public readonly OrganizationServiceEnMemoria Svc = new OrganizationServiceEnMemoria();
            public readonly ContextoDePluginSimulado Ctx;

            public Mundo(params Entity[] catalogo)
            {
                foreach (var regla in catalogo)
                {
                    Svc.Sembrar(regla);
                }

                Ctx = new ContextoDePluginSimulado(Svc, Ahora);
                Ctx.Contexto.PrimaryEntityName = Tablas.Regla;
                Ctx.Contexto.MessageName = "Create";
                Ctx.Contexto.Stage = 20;
            }

            public Mundo Guardando(Entity target, Entity preImagen = null, string mensaje = "Create")
            {
                Ctx.Contexto.MessageName = mensaje;
                Ctx.Contexto.InputParameters["Target"] = target;
                if (preImagen != null)
                {
                    Ctx.Contexto.PreEntityImages["PreImage"] = preImagen;
                }

                return this;
            }

            public void Ejecutar() => new IntegridadDeReglaStep().Execute(Ctx);

            public InvalidPluginExecutionException Rechaza() =>
                Assert.Throws<InvalidPluginExecutionException>(() => Ejecutar());
        }

        /// <summary>Un catálogo de nivel Registro razonable, con los códigos que el código C# sí tiene.</summary>
        private static Entity[] CatalogoRegistro() => new[]
        {
            Regla(ReglasDeRegistro.ListasValidas, NivelDeLaRegla.Registro, 10),
            Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30),
        };

        // ------------------------------------------------------------------ el camino feliz
        [Fact]
        public void Una_regla_bien_armada_se_guarda_sin_ruido()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.Formato11SoloAch, NivelDeLaRegla.Registro, 40,
                $"{ReglasDeRegistro.PlanExiste},{ReglasDeRegistro.ListasValidas}"));

            m.Ejecutar(); // no lanza

            // El step NO escribe: solo deja pasar o rechaza.
            Assert.Empty(m.Svc.Registros(Tablas.Regla).Where(r => r.GetAttributeValue<string>(Codigo) == ReglasDeRegistro.Formato11SoloAch));
        }

        [Fact]
        public void Una_sola_consulta_al_catalogo_por_ejecucion()
        {
            // El catálogo se lee UNA vez: el step corre en cada guardado de regla.
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste));
            var antes = m.Svc.Llamadas.Count;

            m.Ejecutar();

            Assert.Equal(1, m.Svc.Llamadas.Count - antes);
        }

        // ------------------------------------------------------------------ D-13: el código tiene que tener evaluador
        [Fact]
        public void Un_codigo_sin_evaluador_en_el_codigo_no_se_puede_guardar()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla("REGLA_QUE_NADIE_PROGRAMO", NivelDeLaRegla.Registro, 90));

            var ex = m.Rechaza();

            Assert.Contains("REGLA_QUE_NADIE_PROGRAMO", ex.Message);
            // El mensaje lo lee un administrador técnico: le decimos cuáles SÍ valen.
            Assert.Contains(ReglasDeRegistro.PlanExiste, ex.Message);
        }

        [Fact]
        public void Un_codigo_de_otro_nivel_no_se_puede_guardar_en_este()
        {
            // TRAE_ADJUNTO existe, pero su evaluador es de nivel Solicitud, no Registro.
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDelSobre.TraeAdjunto, NivelDeLaRegla.Registro, 90));

            var ex = m.Rechaza();

            Assert.Contains(ReglasDelSobre.TraeAdjunto, ex.Message);
        }

        [Fact]
        public void Los_tres_niveles_reconocen_sus_propios_codigos()
        {
            foreach (var (codigo, nivel) in new[]
            {
                (ReglasDeRegistro.ListasValidas, NivelDeLaRegla.Registro),
                (ReglasDelSobre.TraeAdjunto, NivelDeLaRegla.Solicitud),
            })
            {
                var m = new Mundo();
                m.Guardando(Regla(codigo, nivel, 10));
                m.Ejecutar(); // no lanza
            }
        }

        // ------------------------------------------------------------------ D-20: Envía a revisión nunca en Registro
        [Fact]
        public void Envia_a_revision_no_se_admite_en_nivel_Registro()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60,
                efecto: EfectoDeLaRegla.EnviaARevision));

            var ex = m.Rechaza();

            Assert.Contains("revis", ex.Message, StringComparison.OrdinalIgnoreCase);
        }

        [Fact]
        public void Envia_a_revision_si_se_admite_en_el_sobre()
        {
            foreach (var (codigo, nivel) in new[]
            {
                (ReglasDelSobre.TraeAdjunto, NivelDeLaRegla.Solicitud),
            })
            {
                var m = new Mundo();
                m.Guardando(Regla(codigo, nivel, 10, efecto: EfectoDeLaRegla.EnviaARevision));
                m.Ejecutar(); // no lanza
            }
        }

        // ------------------------------------------------------------------ D-14: AUTORIZACION_CORREO_PLAN solo Rechaza
        [Theory]
        [InlineData(EfectoDeLaRegla.Advierte)]
        [InlineData(EfectoDeLaRegla.EnviaARevision)]
        public void La_regla_de_autorizacion_no_admite_otro_efecto_que_rechaza(EfectoDeLaRegla efecto)
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.AutorizacionCorreoPlan, NivelDeLaRegla.Registro, 70,
                ReglasDeRegistro.PlanExiste, efecto));

            var ex = m.Rechaza();

            Assert.Contains(ReglasDeRegistro.AutorizacionCorreoPlan, ex.Message);
        }

        [Fact]
        public void La_regla_de_autorizacion_con_rechaza_se_guarda()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.AutorizacionCorreoPlan, NivelDeLaRegla.Registro, 70,
                ReglasDeRegistro.PlanExiste, EfectoDeLaRegla.Rechaza));

            m.Ejecutar(); // no lanza
        }

        // ------------------------------------------------------------------ dependencias (02 §152)
        [Fact]
        public void Una_dependencia_que_no_existe_se_rechaza_nombrandola()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, "NO_EXISTE"));

            Assert.Contains("NO_EXISTE", m.Rechaza().Message);
        }

        [Fact]
        public void Una_dependencia_de_otro_nivel_se_rechaza()
        {
            var m = new Mundo(
                Regla(ReglasDelSobre.TraeAdjunto, NivelDeLaRegla.Solicitud, 10),
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30));
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDelSobre.TraeAdjunto));

            Assert.Contains(ReglasDelSobre.TraeAdjunto, m.Rechaza().Message);
        }

        [Theory]
        [InlineData(30)] // igual que la dependencia
        [InlineData(20)] // menor que la dependencia
        public void Una_dependencia_con_orden_mayor_o_igual_se_rechaza(int orden)
        {
            // El orden estrictamente menor es lo que hace imposible un ciclo.
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, orden, ReglasDeRegistro.PlanExiste));

            Assert.Contains("orden", m.Rechaza().Message, StringComparison.OrdinalIgnoreCase);
        }

        [Fact]
        public void Una_regla_no_puede_depender_de_si_misma()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, ReglasDeRegistro.PlanExiste));

            Assert.Throws<InvalidPluginExecutionException>(() => m.Ejecutar());
        }

        [Fact]
        public void Una_regla_no_puede_depender_de_si_misma_ni_subiendo_su_orden_en_el_mismo_guardado()
        {
            // El agujero que destapó la revisión del 2026-09-22: el catálogo que se consulta trae el estado YA
            // COMMITTEADO, o sea el orden VIEJO. Si el mismo Update sube el orden Y agrega la autodependencia, comparar
            // "orden viejo >= orden nuevo" da false y deja pasar un ciclo de tamaño uno. La autodependencia hay que
            // rechazarla por el CÓDIGO, antes de mirar ningún orden.
            var id = Guid.NewGuid();
            var m = new Mundo(
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id),
                Regla(ReglasDeRegistro.ListasValidas, NivelDeLaRegla.Registro, 10));
            var pre = Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id);
            var target = new Entity(Tablas.Regla, id)
            {
                [Orden] = 100,                                  // sube el orden...
                [DependeDe] = ReglasDeRegistro.PlanExiste,      // ...y se referencia a sí misma
            };

            var ex = m.Guardando(target, pre, "Update").Rechaza();

            Assert.Contains(ReglasDeRegistro.PlanExiste, ex.Message);
        }

        [Fact]
        public void La_autodependencia_se_rechaza_tambien_en_un_create_con_orden_alto()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 999, ReglasDeRegistro.MonedaDelPlan));

            Assert.Throws<InvalidPluginExecutionException>(() => m.Ejecutar());
        }

        [Fact]
        public void Una_dependencia_inactiva_se_rechaza()
        {
            var m = new Mundo(
                Regla(ReglasDeRegistro.ListasValidas, NivelDeLaRegla.Registro, 10),
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, estado: 1));
            m.Guardando(Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste));

            Assert.Contains(ReglasDeRegistro.PlanExiste, m.Rechaza().Message);
        }

        [Fact]
        public void La_lista_de_dependencias_tolera_espacios_y_entradas_vacias()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Guardando(Regla(ReglasDeRegistro.Formato11SoloAch, NivelDeLaRegla.Registro, 40,
                $" {ReglasDeRegistro.PlanExiste} , ,{ReglasDeRegistro.ListasValidas} "));

            m.Ejecutar(); // no lanza
        }

        // ------------------------------------------------------------------ Update parcial con pre-image
        [Fact]
        public void Un_update_que_solo_trae_el_orden_se_valida_con_la_regla_entera()
        {
            // El Target no dice ni el código ni el nivel: sin la pre-image no habría nada que validar.
            var id = Guid.NewGuid();
            var m = new Mundo(CatalogoRegistro());
            var pre = Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste, id: id);
            var target = new Entity(Tablas.Regla, id) { [Orden] = 20 }; // 20 < 30, el orden de PLAN_EXISTE

            m.Guardando(target, pre, "Update");

            Assert.Contains("orden", m.Rechaza().Message, StringComparison.OrdinalIgnoreCase);
        }

        [Fact]
        public void Un_update_que_corrige_el_orden_a_uno_valido_pasa()
        {
            var id = Guid.NewGuid();
            var m = new Mundo(CatalogoRegistro());
            var pre = Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 20, ReglasDeRegistro.PlanExiste, id: id);
            var target = new Entity(Tablas.Regla, id) { [Orden] = 60 };

            m.Guardando(target, pre, "Update").Ejecutar(); // no lanza
        }

        // ------------------------------------------------------------------ D-13: desactivar
        [Fact]
        public void No_se_puede_desactivar_una_regla_de_la_que_dependen_otras_activas()
        {
            var id = Guid.NewGuid();
            var m = new Mundo(
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id),
                Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste));
            var pre = Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id);
            var target = new Entity(Tablas.Regla, id) { [Estado] = new OptionSetValue(1) };

            var ex = m.Guardando(target, pre, "Update").Rechaza();

            // El mensaje nombra QUIÉN depende: sin eso el administrador no sabe qué tocar.
            Assert.Contains(ReglasDeRegistro.MonedaDelPlan, ex.Message);
        }

        [Fact]
        public void Se_puede_desactivar_una_regla_de_la_que_nadie_depende()
        {
            var id = Guid.NewGuid();
            var m = new Mundo(
                Regla(ReglasDeRegistro.ListasValidas, NivelDeLaRegla.Registro, 10),
                Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, id: id));
            var pre = Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, id: id);
            var target = new Entity(Tablas.Regla, id) { [Estado] = new OptionSetValue(1) };

            m.Guardando(target, pre, "Update").Ejecutar(); // no lanza
        }

        [Fact]
        public void Se_puede_desactivar_una_regla_si_quien_dependia_ya_esta_inactiva()
        {
            var id = Guid.NewGuid();
            var m = new Mundo(
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id),
                Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste, estado: 1));
            var pre = Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id);
            var target = new Entity(Tablas.Regla, id) { [Estado] = new OptionSetValue(1) };

            m.Guardando(target, pre, "Update").Ejecutar(); // no lanza
        }

        [Fact]
        public void La_dependencia_se_compara_por_codigo_completo_nunca_por_subcadena()
        {
            // `PLAN_EXISTE` NO está dependida por quien declara `PLAN_EXISTE_OTRO`.
            var id = Guid.NewGuid();
            var m = new Mundo(
                Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id),
                Regla(ReglasDeRegistro.MonedaDelPlan, NivelDeLaRegla.Registro, 60, ReglasDeRegistro.PlanExiste + "_OTRO"));
            var pre = Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30, id: id);
            var target = new Entity(Tablas.Regla, id) { [Estado] = new OptionSetValue(1) };

            m.Guardando(target, pre, "Update").Ejecutar(); // no lanza
        }

        // ------------------------------------------------------------------ plomería
        [Fact]
        public void El_control_corre_tambien_para_codigo_de_servidor()
        {
            // Un catálogo mal armado tumba la validación de TODAS las solicitudes, venga de donde venga.
            var m = new Mundo(CatalogoRegistro());
            m.Ctx.Contexto.Depth = 3;
            m.Guardando(Regla("REGLA_QUE_NADIE_PROGRAMO", NivelDeLaRegla.Registro, 90));

            Assert.Throws<InvalidPluginExecutionException>(() => m.Ejecutar());
        }

        [Fact]
        public void Un_target_de_otra_tabla_no_hace_nada()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Ctx.Contexto.InputParameters["Target"] = new Entity(Tablas.Plan) { ["sanic_codigo"] = "0042" };
            var antes = m.Svc.Llamadas.Count;

            m.Ejecutar(); // no lanza

            Assert.Equal(antes, m.Svc.Llamadas.Count); // ni siquiera consulta
        }

        [Fact]
        public void Un_proveedor_incompleto_no_revienta_con_una_referencia_nula()
        {
            Assert.Throws<InvalidPluginExecutionException>(() => new IntegridadDeReglaStep().Execute(null));
            foreach (var quitar in new[] { "contexto", "fabrica", "trace" })
            {
                var m = new Mundo(CatalogoRegistro());
                m.Guardando(Regla(ReglasDeRegistro.PlanExiste, NivelDeLaRegla.Registro, 30));
                m.Ctx.DaContexto = quitar != "contexto";
                m.Ctx.DaFabrica = quitar != "fabrica";
                m.Ctx.DaTrace = quitar != "trace";
                Assert.Throws<InvalidPluginExecutionException>(() => m.Ejecutar());
            }
        }

        [Fact]
        public void Sin_target_no_hace_nada()
        {
            var m = new Mundo(CatalogoRegistro());
            m.Ejecutar(); // no lanza
        }
    }
}
