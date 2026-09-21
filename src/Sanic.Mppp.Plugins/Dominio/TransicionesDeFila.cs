using System;
using System.Collections.Generic;

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

        private const string MensajeRolNoAutorizado = "El rol de quien llama no puede hacer esta transición.";
        private const string MensajeFaltaMensaje = "Esta transición exige un mensaje que explique el motivo.";
        private const string MensajeAmbosRoles = "Un usuario con los roles de Ejecutivo y de Supervisor no puede hacer ninguna transición (D-25).";
        private const string MensajeSinDigitador = "No se puede aprobar una fila sin saber quién la digitó.";
        private const string MensajeMismoDigitador = "Quien digitó la fila no puede aprobarla: falta la segregación de funciones.";

        /// <summary>Una fila de la tabla de diseno/03 §4: desde, hacia (la clave), quién autoriza, si exige mensaje, efecto y evento.</summary>
        private sealed class DefinicionDeTransicion
        {
            public bool RequiereMensaje;

            public EfectoDeTransicion Efecto;

            public EventoDeBitacora Evento;

            /// <summary>Devuelve `null` si el actor puede hacer la transición, o el motivo por el que no.</summary>
            public Func<PedidoDeTransicion, string> Autorizar;
        }

        private static bool EsSoloEsteRol(RolDeActor roles, RolDeActor esperado) => roles == esperado;

        /// <summary>Digitar y Rechazar en AS400 los hace "quien digita": Ejecutivo, o el usuario de aplicación del RPA (03 §4).</summary>
        private static string AutorizarQuienDigita(PedidoDeTransicion p) =>
            EsSoloEsteRol(p.Actor.Roles, RolDeActor.Ejecutivo) || EsSoloEsteRol(p.Actor.Roles, RolDeActor.Rpa)
                ? null
                : MensajeRolNoAutorizado;

        /// <summary>Anular: "Solo Ejecutivo (...); el RPA nunca anula" (03 §4).</summary>
        private static string AutorizarAnular(PedidoDeTransicion p) =>
            EsSoloEsteRol(p.Actor.Roles, RolDeActor.Ejecutivo) ? null : MensajeRolNoAutorizado;

        /// <summary>Devolver: solo el Supervisor, con mensaje (03 §4, DD-07).</summary>
        private static string AutorizarDevolver(PedidoDeTransicion p) =>
            EsSoloEsteRol(p.Actor.Roles, RolDeActor.Supervisor) ? null : MensajeRolNoAutorizado;

        /// <summary>
        /// Aprobar: Supervisor distinto de quien digitó (segregación), o el RPA aprobando lo que él mismo
        /// digitó, solo si `rpa.puedeaprobar` lo habilita (03 §4, la excepción del RPA).
        /// </summary>
        private static string AutorizarAprobar(PedidoDeTransicion p)
        {
            if (EsSoloEsteRol(p.Actor.Roles, RolDeActor.Supervisor))
            {
                if (p.DigitadaPor == null)
                {
                    return MensajeSinDigitador;
                }

                return p.DigitadaPor == p.Actor.UsuarioId ? MensajeMismoDigitador : null;
            }

            if (EsSoloEsteRol(p.Actor.Roles, RolDeActor.Rpa))
            {
                return p.RpaPuedeAprobar && p.DigitadaPor == p.Actor.UsuarioId ? null : MensajeRolNoAutorizado;
            }

            return MensajeRolNoAutorizado;
        }

        /// <summary>La tabla De / A / Quién / Condición / Efecto de diseno/03 §4, una fila por transición.</summary>
        private static readonly Dictionary<(EstadoDeLaFila Desde, EstadoDeLaFila Hacia), DefinicionDeTransicion> Tabla =
            new Dictionary<(EstadoDeLaFila, EstadoDeLaFila), DefinicionDeTransicion>
            {
                [(EstadoDeLaFila.Validada, EstadoDeLaFila.Digitada)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = false,
                    Efecto = EfectoDeTransicion.RegistrarDigitacion,
                    Evento = EventoDeBitacora.FilaDigitada,
                    Autorizar = AutorizarQuienDigita,
                },
                [(EstadoDeLaFila.Validada, EstadoDeLaFila.RechazadaEnAS400)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = true,
                    Efecto = EfectoDeTransicion.Ninguno,
                    Evento = EventoDeBitacora.FilaRechazadaEnAS400,
                    Autorizar = AutorizarQuienDigita,
                },
                [(EstadoDeLaFila.Digitada, EstadoDeLaFila.RechazadaEnAS400)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = true,
                    Efecto = EfectoDeTransicion.Ninguno,
                    Evento = EventoDeBitacora.FilaRechazadaEnAS400,
                    Autorizar = AutorizarQuienDigita,
                },
                [(EstadoDeLaFila.Validada, EstadoDeLaFila.Anulada)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = true,
                    Efecto = EfectoDeTransicion.Ninguno,
                    Evento = EventoDeBitacora.FilaAnulada,
                    Autorizar = AutorizarAnular,
                },
                [(EstadoDeLaFila.Digitada, EstadoDeLaFila.Anulada)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = true,
                    Efecto = EfectoDeTransicion.Ninguno,
                    Evento = EventoDeBitacora.FilaAnulada,
                    Autorizar = AutorizarAnular,
                },
                [(EstadoDeLaFila.Digitada, EstadoDeLaFila.Aprobada)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = false,
                    Efecto = EfectoDeTransicion.RegistrarAprobacion,
                    Evento = EventoDeBitacora.FilaAprobada,
                    Autorizar = AutorizarAprobar,
                },
                [(EstadoDeLaFila.Digitada, EstadoDeLaFila.Validada)] = new DefinicionDeTransicion
                {
                    RequiereMensaje = true,
                    Efecto = EfectoDeTransicion.LimpiarDigitacion,
                    Evento = EventoDeBitacora.FilaDevuelta,
                    Autorizar = AutorizarDevolver,
                },
            };

        public static ResultadoDeTransicion Evaluar(PedidoDeTransicion pedido)
        {
            if (pedido == null)
            {
                throw new ArgumentNullException(nameof(pedido));
            }

            if (pedido.Actor == null)
            {
                throw new ArgumentNullException(nameof(pedido.Actor));
            }

            if (!Tabla.TryGetValue((pedido.Desde, pedido.Hacia), out var definicion))
            {
                return new ResultadoDeTransicion(false, NoPermitida, EfectoDeTransicion.Ninguno, null);
            }

            // D-25 (04 §2): Ejecutivo y Supervisor son mutuamente excluyentes por usuario, para cualquier transición.
            if (pedido.Actor.Roles.HasFlag(RolDeActor.Ejecutivo) && pedido.Actor.Roles.HasFlag(RolDeActor.Supervisor))
            {
                return new ResultadoDeTransicion(false, MensajeAmbosRoles, EfectoDeTransicion.Ninguno, null);
            }

            var motivoDeRechazo = definicion.Autorizar(pedido);
            if (motivoDeRechazo != null)
            {
                return new ResultadoDeTransicion(false, motivoDeRechazo, EfectoDeTransicion.Ninguno, null);
            }

            if (definicion.RequiereMensaje && string.IsNullOrWhiteSpace(pedido.Mensaje))
            {
                return new ResultadoDeTransicion(false, MensajeFaltaMensaje, EfectoDeTransicion.Ninguno, null);
            }

            return new ResultadoDeTransicion(true, null, definicion.Efecto, definicion.Evento);
        }

        /// <summary>Una fila "abierta" todavía espera trabajo en AS400: Validada o Digitada.</summary>
        public static bool EstaAbierta(EstadoDeLaFila estado) =>
            estado == EstadoDeLaFila.Validada || estado == EstadoDeLaFila.Digitada;
    }
}
