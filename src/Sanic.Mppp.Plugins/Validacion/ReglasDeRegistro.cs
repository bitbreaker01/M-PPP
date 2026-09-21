using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
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
        private readonly IDictionary<string, CampoPlantilla> _camposPorNombre;
        private readonly IDictionary<string, PlanDelCatalogo> _planesPorCodigo;
        private readonly IDictionary<Guid, bool> _autorizaciones;

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
            if (estructura == null)
            {
                throw new ArgumentNullException(nameof(estructura));
            }

            if (listas == null)
            {
                throw new ArgumentNullException(nameof(listas));
            }

            if (obligatoriedad == null)
            {
                throw new ArgumentNullException(nameof(obligatoriedad));
            }

            if (planesActivos == null)
            {
                throw new ArgumentNullException(nameof(planesActivos));
            }

            if (autorizacionesActivasDelRemitente == null)
            {
                throw new ArgumentNullException(nameof(autorizacionesActivasDelRemitente));
            }

            // La estructura tiene que traer EXACTAMENTE los diez campos de CamposDeFila.Todos(), por su Nombre: ni uno
            // menos, ni uno de más, ni uno sin nombre, ni uno repetido (diseno/03 §1 paso 5: el resto del código asume esto).
            var nombresEsperados = new HashSet<string>(CamposDeFila.Todos(), StringComparer.Ordinal);
            var camposPorNombre = new Dictionary<string, CampoPlantilla>(StringComparer.Ordinal);
            foreach (var campo in estructura.Campos ?? new List<CampoPlantilla>())
            {
                if (campo == null || string.IsNullOrWhiteSpace(campo.Nombre))
                {
                    throw new ArgumentException("La estructura de la plantilla trae un campo sin nombre.", nameof(estructura));
                }

                if (!nombresEsperados.Contains(campo.Nombre))
                {
                    throw new ArgumentException($"La estructura de la plantilla trae un campo que no es de la fila ('{campo.Nombre}').", nameof(estructura));
                }

                if (camposPorNombre.ContainsKey(campo.Nombre))
                {
                    throw new ArgumentException($"La estructura de la plantilla repite el campo '{campo.Nombre}'.", nameof(estructura));
                }

                camposPorNombre[campo.Nombre] = campo;
            }

            if (camposPorNombre.Count != nombresEsperados.Count)
            {
                throw new ArgumentException("La estructura de la plantilla no trae los diez campos de la fila.", nameof(estructura));
            }

            // Un plan nulo, con código sin normalizar (^[A-Z0-9]{4}$), o repetido: es el catálogo el que está mal armado,
            // no una fila (diseno/02 §2.2).
            var planesPorCodigo = new Dictionary<string, PlanDelCatalogo>(StringComparer.Ordinal);
            foreach (var plan in planesActivos)
            {
                if (plan == null)
                {
                    throw new ArgumentException("Los planes activos traen un plan nulo.", nameof(planesActivos));
                }

                if (!EsCodigoDePlanValido(plan.Codigo))
                {
                    throw new ArgumentException($"El plan '{plan.Codigo}' no tiene un código de plan válido (tiene que cumplir ^[A-Z0-9]{{4}}$).", nameof(planesActivos));
                }

                if (planesPorCodigo.ContainsKey(plan.Codigo))
                {
                    throw new ArgumentException($"Hay dos planes activos con el código '{plan.Codigo}'.", nameof(planesActivos));
                }

                planesPorCodigo[plan.Codigo] = plan;
            }

            Estructura = estructura;
            Listas = listas;
            Obligatoriedad = obligatoriedad;
            _camposPorNombre = camposPorNombre;
            _planesPorCodigo = planesPorCodigo;
            // Copia: cambiar el diccionario después de construir el catálogo no lo cambia (revisión de código, 2026-09-21).
            _autorizaciones = new Dictionary<Guid, bool>(autorizacionesActivasDelRemitente);
        }

        public ConfiguracionPlantilla Estructura { get; }

        public ListasPlantilla Listas { get; }

        public ObligatoriedadPlantilla Obligatoriedad { get; }

        /// <summary>El campo de la estructura con ese nombre de <see cref="CamposDeFila"/>. Otro nombre: <see cref="ArgumentException"/>.</summary>
        public CampoPlantilla Campo(string campo)
        {
            if (campo == null || !_camposPorNombre.TryGetValue(campo, out var campoPlantilla))
            {
                throw new ArgumentException($"'{campo}' no es un campo de la fila ({string.Join(", ", CamposDeFila.Todos())}).", nameof(campo));
            }

            return campoPlantilla;
        }

        /// <summary>El plan activo con ese código EXACTO (ya normalizado), o nulo. Nunca uno parecido.</summary>
        public PlanDelCatalogo PlanPorCodigo(string codigoNormalizado)
        {
            if (codigoNormalizado == null)
            {
                return null;
            }

            return _planesPorCodigo.TryGetValue(codigoNormalizado, out var plan) ? plan : null;
        }

        /// <summary>Nulo: el remitente no tiene autorización activa sobre ese plan. False: la tiene, sin evidencia. True: vigente.</summary>
        public bool? AutorizacionSobre(Guid planId)
        {
            return _autorizaciones.TryGetValue(planId, out var vigente) ? (bool?)vigente : null;
        }

        /// <summary>
        /// `^[A-Z0-9]{4}$`, sin expresiones regulares (dígito y letra son SIEMPRE ASCII, comparados por rango de <see cref="char"/>):
        /// lo usan tanto el catálogo (código de un <see cref="PlanDelCatalogo"/>) como <see cref="FilaEnValidacion.NumeroPlanNormalizado"/>.
        /// </summary>
        internal static bool EsCodigoDePlanValido(string codigo)
        {
            if (codigo == null || codigo.Length != 4)
            {
                return false;
            }

            foreach (char c in codigo)
            {
                bool esDigitoAscii = c >= '0' && c <= '9';
                bool esLetraMayusculaAscii = c >= 'A' && c <= 'Z';
                if (!esDigitoAscii && !esLetraMayusculaAscii)
                {
                    return false;
                }
            }

            return true;
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
        /// <summary>Del `FilaPlantilla` recibido: por LETRA DE COLUMNA. Nulo = todo vacío (`Valores` nulo, diseno/03 §1 paso 5).</summary>
        private readonly IDictionary<string, string> _valores;

        public FilaEnValidacion(FilaPlantilla fila, CatalogosDeValidacion catalogos)
        {
            if (fila == null)
            {
                throw new ArgumentNullException(nameof(fila));
            }

            Catalogos = catalogos ?? throw new ArgumentNullException(nameof(catalogos));
            _valores = fila.Valores;
            NumeroFila = fila.NumeroOrden;
        }

        public CatalogosDeValidacion Catalogos { get; }

        /// <summary>`sanic_numerofila`: la posición de la fila en la ventana (<see cref="FilaPlantilla.NumeroOrden"/>).</summary>
        public int NumeroFila { get; }

        /// <summary>Lo que escribió el cliente en ese campo, sin espacios a los lados; vacío si no escribió nada. Campo desconocido: <see cref="ArgumentException"/>.</summary>
        public string Recibido(string campo)
        {
            var columna = Catalogos.Campo(campo).Columna;
            if (_valores == null || !_valores.TryGetValue(columna, out var valor) || valor == null)
            {
                return string.Empty;
            }

            return valor.Trim();
        }

        /// <summary>Cómo se llama ese campo para el cliente: el encabezado de su columna en la plantilla.</summary>
        public string Encabezado(string campo)
        {
            return Catalogos.Campo(campo).EncabezadoEsperado;
        }

        /// <summary>El valor de la lista, o nulo si vino vacío o no es válido (DD-01: la columna queda vacía).</summary>
        public Gestion? Gestion => ResolverEnumDeLista<Gestion>(CamposDeFila.Gestion);

        public Clasificacion? Clasificacion => ResolverEnumDeLista<Clasificacion>(CamposDeFila.Clasificacion);

        public TipoDeIdentificacion? TipoIdentificacion => ResolverEnumDeLista<TipoDeIdentificacion>(CamposDeFila.TipoIdentificacion);

        public Moneda? Moneda => ResolverEnumDeLista<Moneda>(CamposDeFila.Moneda);

        public Banco? Banco => ResolverEnumDeLista<Banco>(CamposDeFila.Banco);

        /// <summary>El código de 3 dígitos del banco de la fila (de `plantilla.listas`), o nulo si el banco vino vacío o no es válido.</summary>
        public string CodigoDeBanco => Catalogos.Listas.Resolver(CamposDeFila.Banco, Recibido(CamposDeFila.Banco))?.CodigoDeBanco;

        /// <summary>
        /// `sanic_numeroplan`: lo recibido en mayúsculas invariantes y relleno con ceros a la izquierda hasta 4 (`12` → `0012`,
        /// `a1` → `00A1`). Nulo si vino vacío o si el resultado no cumple `^[A-Z0-9]{4}$` (ASCII): nunca se recorta ni se limpia.
        /// </summary>
        public string NumeroPlanNormalizado
        {
            get
            {
                var recibido = Recibido(CamposDeFila.NumeroPlan);
                if (recibido.Length == 0)
                {
                    return null;
                }

                // Mayúscula SOLO ascii (a-z → A-Z): un carácter fuera de ese rango (letra con tilde, dígito de otro alfabeto,
                // símbolo) queda igual, y por eso el patrón de abajo lo rechaza en vez de "arreglarlo" en silencio.
                var mayusculas = new StringBuilder(recibido.Length);
                foreach (char c in recibido)
                {
                    mayusculas.Append(c >= 'a' && c <= 'z' ? (char)(c - 32) : c);
                }

                // Relleno con ceros A LA IZQUIERDA hasta 4; si ya tiene 4 o más, nunca se recorta.
                string relleno = mayusculas.Length >= 4
                    ? mayusculas.ToString()
                    : new string('0', 4 - mayusculas.Length) + mayusculas;

                return CatalogosDeValidacion.EsCodigoDePlanValido(relleno) ? relleno : null;
            }
        }

        /// <summary>`sanic_planid`: el plan activo con ese código exacto, o nulo. NUNCA se adivina un plan parecido.</summary>
        public PlanDelCatalogo Plan => Catalogos.PlanPorCodigo(NumeroPlanNormalizado);

        /// <summary>`sanic_referenciarecibida`: tal cual vino en el Excel (sin recortar); si no vino, nulo. Se guarda siempre.</summary>
        public string ReferenciaRecibida
        {
            get
            {
                var columna = Catalogos.Campo(CamposDeFila.Referencia).Columna;
                return _valores != null && _valores.TryGetValue(columna, out var valor) ? valor : null;
            }
        }

        /// <summary>
        /// La referencia de formato 11 (D-17): código de banco (3) + cuenta rellena con ceros A LA IZQUIERDA hasta 17 = 20
        /// exactos. Nulo si el plan no es formato 11 (o no hay plan), si no hay código de banco, o si la cuenta viene vacía,
        /// tiene más de 17 caracteres o trae algo que no sea 0-9 ASCII.
        /// </summary>
        public string ReferenciaConstruida
        {
            get
            {
                var plan = Plan;
                if (plan == null || plan.TipoFormato != TipoDeFormatoDelPlan._11)
                {
                    return null;
                }

                var codigoDeBanco = CodigoDeBanco;
                if (codigoDeBanco == null)
                {
                    return null;
                }

                var cuenta = Recibido(CamposDeFila.NumeroCuenta);
                if (cuenta.Length == 0 || cuenta.Length > 17)
                {
                    return null;
                }

                foreach (char c in cuenta)
                {
                    if (c < '0' || c > '9')
                    {
                        return null;
                    }
                }

                return codigoDeBanco + cuenta.PadLeft(17, '0');
            }
        }

        /// <summary>
        /// `sanic_referencia`, la que rige. Formato 11: la construida, sin mirar la recibida (DD-10). Formatos 06 y 10: la
        /// recibida sin espacios a los lados, aunque quede vacía (DD-15). Sin plan: nulo.
        /// </summary>
        public string ReferenciaQueRige
        {
            get
            {
                var plan = Plan;
                if (plan == null)
                {
                    return null;
                }

                return plan.TipoFormato == TipoDeFormatoDelPlan._11 ? ReferenciaConstruida : Recibido(CamposDeFila.Referencia);
            }
        }

        /// <summary>Resuelve un campo de lista contra `plantilla.listas` y lo convierte al enum del choice (el valor
        /// resuelto por <see cref="ListasPlantilla"/> es EXACTAMENTE el nombre de un miembro de <typeparamref name="T"/>).</summary>
        private T? ResolverEnumDeLista<T>(string campo) where T : struct
        {
            var valorDeLista = Catalogos.Listas.Resolver(campo, Recibido(campo));
            return valorDeLista == null ? (T?)null : (T)Enum.Parse(typeof(T), valorDeLista.Valor, false);
        }
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
            return new List<IEvaluador<FilaEnValidacion>>
            {
                new EvaluadorListasValidas(),
                new EvaluadorLargosYFormato(),
                new EvaluadorPlanExiste(),
                new EvaluadorFormato11SoloAch(),
                new EvaluadorObligatoriedad(),
                new EvaluadorReferenciaFormato11(),
                new EvaluadorMonedaDelPlan(),
                new EvaluadorAutorizacionCorreoPlan(),
            };
        }

        /// <summary>
        /// Gestión, Clasificación, Tipo de identificación, Moneda y Banco contra `plantilla.listas` (diseno/03 §1 paso 5). Un
        /// campo vacío no falla acá (eso es de OBLIGATORIEDAD); uno con un valor que no está en su lista deja la columna vacía
        /// y su valor recibido se cita SIEMPRE en la precisión (DD-01), la redacte como la redacte el negocio.
        /// </summary>
        private sealed class EvaluadorListasValidas : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => ListasValidas;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var camposInvalidos = new List<string>();
                foreach (var campo in CamposDeFila.DeLista())
                {
                    var recibido = fila.Recibido(campo);
                    if (recibido.Length == 0)
                    {
                        continue;
                    }

                    if (fila.Catalogos.Listas.Resolver(campo, recibido) == null)
                    {
                        camposInvalidos.Add(campo);
                    }
                }

                if (camposInvalidos.Count == 0)
                {
                    return Veredicto.Cumplida();
                }

                var encabezados = string.Join(", ", camposInvalidos.Select(fila.Encabezado));
                var valoresCitados = string.Join(", ", camposInvalidos.Select(c => MensajeAlCliente.Citar(fila.Recibido(c))));
                var marcadores = new Dictionary<string, string> { ["campo"] = encabezados, ["valor"] = valoresCitados };

                // DD-01: el valor recibido se cita SIEMPRE en la precisión, así el catálogo redacte lo que redacte.
                var precision = string.Join(" ", camposInvalidos.Select(c => $"{fila.Encabezado(c)} '{MensajeAlCliente.Citar(fila.Recibido(c))}'."));

                return Veredicto.NoCumplida($"Uno o más valores no son válidos: {encabezados}.", marcadores, precision);
            }
        }

        /// <summary>
        /// Largo mínimo, máximo y formato de cada campo de la estructura (diseno/03 §1 paso 5). El largo se mide sobre lo
        /// recibido sin espacios a los lados; un campo vacío no falla por mínimo (eso es de OBLIGATORIEDAD), y uno sin ningún
        /// límite en la estructura no se mira. La precisión nombra el límite (el número), nunca el valor: el de cuenta y el de
        /// identificación son datos sensibles (DD-08).
        /// </summary>
        private sealed class EvaluadorLargosYFormato : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => LargosYFormato;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var encabezadosQueFallan = new List<string>();
                var precisiones = new List<string>();

                foreach (var campo in CamposDeFila.Todos())
                {
                    var campoPlantilla = fila.Catalogos.Campo(campo);
                    if (campoPlantilla.LargoMinimo == null && campoPlantilla.LargoMaximo == null && campoPlantilla.Formato == null)
                    {
                        continue;
                    }

                    var recibido = fila.Recibido(campo);
                    if (recibido.Length == 0)
                    {
                        continue;
                    }

                    var encabezado = fila.Encabezado(campo);
                    string motivo = null;
                    if (campoPlantilla.LargoMinimo.HasValue && recibido.Length < campoPlantilla.LargoMinimo.Value)
                    {
                        motivo = $"{encabezado} tiene que traer al menos {campoPlantilla.LargoMinimo.Value.ToString(CultureInfo.InvariantCulture)} caracteres.";
                    }
                    else if (campoPlantilla.LargoMaximo.HasValue && recibido.Length > campoPlantilla.LargoMaximo.Value)
                    {
                        motivo = $"{encabezado} no puede pasar de {campoPlantilla.LargoMaximo.Value.ToString(CultureInfo.InvariantCulture)} caracteres.";
                    }
                    else if (campoPlantilla.Formato.HasValue && !CumpleFormato(recibido, campoPlantilla.Formato.Value))
                    {
                        motivo = $"{encabezado} trae un formato que no se acepta.";
                    }

                    if (motivo != null)
                    {
                        encabezadosQueFallan.Add(encabezado);
                        precisiones.Add(motivo);
                    }
                }

                if (encabezadosQueFallan.Count == 0)
                {
                    return Veredicto.Cumplida();
                }

                var marcadores = new Dictionary<string, string> { ["campo"] = string.Join(", ", encabezadosQueFallan) };
                return Veredicto.NoCumplida("Uno o más campos no cumplen su largo o formato permitido.", marcadores, string.Join(" ", precisiones));
            }

            /// <summary>`FormatoDeCampo` es una lista cerrada y ASCII (D-18b): dígito y letra se comparan por rango de <see cref="char"/>,
            /// nunca con `char.IsDigit`/`char.IsLetter` (que aceptan dígitos y letras de otros alfabetos).</summary>
            private static bool CumpleFormato(string valor, FormatoDeCampo formato)
            {
                switch (formato)
                {
                    case FormatoDeCampo.Digitos:
                        foreach (char c in valor)
                        {
                            if (c < '0' || c > '9')
                            {
                                return false;
                            }
                        }

                        return true;
                    case FormatoDeCampo.Alfanumerico:
                        foreach (char c in valor)
                        {
                            bool esDigito = c >= '0' && c <= '9';
                            bool esLetra = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
                            if (!esDigito && !esLetra)
                            {
                                return false;
                            }
                        }

                        return true;
                    default:
                        // Texto: cualquier texto vale (LARGOS_Y_FORMATO ya midió el largo arriba).
                        return true;
                }
            }
        }

        /// <summary>`PLAN_EXISTE` (diseno/03 §1 paso 5): el plan normalizado tiene que existir activo. Nunca se adivina un plan parecido.</summary>
        private sealed class EvaluadorPlanExiste : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => PlanExiste;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                if (fila.Plan != null)
                {
                    return Veredicto.Cumplida();
                }

                var citado = MensajeAlCliente.Citar(fila.Recibido(CamposDeFila.NumeroPlan));
                var marcadores = new Dictionary<string, string> { ["plan"] = citado, ["valor"] = citado };
                return Veredicto.NoCumplida($"El plan '{citado}' no existe o no está activo.", marcadores, null);
            }
        }

        /// <summary>`FORMATO_11_SOLO_ACH` (DD-17): un plan formato 11 solo admite clasificación ACH.</summary>
        private sealed class EvaluadorFormato11SoloAch : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => Formato11SoloAch;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var plan = fila.Plan;
                if (plan == null)
                {
                    // Suelta y sin plan: no se puede comprobar (depende de PLAN_EXISTE, que ya lo dice).
                    return Veredicto.NoCumplida("No se puede comprobar el formato del plan porque el plan no existe.");
                }

                if (plan.TipoFormato != TipoDeFormatoDelPlan._11 || fila.Clasificacion == Clasificacion.ACH)
                {
                    return Veredicto.Cumplida();
                }

                var marcadores = new Dictionary<string, string> { ["plan"] = plan.Codigo };
                return Veredicto.NoCumplida($"El plan {plan.Codigo} solo admite la clasificación ACH.", marcadores, null);
            }
        }

        /// <summary>
        /// `OBLIGATORIEDAD` (diseno/03 §1 paso 5): según `plantilla.obligatoriedad` para la Gestión, Clasificación y tipo de
        /// formato del plan de la fila. Un campo de lista con un valor INVÁLIDO cuenta como vacío (DD-01: la columna queda
        /// vacía), igual que uno que nunca se escribió.
        /// </summary>
        private sealed class EvaluadorObligatoriedad : IEvaluador<FilaEnValidacion>
        {
            private static readonly HashSet<string> CamposDeLista = new HashSet<string>(CamposDeFila.DeLista(), StringComparer.Ordinal);

            public string Codigo => Obligatoriedad;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var opcionales = fila.Catalogos.Obligatoriedad.CamposOpcionales(fila.Gestion, fila.Clasificacion, fila.Plan?.TipoFormato);
                var faltantes = new List<string>();

                foreach (var campo in CamposDeFila.Todos())
                {
                    if (opcionales.Contains(campo))
                    {
                        continue;
                    }

                    bool vacio = CamposDeLista.Contains(campo) ? EsCampoDeListaVacio(fila, campo) : fila.Recibido(campo).Length == 0;
                    if (vacio)
                    {
                        faltantes.Add(fila.Encabezado(campo));
                    }
                }

                if (faltantes.Count == 0)
                {
                    return Veredicto.Cumplida();
                }

                var encabezados = string.Join(", ", faltantes);
                var marcadores = new Dictionary<string, string> { ["campo"] = encabezados };
                return Veredicto.NoCumplida($"Faltan datos obligatorios: {encabezados}.", marcadores, null);
            }

            private static bool EsCampoDeListaVacio(FilaEnValidacion fila, string campo)
            {
                switch (campo)
                {
                    case CamposDeFila.Gestion:
                        return fila.Gestion == null;
                    case CamposDeFila.Clasificacion:
                        return fila.Clasificacion == null;
                    case CamposDeFila.TipoIdentificacion:
                        return fila.TipoIdentificacion == null;
                    case CamposDeFila.Moneda:
                        return fila.Moneda == null;
                    case CamposDeFila.Banco:
                        return fila.Banco == null;
                    default:
                        // CamposDeLista solo trae los cinco de arriba (CamposDeFila.DeLista()): no hay otro caso posible.
                        throw new InvalidOperationException($"'{campo}' no es un campo de lista.");
                }
            }
        }

        /// <summary>`REFERENCIA_FORMATO_11` (D-17): en planes formato 11, se cumple si <see cref="FilaEnValidacion.ReferenciaConstruida"/>
        /// se pudo armar. En los otros formatos siempre se cumple (DD-15: no deriva nada). El mensaje nunca cita la cuenta.</summary>
        private sealed class EvaluadorReferenciaFormato11 : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => ReferenciaFormato11;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var plan = fila.Plan;
                if (plan == null)
                {
                    return Veredicto.NoCumplida("No se puede armar la referencia porque el plan no existe.");
                }

                if (plan.TipoFormato != TipoDeFormatoDelPlan._11 || fila.ReferenciaConstruida != null)
                {
                    return Veredicto.Cumplida();
                }

                return Veredicto.NoCumplida("No se pudo armar la referencia: hace falta un banco válido y una cuenta de hasta 17 dígitos.");
            }
        }

        /// <summary>`MONEDA_DEL_PLAN` (RF-07): la moneda de la fila tiene que ser la del plan. Sin moneda recibida no hay nada
        /// que contradiga al plan (si era obligatoria, lo dice OBLIGATORIEDAD).</summary>
        private sealed class EvaluadorMonedaDelPlan : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => MonedaDelPlan;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var plan = fila.Plan;
                if (plan == null)
                {
                    return Veredicto.NoCumplida("No se puede comprobar la moneda porque el plan no existe.");
                }

                if (fila.Recibido(CamposDeFila.Moneda).Length == 0)
                {
                    return Veredicto.Cumplida();
                }

                var moneda = fila.Moneda;
                if (moneda == null)
                {
                    return Veredicto.NoCumplida($"El plan {plan.Codigo} no admite esa moneda.");
                }

                if (moneda.Value == plan.Moneda)
                {
                    return Veredicto.Cumplida();
                }

                var marcadores = new Dictionary<string, string> { ["plan"] = plan.Codigo, ["valor"] = moneda.Value.ToString() };
                return Veredicto.NoCumplida($"La moneda no coincide con la del plan {plan.Codigo}.", marcadores, null);
            }
        }

        /// <summary>
        /// `AUTORIZACION_CORREO_PLAN` (RF-02, D-14): el remitente tiene que tener una autorización vigente sobre el plan. El
        /// texto GENERAL por defecto nombra el plan y no usa la palabra "evidencia" (la usa solo la precisión, y solo en el
        /// caso en que la autorización existe pero le falta el documento).
        /// </summary>
        private sealed class EvaluadorAutorizacionCorreoPlan : IEvaluador<FilaEnValidacion>
        {
            public string Codigo => AutorizacionCorreoPlan;

            public Veredicto Evaluar(FilaEnValidacion fila)
            {
                if (fila == null)
                {
                    throw new ArgumentNullException(nameof(fila));
                }

                var plan = fila.Plan;
                if (plan == null)
                {
                    return Veredicto.NoCumplida("No se puede comprobar la autorización porque el plan no existe.");
                }

                if (fila.Catalogos.AutorizacionSobre(plan.Id) == true)
                {
                    return Veredicto.Cumplida();
                }

                var marcadores = new Dictionary<string, string> { ["plan"] = plan.Codigo };
                var texto = $"Su correo no está habilitado para operar sobre el plan {plan.Codigo}.";
                var precision = fila.Catalogos.AutorizacionSobre(plan.Id) == null
                    ? "Ese correo no está autorizado sobre ese plan."
                    : "La autorización sobre ese plan no tiene la evidencia cargada.";

                return Veredicto.NoCumplida(texto, marcadores, precision);
            }
        }
    }
}
