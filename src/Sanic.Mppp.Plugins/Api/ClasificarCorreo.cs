using System;
using System.Collections.Generic;
using Sanic.Mppp.Plugins.Correo;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Validacion;

namespace Sanic.Mppp.Plugins.Api
{
    /// <summary>Los valores del parámetro de salida `clasificacion` de `sanic_mppp_capi_clasificarcorreo` (diseno/03 §0). Exactos.</summary>
    public static class Clasificaciones
    {
        public const string Nuevo = "nuevo";
        public const string Reenvio = "reenvio";
        public const string Respuesta = "respuesta";
        public const string RemitenteNoReconocido = "remitente_no_reconocido";
        public const string Ilegible = "ilegible";
    }

    /// <summary>Las salidas de la Custom API (diseno/03 §0).</summary>
    public sealed class ResultadoDeClasificacion
    {
        public ResultadoDeClasificacion(bool procesar, string clasificacion, bool yaProcesada)
        {
            Procesar = procesar;
            Clasificacion = clasificacion;
            YaProcesada = yaProcesada;
        }

        public bool Procesar { get; }

        /// <summary>Uno de <see cref="Clasificaciones"/>; nulo cuando <see cref="YaProcesada"/>.</summary>
        public string Clasificacion { get; }

        public bool YaProcesada { get; }
    }

    /// <summary>Aviso dentro de la app a todos los ejecutivos (diseno/05 DA-08; diseno/03 §0 paso 5). La implementación sobre `appnotification` es de otra pieza.</summary>
    public interface IAvisos
    {
        void AvisarAEjecutivos(Guid solicitudId, string titulo, string cuerpo);
    }

    /// <summary>
    /// Lo que las reglas de nivel Correo miran (diseno/03 §0 paso 3). Sin SDK. Lo arma <see cref="ClasificarCorreo"/> con lo que
    /// leyó; la vista es de solo lectura.
    /// </summary>
    public sealed class CorreoEnValidacion
    {
        public CorreoEnValidacion(CabecerasLeidas cabeceras, IList<string> prefijosDeReenvio, ISet<Guid> planesAutorizadosDelRemitente)
        {
            throw new NotImplementedException();
        }

        public CabecerasLeidas Cabeceras { get; }

        /// <summary>El asunto empieza (sin espacios a los lados, sin distinguir mayúsculas) con alguno de los prefijos de `correo.prefijos.reenvio`.</summary>
        public bool AsuntoEsDeReenvio { get; }

        /// <summary>Cuántos planes tiene autorizados el remitente con todo activo (D-42).</summary>
        public int PlanesAutorizados { get; }
    }

    /// <summary>
    /// Los evaluadores de las dos reglas semilla de nivel Correo (diseno/02 §2.6; diseno/03 §0 paso 3). Sueltos fallan cerrado.
    ///  - `ES_CORREO_NUEVO`: se cumple si las cabeceras son legibles y (no traen referencias a otro correo, o las traen y el asunto
    ///    es de reenvío). Ilegibles o respuesta → no se cumple. Marcador `valor` = el asunto citado.
    ///  - `REMITENTE_RECONOCIDO`: se cumple si el remitente tiene al menos un plan autorizado.
    /// Los textos de estas reglas NO llegan al cliente (no se le responde): son para la bandeja Por clasificar.
    /// </summary>
    public static class ReglasDelCorreo
    {
        public const string EsCorreoNuevo = "ES_CORREO_NUEVO";
        public const string RemitenteReconocido = "REMITENTE_RECONOCIDO";

        public static IList<IEvaluador<CorreoEnValidacion>> Evaluadores()
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// El plugin liviano, sin el envoltorio de `IPlugin` (que es `ClasificarCorreoApi`, pieza 7.6b, y solo traduce parámetros):
    /// "¿este correo merece procesarse?" (diseno/03 §0). Contrato (lo fijan las pruebas `ClasificarCorreoAceptacion`):
    ///  1. lee la Solicitud; si no está en Ingresada → `YaProcesada`, `Procesar` = false, sin tocar nada;
    ///  2. baja SOLO el inicio de `sanic_correocrudo` (tope <see cref="LectorDeCabeceras.TopeBytes"/>) y lee las cabeceras;
    ///  3. lee `correo.prefijos.reenvio` (JSON: lista de textos; ausente o ilegible → error real), las reglas activas de nivel Correo y
    ///     los planes autorizados del remitente (número fijo de consultas); evalúa con el motor y guarda un ResultadoRegla por regla;
    ///  4. decide: cabeceras ilegibles → `ilegible`; `ES_CORREO_NUEVO` no cumplida → `respuesta`; `REMITENTE_RECONOCIDO` no cumplida →
    ///     `remitente_no_reconocido`; si no, `nuevo` o `reenvio` según el asunto. `ilegible` y `respuesta` → estado No es correo nuevo;
    ///     `remitente_no_reconocido` → No reconocida; en los tres, `sanic_motivoclasificacion` con el motivo, Bitácora "Correo
    ///     clasificado" (origen Custom API) y un aviso a los ejecutivos; `Procesar` = false. `nuevo`/`reenvio` → la Solicitud sigue en
    ///     Ingresada, `Procesar` = true, y también Bitácora "Correo clasificado" (ningún camino termina sin rastro);
    ///  5. no abre el Excel, no carga planes por código, no arma ninguna comunicación al remitente;
    ///  6. una excepción real (catálogo mal armado, servicio) se propaga tal cual: la transacción la revierte la plataforma.
    /// Nada de acá lee el reloj: la fecha llega por parámetro (el plugin la toma del contexto) y tiene que ser UTC.
    /// </summary>
    public sealed class ClasificarCorreo
    {
        public const string ParametroPrefijosDeReenvio = "correo.prefijos.reenvio";

        public ClasificarCorreo(SolicitudesDataverse solicitudes, CatalogosDataverse catalogos, IArchivos archivos, IAvisos avisos)
        {
            throw new NotImplementedException();
        }

        public ResultadoDeClasificacion Ejecutar(Guid solicitudId, DateTime ahoraUtc)
        {
            throw new NotImplementedException();
        }
    }
}
