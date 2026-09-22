using System;
using System.Collections.Generic;
using System.Text;

namespace Sanic.Mppp.Plugins.Correo
{
    /// <summary>Lo que el plugin liviano necesita de las cabeceras de un `.eml` (diseno/03 §0 paso 2). Nada del cuerpo.</summary>
    public sealed class CabecerasLeidas
    {
        private CabecerasLeidas(bool legibles, string asunto, bool traeInReplyTo, bool traeReferences)
        {
            Legibles = legibles;
            Asunto = asunto;
            TraeInReplyTo = traeInReplyTo;
            TraeReferences = traeReferences;
        }

        /// <summary>False: no se pudieron leer (sin fin de cabeceras dentro del bloque, sin ninguna cabecera, bytes nulos). Ante la duda, lo ve una persona.</summary>
        public bool Legibles { get; }

        /// <summary>`Subject` decodificado (RFC 2047, B y Q, utf-8 e iso-8859-1) y plegado en una línea, sin espacios a los lados. Vacío si no viene.</summary>
        public string Asunto { get; }

        public bool TraeInReplyTo { get; }

        public bool TraeReferences { get; }

        /// <summary>Trae `In-Reply-To` o `References` con algo adentro: es una respuesta o un reenvío, no un correo nuevo.</summary>
        public bool TraeReferenciasAOtroCorreo => TraeInReplyTo || TraeReferences;

        public static CabecerasLeidas Ilegibles() => new CabecerasLeidas(false, string.Empty, false, false);

        public static CabecerasLeidas De(string asunto, bool traeInReplyTo, bool traeReferences) => new CabecerasLeidas(true, asunto ?? string.Empty, traeInReplyTo, traeReferences);
    }

    /// <summary>
    /// Lee SOLO las cabeceras del inicio de un `.eml` (diseno/03 §0 paso 2). Entrada NO confiable. Contrato (lo fijan las pruebas
    /// `LectorDeCabecerasAceptacion`):
    ///  - recibe el primer bloque del archivo (a lo sumo <see cref="TopeBytes"/>); si viene más, solo mira los primeros <see cref="TopeBytes"/>;
    ///  - las cabeceras terminan en la primera línea en blanco (CRLF CRLF o LF LF); si no hay una dentro del bloque, son ILEGIBLES;
    ///  - nulo, vacío, o un bloque sin ninguna línea `Nombre: valor` al principio: ILEGIBLES;
    ///  - las líneas de continuación (empiezan con espacio o tabulador) se pliegan a la cabecera anterior;
    ///  - los nombres de cabecera no distinguen mayúsculas; si una cabecera se repite, cuenta la primera (`Subject`) o basta con que
    ///    una tenga contenido (`In-Reply-To`, `References`);
    ///  - `In-Reply-To`/`References` cuentan solo si traen algo que no sea espacio;
    ///  - el `Subject` se decodifica de RFC 2047 (`=?utf-8?B?…?=`, `=?iso-8859-1?Q?…?=`); una palabra codificada rota se deja tal cual;
    ///  - el cuerpo no se interpreta nunca: lo que está después de la línea en blanco no se lee;
    ///  - nunca lanza por el contenido: cualquier basura da ILEGIBLES o un asunto vacío.
    /// Función pura, sin expresiones regulares (regla del estudio).
    /// </summary>
    public static class LectorDeCabeceras
    {
        /// <summary>256 KB (diseno/03 §0 paso 2).</summary>
        public const int TopeBytes = 256 * 1024;

