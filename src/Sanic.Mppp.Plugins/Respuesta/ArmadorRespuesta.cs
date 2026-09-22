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

        /// <summary>COMPLETO, como está en la Fila: el armador lo enmascara. Nunca sale entero.</summary>
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
    ///  - la cuenta y la identificación salen SIEMPRE por <see cref="Enmascarado"/>; el valor completo no aparece nunca;
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

            sb.Append("<p>Recibimos ").Append(Numero(ordenadas.Count)).Append(" fila(s): ").Append(Numero(validas))
                .Append(" quedaron validadas y ").Append(Numero(rechazadas)).Append(" quedaron rechazadas.</p>");

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
                // Rechazada porque ninguna fila quedó Validada: la tabla de filas con contadores.
                var ordenadas = filas.OrderBy(f => f.NumeroFila).ToList();
                sb.Append("<p>Recibimos ").Append(Numero(ordenadas.Count)).Append(" fila(s), y ninguna quedó validada.</p>");
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

            sb.Append("<p>De ").Append(Numero(ordenadas.Count)).Append(" fila(s) recibidas, ").Append(Numero(procesadas))
                .Append(" se procesaron y ").Append(Numero(noProcesadas)).Append(" no se procesaron.</p>");

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
                EscribirCelda(sb, Escapar(fila.Mensaje));
                sb.Append("</tr>");
            }

            sb.Append("</tbody></table>");
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
                        // Entidad NOMBRADA (no numérica): el documento es HTML5 (`<!DOCTYPE html>`), donde `&apos;`
                        // es válida; ninguna entidad `&#…;` puede aparecer (la prueba de aceptación lo exige, para
                        // no confundir un escape real con una tilde o una eñe convertida a numérica).
                        sb.Append("&apos;");
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
    }
}
