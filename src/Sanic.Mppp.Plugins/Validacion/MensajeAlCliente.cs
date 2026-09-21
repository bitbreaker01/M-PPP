using System;
using System.Collections.Generic;
using System.Text;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>
    /// Arma el texto que lee el cliente del banco cuando una regla no se cumple (D-19, aprobador 2026-09-21). El catálogo trae una PLANTILLA
    /// (`sanic_mensajecliente`) que el negocio puede redactar sin tocar código; el evaluador trae su texto por defecto, los valores de los
    /// marcadores y la precisión del caso. Contrato (lo fijan las pruebas de aceptación `MensajeAlClienteAceptacion`):
    ///  - plantilla nula o en blanco → el texto por defecto del evaluador;
    ///  - un marcador es `{nombre}`, exacto (minúsculas, sin espacios); `{regla}` lo pone el motor y gana; los demás, el evaluador;
    ///  - una plantilla con CUALQUIER llave que no sea parte de un marcador que alguien sabe completar (`{plna}`, `{VALOR}`, `{ valor }`,
    ///    una `{` suelta) NO se usa: rige el texto por defecto. Un error de tipeo del negocio nunca le llega roto al cliente;
    ///  - un marcador conocido con valor nulo se completa con vacío; si el texto queda en blanco, rige el por defecto;
    ///  - los valores se insertan TAL CUAL y no se vuelven a expandir: vienen del Excel del cliente, que es hostil;
    ///  - la precisión, si hay, se agrega al final, separada por un espacio, en los dos casos;
    ///  - el resultado nunca es nulo ni en blanco.
    /// Función pura.
    /// </summary>
    public static class MensajeAlCliente
    {
        public static string Componer(string plantilla, Veredicto veredicto, string codigoDeRegla)
        {
            if (veredicto == null)
            {
                throw new ArgumentNullException(nameof(veredicto));
            }

            if (veredicto.Cumple)
            {
                throw new ArgumentException("Solo se compone el mensaje de un veredicto que no se cumple.", nameof(veredicto));
            }

            if (string.IsNullOrWhiteSpace(codigoDeRegla))
            {
                throw new ArgumentException("Toda regla tiene código: sin código no hay quién ponga '{regla}'.", nameof(codigoDeRegla));
            }

            // El motor SIEMPRE gana en '{regla}' (D-19), aunque el evaluador haya traído un marcador propio con ese nombre.
            var marcadores = new Dictionary<string, string>(veredicto.Marcadores, StringComparer.Ordinal);
            marcadores["regla"] = codigoDeRegla;

            string texto = null;
            if (!string.IsNullOrWhiteSpace(plantilla) && TryComponerConPlantilla(plantilla, marcadores, out var compuesto))
            {
                compuesto = compuesto.Trim();
                if (compuesto.Length > 0)
                {
                    texto = compuesto;
                }
            }

            // Plantilla ausente, en blanco, con una llave que nadie sabe completar, o que quedó en blanco tras reemplazar: el por
            // defecto del evaluador rige (el veredicto ya garantiza que Razon nunca está en blanco).
            if (texto == null)
            {
                texto = veredicto.Razon.Trim();
            }

            // La precisión (si hay) va al final, separada por un espacio, en los dos casos, y TAL CUAL: no se vuelve a expandir.
            if (!string.IsNullOrEmpty(veredicto.Precision))
            {
                texto = texto + " " + veredicto.Precision;
            }

            return texto;
        }

        /// <summary>
        /// Reemplaza los marcadores de <paramref name="plantilla"/> en UNA sola pasada (nunca <c>Replace</c> encadenados: un valor del
        /// Excel del cliente que trajera "{regla}" no se tiene que volver a expandir). Cualquier '{' o '}' que no sea parte de un
        /// marcador `{nombre}` EXACTO presente en <paramref name="marcadores"/> invalida la plantilla entera.
        /// </summary>
        private static bool TryComponerConPlantilla(string plantilla, IDictionary<string, string> marcadores, out string resultado)
        {
            var texto = new StringBuilder(plantilla.Length);
            var i = 0;
            while (i < plantilla.Length)
            {
                var caracter = plantilla[i];
                if (caracter == '{')
                {
                    var cierre = plantilla.IndexOf('}', i + 1);
                    if (cierre < 0)
                    {
                        // Llave abierta sin cerrar: llave suelta.
                        resultado = null;
                        return false;
                    }

                    var nombre = plantilla.Substring(i + 1, cierre - i - 1);
                    string valor;
                    if (!marcadores.TryGetValue(nombre, out valor))
                    {
                        // Nombre desconocido (typo, mayúsculas, espacios, o incluso otra '{' anidada): nadie lo sabe completar.
                        resultado = null;
                        return false;
                    }

                    // El valor entra TAL CUAL, sin volver a escanearlo: seguimos leyendo la plantilla después de la llave de cierre.
                    texto.Append(valor ?? string.Empty);
                    i = cierre + 1;
                }
                else if (caracter == '}')
                {
                    // Llave de cierre sin una de apertura que la reclame: también es una llave suelta.
                    resultado = null;
                    return false;
                }
                else
                {
                    texto.Append(caracter);
                    i++;
                }
            }

            resultado = texto.ToString();
            return true;
        }
    }
}