        public static CabecerasLeidas Leer(byte[] inicioDelArchivo)
        {
            if (inicioDelArchivo == null || inicioDelArchivo.Length == 0)
            {
                return CabecerasLeidas.Ilegibles();
            }

            // Se corta a TopeBytes ANTES de decodificar (diseno/03 §0 paso 2): nunca se mira más que eso, ni de casualidad.
            var bytes = inicioDelArchivo.Length > TopeBytes ? Recortar(inicioDelArchivo, TopeBytes) : inicioDelArchivo;

            // UTF-8 TOLERANTE: no lanza ante bytes inválidos, los reemplaza (entrada no confiable: nunca revienta).
            var texto = new UTF8Encoding(false, false).GetString(bytes);

            var lineasFisicas = ExtraerLineasFisicasDeCabeceras(texto);
            if (lineasFisicas == null)
            {
                return CabecerasLeidas.Ilegibles();
            }

            var lineasLogicas = PlegarLineas(lineasFisicas);

            string asunto = null;
            var traeInReplyTo = false;
            var traeReferences = false;
            var algunaValida = false;

            foreach (var linea in lineasLogicas)
            {
                var separador = linea.IndexOf(':');
                if (separador <= 0)
                {
                    // sin ':' o nombre vacío (": algo" / ":"): no es una cabecera válida, pero no rompe la lectura.
                    continue;
                }

                var nombre = linea.Substring(0, separador).Trim();
                if (nombre.Length == 0)
                {
                    continue;
                }

                algunaValida = true;
                var valor = linea.Substring(separador + 1).Trim();

                if (asunto == null && string.Equals(nombre, "Subject", StringComparison.OrdinalIgnoreCase))
                {
                    // repetida: cuenta la primera.
                    asunto = DecodificarRfc2047(valor);
                }
                else if (string.Equals(nombre, "In-Reply-To", StringComparison.OrdinalIgnoreCase))
                {
                    if (valor.Length > 0)
                    {
                        traeInReplyTo = true;
                    }
                }
                else if (string.Equals(nombre, "References", StringComparison.OrdinalIgnoreCase))
                {
                    if (valor.Length > 0)
                    {
                        traeReferences = true;
                    }
                }
            }

            if (!algunaValida)
            {
                return CabecerasLeidas.Ilegibles();
            }

            return CabecerasLeidas.De(asunto ?? string.Empty, traeInReplyTo, traeReferences);
        }

        // ------------------------------------------------------------------ fin de cabeceras y plegado

        private static byte[] Recortar(byte[] origen, int cantidad)
        {
            var resultado = new byte[cantidad];
            Array.Copy(origen, resultado, cantidad);
            return resultado;
        }

        /// <summary>
        /// Parte el texto en líneas físicas tratando `\r\n`, `\n` suelto y `\r` suelto como fin de línea (revisión de código,
        /// 2026-09-21: un `\r` sin `\n` tiene que cortar igual, si no un `In-Reply-To` puede quedar escondido dentro del
        /// `Subject` y DF-08 lee una respuesta como correo nuevo). Devuelve las líneas ANTES de la primera línea en blanco
        /// (que cierra las cabeceras, sea `\r\n\r\n`, `\n\n` o `\r\r`); nulo si esa línea nunca aparece. Un solo recorrido,
        /// sin volver a escanear el texto entero (mismo motivo de rendimiento que <see cref="PlegarLineas"/>).
        /// </summary>
        private static IList<string> ExtraerLineasFisicasDeCabeceras(string texto)
        {
            var lineas = new List<string>();
            var inicio = 0;
            var i = 0;

            while (i < texto.Length)
            {
                var c = texto[i];
                if (c == '\n')
                {
                    lineas.Add(texto.Substring(inicio, i - inicio));
                    i++;
                    inicio = i;
                }
                else if (c == '\r')
                {
                    lineas.Add(texto.Substring(inicio, i - inicio));
                    i++;
                    if (i < texto.Length && texto[i] == '\n')
                    {
                        i++; // \r\n es UN solo fin de línea, no dos.
                    }

                    inicio = i;
                }
                else
                {
                    i++;
                    continue;
                }

                if (lineas[lineas.Count - 1].Length == 0)
                {
                    // Línea en blanco: acá terminan las cabeceras. Se devuelve todo lo anterior, sin la línea en blanco.
                    return lineas.GetRange(0, lineas.Count - 1);
                }
            }

            return null; // nunca hubo línea en blanco dentro del bloque: ILEGIBLE.
        }

