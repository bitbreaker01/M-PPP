using System;
using System.Collections.Generic;
using System.Text;
using Microsoft.Xrm.Sdk;

namespace Sanic.Mppp.Plugins.Zzspikec05
{
    /// <summary>
    /// Step de PreOperation en Update de sanic_mppp_tbl_zzspike, filtrado por el atributo
    /// sanic_clave. Pregunta 5 / 5 bis del spike C-05 parte B: como identificar, de forma no
    /// falsificable, al actor que origino la llamada cuando el Update que dispara este step
    /// viene anidado dentro de una Custom API (con SYSTEM o con el usuario que llama).
    ///
    /// Captura y anota en sanic_actorcapturado (resumen) y sanic_actordetalle (completo):
    ///   1. context.UserId / context.InitiatingUserId de este mismo contexto.
    ///   2. La cadena completa de context.ParentContext hasta null (MessageName,
    ///      PrimaryEntityName, Stage, Depth, UserId, InitiatingUserId de cada nivel).
    ///   3. Si la clave "zz_actor" aparece en context.SharedVariables o en el
    ///      SharedVariables de algun ParentContext de la cadena, y en cual.
    ///
    /// Modifica el Target directamente (PreOperation, antes del write a la base): no hace
    /// falta un Update aparte ni guarda de recursion, porque el filtro por sanic_clave hace
    /// que este step nunca se dispare de nuevo al escribir solo sanic_actorcapturado /
    /// sanic_actordetalle.
    /// </summary>
    public class ActorCaptureStep : PluginBase
    {
        public ActorCaptureStep(string unsecureConfiguration, string secureConfiguration)
            : base(typeof(ActorCaptureStep))
        {
        }

        protected override void ExecuteDataversePlugin(ILocalPluginContext localPluginContext)
        {
            if (localPluginContext == null)
            {
                throw new ArgumentNullException(nameof(localPluginContext));
            }

            IPluginExecutionContext context = localPluginContext.PluginExecutionContext;

            if (!context.InputParameters.TryGetValue("Target", out object targetObj) || !(targetObj is Entity target))
            {
                return;
            }

            var detalle = new StringBuilder();

            detalle.AppendLine($"[propio] MessageName={context.MessageName};PrimaryEntityName={context.PrimaryEntityName};Stage={context.Stage};Depth={context.Depth};UserId={context.UserId};InitiatingUserId={context.InitiatingUserId}");

            // Cadena completa de ParentContext hasta null.
            var cadenaParents = new List<IPluginExecutionContext>();
            IPluginExecutionContext actual = context.ParentContext;
            int nivel = 0;
            while (actual != null)
            {
                cadenaParents.Add(actual);
                detalle.AppendLine($"[parent nivel {nivel}] MessageName={actual.MessageName};PrimaryEntityName={actual.PrimaryEntityName};Stage={actual.Stage};Depth={actual.Depth};UserId={actual.UserId};InitiatingUserId={actual.InitiatingUserId}");
                actual = actual.ParentContext;
                nivel++;
            }
            if (cadenaParents.Count == 0)
            {
                detalle.AppendLine("[parents] ParentContext es null: no hay contexto padre (Update de nivel superior, no anidado).");
            }

            // Busqueda de "zz_actor" en el propio SharedVariables y en el de cada ParentContext.
            string dondeAparece = "no aparece en ningun nivel";
            if (context.SharedVariables.TryGetValue("zz_actor", out object propioValor))
            {
                dondeAparece = $"propio contexto, valor={propioValor}";
            }
            else
            {
                for (int i = 0; i < cadenaParents.Count; i++)
                {
                    if (cadenaParents[i].SharedVariables.TryGetValue("zz_actor", out object valorPadre))
                    {
                        dondeAparece = $"parent nivel {i} (MessageName={cadenaParents[i].MessageName}), valor={valorPadre}";
                        break;
                    }
                }
            }
            detalle.AppendLine($"[zz_actor] {dondeAparece}");

            string resumen = $"UserId={context.UserId};InitiatingUserId={context.InitiatingUserId};Depth={context.Depth};MessageName={context.MessageName};ParentContextNull={(context.ParentContext == null)};ZzActor={dondeAparece}";

            target["sanic_actorcapturado"] = Truncar(resumen, 500);
            target["sanic_actordetalle"] = Truncar(detalle.ToString(), 4000);

            localPluginContext.Trace(detalle.ToString());
        }

        private static string Truncar(string texto, int maxLargo)
        {
            if (string.IsNullOrEmpty(texto) || texto.Length <= maxLargo)
            {
                return texto;
            }
            return texto.Substring(0, maxLargo);
        }
    }
}
