using System;

namespace Sanic.Mppp.Plugins.Dominio
{
    /// <summary>Todo lo que hace falta para decidir un cambio de estado de una Fila (diseno/03 §4). Sin SDK.</summary>
    public sealed class PedidoDeTransicion
    {
        public EstadoDeLaFila Desde { get; set; }

        public EstadoDeLaFila Hacia { get; set; }

        public Actor Actor { get; set; }

        /// <summary>`sanic_mensaje`. Obligatorio en rechazar, anular y devolver.</summary>
        public string Mensaje { get; set; }

        /// <summary>`sanic_digitadapor` de la fila ANTES del cambio. Decide la segregación de funciones al aprobar.</summary>
        public Guid? DigitadaPor { get; set; }

        /// <summary>Parámetro `rpa.puedeaprobar` (por defecto, no).</summary>
        public bool RpaPuedeAprobar { get; set; }
    }

    /// <summary>Lo que el step tiene que hacer con las columnas de quién y cuándo, si la transición se permite.</summary>
    public enum EfectoDeTransicion
    {
        Ninguno = 0,
        /// <summary>`digitadapor` = quien llama, `fechadigitada` = ahora.</summary>
        RegistrarDigitacion = 1,
        /// <summary>`aprobadapor` = quien llama, `fechaaprobada` = ahora.</summary>
        RegistrarAprobacion = 2,
        /// <summary>Limpia `digitadapor` y `fechadigitada` (devolución).</summary>
        LimpiarDigitacion = 3,
    }

    public sealed class ResultadoDeTransicion
    {
        public ResultadoDeTransicion(bool permitida, string motivo, EfectoDeTransicion efecto, EventoDeBitacora? evento)
        {
            Permitida = permitida;
            Motivo = motivo;
            Efecto = efecto;
            Evento = evento;
        }

        public bool Permitida { get; }

        /// <summary>Por qué NO se permite, en texto para el usuario. `null` si se permite.</summary>
        public string Motivo { get; }

        public EfectoDeTransicion Efecto { get; }

        /// <summary>Evento a escribir en la Bitácora. `null` si no se permite.</summary>
        public EventoDeBitacora? Evento { get; }
    }

    /// <summary>La máquina de estados de la Fila. Función pura: no lee reloj, no toca Dataverse.</summary>
    public static class TransicionesDeFila
    {
        /// <summary>Texto exacto de diseno/03 §4 para todo lo que no está en la tabla.</summary>
        public const string NoPermitida = "Transición no permitida";

        public static ResultadoDeTransicion Evaluar(PedidoDeTransicion pedido)
        {
            throw new NotImplementedException();
        }

        /// <summary>Una fila "abierta" todavía espera trabajo en AS400: Validada o Digitada.</summary>
        public static bool EstaAbierta(EstadoDeLaFila estado)
        {
            throw new NotImplementedException();
        }
    }
}