        /// <summary>
        /// Junta cada línea que empieza con espacio o tabulador a la anterior, con un único espacio entre las dos partes.
        /// Revisión de código, 2026-09-21: la versión anterior reconcatenaba `anterior + " " + continuado` DENTRO del bucle,
        /// así que cada línea de continuación reconstruía todo lo acumulado hasta ahí (cuadrático: con 60.000 continuaciones
        /// se vuelve inusable). Acá se juntan las partes en una lista y se unen UNA sola vez por cabecera lógica.
        /// </summary>
        private static IList<string> PlegarLineas(IList<string> lineasFisicas)
        {
            var logicas = new List<string>(lineasFisicas.Count);
            string primeraLinea = null;
            var tuvoContinuacion = false;
            List<string> partes = null;

            void CerrarActual()
            {
                if (primeraLinea == null)
                {
                    return;
                }

                if (!tuvoContinuacion)
                {
                    logicas.Add(primeraLinea);
                }
                else if (partes == null || partes.Count == 0)
                {
                    logicas.Add(primeraLinea.TrimEnd());
                }
                else
                {
                    logicas.Add(primeraLinea.TrimEnd() + " " + string.Join(" ", partes));
                }
            }

            foreach (var linea in lineasFisicas)
            {
                var esContinuacion = linea.Length > 0 && (linea[0] == ' ' || linea[0] == '\t') && primeraLinea != null;
                if (esContinuacion)
                {
                    tuvoContinuacion = true;
                    var continuado = linea.Trim();
                    if (continuado.Length > 0)
                    {
                        if (partes == null)
                        {
                            partes = new List<string>();
                        }

                        partes.Add(continuado);
                    }
                }
                else
                {
                    CerrarActual();
                    primeraLinea = linea;
                    tuvoContinuacion = false;
                    partes = null;
                }
            }

            CerrarActual();
            return logicas;
        }

        // ------------------------------------------------------------------ RFC 2047 a mano (sin expresiones regulares)

        /// <summary>Decodifica todas las palabras codificadas `=?charset?B|Q?texto?=` del valor; el resto queda tal cual.</summary>
        private static string DecodificarRfc2047(string valor)
        {
            if (string.IsNullOrEmpty(valor))
            {
                return valor ?? string.Empty;
            }

            var resultado = new StringBuilder(valor.Length);
            var i = 0;
            var anteriorFuePalabraCodificada = false;

            while (i < valor.Length)
            {
                var inicioToken = valor.IndexOf("=?", i, StringComparison.Ordinal);
                if (inicioToken < 0)
                {
                    resultado.Append(valor, i, valor.Length - i);
                    break;
                }

                var literal = valor.Substring(i, inicioToken - i);

                if (TryDecodificarPalabra(valor, inicioToken, out var decodificado, out var finIndice))
                {
                    // Entre dos palabras codificadas seguidas, el espacio que las separa se descarta (RFC 2047).
                    var esSoloEspacios = literal.Length > 0 && EsSoloEspaciosOTabuladores(literal);
                    if (!(esSoloEspacios && anteriorFuePalabraCodificada))
                    {
                        resultado.Append(literal);
                    }

                    resultado.Append(decodificado);
                    anteriorFuePalabraCodificada = true;
                    i = finIndice;
                }
                else
                {
                    // No es un token completo: "=?" queda como texto literal y se sigue buscando más adelante.
                    resultado.Append(literal);
                    resultado.Append("=?");
                    anteriorFuePalabraCodificada = false;
                    i = inicioToken + 2;
                }
            }

            return resultado.ToString();
        }

        /// <summary>RFC 2047 §2: "an 'encoded-word' may not be more than 75 characters long" (incluye `=?...?=` completo).</summary>
        private const int LargoMaximoPalabraCodificada = 75;

