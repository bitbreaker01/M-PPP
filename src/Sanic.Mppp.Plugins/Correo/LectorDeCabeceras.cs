using System;

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
            throw new NotImplementedException();
        }
    }
}
