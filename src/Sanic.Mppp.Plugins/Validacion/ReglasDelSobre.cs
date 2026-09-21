using System;
using System.Collections.Generic;
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
        public SobreEnValidacion(int cantidadAdjuntos, int cantidadExcel, Func<ResultadoLecturaPlantilla> leerPlantilla)
        {
            throw new NotImplementedException();
        }

        public int CantidadAdjuntos { get; }

        public int CantidadExcel { get; }

        /// <summary>True si alguien ya pidió <see cref="Lectura"/>. El plugin lo usa para no abrir el Excel por su cuenta.</summary>
        public bool PlantillaLeida { get; }

        /// <summary>El resultado del lector de 7.2. La primera vez invoca la función; después devuelve lo mismo. Nunca nulo.</summary>
        public ResultadoLecturaPlantilla Lectura => throw new NotImplementedException();
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
            throw new NotImplementedException();
        }
    }
}