        /// <summary>
        /// Reconoce la ESTRUCTURA `=?charset?B|Q?texto?=` a partir de <paramref name="inicio"/> (donde está el `=?`). Si la
        /// estructura es válida, <paramref name="decodificado"/> es el contenido decodificado, o el token CRUDO tal cual si el
        /// charset no se soporta o el contenido está roto (base64 inválido, escape hexadecimal inválido): nunca revienta.
        /// Revisión de código, 2026-09-21: la búsqueda del cierre está acotada a <see cref="LargoMaximoPalabraCodificada"/>
        /// caracteres desde <paramref name="inicio"/>; sin esa cota, miles de `=?utf-8?B?X` sin ningún `?=` disparan un
        /// reescaneo hasta el final del texto en cada intento (cuadrático).
        /// </summary>
        private static bool TryDecodificarPalabra(string valor, int inicio, out string decodificado, out int finIndice)
        {
            decodificado = null;
            finIndice = -1;

            var limite = Math.Min(valor.Length, inicio + LargoMaximoPalabraCodificada);

            var pos = inicio + 2;
            if (pos >= limite)
            {
                return false;
            }

            var finCharset = valor.IndexOf('?', pos, limite - pos);
            if (finCharset < 0)
            {
                return false;
            }

            var charset = valor.Substring(pos, finCharset - pos);
            if (charset.Length == 0)
            {
                return false;
            }

            pos = finCharset + 1;
            if (pos >= limite)
            {
                return false;
            }

            var codificacion = valor[pos];
            if (codificacion != 'B' && codificacion != 'b' && codificacion != 'Q' && codificacion != 'q')
            {
                return false;
            }

            pos++;
            if (pos >= limite || valor[pos] != '?')
            {
                return false;
            }

            pos++; // inicio del texto codificado
            if (pos > limite)
            {
                return false;
            }

            var finTexto = valor.IndexOf("?=", pos, limite - pos, StringComparison.Ordinal);
            if (finTexto < 0)
            {
                return false;
            }

            var texto = valor.Substring(pos, finTexto - pos);
            finIndice = finTexto + 2;
            var tokenCrudo = valor.Substring(inicio, finIndice - inicio);

            var charsetSoportado = string.Equals(charset, "utf-8", StringComparison.OrdinalIgnoreCase)
                                    || string.Equals(charset, "iso-8859-1", StringComparison.OrdinalIgnoreCase);
            if (!charsetSoportado)
            {
                decodificado = tokenCrudo;
                return true;
            }

            var esBase64 = codificacion == 'B' || codificacion == 'b';
            var exito = esBase64 ? TryDecodificarBase64(texto, out var bytes) : TryDecodificarQuotedPrintable(texto, out bytes);

            decodificado = exito ? DecodificarBytesConCharset(bytes, charset) : tokenCrudo;
            return true;
        }

        private static bool TryDecodificarBase64(string texto, out byte[] bytes)
        {
            try
            {
                bytes = Convert.FromBase64String(texto);
                return true;
            }
            catch (FormatException)
            {
                bytes = null;
                return false;
            }
        }

        private static bool TryDecodificarQuotedPrintable(string texto, out byte[] bytes)
        {
            var lista = new List<byte>(texto.Length);
            var i = 0;

            while (i < texto.Length)
            {
                var c = texto[i];
                if (c == '_')
                {
                    // `_` es espacio (RFC 2047, distinto de quoted-printable "puro").
                    lista.Add((byte)' ');
                    i++;
                }
                else if (c == '=')
                {
                    if (i + 2 >= texto.Length)
                    {
                        bytes = null;
                        return false;
                    }

                    var alto = ValorHex(texto[i + 1]);
                    var bajo = ValorHex(texto[i + 2]);
                    if (alto < 0 || bajo < 0)
                    {
                        bytes = null;
                        return false;
                    }

                    lista.Add((byte)((alto << 4) | bajo));
                    i += 3;
                }
                else if (c <= 0xFF)
                {
                    lista.Add((byte)c);
                    i++;
                }
                else
                {
                    // Un carácter fuera de lo que un correo real manda acá (ASCII de por sí): la palabra queda rota.
                    bytes = null;
                    return false;
                }
            }

            bytes = lista.ToArray();
            return true;
        }

        /// <summary>"Dígito" es ASCII por rango de `char` (regla del estudio): sin `char.IsDigit`, que es sensible a Unicode.</summary>
        private static int ValorHex(char c)
        {
            if (c >= '0' && c <= '9')
            {
                return c - '0';
            }

            if (c >= 'A' && c <= 'F')
            {
                return c - 'A' + 10;
            }

            if (c >= 'a' && c <= 'f')
            {
                return c - 'a' + 10;
            }

            return -1;
        }

        private static string DecodificarBytesConCharset(byte[] bytes, string charset)
        {
            if (string.Equals(charset, "utf-8", StringComparison.OrdinalIgnoreCase))
            {
                // Tolerante: una palabra codificada rota no puede reventar la lectura de cabeceras.
                return new UTF8Encoding(false, false).GetString(bytes);
            }

            // iso-8859-1 (Latin-1): cada byte 0..255 tiene un carácter Unicode, nunca lanza.
            return Encoding.GetEncoding(28591).GetString(bytes);
        }

        private static bool EsSoloEspaciosOTabuladores(string texto)
        {
            foreach (var c in texto)
            {
                if (c != ' ' && c != '\t')
                {
                    return false;
                }
            }

            return true;
        }
    }
}
