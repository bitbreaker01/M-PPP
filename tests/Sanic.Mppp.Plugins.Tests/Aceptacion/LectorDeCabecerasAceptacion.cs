using System;
using System.Linq;
using System.Text;
using Sanic.Mppp.Plugins.Correo;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.6b: las cabeceras de un `.eml` son entrada no confiable (diseno/03 §0 paso 2). Nunca se lee el cuerpo; ante la duda, ilegible.</summary>
    public class LectorDeCabecerasAceptacion
    {
        private static byte[] B(string texto) => Encoding.UTF8.GetBytes(texto);

        private const string Nuevo = "From: ana@acme.com\r\nTo: pagos@banco.com\r\nSubject: Inclusiones plan 0042\r\nDate: Mon, 21 Sep 2026 10:00:00 -0600\r\n\r\nCuerpo del correo\r\nIn-Reply-To: <esto-esta-en-el-cuerpo@x>\r\n";

        [Fact]
        public void Un_correo_nuevo_trae_su_asunto_y_ninguna_referencia_y_el_cuerpo_no_se_mira()
        {
            var c = LectorDeCabeceras.Leer(B(Nuevo));
            Assert.True(c.Legibles);
            Assert.Equal("Inclusiones plan 0042", c.Asunto);
            Assert.False(c.TraeInReplyTo);
            Assert.False(c.TraeReferences); // el In-Reply-To del cuerpo NO cuenta
            Assert.False(c.TraeReferenciasAOtroCorreo);
        }

        [Theory]
        [InlineData("In-Reply-To: <a@b>\r\n", true, false)]
        [InlineData("References: <a@b> <c@d>\r\n", false, true)]
        [InlineData("in-reply-to: <a@b>\r\nREFERENCES: <c@d>\r\n", true, true)] // sin distinguir mayúsculas
        [InlineData("In-Reply-To:   \r\n", false, false)] // vacía: no cuenta
        [InlineData("References:\r\n", false, false)]
        [InlineData("In-Reply-To:\r\n <a@b>\r\n", true, false)] // el valor viene en la línea de continuación
        public void Las_referencias_a_otro_correo_cuentan_solo_con_contenido(string cabecera, bool inReplyTo, bool references)
        {
            var c = LectorDeCabeceras.Leer(B("Subject: x\r\n" + cabecera + "\r\ncuerpo"));
            Assert.True(c.Legibles);
            Assert.Equal((inReplyTo, references), (c.TraeInReplyTo, c.TraeReferences));
        }

        [Theory]
        [InlineData("Subject: FW: Inclusiones\r\n\tplan 0042\r\n\r\n", "FW: Inclusiones plan 0042")] // plegado con tabulador
        [InlineData("Subject: RV:\r\n  Inclusiones\r\n\r\n", "RV: Inclusiones")]
        [InlineData("Subject: =?UTF-8?B?UlY6IEluY2x1c2nDs24=?=\r\n\r\n", "RV: Inclusión")] // RFC 2047, base64
        [InlineData("Subject: =?iso-8859-1?Q?RV=3A_Inclusi=F3n?=\r\n\r\n", "RV: Inclusión")] // RFC 2047, quoted-printable
        [InlineData("Subject: =?utf-8?q?FW=3A?= =?utf-8?q?_plan?=\r\n\r\n", "FW: plan")] // dos palabras codificadas seguidas: el espacio entre ellas no cuenta
        [InlineData("Subject:    con espacios   \r\n\r\n", "con espacios")]
        [InlineData("Subject: =?utf-8?B?%%%rota?=\r\n\r\n", "=?utf-8?B?%%%rota?=")] // rota: tal cual, sin reventar
        [InlineData("Subject: primero\r\nSubject: segundo\r\n\r\n", "primero")] // repetida: la primera
        [InlineData("From: a@b\r\n\r\n", "")] // sin asunto
        public void El_asunto_se_pliega_y_se_decodifica(string cabeceras, string esperado)
        {
            Assert.Equal(esperado, LectorDeCabeceras.Leer(B(cabeceras)).Asunto);
        }

        [Fact]
        public void El_fin_de_cabeceras_tambien_puede_ser_solo_lf()
        {
            var c = LectorDeCabeceras.Leer(B("Subject: x\nIn-Reply-To: <a@b>\n\ncuerpo\n"));
            Assert.True(c.Legibles);
            Assert.Equal("x", c.Asunto);
            Assert.True(c.TraeInReplyTo);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("Subject: sin fin de cabeceras\r\nFrom: a@b\r\n")] // nunca llega la línea en blanco
        [InlineData("esto no es una cabecera\r\n\r\n")] // ninguna línea Nombre: valor
        [InlineData("\r\n\r\nSubject: tarde\r\n")] // empieza por el cuerpo
        [InlineData("PK\u0003\u0004binario")] // un zip disfrazado
        public void Lo_que_no_se_puede_leer_es_ilegible_y_nunca_revienta(string contenido)
        {
            var c = LectorDeCabeceras.Leer(contenido == null ? null : B(contenido));
            Assert.False(c.Legibles);
            Assert.Equal(string.Empty, c.Asunto);
            Assert.False(c.TraeReferenciasAOtroCorreo);
        }

        [Fact]
        public void Bytes_que_no_son_utf8_valido_no_revientan()
        {
            var basura = Enumerable.Range(0, 3000).Select(i => (byte)(0x80 + i % 64)).ToArray();
            var c = LectorDeCabeceras.Leer(basura);
            Assert.False(c.Legibles);

            var mezcla = B("Subject: ok\r\nX-Raro: ").Concat(basura).Concat(B("\r\n\r\n")).ToArray();
            var c2 = LectorDeCabeceras.Leer(mezcla);
            Assert.True(c2.Legibles);
            Assert.Equal("ok", c2.Asunto);
        }

        [Fact]
        public void Solo_se_miran_los_primeros_256_kb_y_una_cabecera_enorme_no_es_un_problema()
        {
            Assert.Equal(256 * 1024, LectorDeCabeceras.TopeBytes);
            var enorme = "Subject: x\r\nX-Larga: " + new string('a', 300 * 1024) + "\r\n\r\ncuerpo";
            Assert.False(LectorDeCabeceras.Leer(B(enorme)).Legibles); // el fin de cabeceras queda más allá del tope

            var dentro = "Subject: x\r\nX-Larga: " + new string('a', 100 * 1024) + "\r\n\r\n" + new string('z', 500 * 1024);
            var c = LectorDeCabeceras.Leer(B(dentro));
            Assert.True(c.Legibles);
            Assert.Equal("x", c.Asunto);
        }

        // ------------------------------------------------------------------ revisión de código, 2026-09-21
        [Theory]
        [InlineData("Subject: hola\rIn-Reply-To: <x@y>\r\n\r\n")] // CR suelto: NO puede esconder la referencia
        [InlineData("Subject: hola\rReferences: <x@y>\n\n")]
        [InlineData("Subject: hola\rIn-Reply-To: <x@y>\r\r")] // y un CR CR también cierra las cabeceras
        public void Un_retorno_de_carro_suelto_no_esconde_una_respuesta_dentro_de_otra_cabecera(string eml)
        {
            // DF-08: "una respuesta no se procesa nunca". Si un CR suelto fundiera dos cabeceras, una respuesta se leería
            // como correo nuevo y entraría a validarse: es la dirección peligrosa del error.
            var c = LectorDeCabeceras.Leer(B(eml));
            Assert.True(c.TraeReferenciasAOtroCorreo);
            Assert.DoesNotContain("In-Reply-To", c.Asunto);
            Assert.DoesNotContain("References", c.Asunto);
        }

        [Fact]
        public void Miles_de_lineas_de_continuacion_no_hacen_al_lector_cuadratico()
        {
            // "Es liviano de verdad... corre en milisegundos" (03 §0). El .eml viene de afuera del banco.
            var hostil = "Subject: x\r\n" + string.Concat(Enumerable.Repeat(" a\r\n", 60000)) + "In-Reply-To: <a@b>\r\n\r\n";
            var reloj = System.Diagnostics.Stopwatch.StartNew();
            var c = LectorDeCabeceras.Leer(B(hostil));
            reloj.Stop();
            Assert.True(c.Legibles);
            Assert.True(reloj.ElapsedMilliseconds < 2000, $"tardó {reloj.ElapsedMilliseconds} ms");
        }

        [Fact]
        public void Miles_de_palabras_codificadas_sin_cierre_no_hacen_al_lector_cuadratico()
        {
            var hostil = "Subject: " + string.Concat(Enumerable.Repeat("=?utf-8?B?X", 20000)) + "\r\n\r\n";
            var reloj = System.Diagnostics.Stopwatch.StartNew();
            var c = LectorDeCabeceras.Leer(B(hostil));
            reloj.Stop();
            Assert.True(c.Legibles);
            Assert.True(reloj.ElapsedMilliseconds < 2000, $"tardó {reloj.ElapsedMilliseconds} ms");
        }

        [Fact]
        public void Una_cabecera_con_nombre_vacio_o_solo_dos_puntos_no_rompe_la_lectura()
        {
            var c = LectorDeCabeceras.Leer(B(": sin nombre\r\nSubject: x\r\n:\r\n\r\n"));
            Assert.True(c.Legibles);
            Assert.Equal("x", c.Asunto);
        }
    }
}
