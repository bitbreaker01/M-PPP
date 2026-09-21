using System;
using System.Collections.Generic;
using System.Linq;

namespace Sanic.Mppp.Plugins.Dominio
{
    /// <summary>diseno/03 §4, "Cierre": cuándo una Solicitud En proceso pasa a Procesada.</summary>
    public static class CierreDeSolicitud
    {
        /// <summary>
        /// "El step PostOperation revisa, tras cada cambio de estado de Fila, si la Solicitud sigue En proceso
        /// y ya no queda ninguna fila en Validada ni Digitada. Si es así, pasa la Solicitud a Procesada" (03 §4, "Cierre").
        /// </summary>
        public static bool CorrespondeProcesar(EstadoDeLaSolicitud estado, IEnumerable<EstadoDeLaFila> estadosDeSusFilas)
        {
            if (estadosDeSusFilas == null)
            {
                throw new ArgumentNullException(nameof(estadosDeSusFilas));
            }

            return estado == EstadoDeLaSolicitud.EnProceso && !estadosDeSusFilas.Any(TransicionesDeFila.EstaAbierta);
        }
    }
}
