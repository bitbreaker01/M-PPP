using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// D-19 (aprobador, 2026-09-21): `sanic_mensajecliente` es una plantilla con marcadores. El negocio cambia la redacción sin tocar
    /// código, y el código nunca depende de que la redacción exista ni de que esté bien escrita.
    /// </summary>
    public class MensajeAlClienteAceptacion
    {
        private const string PorDefecto = "El valor recibido no es válido.";

        private static Veredicto Falla(string precision = null, params (string marcador, string valor)[] marcadores)
        {
            return Veredicto.NoCumplida(PorDefecto, marcadores.ToDictionary(m => m.marcador, m => m.valor), precision);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void Sin_plantilla_en_el_catalogo_rige_el_texto_por_defecto_del_evaluador(string plantilla)
        {
            Assert.Equal(PorDefecto, MensajeAlCliente.Componer(plantilla, Falla(null, ("valor", "XYZ")), "LISTAS_VALIDAS"));
        }

        [Fact]
        public void La_plantilla_se_completa_con_los_marcadores_del_evaluador_y_con_la_regla_que_pone_el_motor()
        {
            var v = Falla(null, ("valor", "Dolarez"), ("campo", "Moneda"), ("plan", "0042"));
            Assert.Equal(
                "El campo Moneda trae 'Dolarez', que no se acepta en el plan 0042 (LISTAS_VALIDAS). Revise Moneda.",
                MensajeAlCliente.Componer("El campo {campo} trae '{valor}', que no se acepta en el plan {plan} ({regla}). Revise {campo}.", v, "LISTAS_VALIDAS"));
        }

        [Fact]
        public void Una_plantilla_sin_marcadores_se_usa_tal_cual_recortada()
        {
            Assert.Equal("Adjunte un archivo.", MensajeAlCliente.Componer("  Adjunte un archivo.  ", Falla(), "TRAE_ADJUNTO"));
        }

        [Theory]
        [InlineData("El valor {plna} no existe.")] // error de tipeo
        [InlineData("El valor {VALOR} no existe.")] // los marcadores son exactos
        [InlineData("El valor { valor } no existe.")]
        [InlineData("El valor {valor no existe.")] // llave suelta
        [InlineData("El valor valor} no existe.")]
        [InlineData("El valor {} no existe.")]
        [InlineData("El valor {{valor}} no existe.")]
        [InlineData("El plan {plan} no existe.")] // marcador real, pero ESTE evaluador no lo sabe completar
        public void Una_plantilla_con_cualquier_llave_que_nadie_sabe_completar_no_se_usa_rige_el_por_defecto(string plantilla)
        {
            Assert.Equal(PorDefecto, MensajeAlCliente.Componer(plantilla, Falla(null, ("valor", "XYZ")), "LISTAS_VALIDAS"));
        }

        [Fact]
        public void Los_valores_vienen_del_excel_del_cliente_se_insertan_tal_cual_y_no_se_vuelven_a_expandir()
        {
            var v = Falla(null, ("valor", "{plan} y {regla} y {"), ("plan", "SECRETO"));
            Assert.Equal("Recibido: {plan} y {regla} y {. Plan SECRETO.", MensajeAlCliente.Componer("Recibido: {valor}. Plan {plan}.", v, "R"));
        }

        [Fact]
        public void El_marcador_regla_es_del_motor_aunque_el_evaluador_traiga_uno_propio()
        {
            Assert.Equal("Regla PLAN_EXISTE.", MensajeAlCliente.Componer("Regla {regla}.", Falla(null, ("regla", "OTRA")), "PLAN_EXISTE"));
        }

        [Fact]
        public void Un_marcador_conocido_con_valor_nulo_se_completa_con_vacio_y_si_el_texto_queda_en_blanco_rige_el_por_defecto()
        {
            Assert.Equal("Recibido: ''.", MensajeAlCliente.Componer("Recibido: '{valor}'.", Falla(null, ("valor", null)), "R"));
            Assert.Equal(PorDefecto, MensajeAlCliente.Componer(" {valor} ", Falla(null, ("valor", "  ")), "R"));
        }

        [Fact]
        public void La_precision_del_evaluador_se_agrega_al_final_venga_el_texto_del_catalogo_o_sea_el_por_defecto()
        {
            var v = Falla("  La hoja 'Datos' no existe.  ");
            Assert.Equal("La plantilla no es la vigente. La hoja 'Datos' no existe.", MensajeAlCliente.Componer("La plantilla no es la vigente.", v, "ESTRUCTURA_PLANTILLA"));
            Assert.Equal(PorDefecto + " La hoja 'Datos' no existe.", MensajeAlCliente.Componer(null, v, "ESTRUCTURA_PLANTILLA"));
            Assert.Equal(PorDefecto + " La hoja 'Datos' no existe.", MensajeAlCliente.Componer("Mal {escrita}.", v, "ESTRUCTURA_PLANTILLA"));
            Assert.Equal(PorDefecto, MensajeAlCliente.Componer(null, Falla("   "), "R"));
        }

        [Fact]
        public void La_precision_tampoco_se_expande()
        {
            Assert.Equal("Texto R. Detalle {regla} {valor}", MensajeAlCliente.Componer("Texto {regla}.", Falla("Detalle {regla} {valor}", ("valor", "X")), "R"));
        }

        [Fact]
        public void Pedir_el_mensaje_de_algo_que_no_fallo_o_sin_regla_es_un_error_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => MensajeAlCliente.Componer("x", null, "R"));
            Assert.Throws<ArgumentException>(() => MensajeAlCliente.Componer("x", Veredicto.Cumplida(), "R"));
            Assert.Throws<ArgumentException>(() => MensajeAlCliente.Componer("x", Falla(), " "));
            Assert.Throws<ArgumentException>(() => MensajeAlCliente.Componer("x", Falla(), null));
        }

        [Fact]
        public void El_veredicto_guarda_una_copia_de_los_marcadores_nunca_nula_y_descarta_la_precision_en_blanco()
        {
            var marcadores = new Dictionary<string, string> { ["valor"] = "A" };
            var v = Veredicto.NoCumplida(PorDefecto, marcadores, " ");
            marcadores["valor"] = "CAMBIADO";
            Assert.Equal("A", v.Marcadores["valor"]);
            Assert.Null(v.Precision);
            Assert.Empty(Veredicto.NoCumplida(PorDefecto).Marcadores);
            Assert.Empty(Veredicto.Cumplida().Marcadores);
            Assert.Throws<ArgumentException>(() => Veredicto.NoCumplida(" ", marcadores, "precisión"));
        }

        // ------------------------------------------------------------------ el motor usa la plantilla del catálogo
        private sealed class EvaluadorQueFalla : IEvaluador<object>
        {
            public EvaluadorQueFalla(string codigo)
            {
                Codigo = codigo;
            }

            public string Codigo { get; }

            public Veredicto Evaluar(object contexto) => Falla("Detalle.", ("valor", "XYZ"));
        }

        [Fact]
        public void El_motor_compone_la_razon_de_una_no_cumplida_con_la_plantilla_de_su_regla_y_la_omitida_sigue_nombrando_a_quien_la_bloqueo()
        {
            var motor = new MotorDeReglas<object>(new[] { new EvaluadorQueFalla("A"), new EvaluadorQueFalla("B"), new EvaluadorQueFalla("C") });
            var reglas = new[]
            {
                new DefinicionDeRegla { Codigo = "A", Orden = 1, Efecto = EfectoDeLaRegla.Rechaza, MensajeCliente = "Valor '{valor}' rechazado por {regla}." },
                new DefinicionDeRegla { Codigo = "B", Orden = 2, Efecto = EfectoDeLaRegla.Advierte, MensajeCliente = "Mal {escrita}." },
                new DefinicionDeRegla { Codigo = "C", Orden = 3, Efecto = EfectoDeLaRegla.Rechaza, DependeDe = new[] { "A" }, MensajeCliente = "Nunca se usa: {valor}." },
            };

            var rs = motor.Evaluar(reglas, new object());

            Assert.Equal("Valor 'XYZ' rechazado por A. Detalle.", rs[0].Razon);
            Assert.Equal(PorDefecto + " Detalle.", rs[1].Razon);
            Assert.Equal(ResultadoDeLaRegla.Omitida, rs[2].Resultado);
            Assert.Contains("A", rs[2].Razon);
            Assert.DoesNotContain("Nunca se usa", rs[2].Razon);
        }
    }
}
