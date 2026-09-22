using System;
using Microsoft.Xrm.Sdk;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// 7.9, transición de estado de Fila: `Update` de Fila, PreOperation, síncrono, filtro `sanic_estado`, con pre-image
    /// (`sanic_estado`, `sanic_digitadapor`, `sanic_solicitudid`), orden 1 (diseno/03 §4, D-25). Contrato (lo fijan las pruebas
    /// `StepsDeFilaAceptacion`):
    ///  - el estado de origen sale de la PRE-IMAGE, nunca del `Target` (nadie puede decir de dónde venía);
    ///  - **quién actúa**: si escribe una persona, `sanic_digitadapor`, `sanic_aprobadapor` y sus fechas que vengan en el `Target`
    ///    se IGNORAN y se pisan con `InitiatingUserId` y la fecha del contexto; si escribe código de servidor, se confía en el
    ///    `Target` (es la Custom API del RPA, que ya puso al usuario del bot; `03` §4);
    ///  - los roles del actor se leen de sus security roles (Ejecutivo, Supervisor, RPA), con un número fijo de consultas;
    ///  - la transición se evalúa SIEMPRE con <see cref="Dominio.TransicionesDeFila"/>, venga de quien venga, y si no está
    ///    permitida el guardado se rechaza con su motivo;
    ///  - `rpa.puedeaprobar` se lee del parámetro (`si` habilita la excepción; ausente o cualquier otra cosa = no);
    ///  - los efectos se escriben en el `Target`: Digitada pone `sanic_digitadapor`/`sanic_fechadigitada`; Aprobada pone
    ///    `sanic_aprobadapor`/`sanic_fechaaprobada`; Devolver limpia `sanic_digitadapor`/`sanic_fechadigitada`;
    ///  - un `Update` que no cambia el estado (el `Target` no trae `sanic_estado`) no hace nada.
    /// </summary>
    public sealed class TransicionDeFilaStep : IPlugin
    {
        public const string ParametroRpaPuedeAprobar = "rpa.puedeaprobar";

        public void Execute(IServiceProvider serviceProvider)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// 7.9, post-transición: `Update` de Fila, PostOperation, filtro `sanic_estado`, con pre-image (`sanic_estado`,
    /// `sanic_solicitudid`, `sanic_numerofila`) (diseno/03 §4 "Cierre"). Contrato:
    ///  - escribe la Bitácora del evento que corresponde a la transición (Fila digitada, aprobada, devuelta, rechazada en AS400,
    ///    anulada), con el número de fila y el nombre de quien actuó en texto;
    ///  - después mira las filas de esa Solicitud: si la Solicitud sigue En proceso y ya no queda ninguna en Validada ni en
    ///    Digitada (<see cref="Dominio.CierreDeSolicitud"/>), la pasa a **Procesada**, pone `sanic_fechaprocesada` y arma
    ///    `sanic_respuestafinalcontenido` con <see cref="Respuesta.ArmadorRespuesta.RespuestaFinal"/>. El paso a Cerrada NO es de
    ///    este plugin (lo hace `MPPP-ENV` al enviar);
    ///  - si la Solicitud no está En proceso, o todavía quedan filas abiertas, solo queda la Bitácora;
    ///  - todo con un número fijo de consultas: las filas de la Solicitud en UNA, y la Solicitud en otra.
    /// </summary>
    public sealed class PostTransicionDeFilaStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// 7.12, atender un correo por clasificar: `Update` de Solicitud, PreOperation, filtro `sanic_estadoprocesamiento`
    /// (diseno/03 §5; diseno/07 DF-09). Contrato:
    ///  - solo se admite salir de **No reconocida** o **No es correo nuevo**, y solo hacia **Cerrada** o **Descartada**;
    ///  - cualquier otro cambio de estado hecho por una PERSONA se rechaza con su motivo (el código de servidor no pasa por acá:
    ///    la Custom API y `MPPP-VIG` mueven los estados que les tocan);
    ///  - no completa ninguna columna propia: quién atendió y cuándo queda en la Bitácora, con `sanic_actortexto` (D-21).
    /// </summary>
    public sealed class AtenderPorClasificarStep : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            throw new NotImplementedException();
        }
    }
}
