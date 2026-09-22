using System;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Api;

namespace Sanic.Mppp.Plugins.Datos
{
    /// <summary>Tablas nativas que toca la capa de datos para los avisos dentro de la app (diseno/05 DA-08).</summary>
    public static class TablasNativas
    {
        public const string Notificacion = "appnotification";
        public const string Usuario = "systemuser";
        public const string Rol = "role";
        public const string UsuarioRol = "systemuserroles";

        /// <summary>El rol de Ejecutivo (playbooks/rol/sr_mppp_ejecutivo.md; diseno/04 §2).</summary>
        public const string RolEjecutivo = "sr_mppp_ejecutivo";

        /// <summary>`title` de `appnotification`: 200 caracteres.</summary>
        public const int LargoTitulo = 200;

        /// <summary>`body` de `appnotification`: 2000 caracteres.</summary>
        public const int LargoCuerpo = 2000;
    }

    /// <summary>
    /// Avisos dentro de la app sobre la tabla nativa `appnotification` (diseno/05 DA-08: "a todos los ejecutivos, cuando un
    /// correo va a Por clasificar"). Contrato (lo fijan las pruebas `AvisosDataverseAceptacion`):
    ///  - los destinatarios son los usuarios HABILITADOS (`isdisabled` = false) que tienen el rol
    ///    <see cref="TablasNativas.RolEjecutivo"/>, resueltos con un número FIJO de consultas (a lo sumo tres: el rol, sus
    ///    usuarios, y los usuarios habilitados), nunca una por usuario;
    ///  - un `Create` de `appnotification` por destinatario, con `title`, `body` (recortados) y `ownerid` = ese usuario;
    ///  - sin destinatarios (no existe el rol, nadie lo tiene, o todos están deshabilitados) NO se crea nada y NO se lanza:
    ///    que nadie tenga el rol no puede tumbar la clasificación de un correo;
    ///  - un usuario repetido (el rol asignado dos veces, o por dos caminos) recibe UN solo aviso;
    ///  - título o cuerpo vacíos, o solicitud vacía: <see cref="ArgumentException"/> antes de tocar el servicio.
    /// El enlace que abre la solicitud desde la campana se agrega cuando se verifique en Dev la forma exacta de `data`
    /// (PENDIENTES §B): hoy el aviso nombra la solicitud en el título y en el cuerpo.
    /// </summary>
    public sealed class AvisosDataverse : IAvisos
    {
        public AvisosDataverse(IOrganizationService servicio)
        {
            throw new NotImplementedException();
        }

        public void AvisarAEjecutivos(Guid solicitudId, string titulo, string cuerpo)
        {
            throw new NotImplementedException();
        }
    }
}
