using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// Las cinco reglas semilla de nivel Solicitud (diseno/02 §2.6), con las condiciones que cerró el aprobador el 2026-09-21:
    /// D-15 (`sanic_cantidadexcel`) y D-16. Se prueban POR el motor con el catálogo semilla (como van a correr) y también
    /// sueltas: el catálogo es editable, y un evaluador al que le sacaron la dependencia no puede dar por bueno lo que no miró.
    /// </summary>
    public class ReglasDelSobreAceptacion
    {
        private const string C = "C";
        private const string N = "N";
        private const string O = "O";

        private static readonly string[] Codigos =
        {
            ReglasDelSobre.TraeAdjunto, ReglasDelSobre.AdjuntoEsExcel, ReglasDelSobre.UnSoloExcel, ReglasDelSobre.EstructuraPlantilla, ReglasDelSobre.TieneFilas,
        };

        /// <summary>El catálogo semilla: cada regla depende de la anterior, todas Rechaza (diseno/02 §2.6).</summary>
        private static DefinicionDeRegla[] Semilla(IDictionary<string, string> mensajes = null)
        {
            return Codigos.Select((codigo, i) => new DefinicionDeRegla
            {
                Codigo = codigo,
                Orden = (i + 1) * 10,
                Efecto = EfectoDeLaRegla.Rechaza,
                DependeDe = i == 0 ? null : new[] { Codigos[i - 1] },
                MensajeCliente = mensajes != null && mensajes.TryGetValue(codigo, out var m) ? m : null,
            }).ToArray();
        }

        private static ResultadoLecturaPlantilla Valida(int filas)
        {
            var lista = Enumerable.Range(1, filas)
                .Select(i => new FilaPlantilla { NumeroFilaExcel = 12 + i, NumeroOrden = i, Valores = new Dictionary<string, string> { ["C"] = "x" } })
                .ToList();
            return ResultadoLecturaPlantilla.ConFilas(lista, new List<AdvertenciaLectura>());
        }

        private sealed class Lector
        {
            private readonly ResultadoLecturaPlantilla _resultado;

            public Lector(ResultadoLecturaPlantilla resultado)
            {
                _resultado = resultado;
            }

            public int Llamadas { get; private set; }

            public ResultadoLecturaPlantilla Leer()
            {
                Llamadas++;
                return _resultado;
            }
        }

        private static IList<ResultadoDeRegla> Correr(SobreEnValidacion sobre, IDictionary<string, string> mensajes = null)
        {
            return new MotorDeReglas<SobreEnValidacion>(ReglasDelSobre.Evaluadores()).Evaluar(Semilla(mensajes), sobre);
        }

        private static string Letras(IEnumerable<ResultadoDeRegla> rs)
        {
            return string.Concat(rs.Select(r => r.Resultado == ResultadoDeLaRegla.Cumplida ? C : r.Resultado == ResultadoDeLaRegla.NoCumplida ? N : O));
        }

        private static IEvaluador<SobreEnValidacion> Evaluador(string codigo)
        {
            return ReglasDelSobre.Evaluadores().Single(e => e.Codigo == codigo);
        }

        // ------------------------------------------------------------------ el cableado
        [Fact]
        public void Hay_un_evaluador_por_cada_regla_semilla_del_sobre_ni_uno_mas_y_no_comparten_instancias()
        {
            var unos = ReglasDelSobre.Evaluadores();
            Assert.Equal(Codigos.OrderBy(c => c, StringComparer.Ordinal), unos.Select(e => e.Codigo).OrderBy(c => c, StringComparer.Ordinal));
            Assert.Empty(unos.Intersect(ReglasDelSobre.Evaluadores()));
        }

        // ------------------------------------------------------------------ la matriz del sobre, por el motor
        [Theory]
        [InlineData(0, 0, "NOOOO")] // no adjuntó nada
        [InlineData(1, 0, "CNOOO")] // mandó un PDF
        [InlineData(3, 0, "CNOOO")] // mandó tres archivos y ninguno es Excel
        [InlineData(2, 2, "CCNOO")] // mandó dos Excel
        [InlineData(5, 3, "CCNOO")]
        public void Si_el_sobre_falla_antes_de_la_plantilla_el_excel_no_se_abre(int adjuntos, int excel, string esperado)
        {
            var lector = new Lector(Valida(2));
            var sobre = new SobreEnValidacion(adjuntos, excel, lector.Leer);

            Assert.Equal(esperado, Letras(Correr(sobre)));
            Assert.Equal(0, lector.Llamadas);
            Assert.False(sobre.PlantillaLeida);
        }

        [Theory]
        [InlineData(1, 1)]
        [InlineData(3, 1)] // un Excel entre otros adjuntos (la firma del correo, un PDF): es legítimo
        public void Con_un_solo_excel_bien_armado_y_con_filas_se_cumplen_las_cinco_y_el_excel_se_abre_una_sola_vez(int adjuntos, int excel)
        {
            var lector = new Lector(Valida(2));
            var sobre = new SobreEnValidacion(adjuntos, excel, lector.Leer);

            var rs = Correr(sobre);

            Assert.Equal("CCCCC", Letras(rs));
            Assert.All(rs, r => Assert.Null(r.Razon));
            Assert.Equal(1, lector.Llamadas);
            Assert.True(sobre.PlantillaLeida);
        }

        [Fact]
        public void Una_plantilla_que_el_lector_no_da_por_valida_falla_la_estructura_con_los_motivos_del_lector_y_nunca_con_su_detalle_tecnico()
        {
            var lectura = ResultadoLecturaPlantilla.ConErrorTecnico("El archivo no se puede leer como una plantilla de Excel.", "DocumentFormat.OpenXml: boom en part /xl/workbook.xml");
            var rs = Correr(new SobreEnValidacion(1, 1, () => lectura));

            Assert.Equal("CCCNO", Letras(rs));
            var razon = rs[3].Razon;
            Assert.Contains("El archivo no se puede leer como una plantilla de Excel.", razon);
            Assert.DoesNotContain("OpenXml", razon);
            Assert.DoesNotContain("boom", razon);
        }

        [Fact]
        public void Si_el_lector_da_varios_motivos_van_todos_y_en_su_orden_despues_del_texto_general()
        {
            var lectura = ResultadoLecturaPlantilla.ConErrores(new List<string> { "Falta la hoja 'Datos'.", "El encabezado de la columna C no es 'Gestion'." });
            var mensajes = new Dictionary<string, string> { [ReglasDelSobre.EstructuraPlantilla] = "El archivo no es la plantilla vigente ({regla})." };

            var razon = Correr(new SobreEnValidacion(1, 1, () => lectura), mensajes)[3].Razon;

            Assert.Equal("El archivo no es la plantilla vigente (ESTRUCTURA_PLANTILLA). Falta la hoja 'Datos'. El encabezado de la columna C no es 'Gestion'.", razon);
        }

        [Fact]
        public void Una_plantilla_valida_sin_ninguna_fila_con_datos_falla_tiene_filas()
        {
            var rs = Correr(new SobreEnValidacion(1, 1, () => Valida(0)));
            Assert.Equal("CCCCN", Letras(rs));
            Assert.False(string.IsNullOrWhiteSpace(rs[4].Razon));
        }

        // ------------------------------------------------------------------ los mensajes (D-19)
        [Theory]
        [InlineData(0, 0)]
        [InlineData(1, 0)]
        [InlineData(2, 2)]
        public void Sin_texto_en_el_catalogo_cada_regla_que_falla_trae_su_propio_texto_para_el_cliente(int adjuntos, int excel)
        {
            var falla = Correr(new SobreEnValidacion(adjuntos, excel, () => Valida(1))).Single(r => r.Resultado == ResultadoDeLaRegla.NoCumplida);
            Assert.False(string.IsNullOrWhiteSpace(falla.Razon));
            Assert.DoesNotContain("{", falla.Razon);
            Assert.DoesNotContain("_", falla.Razon); // al cliente no se le habla con códigos de regla
        }

        [Fact]
        public void Los_conteos_viajan_como_marcador_valor_para_que_el_negocio_los_cite()
        {
            var mensajes = new Dictionary<string, string>
            {
                [ReglasDelSobre.AdjuntoEsExcel] = "Recibimos {valor} adjuntos y ninguno es de Excel.",
                [ReglasDelSobre.UnSoloExcel] = "Recibimos {valor} archivos de Excel; envie uno solo.",
            };

            Assert.Equal("Recibimos 3 adjuntos y ninguno es de Excel.", Correr(new SobreEnValidacion(3, 0, () => Valida(1)), mensajes)[1].Razon);
            Assert.Equal("Recibimos 2 archivos de Excel; envie uno solo.", Correr(new SobreEnValidacion(4, 2, () => Valida(1)), mensajes)[2].Razon);
        }

        [Fact]
        public void Una_lectura_invalida_que_no_trae_motivos_igual_deja_un_texto_para_el_cliente()
        {
            var lectura = ResultadoLecturaPlantilla.ConErrores(new List<string>());
            var razon = Correr(new SobreEnValidacion(1, 1, () => lectura))[3].Razon;
            Assert.False(string.IsNullOrWhiteSpace(razon));
        }

        // ------------------------------------------------------------------ sueltas: el catálogo es editable
        [Theory]
        [InlineData(ReglasDelSobre.AdjuntoEsExcel, 0, 0)] // le sacaron la dependencia de TRAE_ADJUNTO
        [InlineData(ReglasDelSobre.UnSoloExcel, 0, 0)]
        [InlineData(ReglasDelSobre.UnSoloExcel, 2, 0)]
        [InlineData(ReglasDelSobre.EstructuraPlantilla, 0, 0)]
        [InlineData(ReglasDelSobre.EstructuraPlantilla, 2, 2)]
        [InlineData(ReglasDelSobre.TieneFilas, 0, 0)]
        [InlineData(ReglasDelSobre.TieneFilas, 2, 2)]
        public void Un_evaluador_al_que_le_sacaron_la_dependencia_no_da_por_bueno_lo_que_no_miro_ni_abre_un_excel_que_no_hay(string codigo, int adjuntos, int excel)
        {
            var lector = new Lector(Valida(2));
            var veredicto = Evaluador(codigo).Evaluar(new SobreEnValidacion(adjuntos, excel, lector.Leer));

            Assert.False(veredicto.Cumple);
            Assert.Equal(0, lector.Llamadas); // sin exactamente un Excel no hay nada que abrir
        }

        [Fact]
        public void Tiene_filas_suelta_sobre_una_plantilla_invalida_no_se_cumple()
        {
            var lectura = ResultadoLecturaPlantilla.ConError("Falta la hoja 'Datos'.");
            Assert.False(Evaluador(ReglasDelSobre.TieneFilas).Evaluar(new SobreEnValidacion(1, 1, () => lectura)).Cumple);
        }

        [Fact]
        public void Un_sobre_nulo_es_un_error_de_programacion()
        {
            Assert.All(ReglasDelSobre.Evaluadores(), e => Assert.Throws<ArgumentNullException>(() => e.Evaluar(null)));
        }

        // ------------------------------------------------------------------ el sobre
        [Fact]
        public void El_sobre_no_se_arma_con_conteos_imposibles_ni_sin_lector()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => new SobreEnValidacion(-1, 0, () => Valida(1)));
            Assert.Throws<ArgumentOutOfRangeException>(() => new SobreEnValidacion(1, -1, () => Valida(1)));
            Assert.Throws<ArgumentException>(() => new SobreEnValidacion(1, 2, () => Valida(1))); // más Excel que adjuntos
            Assert.Throws<ArgumentNullException>(() => new SobreEnValidacion(1, 1, null));
        }

        [Fact]
        public void La_lectura_se_pide_una_sola_vez_aunque_se_consulte_muchas_y_un_lector_que_devuelve_nulo_es_un_error_real()
        {
            var lector = new Lector(Valida(1));
            var sobre = new SobreEnValidacion(1, 1, lector.Leer);
            Assert.False(sobre.PlantillaLeida);

            Assert.Same(sobre.Lectura, sobre.Lectura);
            Assert.Equal(1, lector.Llamadas);
            Assert.True(sobre.PlantillaLeida);
            Assert.Equal(1, sobre.CantidadAdjuntos);
            Assert.Equal(1, sobre.CantidadExcel);

            Assert.Throws<InvalidOperationException>(() => new SobreEnValidacion(1, 1, () => null).Lectura);
        }

        [Fact]
        public void Una_excepcion_real_del_lector_se_propaga_no_se_convierte_en_regla_fallida()
        {
            // diseno/03 §1 "Errores": lo esperable (Excel corrupto) ya lo convierte el lector en resultado inválido; lo demás revienta.
            var sobre = new SobreEnValidacion(1, 1, () => throw new TimeoutException("Dataverse no respondió"));
            Assert.Throws<TimeoutException>(() => Correr(sobre));
        }
    }
}
