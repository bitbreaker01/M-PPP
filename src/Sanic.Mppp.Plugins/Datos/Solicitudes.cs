using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
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

        /// <summary>Largos de las columnas de texto que se escriben (diseno/02 §3): todo texto se recorta a esto antes de mandarse.</summary>
        public const int LargoNumeroPlan = 4, LargoNombreBeneficiario = 200, LargoNumeroIdentificacion = 100, LargoNumeroCuenta = 100,
            LargoReferencia = 100, LargoMensaje = 4000, LargoRazon = 2000, LargoMotivoClasificacion = 300, LargoActor = 200, LargoDetalle = 10000, LargoVersionParametros = 200, LargoReglaCodigo = 50;
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

        /// <summary>`sanic_mensaje` M(4000): se recorta a 4000 al guardar. Los demás textos también se recortan al largo de su columna.</summary>
        public string Mensaje { get; set; }

        public DateTime FechaValidada { get; set; }
    }

    /// <summary>
    /// Lectura y escritura de la Solicitud y su unidad histórica sobre <see cref="IOrganizationService"/> (pieza 7.6, `Datos/`).
    /// Reglas (las fijan las pruebas `SolicitudesDataverseAceptacion`): se leen solo las columnas usadas; los choices se traducen a
    /// los enums de `Dominio` y un valor fuera del enum es <see cref="InvalidOperationException"/> con tabla, columna y registro; TODO
    /// texto se recorta al largo de su columna (diseno/02, constantes `Largo…`) antes de escribir, sin partir un par subrogado (un
    /// carácter fuera del plano básico se descarta entero antes que dejarlo por la mitad); las altas van UNA POR UNA con `Create`
    /// (Microsoft Learn, "Don't use batch request types in plug-ins": el plugin ya corre en la transacción, no hay latencia que
    /// ahorrar, y un lote puede pasarse del tiempo máximo; revisión de código, 2026-09-21) y la primera falla se propaga tal cual;
    /// los lookups a Solicitud son `EntityReference`; toda escritura de estado de Solicitud va por `sanic_estadoprocesamiento`;
    /// nada de acá fija la fecha: la recibe, y EXIGE `DateTimeKind.Utc` (otro `Kind` se guardaría corrido en silencio en una columna
    /// "usuario local": <see cref="ArgumentException"/>); un `solicitudId` vacío es <see cref="ArgumentException"/> en todos los
    /// métodos. Servicio nulo: <see cref="ArgumentNullException"/>.
    /// </summary>
    public sealed class SolicitudesDataverse
    {
        private readonly IOrganizationService _servicio;

        public SolicitudesDataverse(IOrganizationService servicio)
        {
            _servicio = servicio ?? throw new ArgumentNullException(nameof(servicio));
        }

        /// <summary>Una lectura. Inexistente: se propaga la falla del servicio. Estado fuera del enum o `sanic_nombre`/`sanic_remitente`/`sanic_fecharecibido` nulos: <see cref="InvalidOperationException"/>.</summary>
        public SolicitudLeida Leer(Guid solicitudId)
        {
            ValidarSolicitudId(solicitudId);

            var columnas = new ColumnSet(
                "sanic_nombre", "sanic_estadoprocesamiento", "sanic_remitente", "sanic_asunto",
                "sanic_fecharecibido", "sanic_cantidadadjuntos", "sanic_cantidadexcel", "sanic_versionparametros");

            var registro = _servicio.Retrieve(TablasHistorico.Solicitud, solicitudId, columnas);

            return new SolicitudLeida
            {
                Id = registro.Id,
                Numero = RequeridoTexto(registro, "sanic_nombre"),
                Estado = RequeridoChoice<EstadoDeLaSolicitud>(registro, "sanic_estadoprocesamiento"),
                Remitente = RequeridoTexto(registro, "sanic_remitente"),
                Asunto = TextoOpcional(registro, "sanic_asunto"),
                FechaRecibido = RequeridaFecha(registro, "sanic_fecharecibido"),
                CantidadAdjuntos = EnteroOCero(registro, "sanic_cantidadadjuntos"),
                CantidadExcel = EnteroOCero(registro, "sanic_cantidadexcel"),
                VersionParametros = TextoOpcional(registro, "sanic_versionparametros"),
            };
        }

        /// <summary>UN `Update` con exactamente estas columnas: estado, `sanic_fechavalidada`, los tres contadores, `sanic_acusecontenido` y `sanic_versionparametros` (esta última solo si no es nula).</summary>
        public void CerrarValidacion(Guid solicitudId, CierreDeValidacion cierre)
        {
            ValidarSolicitudId(solicitudId);

            if (cierre == null)
            {
                throw new ArgumentNullException(nameof(cierre));
            }

            ValidarUtc(cierre.FechaValidada, nameof(cierre));

            var entidad = new Entity(TablasHistorico.Solicitud, solicitudId);
            entidad["sanic_estadoprocesamiento"] = new OptionSetValue((int)cierre.Estado);
            entidad["sanic_fechavalidada"] = cierre.FechaValidada;
            entidad["sanic_filastotales"] = cierre.FilasTotales;
            entidad["sanic_filasvalidas"] = cierre.FilasValidas;
            entidad["sanic_filasrechazadas"] = cierre.FilasRechazadas;
            entidad["sanic_acusecontenido"] = cierre.AcuseContenido;
            AgregarSiNoEsNulo(entidad, "sanic_versionparametros", Recortar(cierre.VersionParametros, TablasHistorico.LargoVersionParametros));

            _servicio.Update(entidad);
        }

        /// <summary>UN `Update` con estado y `sanic_motivoclasificacion` (recortado a 300).</summary>
        public void Clasificar(Guid solicitudId, ClasificacionDelCorreo clasificacion)
        {
            ValidarSolicitudId(solicitudId);

            if (clasificacion == null)
            {
                throw new ArgumentNullException(nameof(clasificacion));
            }

            var entidad = new Entity(TablasHistorico.Solicitud, solicitudId);
            entidad["sanic_estadoprocesamiento"] = new OptionSetValue((int)clasificacion.Estado);
            entidad["sanic_motivoclasificacion"] = Recortar(clasificacion.Motivo, TablasHistorico.LargoMotivoClasificacion);

            _servicio.Update(entidad);
        }

        /// <summary>
        /// Alta de las filas, un `Create` por fila. `sanic_nombre` NO se manda (es calculado). Los choices van como `OptionSetValue`; un
        /// valor nulo del dominio NO se manda (la columna queda vacía, DD-01). `sanic_planid` como `EntityReference` a Plan.
        /// Vacío → sin llamadas.
        /// </summary>
        public void GuardarFilas(Guid solicitudId, IEnumerable<FilaParaGuardar> filas)
        {
            if (filas == null)
            {
                throw new ArgumentNullException(nameof(filas));
            }

            ValidarSolicitudId(solicitudId);

            var lista = filas.ToList();
            foreach (var fila in lista)
            {
                ValidarUtc(fila.FechaValidada, nameof(fila));
            }

            foreach (var fila in lista)
            {
                _servicio.Create(ArmarEntidadFila(solicitudId, fila));
            }
        }

        /// <summary>
        /// Alta de un `sanic_mppp_tbl_resultadoregla` por cada resultado (diseno/02 §3.3), un `Create` por resultado: `sanic_reglacodigo`,
        /// `sanic_resultado`, `sanic_razon` (recortada a 2000), `sanic_efectoaplicado`, `sanic_orden`, `sanic_fechaevaluacion`.
        /// `sanic_reglaid` se manda solo si el diccionario de ids trae ese código. Vacío → sin llamadas.
        /// </summary>
        public void GuardarResultados(Guid solicitudId, IEnumerable<ResultadoDeRegla> resultados, IDictionary<string, Guid> idsDeReglaPorCodigo, DateTime fechaEvaluacion)
        {
            if (resultados == null)
            {
                throw new ArgumentNullException(nameof(resultados));
            }

            if (idsDeReglaPorCodigo == null)
            {
                throw new ArgumentNullException(nameof(idsDeReglaPorCodigo));
            }

            ValidarSolicitudId(solicitudId);
            ValidarUtc(fechaEvaluacion, nameof(fechaEvaluacion));

            foreach (var resultado in resultados)
            {
                _servicio.Create(ArmarEntidadResultado(solicitudId, resultado, idsDeReglaPorCodigo, fechaEvaluacion));
            }
        }

        /// <summary>UN `Create` en Bitácora: fecha, evento, origen, `sanic_numerofila` (0 = de la solicitud), `sanic_actortexto` (recortado a 200, puede ser nulo), `sanic_detalle` (recortado a 10000).</summary>
        public Guid RegistrarEvento(Guid solicitudId, DateTime fecha, EventoDeBitacora evento, OrigenDelEvento origen, int numeroFila, string actor, string detalle)
        {
            ValidarSolicitudId(solicitudId);
            ValidarUtc(fecha, nameof(fecha));

            var entidad = new Entity(TablasHistorico.Bitacora);
            entidad["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId);
            entidad["sanic_fechaevento"] = fecha;
            entidad["sanic_evento"] = new OptionSetValue((int)evento);
            entidad["sanic_origen"] = new OptionSetValue((int)origen);
            entidad["sanic_numerofila"] = numeroFila;
            AgregarSiNoEsNulo(entidad, "sanic_actortexto", Recortar(actor, TablasHistorico.LargoActor));
            AgregarSiNoEsNulo(entidad, "sanic_detalle", Recortar(detalle, TablasHistorico.LargoDetalle));

            return _servicio.Create(entidad);
        }

        // ------------------------------------------------------------------ armado de entidades

        private static Entity ArmarEntidadFila(Guid solicitudId, FilaParaGuardar fila)
        {
            var entidad = new Entity(TablasHistorico.Fila);
            entidad["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId);
            entidad["sanic_numerofila"] = fila.NumeroFila;
            AgregarChoiceSiNoEsNulo(entidad, "sanic_gestion", fila.Gestion);
            AgregarChoiceSiNoEsNulo(entidad, "sanic_clasificacion", fila.Clasificacion);
            AgregarChoiceSiNoEsNulo(entidad, "sanic_moneda", fila.Moneda);
            AgregarChoiceSiNoEsNulo(entidad, "sanic_tipoidentificacion", fila.TipoIdentificacion);
            AgregarChoiceSiNoEsNulo(entidad, "sanic_banco", fila.Banco);
            AgregarSiNoEsNulo(entidad, "sanic_numeroplan", Recortar(fila.NumeroPlan, TablasHistorico.LargoNumeroPlan));
            if (fila.PlanId.HasValue)
            {
                entidad["sanic_planid"] = new EntityReference(Tablas.Plan, fila.PlanId.Value);
            }

            AgregarSiNoEsNulo(entidad, "sanic_nombrebeneficiario", Recortar(fila.NombreBeneficiario, TablasHistorico.LargoNombreBeneficiario));
            AgregarSiNoEsNulo(entidad, "sanic_numeroidentificacion", Recortar(fila.NumeroIdentificacion, TablasHistorico.LargoNumeroIdentificacion));
            AgregarSiNoEsNulo(entidad, "sanic_numerocuenta", Recortar(fila.NumeroCuenta, TablasHistorico.LargoNumeroCuenta));
            AgregarSiNoEsNulo(entidad, "sanic_referencia", Recortar(fila.Referencia, TablasHistorico.LargoReferencia));
            AgregarSiNoEsNulo(entidad, "sanic_referenciarecibida", Recortar(fila.ReferenciaRecibida, TablasHistorico.LargoReferencia));
            entidad["sanic_estado"] = new OptionSetValue((int)fila.Estado);
            AgregarSiNoEsNulo(entidad, "sanic_mensaje", Recortar(fila.Mensaje, TablasHistorico.LargoMensaje));
            entidad["sanic_fechavalidada"] = fila.FechaValidada;
            return entidad;
        }

        private static Entity ArmarEntidadResultado(Guid solicitudId, ResultadoDeRegla resultado, IDictionary<string, Guid> idsDeReglaPorCodigo, DateTime fechaEvaluacion)
        {
            var entidad = new Entity(TablasHistorico.ResultadoRegla);
            entidad["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId);
            entidad["sanic_reglacodigo"] = Recortar(resultado.Codigo, TablasHistorico.LargoReglaCodigo);
            if (idsDeReglaPorCodigo.TryGetValue(resultado.Codigo, out var reglaId))
            {
                entidad["sanic_reglaid"] = new EntityReference(Tablas.Regla, reglaId);
            }

            entidad["sanic_resultado"] = new OptionSetValue((int)resultado.Resultado);
            AgregarSiNoEsNulo(entidad, "sanic_razon", Recortar(resultado.Razon, TablasHistorico.LargoRazon));
            entidad["sanic_efectoaplicado"] = new OptionSetValue((int)resultado.EfectoAplicado);
            entidad["sanic_orden"] = resultado.Orden;
            entidad["sanic_fechaevaluacion"] = fechaEvaluacion;
            return entidad;
        }

        // ------------------------------------------------------------------ validación de entrada

        /// <summary>Un `solicitudId` vacío es un error de programación en TODOS los métodos (revisión de código, 2026-09-21).</summary>
        private static void ValidarSolicitudId(Guid solicitudId)
        {
            if (solicitudId == Guid.Empty)
            {
                throw new ArgumentException("El id de la solicitud no puede estar vacío.", nameof(solicitudId));
            }
        }

        /// <summary>Toda fecha que entra EXIGE UTC: otro `Kind` se guardaría corrido en silencio en una columna "usuario local" (revisión de código, 2026-09-21). Se valida ANTES de tocar el servicio.</summary>
        private static void ValidarUtc(DateTime fecha, string nombreParametro)
        {
            if (fecha.Kind != DateTimeKind.Utc)
            {
                throw new ArgumentException("La fecha tiene que venir en UTC (Kind = DateTimeKind.Utc); otro Kind se guardaría corrido en una columna de hora local.", nombreParametro);
            }
        }

        // ------------------------------------------------------------------ traducción Entity -> tipos del dominio (mismo estilo que Catalogos.cs)

        private static InvalidOperationException ErrorColumna(Entity registro, string columna)
        {
            return new InvalidOperationException(
                $"La tabla '{registro.LogicalName}' tiene el registro {registro.Id} con la columna '{columna}' vacía o con un valor que no se puede traducir.");
        }

        private static string RequeridoTexto(Entity registro, string columna)
        {
            if (registro.Contains(columna) && registro[columna] is string valor && valor.Length > 0)
            {
                return valor;
            }

            throw ErrorColumna(registro, columna);
        }

        private static string TextoOpcional(Entity registro, string columna)
        {
            return registro.Contains(columna) ? registro[columna] as string : null;
        }

        private static DateTime RequeridaFecha(Entity registro, string columna)
        {
            if (registro.Contains(columna) && registro[columna] is DateTime valor)
            {
                return valor;
            }

            throw ErrorColumna(registro, columna);
        }

        private static int EnteroOCero(Entity registro, string columna)
        {
            return registro.Contains(columna) && registro[columna] is int valor ? valor : 0;
        }

        private static TEnum RequeridoChoice<TEnum>(Entity registro, string columna) where TEnum : struct, Enum
        {
            if (registro.Contains(columna) && registro[columna] is OptionSetValue opcion && Enum.IsDefined(typeof(TEnum), opcion.Value))
            {
                return (TEnum)(object)opcion.Value;
            }

            throw ErrorColumna(registro, columna);
        }

        // ------------------------------------------------------------------ recorte y omisión de nulos al escribir

        /// <summary>Recorta al largo de la columna (diseno/02); un texto nulo sigue nulo. Nunca parte un par subrogado: si el carácter
        /// que quedaría último es la mitad alta de un par, se descarta el par entero (revisión de código, 2026-09-21).</summary>
        private static string Recortar(string texto, int largoMaximo)
        {
            if (texto == null || texto.Length <= largoMaximo)
            {
                return texto;
            }

            var largo = largoMaximo;
            if (largo > 0 && char.IsHighSurrogate(texto[largo - 1]))
            {
                largo--;
            }

            return texto.Substring(0, largo);
        }

        /// <summary>Un valor nulo del dominio NO se manda: la columna queda vacía (DD-01).</summary>
        private static void AgregarSiNoEsNulo(Entity entidad, string columna, object valor)
        {
            if (valor != null)
            {
                entidad[columna] = valor;
            }
        }

        private static void AgregarChoiceSiNoEsNulo<TEnum>(Entity entidad, string columna, TEnum? valor) where TEnum : struct, Enum
        {
            if (valor.HasValue)
            {
                entidad[columna] = new OptionSetValue((int)(object)valor.Value);
            }
        }
    }
}
