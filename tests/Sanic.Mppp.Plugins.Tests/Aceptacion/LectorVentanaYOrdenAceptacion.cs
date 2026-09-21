// PRUEBAS DE ACEPTACIÓN de la pieza 7.2 (Plantilla), parte 2: las reglas que el aprobador corrigió DESPUÉS del spike
// (diseno/03-contratos-custom-api.md §7): LP-04 (solo se lee la ventana configurada y se deja de leer al pasarla),
// LP-05 (el orden se exige: filas y celdas estrictamente ascendentes, o el archivo es inválido) y LP-08 (todo lo que gobierna
// la lectura es parámetro, leído de JSON). EL CONSTRUCTOR NO MODIFICA ESTE ARCHIVO.
using System;
using System.Collections.Generic;
using System.Linq;
using Sanic.Mppp.Plugins.Plantilla;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Xunit;
using static Sanic.Mppp.Plugins.Tests.Apoyo.XlsxCrudo;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    public class LectorVentanaYOrdenAceptacion
    {
        private const string Hoja = "Plantilla";

        /// <summary>Encabezado en la fila 5; datos en las filas 6, 7 y 8; campos en C y D.</summary>
        private static ConfiguracionPlantilla Ventana(int filaEncabezado = 5, int primeraFila = 6, int cantidadFilas = 3)
        {
            return new ConfiguracionPlantilla
            {
                Hoja = Hoja, FilaEncabezado = filaEncabezado, PrimeraFila = primeraFila, CantidadFilas = cantidadFilas,
                Campos = new List<CampoPlantilla>
                {
                    new CampoPlantilla { Nombre = "uno", Columna = "C", EncabezadoEsperado = "Campo Uno" },
                    new CampoPlantilla { Nombre = "dos", Columna = "D", EncabezadoEsperado = "Campo Dos" },
                },
            };
        }

        private static string Encabezado(int fila = 5) => Fila(fila, Celda($"C{fila}", "Campo Uno"), Celda($"D{fila}", "Campo Dos"));

        private static string Datos(int fila) => Fila(fila, Celda($"C{fila}", $"c{fila}"), Celda($"D{fila}", $"d{fila}"));

        private static ResultadoLecturaPlantilla Leer(ConfiguracionPlantilla config, params string[] filas)
        {
            return new LectorOpenXml().Leer(ConFilas(Hoja, filas), config);
        }

        private static void Invalido(ResultadoLecturaPlantilla r, string fragmento)
        {
            Assert.False(r.EsValido);
            Assert.Empty(r.Filas);
            Assert.Contains(r.Errores, e => e.IndexOf(fragmento, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        // ------------------------------------------------------------------ LP-04: solo la ventana
        [Fact]
        public void El_archivo_crudo_de_base_se_lee_bien()
        {
            var r = Leer(Ventana(), Encabezado(), Datos(6), Datos(7), Datos(8));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal(new[] { 6, 7, 8 }, r.Filas.Select(f => f.NumeroFilaExcel));
            Assert.Equal(new[] { 1, 2, 3 }, r.Filas.Select(f => f.NumeroOrden));
            Assert.Equal("c7", r.Filas[1].Valores["C"]);
            Assert.Equal("d7", r.Filas[1].Valores["D"]);
            Assert.Empty(r.Advertencias);
        }

        [Fact]
        public void LP04_lo_que_esta_despues_de_la_ventana_no_se_mira_aunque_este_danado_o_desordenado()
        {
            // La fila 9 es la primera más allá de la ventana: ahí se deja de leer. Ni su celda dañada ni la fila 7 repetida después se ven.
            var r = Leer(Ventana(), Encabezado(), Datos(6), Datos(7), Datos(8), Fila(9, CeldaDanada("C9")), Datos(7), Fila(3, CeldaDanada("C3")));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal(3, r.Filas.Count);
            Assert.Empty(r.Advertencias);
        }

        [Fact]
        public void LP04_dentro_de_una_fila_no_se_mira_nada_mas_alla_de_la_ultima_columna_configurada()
        {
            var r = Leer(Ventana(), Encabezado(), Fila(6, Celda("C6", "c6"), Celda("D6", "d6"), CeldaDanada("E6"), Celda("B6", "desordenada pero fuera de la ventana")));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal("d6", r.Filas.Single().Valores["D"]);
            Assert.Equal(new[] { "C", "D" }, r.Filas.Single().Valores.Keys.OrderBy(k => k, StringComparer.Ordinal));
        }

        [Fact]
        public void LP04_las_filas_que_no_son_el_encabezado_ni_la_ventana_no_se_interpretan()
        {
            // Filas 1 a 4 (antes del encabezado) y 6 a 7 (entre el encabezado y la primera fila de datos): celdas dañadas que nadie mira.
            var r = Leer(Ventana(filaEncabezado: 5, primeraFila: 8, cantidadFilas: 2),
                         Fila(2, CeldaDanada("C2")), Encabezado(), Fila(6, CeldaDanada("C6")), Fila(7, CeldaDanada("D7")), Datos(8), Datos(9));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal(new[] { 8, 9 }, r.Filas.Select(f => f.NumeroFilaExcel));
            Assert.Equal(new[] { 1, 2 }, r.Filas.Select(f => f.NumeroOrden));
        }

        [Fact]
        public void LP04_una_celda_danada_DENTRO_de_la_ventana_si_invalida_el_archivo()
        {
            Invalido(Leer(Ventana(), Encabezado(), Datos(6), Fila(7, Celda("C7", "c7"), CeldaDanada("D7"))), "D7");
        }

        [Fact]
        public void Una_ventana_sin_ninguna_fila_con_datos_es_valida_y_viene_vacia()
        {
            var r = Leer(Ventana(), Encabezado());
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Empty(r.Filas);
        }

        [Fact]
        public void El_numero_de_orden_es_la_posicion_en_la_ventana_aunque_haya_filas_vacias_en_el_medio()
        {
            var r = Leer(Ventana(), Encabezado(), Datos(6), Datos(8));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal(new[] { 6, 8 }, r.Filas.Select(f => f.NumeroFilaExcel));
            Assert.Equal(new[] { 1, 3 }, r.Filas.Select(f => f.NumeroOrden));
        }

        [Fact]
        public void Si_falta_la_fila_de_encabezado_el_archivo_es_invalido()
        {
            Invalido(Leer(Ventana(), Datos(6), Datos(7)), "encabezado");
        }

        // ------------------------------------------------------------------ LP-05: el orden se exige
        [Fact]
        public void LP05_una_fila_fuera_de_orden_antes_de_terminar_la_ventana_invalida_el_archivo()
        {
            // El caso que encontró el revisor del spike: una fila 500 escrita antes que la 6 hacía que la 6 se perdiera en silencio.
            Invalido(Leer(Ventana(), Encabezado(), Fila(500, Celda("C500", "x")), Datos(6)), "orden");
        }

        [Fact]
        public void LP05_una_fila_repetida_invalida_el_archivo()
        {
            Invalido(Leer(Ventana(), Encabezado(), Datos(6), Datos(6), Datos(7)), "orden");
        }

        [Fact]
        public void LP05_el_desorden_antes_del_encabezado_tambien_invalida_el_archivo()
        {
            Invalido(Leer(Ventana(), Fila(3, Celda("A3", "x")), Fila(2, Celda("A2", "x")), Encabezado(), Datos(6)), "orden");
        }

        [Fact]
        public void LP05_celdas_fuera_de_orden_dentro_de_una_fila_de_la_ventana_invalidan_el_archivo()
        {
            Invalido(Leer(Ventana(), Encabezado(), Fila(6, Celda("D6", "d6"), Celda("C6", "c6"))), "orden");
        }

        [Fact]
        public void LP05_una_celda_repetida_dentro_de_una_fila_de_la_ventana_invalida_el_archivo()
        {
            Invalido(Leer(Ventana(), Encabezado(), Fila(6, Celda("C6", "uno"), Celda("C6", "otro"), Celda("D6", "d6"))), "orden");
        }

        [Fact]
        public void LP05_celdas_fuera_de_orden_en_la_fila_de_encabezado_invalidan_el_archivo()
        {
            Invalido(Leer(Ventana(), Fila(5, Celda("D5", "Campo Dos"), Celda("C5", "Campo Uno")), Datos(6)), "orden");
        }

        // ------------------------------------------------------------------ errores de programación, no del archivo
        [Fact]
        public void Una_configuracion_o_un_archivo_nulos_son_un_error_de_programacion_no_un_archivo_invalido()
        {
            // LP-01: un bug nuestro no se disfraza de archivo corrupto.
            var xlsx = ConFilas(Hoja, Encabezado());
            Assert.Throws<ArgumentNullException>(() => new LectorOpenXml().Leer(xlsx, null));
            Assert.Throws<ArgumentNullException>(() => new LectorOpenXml().Leer((byte[])null, Ventana()));
            Assert.Throws<ArgumentNullException>(() => new LectorOpenXml().Leer((System.IO.Stream)null, Ventana()));
            Assert.Throws<ArgumentNullException>(() => new LectorOpenXml(null));
        }

        // ------------------------------------------------------------------ LP-08: todo es parámetro, y viene en JSON
        private const string JsonValido =
            "{\"hoja\":\"Plantilla\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,"
            + "\"campos\":[{\"nombre\":\"numeroPlan\",\"columna\":\"d\",\"encabezado\":\"No. Plan\"},{\"nombre\":\"cuenta\",\"columna\":\"AA\",\"encabezado\":\"No. Cuenta\"}]}";

        [Fact]
        public void LP08_la_estructura_se_lee_de_json_y_la_columna_queda_en_mayuscula()
        {
            var c = ConfiguracionPlantilla.DesdeJson(JsonValido);
            Assert.Equal("Plantilla", c.Hoja);
            Assert.Equal((11, 12, 100), (c.FilaEncabezado, c.PrimeraFila, c.CantidadFilas));
            Assert.Equal(new[] { "numeroPlan|D|No. Plan", "cuenta|AA|No. Cuenta" }, c.Campos.Select(x => $"{x.Nombre}|{x.Columna}|{x.EncabezadoEsperado}"));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("esto no es json")]
        [InlineData("[]")]
        [InlineData("{\"hoja\":\"\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":0,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":11,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":0,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"1A\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"\",\"encabezado\":\"x\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\" \"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"},{\"nombre\":\"b\",\"columna\":\"d\",\"encabezado\":\"y\"}]}")]
        [InlineData("{\"hoja\":\"P\",\"filaEncabezado\":11,\"primeraFila\":12,\"cantidadFilas\":100,\"campos\":[{\"nombre\":\"a\",\"columna\":\"D\",\"encabezado\":\"x\"},{\"nombre\":\"a\",\"columna\":\"E\",\"encabezado\":\"y\"}]}")]
        public void LP08_un_parametro_de_estructura_mal_cargado_es_un_error_con_motivo_nunca_una_lectura_vacia(string json)
        {
            var ex = Assert.Throws<FormatException>(() => ConfiguracionPlantilla.DesdeJson(json));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        [Fact]
        public void LP08_los_limites_por_defecto_son_los_iniciales_del_diseno()
        {
            var porDefecto = new LimitesLectura();
            Assert.Equal((2L * 1024 * 1024, 20L * 1024 * 1024), (porDefecto.TamanoMaximoBytesEntrada, porDefecto.TamanoMaximoBytesDescomprimidos));
            foreach (var vacio in new[] { null, "", "  ", "{}" })
            {
                var l = LimitesLectura.DesdeJson(vacio);
                Assert.Equal((porDefecto.TamanoMaximoBytesEntrada, porDefecto.TamanoMaximoBytesDescomprimidos), (l.TamanoMaximoBytesEntrada, l.TamanoMaximoBytesDescomprimidos));
            }
        }

        [Fact]
        public void LP08_los_limites_se_leen_de_json_y_una_clave_que_falta_toma_su_valor_por_defecto()
        {
            var l = LimitesLectura.DesdeJson("{\"maximoBytesComprimido\":1000,\"maximoBytesDescomprimido\":5000}");
            Assert.Equal((1000L, 5000L), (l.TamanoMaximoBytesEntrada, l.TamanoMaximoBytesDescomprimidos));
            var parcial = LimitesLectura.DesdeJson("{\"maximoBytesDescomprimido\":5000}");
            Assert.Equal((2L * 1024 * 1024, 5000L), (parcial.TamanoMaximoBytesEntrada, parcial.TamanoMaximoBytesDescomprimidos));
        }

        [Theory]
        [InlineData("no es json")]
        [InlineData("{\"maximoBytesComprimido\":0}")]
        [InlineData("{\"maximoBytesComprimido\":-5}")]
        [InlineData("{\"maximoBytesDescomprimido\":\"mucho\"}")]
        public void LP08_unos_limites_mal_cargados_son_un_error_con_motivo(string json)
        {
            Assert.Throws<FormatException>(() => LimitesLectura.DesdeJson(json));
        }

        [Fact]
        public void LP08_la_configuracion_leida_de_json_gobierna_de_verdad_la_lectura()
        {
            var json = "{\"hoja\":\"Plantilla\",\"filaEncabezado\":5,\"primeraFila\":6,\"cantidadFilas\":2,"
                     + "\"campos\":[{\"nombre\":\"uno\",\"columna\":\"c\",\"encabezado\":\"Campo Uno\"},{\"nombre\":\"dos\",\"columna\":\"D\",\"encabezado\":\"Campo Dos\"}]}";
            var r = Leer(ConfiguracionPlantilla.DesdeJson(json), Encabezado(), Datos(6), Datos(7), Datos(8));
            Assert.True(r.EsValido, string.Join(" | ", r.Errores));
            Assert.Equal(new[] { 6, 7 }, r.Filas.Select(f => f.NumeroFilaExcel));
        }
    }
}
