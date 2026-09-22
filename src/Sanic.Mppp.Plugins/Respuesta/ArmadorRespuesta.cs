using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Respuesta
{
    /// <summary>
    /// Enmascarado de datos sensibles para lo que viaja por correo (DD-08: "nunca se devuelven identificación ni cuenta
    /// completas; la cuenta va enmascarada a 4 dígitos"). Una sola regla para los dos: se conservan los ÚLTIMOS CUATRO
    /// caracteres y el resto se reemplaza por asteriscos, uno por carácter (`123456789` → `*****6789`). Con cuatro caracteres o
    /// menos se enmascara todo (`****`, tantos como caracteres haya). Nulo o vacío → vacío. Se enmascara lo recibido tal cual,
    /// sin recortar ni limpiar: lo que se ve son siempre 4 caracteres, sean los que sean.
    /// </summary>
    public static class Enmascarado
    {
        public static string Cuenta(string numeroCuenta)
        {
            return Enmascarar(numeroCuenta);
        }

        public static string Identificacion(string numeroIdentificacion)
        {
            return Enmascarar(numeroIdentificacion);
        }

        // Misma regla para los dos campos (DD-08): último 4, el resto asteriscos, sin tocar el valor recibido.
        private static string Enmascarar(string valor)
        {
            if (string.IsNullOrEmpty(valor))
            {
                return string.Empty;
            }

            if (valor.Length <= 4)
            {
                return new string('*', valor.Length);
            }

            var visibles = valor.Substring(valor.Length - 4);
            return new string('*', valor.Length - 4) + visibles;
        }
    }

    /// <summary>Lo que el acuse y la respuesta final muestran de cada fila. Sin SDK. Los datos vienen como están en `sanic_mppp_tbl_fila`.</summary>
    public sealed class FilaParaRespuesta
    {
        /// <summary>`sanic_numerofila`.</summary>
        public int NumeroFila { get; set; }

        /// <summary>El número de plan como lo escribió el cliente (`sanic_numeroplan` si se normalizó; si no, lo recibido). Puede ser nulo.</summary>
        public string NumeroPlan { get; set; }

        public string NombreBeneficiario { get; set; }

        /// <summary>COMPLETO, como está en la Fila: el armador lo enmascara. Nunca sale entero.</summary>
        public string NumeroCuenta { get; set; }

        /// <summary>
        /// COMPLETO, como está en la Fila. La identificación NUNCA sale en la tabla de la respuesta (a diferencia de
        /// la cuenta, no tiene columna propia): solo se usa si aparece literalmente dentro de <see cref="Mensaje"/>
        /// (DD-08, última línea de defensa), y ahí sí se enmascara antes de escapar.
        /// </summary>
        public string NumeroIdentificacion { get; set; }

        public EstadoDeLaFila Estado { get; set; }

        /// <summary>`sanic_mensaje`: los motivos, ya redactados para el cliente. Puede ser nulo (fila sin motivos).</summary>
        public string Mensaje { get; set; }
    }

    /// <summary>Lo que el armador necesita de la Solicitud. Sin SDK.</summary>
    public sealed class SolicitudParaRespuesta
    {
        /// <summary>`sanic_nombre` (`MPPP-00000123`): la referencia que el cliente puede citar.</summary>
        public string Numero { get; set; }

        /// <summary>La fecha de recibido YA formateada para el cliente (la zona horaria la resuelve quien llama). Puede ser nula.</summary>
        public string FechaRecibidoTexto { get; set; }

        public EstadoDeLaSolicitud Estado { get; set; }

        /// <summary>Motivos de las reglas del sobre que fallaron (Razon de cada NoCumplida con efecto Rechaza), en orden. Vacío si el sobre pasó.</summary>
        public IList<string> MotivosDelSobre { get; set; }

        /// <summary>Las filas, en cualquier orden: el armador las ordena por número. Vacío si el sobre falló antes de leer.</summary>
        public IList<FilaParaRespuesta> Filas { get; set; }
    }

    /// <summary>
    /// Arma el cuerpo HTML de las dos comunicaciones al cliente (DD-08): el ACUSE al terminar la validación (diseno/03 §1
    /// pasos 4 y 7; DD-09) y la RESPUESTA FINAL al terminar el procesamiento (diseno/03 §4 "Cierre"). Función pura. Contrato
    /// (lo fijan las pruebas `ArmadorRespuestaAceptacion`):
    ///  - HTML completo y autocontenido (sin scripts, estilos externos ni imágenes), en español, con el número de la solicitud;
    ///  - TODO texto que venga del cliente o de las filas se escapa (el Excel es hostil): nunca sale una etiqueta sin escapar;
    ///  - la cuenta sale SIEMPRE por <see cref="Enmascarado"/> en su columna; la identificación no se muestra en ninguna
    ///    columna. Ninguna de las dos aparece completa: si el mensaje de una fila la cita literalmente, también se
    ///    enmascara ahí (DD-08, última línea de defensa);
    ///  - las filas van en una tabla ordenada por número, con su estado en palabras del cliente y sus motivos;
    ///  - acuse de una Solicitud Rechazada (por el sobre o porque ninguna fila quedó Validada): texto de DD-09, expreso:
    ///    no hay nada que procesar, no recibirá otro correo por esta solicitud, corrija y reenvíe;
    ///  - acuse de una En proceso: las Validadas se procesan, las demás no, y recibirá una respuesta final;
    ///  - respuesta final de una Procesada: qué se hizo (Aprobada), qué no y por qué (Rechazada en AS400, Anulada, y las que
    ///    ya venían rechazadas de la validación);
    ///  - un estado que no corresponde a esa comunicación es un error de programación (<see cref="ArgumentException"/>).
    /// </summary>
    public static class ArmadorRespuesta
    {
        // Estilos mínimos e INLINE en cada etiqueta (07 §5: el cuerpo va como HTML en un Reply to email, sin
        // adjuntos; los clientes de correo ignoran hojas de estilo externas). Un bloque `<style>` con reglas
        // `selector{...}` queda descartado: la prueba de aceptación prohíbe cualquier `{` en el HTML (ningún
        // marcador sin completar), y esa misma llave es sintaxis de CSS, no un placeholder — así que van como
        // atributos `style="…"` cortos, repetidos solo donde hace falta (contrato punto 7: 100 filas de 450
        // caracteres tienen que entrar holgadas, y estos atributos son unas pocas decenas de caracteres cada uno).
        private const string EstiloCuerpo = "font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222222";
        private const string EstiloTabla = "border-collapse:collapse;width:100%;margin:8px 0";
        private const string EstiloCeldaEncabezado = "border:1px solid #cccccc;padding:4px 8px;text-align:left;background:#f2f2f2";
        private const string EstiloCelda = "border:1px solid #cccccc;padding:4px 8px;text-align:left;vertical-align:top";

        // 07 §5 "Texto obligatorio en las dos comunicaciones" (consecuencia de DF-08): el cuerpo lo arma el código, nunca
        // el flujo (DD-08), así que este aviso tiene que salir de acá.
        private const string TextoNoResponder =
            "<p>Para enviar una plantilla nueva o corregida, escriba un correo nuevo a esta dirección. No responda a este " +
            "mensaje: las respuestas no se procesan.</p>";

        /// <summary>Palabras del cliente para cada estado de fila, sin códigos ni jerga.</summary>
        public static string EstadoParaElCliente(EstadoDeLaFila estado)
        {
            switch (estado)
            {
                case EstadoDeLaFila.RechazadaEnValidacion:
                    return "Rechazada en validación";
                case EstadoDeLaFila.SinAutorizacion:
                    return "Sin autorización";
                case EstadoDeLaFila.Validada:
                    return "Validada";
                case EstadoDeLaFila.Digitada:
                    return "En proceso";
                case EstadoDeLaFila.Aprobada:
                    return "Aprobada";
                case EstadoDeLaFila.RechazadaEnAS400:
                    // DD-08/DD-09: el cliente no sabe qué es AS400, nunca se le nombra.
                    return "Rechazada por el banco";
                case EstadoDeLaFila.Anulada:
                    return "Anulada";
                default:
                    throw new ArgumentException($"El estado de fila {estado} no tiene palabras para el cliente.", nameof(estado));
            }
        }

        public static string Acuse(SolicitudParaRespuesta solicitud)
        {
            ValidarBase(solicitud);

            var filas = solicitud.Filas ?? new List<FilaParaRespuesta>();
            var motivosDelSobre = solicitud.MotivosDelSobre ?? new List<string>();

            switch (solicitud.Estado)
            {
                case EstadoDeLaSolicitud.EnProceso:
                    if (filas.Count == 0)
                    {
                        throw new ArgumentException("Una solicitud En proceso necesita al menos una fila.", nameof(solicitud));
                    }

                    return ArmarAcuseEnProceso(solicitud, filas);

                case EstadoDeLaSolicitud.Rechazada:
                    if (motivosDelSobre.Count == 0 && filas.Count == 0)
                    {
                        // DD-09: si no hay motivos del sobre ni filas, no hay nada que decirle al cliente: es un error de armado.
                        throw new ArgumentException("Una solicitud Rechazada necesita motivos del sobre o filas.", nameof(solicitud));
                    }

                    return ArmarAcuseRechazada(solicitud, motivosDelSobre, filas);

                default:
                    throw new ArgumentException($"El acuse no corresponde al estado {solicitud.Estado} de la solicitud.", nameof(solicitud));
            }
        }

        public static string RespuestaFinal(SolicitudParaRespuesta solicitud)
        {
            ValidarBase(solicitud);

            if (solicitud.Estado != EstadoDeLaSolicitud.Procesada)
            {
                throw new ArgumentException($"La respuesta final no corresponde al estado {solicitud.Estado} de la solicitud.", nameof(solicitud));
            }

            var filas = solicitud.Filas ?? new List<FilaParaRespuesta>();
            if (filas.Count == 0)
            {
                // Simetría con el acuse En proceso: una Procesada sin filas no tiene nada que informar, es un error de armado.
                throw new ArgumentException("Una solicitud Procesada necesita al menos una fila.", nameof(solicitud));
            }

            return ArmarRespuestaFinal(solicitud, filas);
        }

        // ------------------------------------------------------------------ validación (contrato punto 5)

        private static void ValidarBase(SolicitudParaRespuesta solicitud)
        {
            if (solicitud == null)
            {
                throw new ArgumentNullException(nameof(solicitud));
            }

            if (string.IsNullOrWhiteSpace(solicitud.Numero))
            {
                throw new ArgumentException("La solicitud necesita un número para citarle al cliente.", nameof(solicitud));
            }

            if (solicitud.Filas != null && solicitud.Filas.Any(f => f == null))
            {
                throw new ArgumentException("Una fila nula es un error de armado de la solicitud.", nameof(solicitud));
            }
        }

        // ------------------------------------------------------------------ acuse

        private static string ArmarAcuseEnProceso(SolicitudParaRespuesta solicitud, IList<FilaParaRespuesta> filas)
        {
            var ordenadas = filas.OrderBy(f => f.NumeroFila).ToList();
            var validas = ordenadas.Count(f => f.Estado == EstadoDeLaFila.Validada);
            var rechazadas = ordenadas.Count - validas;

            var sb = new StringBuilder();
            AbrirDocumento(sb);
            EscribirSaludoYNumero(sb, solicitud);
            EscribirContadorValidasRechazadas(sb, ordenadas.Count, validas, rechazadas);
            EscribirTablaFilas(sb, ordenadas);

            // DD-08: el acuse anuncia que viene una segunda comunicación cuando termine el procesamiento.
            sb.Append("<p>Las filas validadas se procesarán en el banco. Las filas rechazadas no se procesarán. Cuando el " +
                "procesamiento termine, le enviaremos una respuesta final con el resultado de cada fila.</p>");

            sb.Append(TextoNoResponder);
            CerrarDocumento(sb);
            return sb.ToString();
        }

        private static string ArmarAcuseRechazada(SolicitudParaRespuesta solicitud, IList<string> motivosDelSobre, IList<FilaParaRespuesta> filas)
        {
            var sb = new StringBuilder();
            AbrirDocumento(sb);
            EscribirSaludoYNumero(sb, solicitud);

            if (motivosDelSobre.Count > 0)
            {
                // Rechazada por el sobre: sin tabla de filas (contrato punto 3, "Rechazada").
                sb.Append("<ul>");
                foreach (var motivo in motivosDelSobre)
                {
                    sb.Append("<li>").Append(Escapar(motivo)).Append("</li>");
                }

                sb.Append("</ul>");
            }
            else
            {
                // Rechazada porque ninguna fila quedó Validada: mismos contadores y misma redacción que el acuse
                // En proceso (prueba `Los_contadores_del_acuse_concuerdan_en_numero`, caso validas=0).
                var ordenadas = filas.OrderBy(f => f.NumeroFila).ToList();
                var validas = ordenadas.Count(f => f.Estado == EstadoDeLaFila.Validada);
                var rechazadas = ordenadas.Count - validas;

                EscribirContadorValidasRechazadas(sb, ordenadas.Count, validas, rechazadas);
                EscribirTablaFilas(sb, ordenadas);
            }

            // DD-09, expreso: nada que procesar, no recibirá otro correo, corrija y reenvíe. Sin "respuesta final".
            sb.Append("<p>No hay nada que procesar: no recibirá otro correo por esta solicitud. Corrija la plantilla y " +
                "reenvíela en un correo nuevo a esta misma dirección.</p>");

            sb.Append(TextoNoResponder);
            CerrarDocumento(sb);
            return sb.ToString();
        }

        // ------------------------------------------------------------------ respuesta final

        private static string ArmarRespuestaFinal(SolicitudParaRespuesta solicitud, IList<FilaParaRespuesta> filas)
        {
            var ordenadas = filas.OrderBy(f => f.NumeroFila).ToList();
            var procesadas = ordenadas.Count(f => f.Estado == EstadoDeLaFila.Aprobada);
            var noProcesadas = ordenadas.Count - procesadas;

            var sb = new StringBuilder();
            AbrirDocumento(sb);
            EscribirSaludoYNumero(sb, solicitud);

            // Mismo criterio de concordancia que el acuse (revisión de código, 2026-09-21).
            sb.Append("<p>De ").Append(FilaSingularPlural(ordenadas.Count)).Append(" recibidas, ")
                .Append(Cantidad(procesadas, "se procesó", "se procesaron")).Append(" y ")
                .Append(Cantidad(noProcesadas, "quedó sin procesar", "quedaron sin procesar")).Append(".</p>");

            EscribirTablaFilas(sb, ordenadas);

            // diseno/03 §4 "Cierre": qué se hizo y qué no, sin anunciar otra comunicación ni nombrar AS400.
            sb.Append("<p>Este es el resultado final del procesamiento de su solicitud. Ante cualquier consulta sobre " +
                "una fila, comuníquese con su ejecutivo.</p>");

            sb.Append(TextoNoResponder);
            CerrarDocumento(sb);
            return sb.ToString();
        }

        // ------------------------------------------------------------------ armado común del HTML

        private static void AbrirDocumento(StringBuilder sb)
        {
            sb.Append("<!DOCTYPE html>");
            sb.Append("<html lang=\"es\"><head><meta charset=\"utf-8\"></head>");
            sb.Append("<body style=\"").Append(EstiloCuerpo).Append("\">");
        }

        private static void CerrarDocumento(StringBuilder sb)
        {
            sb.Append("</body></html>");
        }

        private static void EscribirSaludoYNumero(StringBuilder sb, SolicitudParaRespuesta solicitud)
        {
            sb.Append("<p>Estimado/a cliente:</p>");
            sb.Append("<p>Su número de solicitud es <strong>").Append(Escapar(solicitud.Numero)).Append("</strong>");

            var fecha = solicitud.FechaRecibidoTexto;
            if (!string.IsNullOrEmpty(fecha))
            {
                sb.Append(" y la recibimos el ").Append(Escapar(fecha));
            }

            sb.Append(".</p>");
        }

        private static void EscribirTablaFilas(StringBuilder sb, IList<FilaParaRespuesta> ordenadas)
        {
            sb.Append("<table style=\"").Append(EstiloTabla).Append("\"><thead><tr>");
            foreach (var encabezado in new[] { "N.º", "Plan", "Beneficiario", "Cuenta", "Resultado", "Motivos" })
            {
                sb.Append("<th style=\"").Append(EstiloCeldaEncabezado).Append("\">").Append(encabezado).Append("</th>");
            }

            sb.Append("</tr></thead><tbody>");

            foreach (var fila in ordenadas)
            {
                sb.Append("<tr>");
                EscribirCelda(sb, Numero(fila.NumeroFila));
                EscribirCelda(sb, Escapar(fila.NumeroPlan));
                EscribirCelda(sb, Escapar(fila.NombreBeneficiario));
                EscribirCelda(sb, Escapar(Enmascarado.Cuenta(fila.NumeroCuenta)));
                // El estado en palabras sale de nuestro propio diccionario fijo (EstadoParaElCliente), no del cliente:
                // no hace falta escaparlo, y así no se corre el riesgo de tocar sus tildes.
                EscribirCelda(sb, EstadoParaElCliente(fila.Estado));
                EscribirCelda(sb, Escapar(DefenderMensaje(fila)));
                sb.Append("</tr>");
            }

            sb.Append("</tbody></table>");
        }

        // DD-08, última línea de defensa (revisión de código, 2026-09-21): `sanic_mensaje` lo redacta el catálogo
        // (D-19, marcador {valor}) y hoy nunca cita la cuenta ni la identificación completas, pero si algún día lo
        // hiciera, acá se enmascaran igual antes de escapar. Solo en el mensaje de ESA fila: los motivos del sobre
        // no tienen fila ni cuenta/identificación asociada.
        private static string DefenderMensaje(FilaParaRespuesta fila)
        {
            var mensaje = fila.Mensaje;
            mensaje = ReemplazarSiIdentifica(mensaje, fila.NumeroCuenta, Enmascarado.Cuenta(fila.NumeroCuenta));
            mensaje = ReemplazarSiIdentifica(mensaje, fila.NumeroIdentificacion, Enmascarado.Identificacion(fila.NumeroIdentificacion));
            return mensaje;
        }

        // Reemplazo ordinal (String.Replace(string, string) no depende de la cultura), sin Regex. Menos de 5
        // caracteres no califica: es demasiado corto para identificar a alguien y coincidiría con cualquier texto.
        private static string ReemplazarSiIdentifica(string mensaje, string valor, string enmascarado)
        {
            if (string.IsNullOrEmpty(mensaje) || string.IsNullOrEmpty(valor) || valor.Length < 5)
            {
                return mensaje;
            }

            return mensaje.Replace(valor, enmascarado);
        }

        private static void EscribirCelda(StringBuilder sb, string contenidoYaEscapado)
        {
            sb.Append("<td style=\"").Append(EstiloCelda).Append("\">").Append(contenidoYaEscapado).Append("</td>");
        }

        // Escapador directo, carácter por carácter: solo los 5 metacaracteres de HTML se codifican; el resto —
        // tildes, eñe, cualquier otra letra— sale tal cual (el texto al cliente lleva ortografía completa). No
        // depende de cómo un runtime particular codifique lo que no es peligroso, y sigue cerrando el vector: nunca
        // sale un `<`, `>`, `&`, `"` ni `'` sin escapar.
        private static string Escapar(string valor)
        {
            if (string.IsNullOrEmpty(valor))
            {
                return string.Empty;
            }

            var sb = new StringBuilder(valor.Length);
            foreach (var c in valor)
            {
                switch (c)
                {
                    case '&':
                        sb.Append("&amp;");
                        break;
                    case '<':
                        sb.Append("&lt;");
                        break;
                    case '>':
                        sb.Append("&gt;");
                        break;
                    case '"':
                        sb.Append("&quot;");
                        break;
                    case '\'':
                        // Entidad NUMÉRICA, no `&apos;`: Outlook de escritorio renderiza el cuerpo con el motor de
                        // Word, que no conoce `&apos;` (es válida en HTML5/XML pero no en ese motor) y lo mostraría
                        // tal cual, literal. `&#39;` es el apóstrofo en cualquier motor. No es ambigüedad con una
                        // tilde o una eñe convertidas a numérica: esas nunca se tocan (van tal cual, sin escapar).
                        sb.Append("&#39;");
                        break;
                    default:
                        sb.Append(c);
                        break;
                }
            }

            return sb.ToString();
        }

        private static string Numero(int valor)
        {
            return valor.ToString(CultureInfo.InvariantCulture);
        }

        // Compartido por las dos ramas del acuse que muestran tabla (En proceso y Rechazada sin ninguna Validada):
        // misma pregunta ("¿cuántas quedaron validadas y cuántas rechazadas?"), misma redacción con concordancia
        // número-verbo (revisión de código, 2026-09-21: "1 quedaron validadas" no es español de un banco).
        private static void EscribirContadorValidasRechazadas(StringBuilder sb, int total, int validas, int rechazadas)
        {
            sb.Append("<p>Recibimos ").Append(FilaSingularPlural(total)).Append(": ")
                .Append(Cantidad(validas, "quedó validada", "quedaron validadas")).Append(" y ")
                .Append(Cantidad(rechazadas, "quedó rechazada", "quedaron rechazadas")).Append(".</p>");
        }

        // "1 fila" / "2 filas" (nunca 0: quien llama garantiza al menos una fila en los dos casos que usan esto).
        private static string FilaSingularPlural(int cantidad)
        {
            return cantidad == 1 ? "1 fila" : Numero(cantidad) + " filas";
        }

        // Concordancia número-verbo para los contadores (revisión de código, 2026-09-21): 0 → "ninguna <singular>",
        // 1 → "1 <singular>", N → "N <plural>". `singular` y `plural` ya traen el verbo conjugado.
        private static string Cantidad(int cantidad, string singular, string plural)
        {
            if (cantidad == 0)
            {
                return "ninguna " + singular;
            }

            if (cantidad == 1)
            {
                return "1 " + singular;
            }

            return Numero(cantidad) + " " + plural;
        }
    }
}
