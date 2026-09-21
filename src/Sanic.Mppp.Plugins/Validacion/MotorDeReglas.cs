using System;
using System.Collections.Generic;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Validacion
{
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
        public MotorDeReglas(IEnumerable<IEvaluador<TContexto>> evaluadores)
        {
            throw new NotImplementedException();
        }

        /// <summary>
        /// Evalúa TODAS las reglas activas en su orden y devuelve un resultado por cada una (nunca corta antes: "un ResultadoRegla por cada una").
        /// Una regla cuyas dependencias no resultaron todas Cumplida no se evalúa: queda Omitida y su razón nombra a la que la bloqueó.
        /// </summary>
        public IList<ResultadoDeRegla> Evaluar(IEnumerable<DefinicionDeRegla> reglasActivas, TContexto contexto)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>Cómo se traduce el historial de reglas en estados (diseno/03 §1 pasos 4, 5 y 7).</summary>
    public static class EstadosPorReglas
    {
        /// <summary>La única regla que tiene estado propio cuando falla: deja la fila en Sin autorización.</summary>
        public const string CodigoAutorizacion = "AUTORIZACION_CORREO_PLAN";

        public static EstadoDeLaFila DeLaFila(IEnumerable<ResultadoDeRegla> resultadosDeRegistro)
        {
            throw new NotImplementedException();
        }

        /// <summary>Los motivos de las reglas que FALLARON, todos y en orden, para `sanic_mensaje`. Las Omitidas y las Cumplidas no aportan.</summary>
        public static IList<string> MotivosDeLaFila(IEnumerable<ResultadoDeRegla> resultadosDeRegistro)
        {
            throw new NotImplementedException();
        }

        /// <summary>¿Las reglas del sobre rechazan la solicitud? (paso 4: falla alguna con efecto Rechaza).</summary>
        public static bool ElSobreRechaza(IEnumerable<ResultadoDeRegla> resultadosDeSolicitud)
        {
            throw new NotImplementedException();
        }

        /// <summary>Estado final de la solicitud (paso 7): Rechazada si el sobre rechaza o si ninguna fila quedó Validada; si no, En proceso.</summary>
        public static EstadoDeLaSolicitud DeLaSolicitud(IEnumerable<ResultadoDeRegla> resultadosDeSolicitud, IEnumerable<EstadoDeLaFila> estadosDeLasFilas)
        {
            throw new NotImplementedException();
        }
    }
}
