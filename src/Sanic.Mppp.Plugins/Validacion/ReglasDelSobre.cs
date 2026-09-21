using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Sanic.Mppp.Plugins.Plantilla;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>
    /// Lo que miran las reglas de nivel Solicitud (diseno/03 §1 paso 4): el correo y su adjunto. Sin SDK. Los conteos los llenó
    /// `MPPP-ING` (`sanic_cantidadadjuntos`, `sanic_cantidadexcel`, D-15); que una columna venga vacía lo resuelve quien arma el
    /// sobre (pieza 7.6), no este tipo. La plantilla se lee A DEMANDA y UNA sola vez: abrir el Excel es lo caro, y si el sobre ya
    /// falló antes (sin adjunto, dos Excel) no se abre nada.
    /// </summary>
    public sealed class SobreEnValidacion
    {
        private readonly Func<ResultadoLecturaPlantilla> _leerPlantilla;
        private ResultadoLecturaPlantilla _lectura;
        private bool _plantillaLeida;

        public SobreEnValidacion(int cantidadAdjuntos, int cantidadExcel, Func<ResultadoLecturaPlantilla> leerPlantilla)
        {
            if (cantidadAdjuntos < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(cantidadAdjuntos), cantidadAdjuntos, "La cantidad de adjuntos no puede ser negativa.");
            }

            if (cantidadExcel < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(cantidadExcel), cantidadExcel, "La cantidad de Excel no puede ser negativa.");
            }

            if (cantidadExcel > cantidadAdjuntos)
            {
                throw new ArgumentException("La cantidad de Excel no puede ser mayor que la cantidad de adjuntos.", nameof(cantidadExcel));
            }

            if (leerPlantilla == null)
            {
                throw new ArgumentNullException(nameof(leerPlantilla));
            }

            CantidadAdjuntos = cantidadAdjuntos;
            CantidadExcel = cantidadExcel;
            _leerPlantilla = leerPlantilla;
        }

        public int CantidadAdjuntos { get; }

        public int CantidadExcel { get; }

        /// <summary>True si alguien ya pidió <see cref="Lectura"/>. El plugin lo usa para no abrir el Excel por su cuenta.</summary>
        public bool PlantillaLeida => _plantillaLeida;

        /// <summary>El resultado del lector de 7.2. La primera vez invoca la función; después devuelve lo mismo. Nunca nulo.</summary>
        public ResultadoLecturaPlantilla Lectura
        {
            get
            {
                if (!_plantillaLeida)
                {
                    // Si _leerPlantilla lanza, la excepción se propaga tal cual (diseno/03 §1 "Errores") y NO marcamos
                    // _plantillaLeida: no queda un estado a medio armar que después devuelva null en silencio.
                    var resultado = _leerPlantilla();
                    if (resultado == null)
                    {
                        throw new InvalidOperationException("El lector de la plantilla devolvió un resultado nulo.");
                    }

                    _lectura = resultado;
                    _plantillaLeida = true;
                }

                return _lectura;
            }
        }
    }

    /// <summary>
    /// Los evaluadores de las cinco reglas semilla de nivel Solicitud (diseno/02 §2.6; condiciones exactas: D-15 y D-16, aprobador
    /// 2026-09-21). Cada uno entrega su texto por defecto para el cliente y sus marcadores; el mensaje final lo arma
    /// <see cref="MensajeAlCliente"/> (D-19).
    /// </summary>
    public static class ReglasDelSobre
    {
        public const string TraeAdjunto = "TRAE_ADJUNTO";
        public const string AdjuntoEsExcel = "ADJUNTO_ES_EXCEL";
        public const string UnSoloExcel = "UN_SOLO_EXCEL";
        public const string EstructuraPlantilla = "ESTRUCTURA_PLANTILLA";
        public const string TieneFilas = "TIENE_FILAS";

        /// <summary>Un evaluador por cada código de arriba, ni uno más. Instancias nuevas en cada llamada: no guardan estado.</summary>
        public static IList<IEvaluador<SobreEnValidacion>> Evaluadores()
        {
            return new List<IEvaluador<SobreEnValidacion>>
            {
                new TraeAdjuntoEvaluador(),
                new AdjuntoEsExcelEvaluador(),
                new UnSoloExcelEvaluador(),
                new EstructuraPlantillaEvaluador(),
                new TieneFilasEvaluador(),
            };
        }

        private static string ConteoAdjuntos(int n)
        {
            return n == 1 ? "1 archivo adjunto" : $"{n.ToString(CultureInfo.InvariantCulture)} archivos adjuntos";
        }

        private static string ConteoExcel(int n)
        {
            return n == 1 ? "1 archivo de Excel" : $"{n.ToString(CultureInfo.InvariantCulture)} archivos de Excel";
        }

        private static SobreEnValidacion Requerido(SobreEnValidacion sobre)
        {
            if (sobre == null)
            {
                throw new ArgumentNullException(nameof(sobre));
            }

            return sobre;
        }

        /// <summary>TRAE_ADJUNTO = `sanic_cantidadadjuntos` ≥ 1 (diseno/02 §2.6, D-15).</summary>
        private sealed class TraeAdjuntoEvaluador : IEvaluador<SobreEnValidacion>
        {
            public string Codigo => TraeAdjunto;

            public Veredicto Evaluar(SobreEnValidacion sobre)
            {
                sobre = Requerido(sobre);

                if (sobre.CantidadAdjuntos >= 1)
                {
                    return Veredicto.Cumplida();
                }

                return Veredicto.NoCumplida(
                    "No encontramos ningún archivo adjunto en su correo. Por favor, envíe la plantilla de Excel como adjunto y vuelva a intentarlo.");
            }
        }

        /// <summary>ADJUNTO_ES_EXCEL = `sanic_cantidadexcel` ≥ 1; marcador `valor` = cantidad de adjuntos (diseno/02 §2.6, D-15).</summary>
        private sealed class AdjuntoEsExcelEvaluador : IEvaluador<SobreEnValidacion>
        {
            public string Codigo => AdjuntoEsExcel;

            public Veredicto Evaluar(SobreEnValidacion sobre)
            {
                sobre = Requerido(sobre);

                if (sobre.CantidadExcel >= 1)
                {
                    return Veredicto.Cumplida();
                }

                var razon = $"Recibimos {ConteoAdjuntos(sobre.CantidadAdjuntos)} y ninguno es un archivo de Excel. " +
                            "Por favor, envíe la plantilla en formato Excel (.xlsx).";
                var marcadores = new Dictionary<string, string> { ["valor"] = sobre.CantidadAdjuntos.ToString(CultureInfo.InvariantCulture) };
                return Veredicto.NoCumplida(razon, marcadores, null);
            }
        }

        /// <summary>UN_SOLO_EXCEL = `sanic_cantidadexcel` = 1; marcador `valor` = cantidad de Excel (diseno/02 §2.6, D-15).</summary>
        private sealed class UnSoloExcelEvaluador : IEvaluador<SobreEnValidacion>
        {
            public string Codigo => UnSoloExcel;

            public Veredicto Evaluar(SobreEnValidacion sobre)
            {
                sobre = Requerido(sobre);

                if (sobre.CantidadExcel == 1)
                {
                    return Veredicto.Cumplida();
                }

                var razon = $"Recibimos {ConteoExcel(sobre.CantidadExcel)}; por favor, envíe un único archivo de Excel con la plantilla completa.";
                var marcadores = new Dictionary<string, string> { ["valor"] = sobre.CantidadExcel.ToString(CultureInfo.InvariantCulture) };
                return Veredicto.NoCumplida(razon, marcadores, null);
            }
        }

        /// <summary>
        /// ESTRUCTURA_PLANTILLA = hay exactamente un Excel Y el lector de 7.2 lo da por válido (diseno/02 §2.6). Sin exactamente
        /// un Excel no se abre nada (contrato de la pieza, ni por el motor ni suelto): eso ya lo dice UN_SOLO_EXCEL. Si el lector
        /// lo rechaza, la PRECISIÓN son sus Errores, todos y en su orden, separados por un espacio — nunca su DetalleTecnico
        /// (diseno/03 §1 "Errores": ese detalle es solo para la traza).
        /// </summary>
        private sealed class EstructuraPlantillaEvaluador : IEvaluador<SobreEnValidacion>
        {
            private const string RazonPorDefecto =
                "El archivo de Excel no tiene la estructura de la plantilla esperada. Por favor, solicite la plantilla vigente a su ejecutivo y envíela sin modificar su formato ni sus encabezados.";

            public string Codigo => EstructuraPlantilla;

            public Veredicto Evaluar(SobreEnValidacion sobre)
            {
                sobre = Requerido(sobre);

                if (sobre.CantidadExcel != 1)
                {
                    return Veredicto.NoCumplida(RazonPorDefecto);
                }

                var lectura = sobre.Lectura;
                if (lectura.EsValido)
                {
                    return Veredicto.Cumplida();
                }

                var precision = string.Join(" ", lectura.Errores);
                return Veredicto.NoCumplida(RazonPorDefecto, null, precision);
            }
        }

        /// <summary>
        /// TIENE_FILAS = hay exactamente un Excel, la lectura es válida y trae al menos una fila (diseno/02 §2.6). Igual que
        /// ESTRUCTURA_PLANTILLA: sin exactamente un Excel no se abre nada.
        /// </summary>
        private sealed class TieneFilasEvaluador : IEvaluador<SobreEnValidacion>
        {
            public string Codigo => TieneFilas;

            public Veredicto Evaluar(SobreEnValidacion sobre)
            {
                sobre = Requerido(sobre);

                if (sobre.CantidadExcel != 1)
                {
                    return NoCumpleSinFilas();
                }

                var lectura = sobre.Lectura;
                if (!lectura.EsValido || lectura.Filas == null || lectura.Filas.Count == 0)
                {
                    return NoCumpleSinFilas();
                }

                return Veredicto.Cumplida();
            }

            private static Veredicto NoCumpleSinFilas()
            {
                return Veredicto.NoCumplida(
                    "La plantilla no contiene ninguna fila con datos para procesar. Por favor, complete al menos una fila con la información de la gestión antes de enviarla.");
            }
        }
    }
}
