using System;
using System.Collections.Generic;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Validacion;

namespace Sanic.Mppp.Plugins.Datos
{
    /// <summary>Tablas de la unidad histórica (diseno/02 §3) y sus columnas. Sigue la regla de <see cref="Tablas"/>: único lugar donde se escriben.</summary>
    public static class TablasHistorico
    {
        public const string Solicitud = "sanic_mppp_tbl_solicitud";
        public const string Fila = "sanic_mppp_tbl_fila";
        public const string ResultadoRegla = "sanic_mppp_tbl_resultadoregla";
        public const string Bitacora = "sanic_mppp_tbl_bitacora";

        /// <summary>Tamaño máximo de un lote de `ExecuteMultiple` (límite de la plataforma: 1000; se usa un margen amplio).</summary>
        public const int TamanoDeLote = 100;
    }

    /// <summary>Lo que el plugin liviano y el de validación leen de una Solicitud (diseno/02 §3.1). Sin SDK hacia afuera.</summary>
    public sealed class SolicitudLeida
    {
        public Guid Id { get; set; }

        /// <summary>`sanic_nombre` (`MPPP-00000123`).</summary>
        public string Numero { get; set; }

        public EstadoDeLaSolicitud Estado { get; set; }

        public string Remitente { get; set; }

        public string Asunto { get; set; }

        public DateTime FechaRecibido { get; set; }

        /// <summary>`sanic_cantidadadjuntos`; 0 si la columna viene vacía.</summary>
        public int CantidadAdjuntos { get; set; }

        /// <summary>`sanic_cantidadexcel`; 0 si la columna viene vacía (D-15; quien la llena es `MPPP-ING`).</summary>
        public int CantidadExcel { get; set; }

        /// <summary>`sanic_versionparametros`, puede ser nulo.</summary>
        public string VersionParametros { get; set; }
    }

    /// <summary>Lo que el plugin de validación escribe en la Solicitud al terminar (diseno/03 §1 pasos 4 y 7). Solo se escribe lo que no es nulo.</summary>
    public sealed class CierreDeValidacion
    {
        public EstadoDeLaSolicitud Estado { get; set; }

        public DateTime FechaValidada { get; set; }

        public int FilasTotales { get; set; }

        public int FilasValidas { get; set; }

        public int FilasRechazadas { get; set; }

        /// <summary>El HTML del acuse (`sanic_acusecontenido`).</summary>
        public string AcuseContenido { get; set; }

        /// <summary>`sanic_versionparametros`: versiones de los parámetros `plantilla.*` usadas (`listas=3;estructura=2;obligatoriedad=1`).</summary>
        public string VersionParametros { get; set; }
    }

    /// <summary>Lo que el plugin liviano escribe cuando el correo no se procesa (diseno/03 §0 paso 4).</summary>
    public sealed class ClasificacionDelCorreo
    {
        public EstadoDeLaSolicitud Estado { get; set; }

        /// <summary>`sanic_motivoclasificacion`, T(300): se recorta a 300.</summary>
        public string Motivo { get; set; }
    }

    /// <summary>Una fila lista para guardarse en `sanic_mppp_tbl_fila` (diseno/02 §3.2). Lo arma el plugin desde <see cref="FilaEnValidacion"/>.</summary>
    public sealed class FilaParaGuardar
    {
        public int NumeroFila { get; set; }

        public Gestion? Gestion { get; set; }

        public Clasificacion? Clasificacion { get; set; }

        public Moneda? Moneda { get; set; }

        public TipoDeIdentificacion? TipoIdentificacion { get; set; }

        public Banco? Banco { get; set; }

        public string NumeroPlan { get; set; }

        public Guid? PlanId { get; set; }

        public string NombreBeneficiario { get; set; }

        public string NumeroIdentificacion { get; set; }

        public string NumeroCuenta { get; set; }

        public string Referencia { get; set; }

        public string ReferenciaRecibida { get; set; }

        public EstadoDeLaFila Estado { get; set; }

        /// <summary>`sanic_mensaje` M(4000): se recorta a 4000 al guardar.</summary>
        public string Mensaje { get; set; }

