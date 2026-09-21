using System;

namespace Sanic.Mppp.Plugins.Dominio
{
    /// <summary>Roles que importan para decidir una transición (diseno/04 §2 y §3). Se combinan: un usuario puede traer más de uno.</summary>
    [Flags]
    public enum RolDeActor
    {
        Ninguno = 0,
        Ejecutivo = 1,
        Supervisor = 2,
        /// <summary>El usuario de aplicación del RPA (fase 2).</summary>
        Rpa = 4,
    }

    /// <summary>Quién pide la transición. Sin dependencia del SDK: lo arma la capa de Steps.</summary>
    public sealed class Actor
    {
        public Actor(Guid usuarioId, RolDeActor roles)
        {
            UsuarioId = usuarioId;
            Roles = roles;
        }

        public Guid UsuarioId { get; }

        public RolDeActor Roles { get; }
    }
}
