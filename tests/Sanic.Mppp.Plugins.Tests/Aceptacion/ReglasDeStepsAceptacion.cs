using System;
using System.Linq;
using Sanic.Mppp.Plugins.Steps;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.8, 7.10 y 7.11: las decisiones puras de los steps (diseno/03 §5, diseno/04 §1). Sin Dataverse: se prueban solas.</summary>
    public class ReglasDeStepsAceptacion
    {
        // ------------------------------------------------------------------ 7.8 lista blanca
        [Fact]
        public void En_fila_una_persona_solo_puede_mandar_estado_y_mensaje()
        {
            Assert.Empty(ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new[] { "sanic_estado", "sanic_mensaje" }));
            Assert.Empty(ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new[] { "sanic_mppp_tbl_filaid", "sanic_estado" })); // la primaria no cuenta
            Assert.Equal(
                new[] { "sanic_numerocuenta", "sanic_planid" },
                ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new[] { "sanic_planid", "sanic_estado", "sanic_numerocuenta" }));
        }

        [Fact]
        public void En_solicitud_una_persona_solo_puede_mandar_requiere_revision_y_el_estado()
        {
            Assert.Empty(ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Solicitud, new[] { "sanic_requiererevision", "sanic_estadoprocesamiento" }));
            Assert.Equal(new[] { "sanic_acusecontenido" }, ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Solicitud, new[] { "sanic_acusecontenido" }));
            // Lo que se permite en una tabla no se permite en la otra.
            Assert.Equal(new[] { "sanic_mensaje" }, ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Solicitud, new[] { "sanic_mensaje" }));
            Assert.Equal(new[] { "sanic_requiererevision" }, ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new[] { "sanic_requiererevision" }));
        }

        [Fact]
        public void Una_tabla_que_no_se_controla_y_los_casos_de_borde()
        {
            Assert.Empty(ListaBlancaDeColumnas.ColumnasNoPermitidas("sanic_mppp_tbl_plan", new[] { "sanic_codigo" }));
            Assert.Empty(ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new string[0]));
            Assert.Equal(new[] { "SANIC_ESTADO" }, ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, new[] { "SANIC_ESTADO" })); // ordinal: Dataverse manda minúscula
            Assert.Throws<ArgumentNullException>(() => ListaBlancaDeColumnas.ColumnasNoPermitidas(ListaBlancaDeColumnas.Fila, null));
        }

        // ------------------------------------------------------------------ 7.10 normalizar y validar
        [Theory]
        [InlineData("123456789", "123456789")]
        [InlineData("1234", "000001234")]
        [InlineData("  1234  ", "000001234")]
        [InlineData("0", "000000000")]
        public void El_cif_bac_se_rellena_con_ceros_hasta_nueve(string recibido, string esperado)
        {
            Assert.Equal(esperado, Normalizacion.CifBac(recibido));
        }

        [Theory]
        [InlineData("1234567890")] // más de 9
        [InlineData("12A456789")]
        [InlineData("12 456789")]
        [InlineData("١٢٣٤")] // dígitos que no son ASCII
        public void Un_cif_bac_que_no_son_nueve_digitos_es_un_error(string recibido)
        {
            var ex = Assert.Throws<ArgumentException>(() => Normalizacion.CifBac(recibido));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        [Theory]
        [InlineData("abc123xy9012", "ABC123XY9012")]
        [InlineData("  ABC12 XY9 012  ", "ABC12 XY9 012")] // 9 con espacio + 3 dígitos
        public void El_cif_com_va_en_mayuscula_y_con_su_formato(string recibido, string esperado)
        {
            Assert.Equal(esperado, Normalizacion.CifCom(recibido));
        }

        [Theory]
        [InlineData("ABC123XY901")] // 11
        [InlineData("ABC123XY90123")] // 13
        [InlineData("ABC123XY9A12")] // los últimos tres tienen que ser dígitos
        [InlineData("ABC-23XY9012")] // guion no
        public void Un_cif_com_con_otro_formato_es_un_error(string recibido)
        {
            Assert.Throws<ArgumentException>(() => Normalizacion.CifCom(recibido));
        }

        [Theory]
        [InlineData("42", "0042")]
        [InlineData("a1", "00A1")]
        [InlineData("  00a1 ", "00A1")]
        [InlineData("ABCD", "ABCD")]
        public void El_codigo_de_plan_va_en_mayuscula_y_relleno_a_cuatro(string recibido, string esperado)
        {
            Assert.Equal(esperado, Normalizacion.CodigoDePlan(recibido));
        }

        [Theory]
        [InlineData("00042")] // 5
        [InlineData("00-1")]
        [InlineData("0 42")]
        [InlineData("００４２")]
        public void Un_codigo_de_plan_que_no_cumple_es_un_error(string recibido)
        {
            Assert.Throws<ArgumentException>(() => Normalizacion.CodigoDePlan(recibido));
        }

        [Theory]
        [InlineData("  Ana@ACME.com ", "ana@acme.com")]
        [InlineData("a.b-c+d@sub.dominio.com", "a.b-c+d@sub.dominio.com")]
        public void El_correo_del_autorizado_va_sin_espacios_y_en_minuscula(string recibido, string esperado)
        {
            Assert.Equal(esperado, Normalizacion.CorreoAutorizado(recibido));
        }

        [Theory]
        [InlineData("sin-arroba.com")]
        [InlineData("dos@@acme.com")]
        [InlineData("con espacio@acme.com")]
        [InlineData("@acme.com")]
        [InlineData("ana@")]
        [InlineData("ana@acme")] // sin punto en el dominio
        public void Un_correo_que_no_tiene_forma_de_correo_es_un_error(string recibido)
        {
            Assert.Throws<ArgumentException>(() => Normalizacion.CorreoAutorizado(recibido));
        }

        [Theory]
        [InlineData("  Plantilla.Listas  ", "plantilla.listas")]
        [InlineData("vigilancia.minutos.sinvalidar", "vigilancia.minutos.sinvalidar")]
        [InlineData("rpa.puedeaprobar", "rpa.puedeaprobar")]
        public void El_nombre_de_un_parametro_va_en_minuscula_y_separado_por_puntos(string recibido, string esperado)
        {
            Assert.Equal(esperado, Normalizacion.NombreDeParametro(recibido));
        }

        [Theory]
        [InlineData(".plantilla")]
        [InlineData("plantilla.")]
        [InlineData("plantilla..listas")]
        [InlineData("plantilla listas")]
        [InlineData("plantilla_listas")]
        [InlineData("plantilla-listas")]
        [InlineData("plantílla.listas")]
        public void Un_nombre_de_parametro_mal_armado_es_un_error(string recibido)
        {
            Assert.Throws<ArgumentException>(() => Normalizacion.NombreDeParametro(recibido));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void Lo_que_viene_vacio_no_se_normaliza_y_no_es_error(string vacio)
        {
            Assert.Null(Normalizacion.CifBac(vacio));
            Assert.Null(Normalizacion.CifCom(vacio));
            Assert.Null(Normalizacion.CodigoDePlan(vacio));
            Assert.Null(Normalizacion.CorreoAutorizado(vacio));
            Assert.Null(Normalizacion.NombreDeParametro(vacio));
        }

        // ------------------------------------------------------------------ 7.11 nombre calculado
        [Fact]
        public void Los_nombres_calculados_siguen_el_diccionario_y_se_recortan()
        {
            Assert.Equal("0042 - ACME S.A.", NombreCalculado.DePlan("0042", "ACME S.A."));
            Assert.Equal("0042", NombreCalculado.DePlan("0042", null));
            Assert.Equal("ana@acme.com → 0042", NombreCalculado.DeAutorizacionPlan("ana@acme.com", "0042"));
            Assert.Equal("MPPP-00000123-F01", NombreCalculado.DeFila("MPPP-00000123", 1));
            Assert.Equal("MPPP-00000123-F100", NombreCalculado.DeFila("MPPP-00000123", 100));

            Assert.Equal(100, NombreCalculado.DePlan("0042", new string('c', 300)).Length);
            Assert.Equal(400, NombreCalculado.DeAutorizacionPlan(new string('a', 500) + "@x.com", "0042").Length);
            Assert.Equal(120, NombreCalculado.DeFila(new string('s', 200), 7).Length);
        }

        [Fact]
        public void Un_nombre_calculado_sin_lo_minimo_es_un_error_de_programacion()
        {
            Assert.Throws<ArgumentException>(() => NombreCalculado.DePlan(" ", "ACME"));
            Assert.Throws<ArgumentException>(() => NombreCalculado.DeAutorizacionPlan(null, "0042"));
            Assert.Throws<ArgumentException>(() => NombreCalculado.DeAutorizacionPlan("ana@acme.com", " "));
            Assert.Throws<ArgumentException>(() => NombreCalculado.DeFila(null, 1));
            Assert.Throws<ArgumentOutOfRangeException>(() => NombreCalculado.DeFila("MPPP-1", 0));
        }
    }
}
