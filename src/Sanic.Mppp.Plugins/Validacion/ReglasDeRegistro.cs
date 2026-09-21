using System;
using System.Collections.Generic;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>Un plan ACTIVO del maestro (`sanic_mppp_tbl_plan`), tal como lo entrega la capa de datos. Sin SDK.</summary>
    public sealed class PlanDelCatalogo
    {
        public PlanDelCatalogo(Guid id, string codigo, TipoDeFormatoDelPlan tipoFormato, Moneda moneda)
        {
            Id = id;
            Codigo = codigo;
            TipoFormato = tipoFormato;
            Moneda = moneda;
        }

        public Guid Id { get; }

        /// <summary>`sanic_codigo`: `^[A-Z0-9]{4}$`.</summary>
        public string Codigo { get; }

        public TipoDeFormatoDelPlan TipoFormato { get; }

        public Moneda Moneda { get; }
    }

    /// <summary>
    /// Todo lo que las reglas de registro consultan, cargado UNA vez por ejecución (diseno/03 §1 paso 6: nunca una consulta por
    /// fila). Inmutable. Un catálogo mal armado es un error real (<see cref="ArgumentException"/>), no una regla fallida:
    /// algún argumento nulo; la estructura no trae EXACTAMENTE los diez campos de <see cref="CamposDeFila.Todos"/> por su
    /// `Nombre` (ni uno menos, ni uno de más, ni uno sin nombre); un plan nulo, con código que no cumple `^[A-Z0-9]{4}$`, o dos
    /// planes con el mismo código.
    /// </summary>
    public sealed class CatalogosDeValidacion
    {
        /// <param name="autorizacionesActivasDelRemitente">
        /// Por id de plan: las autorizaciones del remitente donde TODO está activo (Autorizado, Plan, Cliente y la propia
        /// AutorizacionPlan; diseno/02 §2.4). El valor dice si tiene la evidencia cargada: sin evidencia NO es vigente, pero el
        /// mensaje al cliente es otro. Se copia: cambiar el diccionario después no cambia el catálogo.
        /// </param>
        public CatalogosDeValidacion(
            ConfiguracionPlantilla estructura,
            ListasPlantilla listas,
            ObligatoriedadPlantilla obligatoriedad,
            IEnumerable<PlanDelCatalogo> planesActivos,
            IDictionary<Guid, bool> autorizacionesActivasDelRemitente)
        {
            throw new NotImplementedException();
        }

        public ConfiguracionPlantilla Estructura { get; }

        public ListasPlantilla Listas { get; }

        public ObligatoriedadPlantilla Obligatoriedad { get; }

        /// <summary>El campo de la estructura con ese nombre de <see cref="CamposDeFila"/>. Otro nombre: <see cref="ArgumentException"/>.</summary>
        public CampoPlantilla Campo(string campo)
        {
            throw new NotImplementedException();
        }

        /// <summary>El plan activo con ese código EXACTO (ya normalizado), o nulo. Nunca uno parecido.</summary>
        public PlanDelCatalogo PlanPorCodigo(string codigoNormalizado)
        {
            throw new NotImplementedException();
        }

        /// <summary>Nulo: el remitente no tiene autorización activa sobre ese plan. False: la tiene, sin evidencia. True: vigente.</summary>
        public bool? AutorizacionSobre(Guid planId)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// Una fila de la plantilla, vista por las reglas de registro (diseno/03 §1 paso 5). Es una VISTA DE SOLO LECTURA: todo lo
    /// derivado (el valor de cada lista, el plan, la referencia que rige) se calcula de lo recibido y de los catálogos, siempre
    /// igual, lo pida quien lo pida y en el orden que sea. Ningún evaluador la modifica: así una regla no depende de que otra
    /// haya corrido antes, y el plugin lee de acá mismo lo que guarda en `sanic_mppp_tbl_fila`.
    /// </summary>
    public sealed class FilaEnValidacion
    {
        public FilaEnValidacion(FilaPlantilla fila, CatalogosDeValidacion catalogos)
        {
            throw new NotImplementedException();
        }

        public CatalogosDeValidacion Catalogos { get; }

        /// <summary>`sanic_numerofila`: la posición de la fila en la ventana (<see cref="FilaPlantilla.NumeroOrden"/>).</summary>
        public int NumeroFila { get; }

        /// <summary>Lo que escribió el cliente en ese campo, sin espacios a los lados; vacío si no escribió nada. Campo desconocido: <see cref="ArgumentException"/>.</summary>
        public string Recibido(string campo)
        {
            throw new NotImplementedException();
        }

        /// <summary>Cómo se llama ese campo para el cliente: el encabezado de su columna en la plantilla.</summary>
        public string Encabezado(string campo)
        {
            throw new NotImplementedException();
        }

        /// <summary>El valor de la lista, o nulo si vino vacío o no es válido (DD-01: la columna queda vacía).</summary>
        public Gestion? Gestion => throw new NotImplementedException();

        public Clasificacion? Clasificacion => throw new NotImplementedException();

        public TipoDeIdentificacion? TipoIdentificacion => throw new NotImplementedException();

        public Moneda? Moneda => throw new NotImplementedException();

        public Banco? Banco => throw new NotImplementedException();

        /// <summary>El código de 3 dígitos del banco de la fila (de `plantilla.listas`), o nulo si el banco vino vacío o no es válido.</summary>
        public string CodigoDeBanco => throw new NotImplementedException();

        /// <summary>
        /// `sanic_numeroplan`: lo recibido en mayúsculas invariantes y relleno con ceros a la izquierda hasta 4 (`12` → `0012`,
        /// `a1` → `00A1`). Nulo si vino vacío o si el resultado no cumple `^[A-Z0-9]{4}$` (ASCII): nunca se recorta ni se limpia.
        /// </summary>
        public string NumeroPlanNormalizado => throw new NotImplementedException();

        /// <summary>`sanic_planid`: el plan activo con ese código exacto, o nulo. NUNCA se adivina un plan parecido.</summary>
        public PlanDelCatalogo Plan => throw new NotImplementedException();

        /// <summary>`sanic_referenciarecibida`: tal cual vino en el Excel (sin recortar); si no vino, nulo. Se guarda siempre.</summary>
        public string ReferenciaRecibida => throw new NotImplementedException();

        /// <summary>
        /// La referencia de formato 11 (D-17): código de banco (3) + cuenta rellena con ceros A LA IZQUIERDA hasta 17 = 20
        /// exactos. Nulo si el plan no es formato 11 (o no hay plan), si no hay código de banco, o si la cuenta viene vacía,
        /// tiene más de 17 caracteres o trae algo que no sea 0-9 ASCII.
        /// </summary>
        public string ReferenciaConstruida => throw new NotImplementedException();

        /// <summary>
        /// `sanic_referencia`, la que rige. Formato 11: la construida, sin mirar la recibida (DD-10). Formatos 06 y 10: la
        /// recibida sin espacios a los lados, aunque quede vacía (DD-15). Sin plan: nulo.
        /// </summary>
        public string ReferenciaQueRige => throw new NotImplementedException();
    }

    /// <summary>
    /// Los evaluadores de las ocho reglas semilla de nivel Registro (diseno/03 §1 paso 5; D-17, D-18 y D-19). Son lectores de
    /// <see cref="FilaEnValidacion"/>. El catálogo es editable: un evaluador al que le sacaron una dependencia no da por bueno
    /// lo que no puede comprobar. Ningún mensaje cita la cuenta ni la identificación (datos sensibles, DD-08); lo que se cita
    /// del cliente pasa por <see cref="MensajeAlCliente.Citar"/>; los campos se nombran por su encabezado en la plantilla.
    /// </summary>
    public static class ReglasDeRegistro
    {
        public const string ListasValidas = "LISTAS_VALIDAS";
        public const string LargosYFormato = "LARGOS_Y_FORMATO";
        public const string PlanExiste = "PLAN_EXISTE";
        public const string Formato11SoloAch = "FORMATO_11_SOLO_ACH";
        public const string Obligatoriedad = "OBLIGATORIEDAD";
        public const string ReferenciaFormato11 = "REFERENCIA_FORMATO_11";
        public const string MonedaDelPlan = "MONEDA_DEL_PLAN";
        public const string AutorizacionCorreoPlan = "AUTORIZACION_CORREO_PLAN";

        /// <summary>Un evaluador por cada código de arriba, ni uno más. Instancias nuevas en cada llamada: no guardan estado.</summary>
        public static IList<IEvaluador<FilaEnValidacion>> Evaluadores()
        {
            throw new NotImplementedException();
        }
    }
}
