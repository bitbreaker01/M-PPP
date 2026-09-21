using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>
    /// El catálogo de reglas, o el cableado de sus evaluadores, está mal: código vacío o repetido, dependencia vacía, una regla que depende de sí
    /// misma, un ciclo, una dependencia que no se evaluó antes, un evaluador que devuelve nulo. SIEMPRE nombra la regla. No es un rechazo de negocio:
    /// es una excepción real (diseno/03 §1 "Errores"): la transacción se revierte y la solicitud queda para reintento y revisión.
    /// </summary>
    public sealed class ConfiguracionDeReglasInvalidaException : Exception
    {
        public ConfiguracionDeReglasInvalidaException(string codigoDeRegla, string mensaje)
            : base(mensaje)
        {
            CodigoDeRegla = codigoDeRegla;
        }

        /// <summary>La regla que tiene el problema (o `null` si el problema es justamente que no tiene código).</summary>
        public string CodigoDeRegla { get; }
    }

    /// <summary>Una regla ACTIVA del catálogo (`sanic_mppp_tbl_regla`), tal como la entrega la capa de datos. Sin SDK.</summary>
    public sealed class DefinicionDeRegla
    {
        public string Codigo { get; set; }

        /// <summary>`sanic_orden`: el motor evalúa de menor a mayor.</summary>
        public int Orden { get; set; }

        /// <summary>`sanic_dependede`: códigos de las reglas que tienen que haber resultado Cumplida. Puede ser nulo o vacío.</summary>
        public IList<string> DependeDe { get; set; }

        public EfectoDeLaRegla Efecto { get; set; }
    }

    /// <summary>Lo que devuelve un evaluador: cumple o no, y por qué no (texto para el cliente).</summary>
    public sealed class Veredicto
    {
        private Veredicto(bool cumple, string razon)
        {
            Cumple = cumple;
            Razon = razon;
        }

        public bool Cumple { get; }

        public string Razon { get; }

        public static Veredicto Cumplida() => new Veredicto(true, null);

        /// <summary>La razón es obligatoria: una regla que falla sin decir por qué es un error de programación.</summary>
        public static Veredicto NoCumplida(string razon)
        {
            if (string.IsNullOrWhiteSpace(razon))
            {
                throw new ArgumentException("Una regla que no se cumple tiene que decir por qué.", nameof(razon));
            }

            return new Veredicto(false, razon);
        }
    }

    /// <summary>El código C# tiene un evaluador por código de regla (diseno/02 §2.6). `TContexto` es lo que mira: el sobre, o una fila.</summary>
    public interface IEvaluador<in TContexto>
    {
        string Codigo { get; }

        Veredicto Evaluar(TContexto contexto);
    }

    /// <summary>Un renglón del historial (`sanic_mppp_tbl_resultadoregla`, diseno/02 §3.3).</summary>
    public sealed class ResultadoDeRegla
    {
        public ResultadoDeRegla(string codigo, int orden, ResultadoDeLaRegla resultado, string razon, EfectoDeLaRegla efectoAplicado)
        {
            // Es el tipo que sobrevive a la evaluación (se persiste y se rehidrata): protege la misma invariante que Veredicto.
            if (string.IsNullOrWhiteSpace(codigo))
            {
                throw new ArgumentException("Un resultado tiene que decir de qué regla es.", nameof(codigo));
            }

            if (resultado != ResultadoDeLaRegla.Cumplida && string.IsNullOrWhiteSpace(razon))
            {
                throw new ArgumentException($"El resultado {resultado} de la regla {codigo} tiene que llevar su razón: un motivo en blanco nunca llega al cliente.", nameof(razon));
            }

            Codigo = codigo;
            Orden = orden;
            Resultado = resultado;
            Razon = razon;
            EfectoAplicado = efectoAplicado;
        }

        public string Codigo { get; }

        public int Orden { get; }

        public ResultadoDeLaRegla Resultado { get; }

        /// <summary>No cumplida: lo que dijo el evaluador. Omitida: qué regla la bloqueó (DD-13). Cumplida: nulo.</summary>
        public string Razon { get; }

        /// <summary>FOTO del efecto que tenía la regla al evaluarse: el catálogo es editable y el histórico tiene que seguir diciendo qué pasó.</summary>
        public EfectoDeLaRegla EfectoAplicado { get; }
    }

    /// <summary>
    /// El motor de orden y dependencias (DD-13; diseno/03 §1 pasos 4 y 5). Es el MISMO para los tres niveles (Correo, Solicitud, Registro):
    /// por eso es genérico. Función pura: no lee reloj, no toca Dataverse.
    /// </summary>
    public sealed class MotorDeReglas<TContexto>
    {
        private readonly Dictionary<string, IEvaluador<TContexto>> _evaluadoresPorCodigo;

        public MotorDeReglas(IEnumerable<IEvaluador<TContexto>> evaluadores)
        {
            if (evaluadores == null)
            {
                throw new ArgumentNullException(nameof(evaluadores));
            }

            // Códigos de regla se comparan ordinal (son identificadores, no texto de usuario).
            _evaluadoresPorCodigo = new Dictionary<string, IEvaluador<TContexto>>(StringComparer.Ordinal);
            foreach (var evaluador in evaluadores)
            {
                // Cableado mal armado (revisión de código, 2026-09-21): un evaluador nulo, sin código, o dos evaluadores
                // para el mismo código (antes ganaba el último en silencio) son un error de configuración, no un caso a tolerar.
                if (evaluador == null)
                {
                    throw new ConfiguracionDeReglasInvalidaException(null, "El cableado de evaluadores trae un evaluador nulo.");
                }

                if (string.IsNullOrWhiteSpace(evaluador.Codigo))
                {
                    throw new ConfiguracionDeReglasInvalidaException(null, "El cableado de evaluadores trae un evaluador sin código.");
                }

                if (_evaluadoresPorCodigo.ContainsKey(evaluador.Codigo))
                {
                    throw new ConfiguracionDeReglasInvalidaException(evaluador.Codigo, $"Hay dos evaluadores registrados para el código de regla '{evaluador.Codigo}'.");
                }

                _evaluadoresPorCodigo[evaluador.Codigo] = evaluador;
            }
        }

        /// <summary>
        /// Evalúa TODAS las reglas activas en su orden y devuelve un resultado por cada una (nunca corta antes: "un ResultadoRegla por cada una").
        /// Una regla cuyas dependencias no resultaron todas Cumplida no se evalúa: queda Omitida y su razón nombra a la que la bloqueó.
        /// </summary>
        public IList<ResultadoDeRegla> Evaluar(IEnumerable<DefinicionDeRegla> reglasActivas, TContexto contexto)
        {
            if (reglasActivas == null)
            {
                throw new ArgumentNullException(nameof(reglasActivas));
            }

            var lista = reglasActivas.ToList();

            // Valida el catálogo ENTERO (definiciones nulas, códigos nulos/en blanco/repetidos, dependencias, ciclos) ANTES de
            // llamar a ningún evaluador, y recién ADENTRO lo ordena (revisión de código, 2026-09-21): si se ordena primero, una
            // definición nula revienta con NullReferenceException al leer r.Orden en vez de fallar cerrado con
            // ConfiguracionDeReglasInvalidaException — con un solo elemento el runtime no llega a invocar el selector, por eso
            // ese caso pasaba antes y el de dos o más no.
            var ordenadas = ValidarCatalogo(lista);

            var resultados = new List<ResultadoDeRegla>(ordenadas.Count);
            var resultadoPorCodigo = new Dictionary<string, ResultadoDeLaRegla>(StringComparer.Ordinal);

            foreach (var regla in ordenadas)
            {
                // DD-13: las dependencias que no resultaron TODAS Cumplida (incluye Omitida) bloquean la regla, que queda Omitida.
                // Una dependencia repetida (DependeDe = ["A","A"]) nombra a "A" una sola vez en la razón.
                var dependenciasQueBloquean = new List<string>();
                if (regla.DependeDe != null)
                {
                    foreach (var codigoDependencia in regla.DependeDe)
                    {
                        // El catálogo ya está validado: la dependencia existe y se evaluó antes (ValidarCatalogo lo garantiza).
                        var resultadoDependencia = resultadoPorCodigo[codigoDependencia];
                        if (resultadoDependencia != ResultadoDeLaRegla.Cumplida
                            && !dependenciasQueBloquean.Contains(codigoDependencia, StringComparer.Ordinal))
                        {
                            dependenciasQueBloquean.Add(codigoDependencia);
                        }
                    }
                }

                ResultadoDeRegla resultado;
                if (dependenciasQueBloquean.Count > 0)
                {
                    // El evaluador de una regla Omitida no se llama. La razón nombra a TODAS las dependencias directas que no fueron Cumplida.
                    var razon = "Omitida: no se cumplió " + string.Join(", ", dependenciasQueBloquean) + ".";
                    resultado = new ResultadoDeRegla(regla.Codigo, regla.Orden, ResultadoDeLaRegla.Omitida, razon, regla.Efecto);
                }
                else
                {
                    // El catálogo ya está validado: la regla tiene evaluador registrado (ValidarCatalogo lo garantiza).
                    var evaluador = _evaluadoresPorCodigo[regla.Codigo];
                    var veredicto = evaluador.Evaluar(contexto);
                    if (veredicto == null)
                    {
                        // Un evaluador nuestro con un bug (devuelve null en vez de un Veredicto) es cableado mal armado, no una excepción real
                        // del evaluador: si lo fuera (Una_excepcion_real_de_un_evaluador...), no pasa por acá porque Evaluar() misma revienta antes.
                        throw new ConfiguracionDeReglasInvalidaException(regla.Codigo, $"El evaluador de la regla '{regla.Codigo}' devolvió un veredicto nulo.");
                    }

                    var resultadoRegla = veredicto.Cumple ? ResultadoDeLaRegla.Cumplida : ResultadoDeLaRegla.NoCumplida;
                    resultado = new ResultadoDeRegla(regla.Codigo, regla.Orden, resultadoRegla, veredicto.Razon, regla.Efecto);
                }

                resultados.Add(resultado);
                resultadoPorCodigo[regla.Codigo] = resultado.Resultado;
            }

            return resultados;
        }

        /// <summary>
        /// Valida el catálogo entero antes de ordenarlo y de evaluar nada (revisión de código, 2026-09-21): PRIMERO definiciones nulas y
        /// código nulo o en blanco (así el OrderBy de abajo nunca lee r.Orden de una definición nula), después códigos repetidos; recién ahí
        /// ordena y valida dependencias nulas o en blanco, una regla que depende de sí misma, un ciclo (que siempre se manifiesta como una
        /// dependencia con Orden mayor o igual: ver nota abajo), una dependencia que no está entre las activas, y una regla activa sin
        /// evaluador. Devuelve el catálogo ya ordenado (Orden asc, empatadas por Código ordinal) para que Evaluar lo use directamente.
        /// </summary>
        private List<DefinicionDeRegla> ValidarCatalogo(IList<DefinicionDeRegla> lista)
        {
            foreach (var regla in lista)
            {
                if (regla == null)
                {
                    throw new ConfiguracionDeReglasInvalidaException(null, "El catálogo de reglas trae una definición nula.");
                }

                if (string.IsNullOrWhiteSpace(regla.Codigo))
                {
                    throw new ConfiguracionDeReglasInvalidaException(null, "El catálogo de reglas trae una regla sin código.");
                }
            }

            var porCodigo = new Dictionary<string, DefinicionDeRegla>(StringComparer.Ordinal);
            foreach (var regla in lista)
            {
                if (porCodigo.ContainsKey(regla.Codigo))
                {
                    throw new ConfiguracionDeReglasInvalidaException(regla.Codigo, $"El código de regla '{regla.Codigo}' está repetido en el catálogo.");
                }

                porCodigo[regla.Codigo] = regla;
            }

            // "El motor evalúa todas las reglas activas, de menor a mayor Orden; empatadas, por Código ordinal" (desempate determinista:
            // no depende de cómo vinieron de la consulta). Ya se sabe que no hay definiciones nulas ni códigos nulos/en blanco: el
            // selector r.Orden no puede reventar acá.
            var ordenadas = lista.OrderBy(r => r.Orden).ThenBy(r => r.Codigo, StringComparer.Ordinal).ToList();

            // Posición de cada regla en el orden real de evaluación: sirve para saber si una dependencia ya se evaluó cuando le
            // toca el turno a quien depende de ella.
            var posicion = new Dictionary<string, int>(StringComparer.Ordinal);
            for (var i = 0; i < ordenadas.Count; i++)
            {
                posicion[ordenadas[i].Codigo] = i;
            }

            foreach (var regla in lista)
            {
                // Decisión provisoria (D-13, pendiente; ninguna prueba lo ejercita): una regla activa sin evaluador registrado falla
                // cerrado (02 §2.6: "es un error de configuración") en vez de decidir algo por su cuenta.
                if (!_evaluadoresPorCodigo.ContainsKey(regla.Codigo))
                {
                    throw new ConfiguracionDeReglasInvalidaException(regla.Codigo, $"La regla activa '{regla.Codigo}' no tiene evaluador registrado.");
                }

                if (regla.DependeDe == null)
                {
                    continue;
                }

                foreach (var codigoDependencia in regla.DependeDe)
                {
                    if (string.IsNullOrWhiteSpace(codigoDependencia))
                    {
                        throw new ConfiguracionDeReglasInvalidaException(regla.Codigo, $"La regla '{regla.Codigo}' tiene una dependencia sin código.");
                    }

                    if (string.Equals(codigoDependencia, regla.Codigo, StringComparison.Ordinal))
                    {
                        throw new ConfiguracionDeReglasInvalidaException(regla.Codigo, $"La regla '{regla.Codigo}' depende de sí misma.");
                    }

                    if (!porCodigo.ContainsKey(codigoDependencia))
                    {
                        // Decisión provisoria (D-13, pendiente; ninguna prueba lo ejercita): una dependencia que no está entre
                        // las reglas activas falla cerrado en vez de decidir algo por su cuenta.
                        throw new ConfiguracionDeReglasInvalidaException(
                            regla.Codigo, $"La regla '{regla.Codigo}' depende de '{codigoDependencia}', que no está entre las reglas activas.");
                    }

                    if (posicion[codigoDependencia] >= posicion[regla.Codigo])
                    {
                        // Distinto del caso de arriba: la dependencia SÍ existe en el catálogo, pero por su Orden (mayor o igual al de
                        // quien depende de ella) todavía no se evaluó cuando le toca el turno. Un ciclo (A depende de B, B depende de A)
                        // siempre se manifiesta acá: en cualquier ciclo hay al menos un tramo que "sube" de Orden.
                        throw new ConfiguracionDeReglasInvalidaException(
                            regla.Codigo,
                            $"La regla '{regla.Codigo}' depende de '{codigoDependencia}', pero por ORDEN esa dependencia todavía no se evaluó "
                            + "(tiene 'sanic_orden' mayor o igual, o hay un ciclo entre ambas).");
                    }
                }
            }

            return ordenadas;
        }
    }

    /// <summary>Cómo se traduce el historial de reglas en estados (diseno/03 §1 pasos 4, 5 y 7).</summary>
    public static class EstadosPorReglas
    {
        /// <summary>La única regla que tiene estado propio cuando falla: deja la fila en Sin autorización.</summary>
        public const string CodigoAutorizacion = "AUTORIZACION_CORREO_PLAN";

        public static EstadoDeLaFila DeLaFila(IEnumerable<ResultadoDeRegla> resultadosDeRegistro)
        {
            if (resultadosDeRegistro == null)
            {
                throw new ArgumentNullException(nameof(resultadosDeRegistro));
            }

            var lista = resultadosDeRegistro as IList<ResultadoDeRegla> ?? resultadosDeRegistro.ToList();

            // AUTORIZACION_CORREO_PLAN No cumplida manda: Sin autorización, aunque otras reglas también hayan fallado.
            if (lista.Any(r => string.Equals(r.Codigo, CodigoAutorizacion, StringComparison.Ordinal) && r.Resultado == ResultadoDeLaRegla.NoCumplida))
            {
                return EstadoDeLaFila.SinAutorizacion;
            }

            // Una Omitida nunca cuenta como falla; solo una No cumplida con efecto Rechaza rechaza la fila.
            if (lista.Any(r => r.Resultado == ResultadoDeLaRegla.NoCumplida && r.EfectoAplicado == EfectoDeLaRegla.Rechaza))
            {
                return EstadoDeLaFila.RechazadaEnValidacion;
            }

            return EstadoDeLaFila.Validada;
        }

        /// <summary>Los motivos de las reglas que FALLARON, todos y en orden, para `sanic_mensaje`. Las Omitidas y las Cumplidas no aportan.</summary>
        public static IList<string> MotivosDeLaFila(IEnumerable<ResultadoDeRegla> resultadosDeRegistro)
        {
            if (resultadosDeRegistro == null)
            {
                throw new ArgumentNullException(nameof(resultadosDeRegistro));
            }

            // Cualquiera sea su efecto (Rechaza o Advierte): "los motivos de las reglas que fallaron, todos y no solo el primero".
            return resultadosDeRegistro
                .Where(r => r.Resultado == ResultadoDeLaRegla.NoCumplida)
                .OrderBy(r => r.Orden)
                .Select(r => r.Razon)
                .ToList();
        }

        /// <summary>¿Las reglas del sobre rechazan la solicitud? (paso 4: falla alguna con efecto Rechaza).</summary>
        public static bool ElSobreRechaza(IEnumerable<ResultadoDeRegla> resultadosDeSolicitud)
        {
            if (resultadosDeSolicitud == null)
            {
                throw new ArgumentNullException(nameof(resultadosDeSolicitud));
            }

            return resultadosDeSolicitud.Any(r => r.Resultado == ResultadoDeLaRegla.NoCumplida && r.EfectoAplicado == EfectoDeLaRegla.Rechaza);
        }

        /// <summary>Estado final de la solicitud (paso 7): Rechazada si el sobre rechaza o si ninguna fila quedó Validada; si no, En proceso.</summary>
        public static EstadoDeLaSolicitud DeLaSolicitud(IEnumerable<ResultadoDeRegla> resultadosDeSolicitud, IEnumerable<EstadoDeLaFila> estadosDeLasFilas)
        {
            if (resultadosDeSolicitud == null)
            {
                throw new ArgumentNullException(nameof(resultadosDeSolicitud));
            }

            if (estadosDeLasFilas == null)
            {
                throw new ArgumentNullException(nameof(estadosDeLasFilas));
            }

            if (ElSobreRechaza(resultadosDeSolicitud))
            {
                return EstadoDeLaSolicitud.Rechazada;
            }

            // "Rechazada si ninguna fila es válida" (DD-09): también rechaza si no hay ninguna fila.
            if (!estadosDeLasFilas.Any(f => f == EstadoDeLaFila.Validada))
            {
                return EstadoDeLaSolicitud.Rechazada;
            }

            return EstadoDeLaSolicitud.EnProceso;
        }
    }
}
