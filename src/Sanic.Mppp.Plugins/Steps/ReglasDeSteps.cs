using System;
using System.Collections.Generic;
using System.Globalization;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// La lista blanca de columnas (diseno/04 §1; diseno/03 §5): `W` en Dataverse es sobre la fila entera, así que el control de
    /// qué puede tocar una persona es este step, no el formulario. Contrato (lo fijan las pruebas `ReglasDeStepsAceptacion`):
    ///  - en Fila una persona solo puede mandar `sanic_estado` y `sanic_mensaje`; en Solicitud, `sanic_requiererevision` y
    ///    `sanic_estadoprocesamiento`;
    ///  - una tabla que no está en la lista no se controla acá (el step no se registra sobre ella): devuelve vacío;
    ///  - los nombres de columna se comparan como los manda Dataverse (minúscula, ordinal);
    ///  - devuelve TODAS las columnas no permitidas, ordenadas, para que el mensaje del error las nombre a todas;
    ///  - la columna primaria (`<tabla>id`) que el SDK incluye en el `Target` no cuenta como intento de escritura.
    /// </summary>
    public static class ListaBlancaDeColumnas
    {
        public const string Fila = "sanic_mppp_tbl_fila";
        public const string Solicitud = "sanic_mppp_tbl_solicitud";

        // diseno/04 §1: lo único que un humano puede mandar en el Target de cada tabla controlada.
        private static readonly string[] PermitidasEnFila = { "sanic_estado", "sanic_mensaje" };
        private static readonly string[] PermitidasEnSolicitud = { "sanic_requiererevision", "sanic_estadoprocesamiento" };

        /// <summary>Las columnas del `Target` que esa tabla NO admite de una persona. Vacío si todo está permitido.</summary>
        public static IList<string> ColumnasNoPermitidas(string tabla, IEnumerable<string> columnasDelTarget)
        {
            if (columnasDelTarget == null)
                throw new ArgumentNullException(nameof(columnasDelTarget));

            string[] permitidas;
            if (string.Equals(tabla, Fila, StringComparison.Ordinal))
                permitidas = PermitidasEnFila;
            else if (string.Equals(tabla, Solicitud, StringComparison.Ordinal))
                permitidas = PermitidasEnSolicitud;
            else
                return new List<string>(); // tabla no controlada por este step (diseno/04 §1): no se registra sobre ella.

            var primaria = tabla + "id";

            // SortedSet ordinal: dedupe y ordena a la vez, para que el mensaje de error liste todas las columnas una sola vez.
            var noPermitidas = new SortedSet<string>(StringComparer.Ordinal);
            foreach (var columna in columnasDelTarget)
            {
                if (string.Equals(columna, primaria, StringComparison.Ordinal))
                    continue; // la primaria del Target no es un intento de escritura de la persona.

                var esPermitida = false;
                foreach (var permitida in permitidas)
                {
                    if (string.Equals(columna, permitida, StringComparison.Ordinal))
                    {
                        esPermitida = true;
                        break;
                    }
                }

                if (!esPermitida)
                    noPermitidas.Add(columna);
            }

            return new List<string>(noPermitidas);
        }
    }

    /// <summary>
    /// Helpers de texto ASCII puro: sin `char.ToUpperInvariant`/`ToLowerInvariant` ni expresiones regulares (reglas del proyecto).
    /// "Dígito" y "letra" son siempre ASCII por rango de `char`; cualquier otro carácter (acentuado, fullwidth, dígito arábigo,
    /// etc.) queda fuera de rango y por lo tanto es inválido para estos catálogos.
    /// </summary>
    internal static class TextoAscii
    {
        internal static bool EsDigito(char c) => c >= '0' && c <= '9';
        internal static bool EsMayuscula(char c) => c >= 'A' && c <= 'Z';
        internal static bool EsMinuscula(char c) => c >= 'a' && c <= 'z';

        private static char AMayuscula(char c) => EsMinuscula(c) ? (char)(c - 32) : c;
        private static char AMinuscula(char c) => EsMayuscula(c) ? (char)(c + 32) : c;

        internal static string AMayusculas(string valor)
        {
            var arreglo = valor.ToCharArray();
            for (var i = 0; i < arreglo.Length; i++)
                arreglo[i] = AMayuscula(arreglo[i]);
            return new string(arreglo);
        }

        internal static string AMinusculas(string valor)
        {
            var arreglo = valor.ToCharArray();
            for (var i = 0; i < arreglo.Length; i++)
                arreglo[i] = AMinuscula(arreglo[i]);
            return new string(arreglo);
        }

        /// <summary>Recorta a lo sumo <paramref name="maximo"/> caracteres, sin partir nunca un par subrogado.</summary>
        internal static string Recortar(string valor, int maximo)
        {
            if (maximo < 0) maximo = 0;
            if (valor.Length <= maximo) return valor;
            var largo = maximo;
            if (largo > 0 && char.IsLowSurrogate(valor[largo]) && char.IsHighSurrogate(valor[largo - 1]))
                largo--; // el corte caía en la mitad de un par subrogado: retrocedo al carácter completo anterior.
            return valor.Substring(0, largo);
        }
    }

    /// <summary>
    /// Normalización y validación de los catálogos antes de guardarlos (diseno/03 §5; diseno/02 §2.1, §2.2, §2.3, §2.5).
    /// Cada método devuelve el valor YA normalizado, o lanza <see cref="ArgumentException"/> con un motivo para quien está
    /// cargando el catálogo (lo lee una persona en la app, no un cliente del banco). Un valor nulo o en blanco no se normaliza:
    /// devuelve nulo, y que sea obligatorio lo exige la plataforma con la columna requerida.
    /// </summary>
    public static class Normalizacion
    {
        /// <summary>`sanic_cifbac`: solo dígitos ASCII, relleno con ceros a la izquierda hasta 9. Más de 9 dígitos, o algo que no sea dígito, es error.</summary>
        public static string CifBac(string valor)
        {
            if (string.IsNullOrWhiteSpace(valor)) return null;

            var recortado = valor.Trim();
            if (recortado.Length < 1 || recortado.Length > 9)
                throw new ArgumentException("El CIF BAC tiene que tener entre 1 y 9 dígitos.", nameof(valor));

            foreach (var c in recortado)
            {
                if (!TextoAscii.EsDigito(c))
                    throw new ArgumentException("El CIF BAC solo admite dígitos.", nameof(valor));
            }

            return recortado.PadLeft(9, '0');
        }

        /// <summary>`sanic_cifcom`: en mayúscula; tiene que quedar `^[A-Z0-9 ]{9}\d{3}$` (12 caracteres exactos).</summary>
        public static string CifCom(string valor)
        {
            if (string.IsNullOrWhiteSpace(valor)) return null;

            var mayuscula = TextoAscii.AMayusculas(valor.Trim());
            if (mayuscula.Length != 12)
                throw new ArgumentException("El CIF COM tiene que tener 12 caracteres: 9 alfanuméricos o espacio y 3 dígitos.", nameof(valor));

            for (var i = 0; i < 9; i++)
            {
                var c = mayuscula[i];
                if (!(TextoAscii.EsMayuscula(c) || TextoAscii.EsDigito(c) || c == ' '))
                    throw new ArgumentException("Los primeros 9 caracteres del CIF COM tienen que ser alfanuméricos o espacio.", nameof(valor));
            }

            for (var i = 9; i < 12; i++)
            {
                if (!TextoAscii.EsDigito(mayuscula[i]))
                    throw new ArgumentException("Los últimos 3 caracteres del CIF COM tienen que ser dígitos.", nameof(valor));
            }

            return mayuscula;
        }

        /// <summary>`sanic_codigo` de Plan: en mayúscula y relleno con ceros a la izquierda hasta 4; tiene que quedar `^[A-Z0-9]{4}$`.</summary>
        public static string CodigoDePlan(string valor)
        {
            if (string.IsNullOrWhiteSpace(valor)) return null;

            var mayuscula = TextoAscii.AMayusculas(valor.Trim());
            if (mayuscula.Length < 1 || mayuscula.Length > 4)
                throw new ArgumentException("El código de plan tiene que tener entre 1 y 4 caracteres alfanuméricos.", nameof(valor));

            foreach (var c in mayuscula)
            {
                if (!(TextoAscii.EsMayuscula(c) || TextoAscii.EsDigito(c)))
                    throw new ArgumentException("El código de plan solo admite letras y dígitos.", nameof(valor));
            }

            return mayuscula.PadLeft(4, '0');
        }

        /// <summary>`sanic_nombre` de Autorizado: sin espacios a los lados y en minúscula; tiene que tener forma de correo (algo@algo.algo, sin espacios ni dos arrobas).</summary>
        public static string CorreoAutorizado(string valor)
        {
            if (string.IsNullOrWhiteSpace(valor)) return null;

            var minuscula = TextoAscii.AMinusculas(valor.Trim());
            if (minuscula.IndexOf(' ') >= 0)
                throw new ArgumentException("El correo no puede tener espacios.", nameof(valor));

            var primeraArroba = minuscula.IndexOf('@');
            var ultimaArroba = minuscula.LastIndexOf('@');
            if (primeraArroba < 0 || primeraArroba != ultimaArroba)
                throw new ArgumentException("El correo tiene que tener exactamente un @.", nameof(valor));

            var parteLocal = minuscula.Substring(0, primeraArroba);
            if (parteLocal.Length == 0)
                throw new ArgumentException("El correo necesita algo antes del @.", nameof(valor));

            var dominio = minuscula.Substring(primeraArroba + 1);
            var punto = dominio.IndexOf('.');
            if (punto <= 0 || punto == dominio.Length - 1)
                throw new ArgumentException("El dominio del correo tiene que tener un punto que no sea el primero ni el último carácter.", nameof(valor));

            return minuscula;
        }

        /// <summary>`sanic_nombre` de Parametro: en minúscula, sin espacios a los lados; solo letras ASCII, dígitos y puntos, sin puntos al principio, al final ni repetidos.</summary>
        public static string NombreDeParametro(string valor)
        {
            if (string.IsNullOrWhiteSpace(valor)) return null;

            var minuscula = TextoAscii.AMinusculas(valor.Trim());
            if (minuscula[0] == '.' || minuscula[minuscula.Length - 1] == '.')
                throw new ArgumentException("El nombre del parámetro no puede empezar ni terminar con punto.", nameof(valor));

            for (var i = 0; i < minuscula.Length; i++)
            {
                var c = minuscula[i];
                if (!(TextoAscii.EsMinuscula(c) || TextoAscii.EsDigito(c) || c == '.'))
                    throw new ArgumentException("El nombre del parámetro solo admite letras, dígitos y puntos.", nameof(valor));

                if (c == '.' && minuscula[i - 1] == '.')
                    throw new ArgumentException("El nombre del parámetro no puede tener puntos seguidos.", nameof(valor));
            }

            return minuscula;
        }
    }

    /// <summary>
    /// Los nombres calculados que llena un step PreOperation en el `Create` (diseno/03 §5; diseno/02). No aplica a Autorizado ni
    /// a Parametro, donde la primaria es la clave de negocio (BP-PP-192). Cada uno se recorta al largo de su columna.
    /// </summary>
    public static class NombreCalculado
    {
        /// <summary>Plan: `<codigo> - <cliente>`, T(100). Sin nombre de cliente, solo el código.</summary>
        public static string DePlan(string codigo, string nombreDelCliente)
        {
            if (string.IsNullOrWhiteSpace(codigo))
                throw new ArgumentException("El código del plan es obligatorio para armar su nombre.", nameof(codigo));

            var nombre = string.IsNullOrWhiteSpace(nombreDelCliente)
                ? codigo
                : codigo + " - " + nombreDelCliente;

            return TextoAscii.Recortar(nombre, 100);
        }

        /// <summary>AutorizacionPlan: `<correo> → <plan>`, T(400).</summary>
        public static string DeAutorizacionPlan(string correo, string codigoDePlan)
        {
            if (string.IsNullOrWhiteSpace(correo))
                throw new ArgumentException("El correo es obligatorio para armar el nombre de la autorización.", nameof(correo));
            if (string.IsNullOrWhiteSpace(codigoDePlan))
                throw new ArgumentException("El código del plan es obligatorio para armar el nombre de la autorización.", nameof(codigoDePlan));

            var nombre = correo + " → " + codigoDePlan;
            return TextoAscii.Recortar(nombre, 400);
        }

        /// <summary>Fila: `<solicitud>-F<nn>`, T(120), con el número de fila en dos dígitos como mínimo.</summary>
        public static string DeFila(string numeroDeSolicitud, int numeroDeFila)
        {
            if (string.IsNullOrWhiteSpace(numeroDeSolicitud))
                throw new ArgumentException("El número de solicitud es obligatorio para armar el nombre de la fila.", nameof(numeroDeSolicitud));
            if (numeroDeFila < 1)
                throw new ArgumentOutOfRangeException(nameof(numeroDeFila), numeroDeFila, "El número de fila tiene que ser 1 o más.");

            // El número nunca se recorta (diseño): si hace falta recortar, se recorta la parte de la solicitud.
            var sufijo = "-F" + numeroDeFila.ToString("00", CultureInfo.InvariantCulture);
            var maximoParaSolicitud = 120 - sufijo.Length;
            var solicitud = TextoAscii.Recortar(numeroDeSolicitud, maximoParaSolicitud);

            return solicitud + sufijo;
        }
    }
}
