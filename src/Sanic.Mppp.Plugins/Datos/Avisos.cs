using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
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

        // Los nombres de los roles, tal como se LLAMAN en el entorno (columna `name` de la tabla
        // `role`), que es por donde el plugin los busca. No es el nombre del archivo del playbook.
        //
        // Hasta el 2026-09-23 estas constantes decían `sr_mppp_ejecutivo`, tomado del nombre de
        // `playbooks/rol/sr_mppp_ejecutivo.md`. Ese valor no existe en ninguna columna de
        // Dataverse: el rol se llama `SR - MPPP - Ejecutivo`. La consulta devolvía cero filas
        // SIEMPRE, `DeterminarRoles` caía en `RolDeActor.Ninguno` y **ninguna transición de Fila
        // se podía autorizar, para nadie**. Las 793 pruebas pasaban porque el doble sembraba el
        // mismo string equivocado. Un identificador con el que se le habla al entorno se verifica
        // CONTRA EL ENTORNO (`herramientas/pruebas/verificar_roles.py`), no contra una constante.

        /// <summary>El rol de Ejecutivo (playbooks/rol/sr_mppp_ejecutivo.md; diseno/04 §2).</summary>
        public const string RolEjecutivo = "SR - MPPP - Ejecutivo";

        /// <summary>El rol de Supervisor (playbooks/rol/sr_mppp_supervisor.md; diseno/04 §2).</summary>
        public const string RolSupervisor = "SR - MPPP - Supervisor";

        /// <summary>
        /// D-44: el usuario de aplicación del RPA tiene su propio rol, distinto del de la cuenta de
        /// servicio de los flujos. Es de FASE 2 y todavía NO existe en el entorno: hasta que se cree
        /// con este nombre, ninguna transición del RPA es posible, que es lo correcto en fase 1.
        /// </summary>
        public const string RolRpa = "SR - MPPP - RPA";

        /// <summary>`title` de `appnotification`: 256 caracteres (Microsoft Learn, tabla `appnotification`).</summary>
        public const int LargoTitulo = 256;

        /// <summary>
        /// `body` de `appnotification`: 500 caracteres (Microsoft Learn, tabla `appnotification`). Revisión de código,
        /// 2026-09-21: acá decía 2000, así que un cuerpo largo no se recortaba y el `Create` habría fallado en Dataverse.
        /// </summary>
        public const int LargoCuerpo = 500;
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
        private const string ColumnaIdRol = "roleid";
        private const string ColumnaIdUsuario = "systemuserid";

        private readonly IOrganizationService _servicio;

        public AvisosDataverse(IOrganizationService servicio)
        {
            _servicio = servicio ?? throw new ArgumentNullException(nameof(servicio));
        }

        public void AvisarAEjecutivos(Guid solicitudId, string titulo, string cuerpo)
        {
            if (solicitudId == Guid.Empty)
            {
                throw new ArgumentException("El id de la solicitud no puede estar vacío.", nameof(solicitudId));
            }

            if (string.IsNullOrWhiteSpace(titulo))
            {
                throw new ArgumentException("El título del aviso no puede estar vacío.", nameof(titulo));
            }

            if (string.IsNullOrWhiteSpace(cuerpo))
            {
                throw new ArgumentException("El cuerpo del aviso no puede estar vacío.", nameof(cuerpo));
            }

            // Consulta 1: el rol Ejecutivo. Si no existe, nadie tiene que enterarse (DA-08): que nadie tenga el rol
            // no puede tumbar la clasificación de un correo.
            var consultaRol = new QueryExpression(TablasNativas.Rol) { ColumnSet = new ColumnSet(false) };
            consultaRol.Criteria.AddCondition("name", ConditionOperator.Equal, TablasNativas.RolEjecutivo);
            var rolesEjecutivo = _servicio.RetrieveMultiple(consultaRol).Entities.Select(e => e.Id).ToList();
            if (rolesEjecutivo.Count == 0)
            {
                return;
            }

            // Consulta 2: quiénes tienen ese rol asignado (repetido o no).
            var consultaAsignaciones = new QueryExpression(TablasNativas.UsuarioRol) { ColumnSet = new ColumnSet(ColumnaIdUsuario) };
            consultaAsignaciones.Criteria.AddCondition("roleid", ConditionOperator.In, rolesEjecutivo.Cast<object>().ToArray());
            var usuariosConRol = _servicio.RetrieveMultiple(consultaAsignaciones).Entities
                .Select(e => e.GetAttributeValue<EntityReference>(ColumnaIdUsuario).Id)
                .Distinct()
                .ToList();
            if (usuariosConRol.Count == 0)
            {
                return;
            }

            // Consulta 3: de esos, quiénes están habilitados hoy.
            var consultaUsuarios = new QueryExpression(TablasNativas.Usuario) { ColumnSet = new ColumnSet(false) };
            consultaUsuarios.Criteria.AddCondition(ColumnaIdUsuario, ConditionOperator.In, usuariosConRol.Cast<object>().ToArray());
            consultaUsuarios.Criteria.AddCondition("isdisabled", ConditionOperator.Equal, false);
            var usuariosHabilitados = _servicio.RetrieveMultiple(consultaUsuarios).Entities.Select(e => e.Id);

            var tituloRecortado = Recortar(titulo, TablasNativas.LargoTitulo);
            var cuerpoRecortado = Recortar(cuerpo, TablasNativas.LargoCuerpo);

            // Un Create por destinatario (DA-08: "una por solicitud y por tanda, nunca una por fila" — acá la
            // "tanda" es el correo sin procesar, y cada ejecutivo recibe la suya).
            foreach (var usuarioId in usuariosHabilitados)
            {
                var aviso = new Entity(TablasNativas.Notificacion)
                {
                    ["title"] = tituloRecortado,
                    ["body"] = cuerpoRecortado,
                    ["ownerid"] = new EntityReference(TablasNativas.Usuario, usuarioId),
                };
                _servicio.Create(aviso);
            }
        }

        /// <summary>Recorta sin partir un par subrogado (un carácter Unicode fuera del plano básico ocupa dos `char`).</summary>
        private static string Recortar(string texto, int largoMaximo)
        {
            if (texto.Length <= largoMaximo)
            {
                return texto;
            }

            var corte = largoMaximo;
            if (char.IsHighSurrogate(texto[corte - 1]))
            {
                corte--;
            }

            return texto.Substring(0, corte);
        }
    }
}
