// PRUEBAS DE ACEPTACIÓN de la pieza 7.2 (Plantilla), parte 1: interpretación de celdas y fronteras LP-01, LP-02, LP-03, LP-06 y LP-07.
// Vienen del spike C-05 (spikes/c05-parseo-excel), que las hizo pasar contra el Open XML SDK real. Se quitaron las cuatro que
// probaban reglas que el aprobador derogó (recorrido completo, topes de filas y de celdas): las reglas vigentes LP-04, LP-05 y LP-08
// están en LectorVentanaYOrdenAceptacion.cs. EL CONSTRUCTOR NO MODIFICA ESTE ARCHIVO.
using System;
using System.IO;
using System.Linq;
using Sanic.Mppp.Plugins.Plantilla;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    public class LectorOpenXmlAceptacion
    {
        private static ConfiguracionPlantilla ConfigSimple(int filaEncabezado = 5, int primeraFila = 6, int cantidadFilas = 3)
        {
            return new ConfiguracionPlantilla
            {
                Hoja = "Datos",
                FilaEncabezado = filaEncabezado,
                PrimeraFila = primeraFila,
                CantidadFilas = cantidadFilas,
                Campos = new System.Collections.Generic.List<CampoPlantilla>
                {
                    new CampoPlantilla { Columna = "C", EncabezadoEsperado = "Campo Uno" },
                    new CampoPlantilla { Columna = "D", EncabezadoEsperado = "Campo Dos" },
                }
            };
        }

        [Fact]
        public void Respeta_la_configuracion_de_hoja_fila_y_columnas_sin_posiciones_fijas()
        {
            // Encabezados fuera de la fila 12 "clasica" de la plantilla real, a proposito.
            var config = ConfigSimple(filaEncabezado: 5, primeraFila: 6, cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno")
                .ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "valor-c")
                .ConTexto("D6", "valor-d")
                .Bytes();

            var lector = new LectorOpenXml();
            var resultado = lector.Leer(xlsx, config);

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            var fila = Assert.Single(resultado.Filas);
            Assert.Equal(6, fila.NumeroFilaExcel);
            Assert.Equal("valor-c", fila.Valores["C"]);
            Assert.Equal("valor-d", fila.Valores["D"]);
        }

        [Fact]
        public void Devuelve_filas_con_numero_de_excel_y_numero_de_orden_y_omite_filas_totalmente_vacias()
        {
            var config = ConfigSimple(filaEncabezado: 5, primeraFila: 6, cantidadFilas: 3);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "fila-1").ConTexto("D6", "d1")
                // fila 7 totalmente vacia: ninguna celda C7/D7
                .ConTexto("C8", "fila-3").ConTexto("D8", "d3")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.True(resultado.EsValido);
            Assert.Equal(2, resultado.Filas.Count);
            Assert.Equal(6, resultado.Filas[0].NumeroFilaExcel);
            Assert.Equal(1, resultado.Filas[0].NumeroOrden);
            Assert.Equal(8, resultado.Filas[1].NumeroFilaExcel);
            Assert.Equal(2, resultado.Filas[1].NumeroOrden);
        }

        [Fact]
        public void Lee_texto_compartido_shared_strings()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "texto compartido").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal("texto compartido", resultado.Filas[0].Valores["C"]);
        }

        [Fact]
        public void Lee_texto_en_linea_inline_string()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTextoEnLinea("C6", "texto en linea").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal("texto en linea", resultado.Filas[0].Valores["C"]);
        }

        [Theory]
        [InlineData("12", "12")]
        [InlineData("12.0", "12")]
        [InlineData("1.6E+16", "16000000000000000")]
        // 16 digitos significativos NO triviales (no solo ceros de relleno): un lector basado
        // en double redondea esto distinto a como lo hace decimal (double solo garantiza
        // ~15-17 digitos, y a esta magnitud la separacion entre valores representables ya es
        // mayor a 1). Ver CONCLUSIONES.md para la comprobacion por mutacion.
        [InlineData("9.876543210123457E+15", "9876543210123457")]
        [InlineData("9876543210123457", "9876543210123457")]
        public void Lee_numeros_sin_notacion_cientifica_ni_decimales_espurios(string crudo, string esperado)
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConNumero("C6", crudo).ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal(esperado, resultado.Filas[0].Valores["C"]);
        }

        [Fact]
        public void Lee_celda_con_formula_usando_el_valor_en_cache()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConFormulaTexto("C6", "UPPER(\"atlantida\")", "ATLANTIDA").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal("ATLANTIDA", resultado.Filas[0].Valores["C"]);
        }

        [Fact]
        public void Lee_celda_vacia_en_medio_de_una_fila_como_texto_vacio()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "solo c") // D6 no existe
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Single(resultado.Filas);
            Assert.Equal("solo c", resultado.Filas[0].Valores["C"]);
            Assert.Equal(string.Empty, resultado.Filas[0].Valores["D"]);
        }

        [Fact]
        public void Recorta_espacios_al_inicio_y_al_final()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "  con espacios  ").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal("con espacios", resultado.Filas[0].Valores["C"]);
        }

        [Fact]
        public void Conserva_ceros_a_la_izquierda_en_celdas_de_texto()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "0045").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.Equal("0045", resultado.Filas[0].Valores["C"]);
        }

        [Fact]
        public void Estructura_invalida_informa_columna_y_celda_del_encabezado_sin_lanzar_excepcion()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno Distinto").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "x").ConTexto("D6", "y")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("C5") && e.Contains("Campo Uno") && e.Contains("Campo Uno Distinto"));
            Assert.Empty(resultado.Filas);
        }

        [Fact]
        public void Archivo_que_no_es_xlsx_devuelve_error_sin_lanzar_excepcion()
        {
            byte[] archivoBasura = System.Text.Encoding.UTF8.GetBytes("esto no es un excel, es texto plano");

            var resultado = new LectorOpenXml().Leer(archivoBasura, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.NotEmpty(resultado.Errores);
        }

        [Fact]
        public void Xlsx_corrupto_devuelve_error_sin_lanzar_excepcion()
        {
            byte[] xlsxValido = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .Bytes();
            // Trunca el zip a la mitad: corrompe el paquete sin dejar de "parecer" binario.
            byte[] corrupto = xlsxValido.Take(xlsxValido.Length / 2).ToArray();

            var resultado = new LectorOpenXml().Leer(corrupto, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.NotEmpty(resultado.Errores);
        }

        [Fact]
        public void Hoja_inexistente_devuelve_error_sin_lanzar_excepcion()
        {
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .Bytes();
            var config = ConfigSimple();
            config.Hoja = "HojaQueNoExiste";

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("HojaQueNoExiste"));
        }

        [Fact]
        public void La_entrada_por_stream_y_por_byte_array_devuelven_el_mismo_resultado()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "valor").ConTexto("D6", "otro")
                .Bytes();

            var porBytes = new LectorOpenXml().Leer(xlsx, config);
            ResultadoLecturaPlantilla porStream;
            using (var stream = new MemoryStream(xlsx))
                porStream = new LectorOpenXml().Leer(stream, config);

            Assert.Equal(porBytes.EsValido, porStream.EsValido);
            Assert.Equal(porBytes.Filas[0].Valores["C"], porStream.Filas[0].Valores["C"]);
        }

        [Fact]
        public void La_plantilla_real_pasa_la_validacion_de_estructura_con_sus_encabezados_reales()
        {
            byte[] xlsx = File.ReadAllBytes(Path.Combine(AppContext.BaseDirectory, "Fixtures", "plantilla-real.xlsx"));

            var config = new ConfiguracionPlantilla
            {
                Hoja = "Datos",
                FilaEncabezado = 12,
                PrimeraFila = 13,
                CantidadFilas = 25,
                Campos = new System.Collections.Generic.List<CampoPlantilla>
                {
                    new CampoPlantilla { Columna = "B", EncabezadoEsperado = "Gestión" },
                    new CampoPlantilla { Columna = "C", EncabezadoEsperado = "Clasificación" },
                    // El encabezado real trae un espacio final ("No. Plan "): se recorta al comparar.
                    new CampoPlantilla { Columna = "D", EncabezadoEsperado = "No. Plan" },
                    new CampoPlantilla { Columna = "E", EncabezadoEsperado = "Nombre Colaborador / Proveedor" },
                    new CampoPlantilla { Columna = "F", EncabezadoEsperado = "Tipo ID" },
                    new CampoPlantilla { Columna = "G", EncabezadoEsperado = "No. Identificación" },
                    new CampoPlantilla { Columna = "H", EncabezadoEsperado = "Referencia" },
                    new CampoPlantilla { Columna = "I", EncabezadoEsperado = "No. Cuenta" },
                    new CampoPlantilla { Columna = "J", EncabezadoEsperado = "Moneda" },
                    new CampoPlantilla { Columna = "K", EncabezadoEsperado = "Banco" },
                }
            };

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            // La plantilla distribuible esta en blanco: sin filas cargadas todavia.
            Assert.Empty(resultado.Filas);
        }

        // --- Hallazgos del revisor sobre la primera entrega ---

        [Fact]
        public void Indice_de_texto_compartido_no_numerico_devuelve_error_sin_lanzar_excepcion()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConIndiceCompartidoCrudo("C6", "abc").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("C6"));
        }

        [Fact]
        public void Indice_de_texto_compartido_negativo_devuelve_error_sin_lanzar_excepcion()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConIndiceCompartidoCrudo("C6", "-1").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("C6"));
        }

        [Fact]
        public void Indice_de_texto_compartido_fuera_de_rango_devuelve_error_sin_lanzar_excepcion()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConIndiceCompartidoCrudo("C6", "9999").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("C6"));
        }

        [Fact]
        public void Indice_de_texto_compartido_vacio_devuelve_error_sin_lanzar_excepcion()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConIndiceCompartidoCrudo("C6", null).ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("C6"));
        }

        [Fact]
        public void Celda_con_valor_de_error_de_excel_se_devuelve_tal_cual_y_queda_marcada_como_advertencia()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConError("C6", "#REF!").ConTexto("D6", "x")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            Assert.Equal("#REF!", resultado.Filas[0].Valores["C"]);
            Assert.Contains(resultado.Advertencias, a => a.NumeroFilaExcel == 6 && a.Columna == "C" && a.Motivo.Contains("#REF!"));
        }

        [Fact]
        public void Archivo_que_supera_el_tope_de_tamano_configurado_devuelve_error_sin_lanzar_excepcion()
        {
            byte[] xlsxValido = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .Bytes();

            var lector = new LectorOpenXml(new LimitesLectura { TamanoMaximoBytesEntrada = 10 });
            var resultado = lector.Leer(xlsxValido, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("bytes"));
        }

        [Fact]
        public void Nombre_de_hoja_no_distingue_mayusculas()
        {
            var config = ConfigSimple(cantidadFilas: 1);
            config.Hoja = "Datos";
            byte[] xlsx = new ConstructorXlsxDePrueba("DATOS")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "valor").ConTexto("D6", "otro")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            Assert.Single(resultado.Filas);
        }

        // --- Segundo rechazo del revisor: LP-01 a LP-08 (03-contratos-custom-api.md #7) ---


        [Fact]
        public void LP06_infiere_posicion_de_filas_y_celdas_sin_atributo_r()
        {
            // Hallazgo B: ninguna fila ni celda trae "r". Primera fila = 1, primera columna = A;
            // de ahi, cada una es la anterior + 1. La config apunta exactamente a donde deberian
            // caer con esa inferencia: encabezado en fila 1 (columnas A y B), datos en fila 2.
            var config = new ConfiguracionPlantilla
            {
                Hoja = "Datos",
                FilaEncabezado = 1,
                PrimeraFila = 2,
                CantidadFilas = 1,
                Campos = new System.Collections.Generic.List<CampoPlantilla>
                {
                    new CampoPlantilla { Columna = "A", EncabezadoEsperado = "Campo Uno" },
                    new CampoPlantilla { Columna = "B", EncabezadoEsperado = "Campo Dos" },
                }
            };
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConFilaSinR("Campo Uno", "Campo Dos")
                .ConFilaSinR("valor-a", "valor-b")
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, config);

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            Assert.Single(resultado.Filas);
            Assert.Equal(2, resultado.Filas[0].NumeroFilaExcel);
            Assert.Equal("valor-a", resultado.Filas[0].Valores["A"]);
            Assert.Equal("valor-b", resultado.Filas[0].Valores["B"]);
        }

        [Fact]
        public void LP03_rechaza_archivo_cuyo_tamano_descomprimido_declarado_supera_el_tope_chico_inyectado()
        {
            // Hallazgo C (bytes descomprimidos). Tope deliberadamente diminuto (500 bytes): CUALQUIER
            // .xlsx minimo valido ya supera eso por el overhead propio del formato OOXML
            // ([Content_Types].xml, _rels, workbook.xml...). No hace falta un archivo gigante.
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .Bytes();

            var lector = new LectorOpenXml(new LimitesLectura { TamanoMaximoBytesDescomprimidos = 500 });
            var resultado = lector.Leer(xlsx, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("descomprimid"));
        }



        [Fact]
        public void LP01_hoja_con_relacion_inexistente_devuelve_error_sin_lanzar_excepcion()
        {
            // Hallazgo D: workbook.xml declara r:id="rId999" (ConIdDeHojaInvalido) que no existe
            // en workbook.xml.rels. GetPartById tira ArgumentOutOfRangeException: el catch
            // general de LP-01 la convierte en resultado de error, no en excepcion sin atrapar.
            byte[] xlsx = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConIdDeHojaInvalido()
                .Bytes();

            var resultado = new LectorOpenXml().Leer(xlsx, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.NotEmpty(resultado.Errores);
        }

        [Fact]
        public void LP02_tope_de_bytes_de_entrada_aplica_con_stream_no_seekable_cuyo_length_falla()
        {
            // Hallazgo E: un chequeo por Stream.Length/CanSeek se saltea entero con esto.
            byte[] xlsxValido = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .Bytes();
            var stream = new StreamNoConfiable(xlsxValido);

            var lector = new LectorOpenXml(new LimitesLectura { TamanoMaximoBytesEntrada = 10 });
            var resultado = lector.Leer(stream, ConfigSimple());

            Assert.False(resultado.EsValido);
            Assert.Contains(resultado.Errores, e => e.Contains("bytes"));
        }

        [Fact]
        public void LP02_stream_no_seekable_por_debajo_del_tope_se_lee_normalmente()
        {
            byte[] xlsxValido = new ConstructorXlsxDePrueba("Datos")
                .ConTexto("C5", "Campo Uno").ConTexto("D5", "Campo Dos")
                .ConTexto("C6", "valor").ConTexto("D6", "otro")
                .Bytes();
            var stream = new StreamNoConfiable(xlsxValido);

            var resultado = new LectorOpenXml().Leer(stream, ConfigSimple());

            Assert.True(resultado.EsValido, string.Join(" | ", resultado.Errores));
            Assert.Single(resultado.Filas);
        }
    }
}
