using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Respuesta;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// 7.4 Respuesta: las dos comunicaciones al cliente (DD-08, DD-09; diseno/03 §1 paso 7 y §4 "Cierre"). Lo que se fija acá
    /// es lo que el cliente ve y, sobre todo, lo que NUNCA ve: la cuenta y la identificación completas, y etiquetas sin escapar.
    /// </summary>
    public class ArmadorRespuestaAceptacion
    {
        private const string Cuenta = "123456789012";
        private const string Identificacion = "0011234567890A";

        private static FilaParaRespuesta Fila(int numero, EstadoDeLaFila estado, string mensaje = null, string nombre = "Juan Perez", string plan = "0042")
        {
            return new FilaParaRespuesta
            {
                NumeroFila = numero, NumeroPlan = plan, NombreBeneficiario = nombre, NumeroCuenta = Cuenta, NumeroIdentificacion = Identificacion,
                Estado = estado, Mensaje = mensaje,
            };
        }

        private static SolicitudParaRespuesta Solicitud(EstadoDeLaSolicitud estado, params FilaParaRespuesta[] filas)
        {
            return new SolicitudParaRespuesta
            {
                Numero = "MPPP-00000123", FechaRecibidoTexto = "21/09/2026 10:15", Estado = estado, MotivosDelSobre = new List<string>(), Filas = filas.ToList(),
            };
        }

        private static readonly FilaParaRespuesta[] Mixtas =
        {
            Fila(2, EstadoDeLaFila.RechazadaEnValidacion, "Faltan datos obligatorios: Moneda."),
            Fila(1, EstadoDeLaFila.Validada),
            Fila(3, EstadoDeLaFila.SinAutorizacion, "Su correo no está autorizado sobre el plan 00A1.", plan: "A1"),
        };

        private static string SinEtiquetas(string html) => Regex.Replace(html, "<[^>]+>", " ");

        private static void NuncaSaleLoSensible(string html)
        {
            Assert.DoesNotContain(Cuenta, html);
            Assert.DoesNotContain(Identificacion, html);
            Assert.DoesNotContain("12345678", html); // ni un pedazo largo
            Assert.DoesNotContain("00112345", html);
        }

        // ------------------------------------------------------------------ enmascarado (DD-08)
        [Theory]
        [InlineData("123456789012", "********9012")]
        [InlineData("12345", "*2345")]
        [InlineData("1234", "****")]
        [InlineData("12", "**")]
        [InlineData("", "")]
        [InlineData(null, "")]
        [InlineData("  123456789  ", "*********89  ")] // tal cual vino: no se recorta (los espacios también se ven)
        [InlineData("J0310000000123", "**********0123")]
        public void La_cuenta_y_la_identificacion_se_enmascaran_a_los_ultimos_cuatro_caracteres(string valor, string esperado)
        {
            Assert.Equal(esperado, Enmascarado.Cuenta(valor));
            Assert.Equal(esperado, Enmascarado.Identificacion(valor));
        }

        // ------------------------------------------------------------------ estados en palabras del cliente
        [Fact]
        public void Cada_estado_de_fila_tiene_palabras_para_el_cliente_sin_jerga()
        {
            foreach (EstadoDeLaFila estado in Enum.GetValues(typeof(EstadoDeLaFila)))
            {
                var texto = ArmadorRespuesta.EstadoParaElCliente(estado);
                Assert.False(string.IsNullOrWhiteSpace(texto));
                Assert.DoesNotContain("_", texto);
                Assert.DoesNotContain("AS400", texto); // el cliente no sabe qué es AS400
            }

            Assert.Equal("Validada", ArmadorRespuesta.EstadoParaElCliente(EstadoDeLaFila.Validada));
            Assert.Equal("Sin autorización", ArmadorRespuesta.EstadoParaElCliente(EstadoDeLaFila.SinAutorizacion));
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.EstadoParaElCliente((EstadoDeLaFila)1));
        }

        // ------------------------------------------------------------------ el acuse de una En proceso
        [Fact]
        public void El_acuse_de_una_en_proceso_lista_las_filas_por_numero_con_su_estado_y_sus_motivos_y_anuncia_la_respuesta_final()
        {
            var html = ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.EnProceso, Mixtas));
            var texto = SinEtiquetas(html);

            Assert.StartsWith("<!DOCTYPE html>", html.TrimStart(), StringComparison.OrdinalIgnoreCase);
            Assert.Contains("</html>", html, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("MPPP-00000123", texto);
            Assert.Contains("21/09/2026 10:15", texto);
            Assert.Contains("<table", html);

            // Ordenadas por número, no como llegaron.
            var posiciones = new[] { "Validada", "Faltan datos obligatorios: Moneda.", "Su correo no está autorizado sobre el plan 00A1." }.Select(t => texto.IndexOf(t, StringComparison.Ordinal)).ToArray();
            Assert.All(posiciones, p => Assert.True(p >= 0));
            Assert.True(posiciones[0] < posiciones[1] && posiciones[1] < posiciones[2]);

            Assert.Contains("Rechazada en validación", texto);
            Assert.Contains("Sin autorización", texto);
            Assert.Contains("********9012", texto);
            Assert.Contains("0042", texto);
            Assert.Contains("Juan Perez", texto);
            Assert.Contains("respuesta final", texto, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("no hay nada que procesar", texto, StringComparison.OrdinalIgnoreCase);
            NuncaSaleLoSensible(html);
        }

        [Fact]
        public void El_acuse_trae_los_contadores()
        {
            var texto = SinEtiquetas(ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.EnProceso, Mixtas)));
            // 3 filas, 1 válida, 2 rechazadas: se dicen con números, para que el cliente coteje con su Excel.
            Assert.Matches(@"\b3\b", texto);
            Assert.Matches(@"\b1\b", texto);
            Assert.Matches(@"\b2\b", texto);
        }

        // ------------------------------------------------------------------ el acuse de una Rechazada (DD-09)
        [Fact]
        public void El_acuse_de_una_rechazada_por_el_sobre_lleva_los_motivos_y_el_texto_de_dd09_y_ninguna_tabla()
        {
            var solicitud = Solicitud(EstadoDeLaSolicitud.Rechazada);
            solicitud.MotivosDelSobre = new List<string> { "No encontramos ningún archivo adjunto en su correo.", "Segundo motivo." };

            var html = ArmadorRespuesta.Acuse(solicitud);
            var texto = SinEtiquetas(html);

            Assert.Contains("No encontramos ningún archivo adjunto en su correo.", texto);
            Assert.Contains("Segundo motivo.", texto);
            Assert.DoesNotContain("<table", html);
            AfirmaDd09(texto);
        }

        [Fact]
        public void El_acuse_de_una_rechazada_porque_ninguna_fila_quedo_validada_lleva_la_tabla_y_el_texto_de_dd09()
        {
            var html = ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.Rechazada, Fila(1, EstadoDeLaFila.RechazadaEnValidacion, "Motivo uno."), Fila(2, EstadoDeLaFila.SinAutorizacion, "Motivo dos.")));
            var texto = SinEtiquetas(html);

            Assert.Contains("<table", html);
            Assert.Contains("Motivo uno.", texto);
            Assert.Contains("Motivo dos.", texto);
            AfirmaDd09(texto);
            Assert.DoesNotContain("respuesta final", texto, StringComparison.OrdinalIgnoreCase);
            NuncaSaleLoSensible(html);
        }

        private static void AfirmaDd09(string texto)
        {
            // diseno/03 §1 paso 4 y DD-09, "expresamente": nada que procesar, no recibirá otro correo, corrija y reenvíe.
            Assert.Contains("nada que procesar", texto, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("no recibirá otro correo", texto, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("corrija", texto, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("reenv", texto, StringComparison.OrdinalIgnoreCase);
        }

        // ------------------------------------------------------------------ la respuesta final
        [Fact]
        public void La_respuesta_final_dice_que_se_hizo_que_no_y_por_que()
        {
            var filas = new[]
            {
                Fila(1, EstadoDeLaFila.Aprobada),
                Fila(2, EstadoDeLaFila.RechazadaEnAS400, "La cuenta está inactiva."),
                Fila(3, EstadoDeLaFila.Anulada, "Anulada por el supervisor: duplicada."),
                Fila(4, EstadoDeLaFila.RechazadaEnValidacion, "Faltan datos obligatorios: Moneda."),
            };
            var html = ArmadorRespuesta.RespuestaFinal(Solicitud(EstadoDeLaSolicitud.Procesada, filas));
            var texto = SinEtiquetas(html);

            Assert.Contains("MPPP-00000123", texto);
            Assert.Contains("<table", html);
            Assert.Contains("La cuenta está inactiva.", texto);
            Assert.Contains("Anulada por el supervisor: duplicada.", texto);
            Assert.Contains("Faltan datos obligatorios: Moneda.", texto);
            Assert.Contains(ArmadorRespuesta.EstadoParaElCliente(EstadoDeLaFila.Aprobada), texto);
            Assert.Contains(ArmadorRespuesta.EstadoParaElCliente(EstadoDeLaFila.RechazadaEnAS400), texto);
            Assert.DoesNotContain("AS400", texto);
            Assert.DoesNotContain("respuesta final", texto, StringComparison.OrdinalIgnoreCase); // esta ES la respuesta final: no se anuncia otra
            Assert.Matches(@"\b4\b", texto); // contadores: total
            NuncaSaleLoSensible(html);
        }

        // ------------------------------------------------------------------ el Excel es hostil
        [Fact]
        public void Todo_lo_que_viene_del_cliente_se_escapa_y_nunca_sale_una_etiqueta_ni_un_script()
        {
            var hostil = "<script>alert(1)</script><img src=x onerror=alert(2)>\"'&";
            var solicitud = Solicitud(EstadoDeLaSolicitud.EnProceso, Fila(1, EstadoDeLaFila.Validada, nombre: hostil, plan: "<b>42</b>"), Fila(2, EstadoDeLaFila.RechazadaEnValidacion, "Motivo con <i>etiqueta</i> & ampersand."));
            solicitud.Numero = "MPPP-<u>1</u>";
            solicitud.FechaRecibidoTexto = "<hoy>";

            foreach (var html in new[] { ArmadorRespuesta.Acuse(solicitud), ArmadorRespuesta.RespuestaFinal(Procesada(solicitud)) })
            {
                Assert.DoesNotContain("<script", html, StringComparison.OrdinalIgnoreCase);
                Assert.Contains("&lt;img src=x onerror=alert(2)&gt;", html); // escapado, no borrado: la palabra queda visible e inerte
                Assert.DoesNotContain("<img", html);
                Assert.DoesNotContain("<b>42</b>", html);
                Assert.DoesNotContain("<i>etiqueta</i>", html);
                Assert.DoesNotContain("<u>1</u>", html);
                Assert.DoesNotContain("<hoy>", html);
                Assert.Contains("&lt;script&gt;", html);
                Assert.Contains("&amp; ampersand", html);
                Assert.Contains("Motivo con", html); // las tildes y la ñ del español NO se convierten en entidades numéricas
                Assert.DoesNotContain("&#", html);
                Assert.DoesNotContain("{", html); // ningún marcador sin completar
            }
        }

        private static SolicitudParaRespuesta Procesada(SolicitudParaRespuesta s)
        {
            return new SolicitudParaRespuesta { Numero = s.Numero, FechaRecibidoTexto = s.FechaRecibidoTexto, Estado = EstadoDeLaSolicitud.Procesada, MotivosDelSobre = s.MotivosDelSobre, Filas = s.Filas };
        }

        [Fact]
        public void El_acuse_se_arma_para_los_dos_finales_y_la_respuesta_final_solo_para_una_procesada()
        {
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.Ingresada, Mixtas)));
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.NoReconocida, Mixtas)));
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.Procesada, Mixtas)));
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.RespuestaFinal(Solicitud(EstadoDeLaSolicitud.EnProceso, Mixtas)));
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.RespuestaFinal(Solicitud(EstadoDeLaSolicitud.Rechazada, Mixtas)));
            Assert.Throws<ArgumentNullException>(() => ArmadorRespuesta.Acuse(null));
            Assert.Throws<ArgumentNullException>(() => ArmadorRespuesta.RespuestaFinal(null));
        }

        [Fact]
        public void Una_solicitud_mal_armada_es_un_error_de_programacion()
        {
            var sinFilas = Solicitud(EstadoDeLaSolicitud.EnProceso);
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(sinFilas)); // En proceso sin filas no existe
            var filaNula = Solicitud(EstadoDeLaSolicitud.EnProceso, Fila(1, EstadoDeLaFila.Validada));
            filaNula.Filas.Add(null);
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(filaNula));
            var sinNumero = Solicitud(EstadoDeLaSolicitud.EnProceso, Fila(1, EstadoDeLaFila.Validada));
            sinNumero.Numero = " ";
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(sinNumero));
            var rechazadaSinNada = Solicitud(EstadoDeLaSolicitud.Rechazada);
            Assert.Throws<ArgumentException>(() => ArmadorRespuesta.Acuse(rechazadaSinNada)); // ni motivos del sobre ni filas: no hay qué decir
        }

        [Fact]
        public void Los_nulos_de_una_fila_salen_como_vacio_no_como_null_ni_revientan()
        {
            var fila = new FilaParaRespuesta { NumeroFila = 1, Estado = EstadoDeLaFila.Validada };
            var solicitud = Solicitud(EstadoDeLaSolicitud.EnProceso, fila);
            solicitud.FechaRecibidoTexto = null;
            solicitud.MotivosDelSobre = null;

            var html = ArmadorRespuesta.Acuse(solicitud);
            Assert.DoesNotContain("null", html, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("Validada", html);
        }

        [Fact]
        public void Cien_filas_entran_holgadas_en_la_columna_del_acuse()
        {
            var filas = Enumerable.Range(1, 100).Select(i => Fila(i, i % 2 == 0 ? EstadoDeLaFila.Validada : EstadoDeLaFila.RechazadaEnValidacion, new string('m', 450))).ToArray();
            var html = ArmadorRespuesta.Acuse(Solicitud(EstadoDeLaSolicitud.EnProceso, filas));
            Assert.True(html.Length < 1048576 / 4, $"largo {html.Length}"); // `sanic_acusecontenido` es M(1048576)
            Assert.Equal(100, Regex.Matches(html, "<tr").Count - 1); // una fila de encabezado más una por fila
        }
    }
}
