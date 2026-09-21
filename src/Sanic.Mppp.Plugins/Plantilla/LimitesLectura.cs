using System;

namespace Sanic.Mppp.Plugins.Plantilla
{
    /// <summary>
    /// Parámetro `lectura.limites` (diseno/03 §7 LP-02, LP-03 y LP-08). Los valores por defecto son los iniciales del diseño
    /// y valen solo si el parámetro falta. Ya NO existen topes de filas recorridas ni de celdas por fila: el costo lo acota la ventana.
    /// </summary>
    public sealed class LimitesLectura
    {
        /// <summary>Peso máximo del archivo comprimido. Por defecto 2 MB.</summary>
        public long TamanoMaximoBytesEntrada { get; set; } = 2L * 1024 * 1024;

        /// <summary>Peso máximo declarado del contenido descomprimido. Por defecto 20 MB.</summary>
        public long TamanoMaximoBytesDescomprimidos { get; set; } = 20L * 1024 * 1024;

        /// <summary>
        /// Lee {"maximoBytesComprimido":2097152,"maximoBytesDescomprimido":20971520}. Una clave que falta toma su valor por defecto;
        /// `null` o vacío devuelve todos los valores por defecto; un valor que no es un entero positivo es <see cref="FormatException"/>.
        /// </summary>
        public static LimitesLectura DesdeJson(string json)
        {
            throw new NotImplementedException();
        }
    }
}
