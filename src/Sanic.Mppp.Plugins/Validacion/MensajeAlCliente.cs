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
        /// <summary>
        /// Largo máximo de un mensaje compuesto (revisión de código, 2026-09-21). `sanic_mensaje` de la Fila es M(4000) y junta los
        /// motivos de hasta ocho reglas, y después se le agrega el motivo de una anulación o devolución: 8 × 450 deja ese margen.
        /// Un texto más largo se corta ahí y termina en "…" (que cuenta dentro del máximo). Sin este tope, un valor larguísimo en
        /// el Excel termina en una excepción de Dataverse al guardar: reintentos, revisión manual y el cliente sin respuesta.
        /// </summary>
        public const int LargoMaximo = 450;

        /// <summary>Largo máximo de un valor del cliente citado en un mensaje.</summary>
        public const int LargoMaximoDeCita = 40;

        /// <summary>
        /// Prepara un valor que escribió el cliente para citarlo en un mensaje (DD-01: "el valor recibido se cita"). El Excel es
        /// hostil: todo carácter de control o de espacio (saltos de línea, tabuladores) pasa a ser un espacio, los espacios
        /// seguidos quedan de a uno, se recorta a los lados, y si pasa de <see cref="LargoMaximoDeCita"/> caracteres se corta ahí
        /// y se le agrega "…". Nulo → vacío. NUNCA se cita un dato sensible (cuenta, identificación): eso lo cuida quien llama.
        /// </summary>
        public static string Citar(string valorDelCliente)
        {
            if (string.IsNullOrEmpty(valorDelCliente))
            {
                return string.Empty;
            }

            // Todo carácter de control o de espacio (saltos de línea, tabuladores) pasa a ser un espacio; el Excel del
            // cliente es hostil y puede traer cualquier cosa en una celda de texto.
            var normalizado = new StringBuilder(valorDelCliente.Length);
            foreach (char caracter in valorDelCliente)
            {
                normalizado.Append(char.IsControl(caracter) || char.IsWhiteSpace(caracter) ? ' ' : caracter);
            }

            // Espacios seguidos de a uno, recortado a los lados: mismo criterio de "una sola línea" que ListasPlantilla.Normalizar.
            var compacto = new StringBuilder(normalizado.Length);
            var huboEspacio = false;
            foreach (char caracter in normalizado.ToString().Trim())
            {
                if (caracter == ' ')
                {
                    if (!huboEspacio)
                    {
                        compacto.Append(caracter);
                    }

                    huboEspacio = true;
                }
                else
                {
                    compacto.Append(caracter);
                    huboEspacio = false;
                }
            }

            string resultado = compacto.ToString();
            if (resultado.Length > LargoMaximoDeCita)
            {
                resultado = resultado.Substring(0, LargoMaximoDeCita) + "…";
            }

            return resultado;
        }

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
            var marcadores = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var marcador in veredicto.Marcadores)
            {
                marcadores[marcador.Key] = marcador.Value;
            }

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

            // `sanic_mensaje` (M(4000)) junta hasta ocho de estos motivos: sin este tope, un valor larguísimo del Excel del
            // cliente (citado o no) termina en una excepción de Dataverse al guardar. Se corta la COLA -el texto general
            // queda adelante- y el "…" cuenta dentro de LargoMaximo (quedan 449 caracteres + "…").
            if (texto.Length > LargoMaximo)
            {
                texto = texto.Substring(0, LargoMaximo - 1) + "…";
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
