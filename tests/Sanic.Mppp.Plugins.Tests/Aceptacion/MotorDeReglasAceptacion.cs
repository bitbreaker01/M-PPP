// PRUEBAS DE ACEPTACIÓN de la pieza 7.3 (Validacion), parte 1: EL MOTOR. Salen de diseno/03-contratos-custom-api.md §1 (pasos 4, 5 y 7)
// y de la decisión DD-13 (diseno/02-diccionario-datos.md). Las reglas concretas van aparte. EL CONSTRUCTOR NO MODIFICA ESTE ARCHIVO.
using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    public class MotorDeReglasAceptacion
    {
        /// <summary>Evaluador de prueba: cumple o no según el contexto (la lista de códigos que "fallan"), y anota que lo llamaron.</summary>
        private sealed class Evaluador : IEvaluador<ISet<string>>
        {
            private readonly List<string> _bitacora;

            public Evaluador(string codigo, List<string> bitacora)
            {
                Codigo = codigo;
                _bitacora = bitacora;
            }

            public string Codigo { get; }

            public Veredicto Evaluar(ISet<string> fallan)
            {
                _bitacora.Add(Codigo);
                return fallan.Contains(Codigo) ? Veredicto.NoCumplida($"No se cumple {Codigo}.") : Veredicto.Cumplida();
            }
        }

        private static DefinicionDeRegla Regla(string codigo, int orden, params string[] dependeDe)
        {
            return new DefinicionDeRegla { Codigo = codigo, Orden = orden, DependeDe = dependeDe, Efecto = EfectoDeLaRegla.Rechaza };
        }

        /// <summary>La cadena real de las reglas del sobre (diseno/02 §2.6).</summary>
        private static readonly DefinicionDeRegla[] Sobre =
        {
            Regla("TRAE_ADJUNTO", 10), Regla("ADJUNTO_ES_EXCEL", 20, "TRAE_ADJUNTO"), Regla("UN_SOLO_EXCEL", 30, "ADJUNTO_ES_EXCEL"),
            Regla("ESTRUCTURA_PLANTILLA", 40, "UN_SOLO_EXCEL"), Regla("TIENE_FILAS", 50, "ESTRUCTURA_PLANTILLA"),
        };

        /// <summary>Las dependencias reales de las reglas de registro (diseno/03 §1 paso 5).</summary>
        private static readonly DefinicionDeRegla[] Registro =
        {
            Regla("LISTAS_VALIDAS", 10), Regla("LARGOS_Y_FORMATO", 20), Regla("PLAN_EXISTE", 30),
            Regla("FORMATO_11_SOLO_ACH", 40, "PLAN_EXISTE", "LISTAS_VALIDAS"), Regla("OBLIGATORIEDAD", 50, "PLAN_EXISTE", "LISTAS_VALIDAS"),
            Regla("REFERENCIA_FORMATO_11", 60, "FORMATO_11_SOLO_ACH", "OBLIGATORIEDAD"), Regla("MONEDA_DEL_PLAN", 70, "PLAN_EXISTE", "LISTAS_VALIDAS"),
            Regla("AUTORIZACION_CORREO_PLAN", 80, "PLAN_EXISTE"),
        };

        private static (IList<ResultadoDeRegla> resultados, List<string> llamados) Correr(IEnumerable<DefinicionDeRegla> reglas, params string[] fallan)
        {
            var llamados = new List<string>();
            var lista = reglas.ToList();
            var motor = new MotorDeReglas<ISet<string>>(lista.Select(r => new Evaluador(r.Codigo, llamados)).ToList());
            return (motor.Evaluar(lista, new HashSet<string>(fallan, StringComparer.Ordinal)), llamados);
        }

        private static string Resumen(IEnumerable<ResultadoDeRegla> rs) => string.Join(" ", rs.Select(r => $"{r.Codigo}={r.Resultado}"));

        // ------------------------------------------------------------------ orden y un resultado por cada regla
        [Fact]
        public void Si_todo_cumple_hay_un_resultado_cumplida_por_cada_regla_en_su_orden()
        {
            var (rs, llamados) = Correr(Sobre);
            Assert.Equal(Sobre.Select(r => r.Codigo), rs.Select(r => r.Codigo));
            Assert.All(rs, r => Assert.Equal(ResultadoDeLaRegla.Cumplida, r.Resultado));
            Assert.All(rs, r => Assert.Null(r.Razon));
            Assert.Equal(Sobre.Select(r => r.Codigo), llamados);
        }

        [Fact]
        public void El_orden_lo_da_sanic_orden_no_el_orden_en_que_llegan_las_reglas()
        {
            var (rs, llamados) = Correr(Sobre.Reverse());
            Assert.Equal(new[] { 10, 20, 30, 40, 50 }, rs.Select(r => r.Orden));
            Assert.Equal(Sobre.Select(r => r.Codigo), llamados);
        }

        // ------------------------------------------------------------------ dependencias: DD-13
        [Fact]
        public void DD13_sin_adjunto_todo_lo_que_depende_queda_omitido_y_no_se_evalua()
        {
            // El ejemplo literal del diseño: sin adjunto, ESTRUCTURA_PLANTILLA queda Omitida.
            var (rs, llamados) = Correr(Sobre, "TRAE_ADJUNTO");
            Assert.Equal("TRAE_ADJUNTO=NoCumplida ADJUNTO_ES_EXCEL=Omitida UN_SOLO_EXCEL=Omitida ESTRUCTURA_PLANTILLA=Omitida TIENE_FILAS=Omitida", Resumen(rs));
            Assert.Equal(new[] { "TRAE_ADJUNTO" }, llamados);
            Assert.Equal("No se cumple TRAE_ADJUNTO.", rs[0].Razon);
        }

        [Fact]
        public void DD13_la_razon_de_una_omitida_nombra_a_la_regla_que_la_bloqueo_directamente()
        {
            var (rs, _) = Correr(Sobre, "TRAE_ADJUNTO");
            Assert.Contains("TRAE_ADJUNTO", rs.Single(r => r.Codigo == "ADJUNTO_ES_EXCEL").Razon);
            // A ESTRUCTURA_PLANTILLA la bloquea UN_SOLO_EXCEL (que quedó Omitida): una Omitida tampoco es Cumplida.
            Assert.Contains("UN_SOLO_EXCEL", rs.Single(r => r.Codigo == "ESTRUCTURA_PLANTILLA").Razon);
        }

        [Fact]
        public void DD13_con_varias_dependencias_basta_que_una_no_sea_cumplida()
        {
            var (rs, llamados) = Correr(Registro, "LISTAS_VALIDAS");
            Assert.Equal("LISTAS_VALIDAS=NoCumplida LARGOS_Y_FORMATO=Cumplida PLAN_EXISTE=Cumplida FORMATO_11_SOLO_ACH=Omitida OBLIGATORIEDAD=Omitida "
                         + "REFERENCIA_FORMATO_11=Omitida MONEDA_DEL_PLAN=Omitida AUTORIZACION_CORREO_PLAN=Cumplida", Resumen(rs));
            Assert.Equal(new[] { "LISTAS_VALIDAS", "LARGOS_Y_FORMATO", "PLAN_EXISTE", "AUTORIZACION_CORREO_PLAN" }, llamados);
            Assert.Contains("LISTAS_VALIDAS", rs.Single(r => r.Codigo == "MONEDA_DEL_PLAN").Razon);
        }

        [Fact]
        public void Una_regla_que_falla_no_corta_a_las_que_no_dependen_de_ella()
        {
            // Paso 4: "un ResultadoRegla por cada una". Paso 5: "todos los motivos y no solo el primero".
            var (rs, llamados) = Correr(Registro, "LARGOS_Y_FORMATO", "MONEDA_DEL_PLAN");
            Assert.Equal(8, rs.Count);
            Assert.Equal(8, llamados.Count);
            Assert.Equal(new[] { "LARGOS_Y_FORMATO", "MONEDA_DEL_PLAN" }, rs.Where(r => r.Resultado == ResultadoDeLaRegla.NoCumplida).Select(r => r.Codigo));
        }

        // ------------------------------------------------------------------ la foto del efecto
        [Fact]
        public void Cada_resultado_lleva_la_foto_del_efecto_que_tenia_la_regla_al_evaluarse()
        {
            var reglas = new[]
            {
                new DefinicionDeRegla { Codigo = "A", Orden = 1, Efecto = EfectoDeLaRegla.Advierte },
                new DefinicionDeRegla { Codigo = "B", Orden = 2, Efecto = EfectoDeLaRegla.EnviaARevision, DependeDe = new[] { "A" } },
                new DefinicionDeRegla { Codigo = "C", Orden = 3, Efecto = EfectoDeLaRegla.Rechaza, DependeDe = null },
            };
            var (rs, _) = Correr(reglas, "A");
            Assert.Equal(new[] { EfectoDeLaRegla.Advierte, EfectoDeLaRegla.EnviaARevision, EfectoDeLaRegla.Rechaza }, rs.Select(r => r.EfectoAplicado));
            Assert.Equal("A=NoCumplida B=Omitida C=Cumplida", Resumen(rs));
        }

        [Fact]
        public void Sin_reglas_activas_no_hay_resultados()
        {
            Assert.Empty(new MotorDeReglas<ISet<string>>(new List<IEvaluador<ISet<string>>>()).Evaluar(new DefinicionDeRegla[0], new HashSet<string>()));
        }

        [Fact]
        public void Los_argumentos_nulos_y_un_veredicto_sin_razon_son_errores_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => new MotorDeReglas<ISet<string>>(null));
            var motor = new MotorDeReglas<ISet<string>>(new List<IEvaluador<ISet<string>>>());
            Assert.Throws<ArgumentNullException>(() => motor.Evaluar(null, new HashSet<string>()));
            Assert.Throws<ArgumentException>(() => Veredicto.NoCumplida(" "));
        }

        // ------------------------------------------------------------------ del historial a los estados (pasos 5 y 7)
        private static ResultadoDeRegla R(string codigo, ResultadoDeLaRegla resultado, EfectoDeLaRegla efecto = EfectoDeLaRegla.Rechaza, int orden = 1)
        {
            return new ResultadoDeRegla(codigo, orden, resultado, resultado == ResultadoDeLaRegla.Cumplida ? null : $"motivo de {codigo}", efecto);
        }

        [Fact]
        public void La_fila_queda_validada_si_ninguna_regla_falla()
        {
            Assert.Equal(EstadoDeLaFila.Validada, EstadosPorReglas.DeLaFila(new[] { R("LISTAS_VALIDAS", ResultadoDeLaRegla.Cumplida), R("PLAN_EXISTE", ResultadoDeLaRegla.Cumplida) }));
        }

        [Fact]
        public void La_fila_queda_rechazada_en_validacion_si_falla_una_regla_con_efecto_rechaza()
        {
            var rs = new[] { R("LISTAS_VALIDAS", ResultadoDeLaRegla.NoCumplida), R("OBLIGATORIEDAD", ResultadoDeLaRegla.Omitida), R("PLAN_EXISTE", ResultadoDeLaRegla.Cumplida) };
            Assert.Equal(EstadoDeLaFila.RechazadaEnValidacion, EstadosPorReglas.DeLaFila(rs));
        }

        [Fact]
        public void La_fila_queda_sin_autorizacion_si_falla_la_regla_de_autorizacion()
        {
            Assert.Equal(EstadoDeLaFila.SinAutorizacion, EstadosPorReglas.DeLaFila(new[] { R("PLAN_EXISTE", ResultadoDeLaRegla.Cumplida), R(EstadosPorReglas.CodigoAutorizacion, ResultadoDeLaRegla.NoCumplida) }));
        }

        [Fact]
        public void Una_regla_omitida_no_cuenta_como_falla_por_si_misma()
        {
            // Si la de autorización quedó Omitida (porque falló PLAN_EXISTE), la fila está Rechazada en validación, no Sin autorización.
            var rs = new[] { R("PLAN_EXISTE", ResultadoDeLaRegla.NoCumplida), R(EstadosPorReglas.CodigoAutorizacion, ResultadoDeLaRegla.Omitida) };
            Assert.Equal(EstadoDeLaFila.RechazadaEnValidacion, EstadosPorReglas.DeLaFila(rs));
            Assert.Equal(EstadoDeLaFila.Validada, EstadosPorReglas.DeLaFila(new[] { R("X", ResultadoDeLaRegla.Omitida) }));
        }

        [Fact]
        public void Una_regla_que_solo_advierte_no_rechaza_la_fila_pero_su_motivo_se_informa()
        {
            var rs = new[] { R("LISTAS_VALIDAS", ResultadoDeLaRegla.Cumplida), R("AVISO", ResultadoDeLaRegla.NoCumplida, EfectoDeLaRegla.Advierte) };
            Assert.Equal(EstadoDeLaFila.Validada, EstadosPorReglas.DeLaFila(rs));
            Assert.Equal(new[] { "motivo de AVISO" }, EstadosPorReglas.MotivosDeLaFila(rs));
        }

        [Fact]
        public void El_mensaje_de_la_fila_lleva_todos_los_motivos_de_lo_que_fallo_en_orden_y_nada_de_las_omitidas()
        {
            var rs = new[]
            {
                R("MONEDA_DEL_PLAN", ResultadoDeLaRegla.NoCumplida, orden: 70), R("LISTAS_VALIDAS", ResultadoDeLaRegla.Cumplida, orden: 10),
                R("LARGOS_Y_FORMATO", ResultadoDeLaRegla.NoCumplida, orden: 20), R("OBLIGATORIEDAD", ResultadoDeLaRegla.Omitida, orden: 50),
            };
            Assert.Equal(new[] { "motivo de LARGOS_Y_FORMATO", "motivo de MONEDA_DEL_PLAN" }, EstadosPorReglas.MotivosDeLaFila(rs));
        }

        [Fact]
        public void El_sobre_rechaza_si_falla_una_regla_con_efecto_rechaza_y_no_por_una_omitida_ni_por_una_advertencia()
        {
            Assert.True(EstadosPorReglas.ElSobreRechaza(new[] { R("TRAE_ADJUNTO", ResultadoDeLaRegla.NoCumplida), R("ADJUNTO_ES_EXCEL", ResultadoDeLaRegla.Omitida) }));
            Assert.False(EstadosPorReglas.ElSobreRechaza(new[] { R("TRAE_ADJUNTO", ResultadoDeLaRegla.Cumplida), R("AVISO", ResultadoDeLaRegla.NoCumplida, EfectoDeLaRegla.Advierte) }));
            Assert.False(EstadosPorReglas.ElSobreRechaza(new ResultadoDeRegla[0]));
        }

        [Fact]
        public void La_solicitud_queda_rechazada_si_el_sobre_rechaza_o_si_ninguna_fila_quedo_validada_y_si_no_en_proceso()
        {
            var sobreBien = new[] { R("TRAE_ADJUNTO", ResultadoDeLaRegla.Cumplida) };
            var sobreMal = new[] { R("TRAE_ADJUNTO", ResultadoDeLaRegla.NoCumplida) };
            Assert.Equal(EstadoDeLaSolicitud.Rechazada, EstadosPorReglas.DeLaSolicitud(sobreMal, new EstadoDeLaFila[0]));
            Assert.Equal(EstadoDeLaSolicitud.Rechazada, EstadosPorReglas.DeLaSolicitud(sobreBien, new[] { EstadoDeLaFila.RechazadaEnValidacion, EstadoDeLaFila.SinAutorizacion }));
            Assert.Equal(EstadoDeLaSolicitud.Rechazada, EstadosPorReglas.DeLaSolicitud(sobreBien, new EstadoDeLaFila[0]));
            Assert.Equal(EstadoDeLaSolicitud.EnProceso, EstadosPorReglas.DeLaSolicitud(sobreBien, new[] { EstadoDeLaFila.RechazadaEnValidacion, EstadoDeLaFila.Validada }));
        }

        [Fact]
        public void Los_historiales_nulos_son_errores_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => EstadosPorReglas.DeLaFila(null));
            Assert.Throws<ArgumentNullException>(() => EstadosPorReglas.MotivosDeLaFila(null));
            Assert.Throws<ArgumentNullException>(() => EstadosPorReglas.ElSobreRechaza(null));
            Assert.Throws<ArgumentNullException>(() => EstadosPorReglas.DeLaSolicitud(null, new EstadoDeLaFila[0]));
            Assert.Throws<ArgumentNullException>(() => EstadosPorReglas.DeLaSolicitud(new ResultadoDeRegla[0], null));
        }
    }
}