        public DateTime FechaValidada { get; set; }
    }

    /// <summary>
    /// Lectura y escritura de la Solicitud y su unidad histórica sobre <see cref="IOrganizationService"/> (pieza 7.6, `Datos/`).
    /// Reglas (las fijan las pruebas `SolicitudesDataverseAceptacion`): se leen solo las columnas usadas; los choices se traducen a
    /// los enums de `Dominio` y un valor fuera del enum es <see cref="InvalidOperationException"/> con tabla, columna y registro; los
    /// textos se recortan al largo de su columna (diseno/02) antes de escribir; las altas masivas van en lotes de
    /// <see cref="TablasHistorico.TamanoDeLote"/> con `ExecuteMultiple` (`ContinueOnError` = false) y si un ítem falla se lanza la
    /// falla del servicio; los lookups a Solicitud son `EntityReference`; toda escritura de estado de Solicitud va por
    /// `sanic_estadoprocesamiento`; nada de acá fija la fecha: la recibe (el plugin la toma del contexto). Servicio nulo:
    /// <see cref="ArgumentNullException"/>.
    /// </summary>
    public sealed class SolicitudesDataverse
    {
        public SolicitudesDataverse(IOrganizationService servicio)
        {
            throw new NotImplementedException();
        }

        /// <summary>Una lectura. Inexistente: se propaga la falla del servicio. Estado fuera del enum o `sanic_nombre`/`sanic_remitente`/`sanic_fecharecibido` nulos: <see cref="InvalidOperationException"/>.</summary>
        public SolicitudLeida Leer(Guid solicitudId)
        {
            throw new NotImplementedException();
        }

        /// <summary>UN `Update` con exactamente estas columnas: estado, `sanic_fechavalidada`, los tres contadores, `sanic_acusecontenido` y `sanic_versionparametros` (esta última solo si no es nula).</summary>
        public void CerrarValidacion(Guid solicitudId, CierreDeValidacion cierre)
        {
            throw new NotImplementedException();
        }

        /// <summary>UN `Update` con estado y `sanic_motivoclasificacion` (recortado a 300).</summary>
        public void Clasificar(Guid solicitudId, ClasificacionDelCorreo clasificacion)
        {
            throw new NotImplementedException();
        }

        /// <summary>
        /// Alta de las filas en lotes. `sanic_nombre` NO se manda (es calculado). Los choices van como `OptionSetValue`; un
        /// valor nulo del dominio NO se manda (la columna queda vacía, DD-01). `sanic_planid` como `EntityReference` a Plan.
        /// Vacío → sin llamadas.
        /// </summary>
        public void GuardarFilas(Guid solicitudId, IEnumerable<FilaParaGuardar> filas)
        {
            throw new NotImplementedException();
        }

        /// <summary>
        /// Alta de un `sanic_mppp_tbl_resultadoregla` por cada resultado (diseno/02 §3.3), en lotes: `sanic_reglacodigo`,
        /// `sanic_resultado`, `sanic_razon` (recortada a 2000), `sanic_efectoaplicado`, `sanic_orden`, `sanic_fechaevaluacion`.
        /// `sanic_reglaid` se manda solo si el diccionario de ids trae ese código. Vacío → sin llamadas.
        /// </summary>
        public void GuardarResultados(Guid solicitudId, IEnumerable<ResultadoDeRegla> resultados, IDictionary<string, Guid> idsDeReglaPorCodigo, DateTime fechaEvaluacion)
        {
            throw new NotImplementedException();
        }

        /// <summary>UN `Create` en Bitácora: fecha, evento, origen, `sanic_numerofila` (0 = de la solicitud), `sanic_actortexto` (recortado a 200, puede ser nulo), `sanic_detalle` (recortado a 10000).</summary>
        public Guid RegistrarEvento(Guid solicitudId, DateTime fecha, EventoDeBitacora evento, OrigenDelEvento origen, int numeroFila, string actor, string detalle)
        {
            throw new NotImplementedException();
        }
    }
}
