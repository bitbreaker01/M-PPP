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
    /// D-18 (aprobador, 2026-09-21): las tres formas de los parámetros de la plantilla. Un parámetro lo carga una persona:
    /// si está mal cargado tiene que REVENTAR con el motivo, nunca aflojar la validación en silencio.
    /// </summary>
    public class ParametrosDePlantillaAceptacion
    {
        // ------------------------------------------------------------------ los campos
        [Fact]
        public void Los_campos_de_la_fila_son_diez_y_cinco_son_de_lista()
        {
            Assert.Equal(
                new[] { "gestion", "clasificacion", "tipoIdentificacion", "moneda", "banco", "numeroPlan", "nombreBeneficiario", "numeroIdentificacion", "numeroCuenta", "referencia" },
                CamposDeFila.Todos());
            Assert.Equal(new[] { "gestion", "clasificacion", "tipoIdentificacion", "moneda", "banco" }, CamposDeFila.DeLista());
            Assert.NotSame(CamposDeFila.Todos(), CamposDeFila.Todos());
        }

        // ------------------------------------------------------------------ plantilla.listas
        internal const string ListasValidas = @"{
            ""gestion"":[{""valor"":""Inclusion"",""variantes"":[""inclusión"",""alta""]},{""valor"":""Exclusion"",""variantes"":[""baja""]},{""valor"":""Modificacion""}],
            ""clasificacion"":[{""valor"":""BAC""},{""valor"":""ACH""},{""valor"":""CK"",""variantes"":[""cheque""]}],
            ""tipoIdentificacion"":[{""valor"":""CNA"",""variantes"":[""Cédula nacional""]},{""valor"":""RUC""},{""valor"":""PAS"",""variantes"":[""pasaporte""]}],
            ""moneda"":[{""valor"":""COR"",""variantes"":[""córdobas"",""C$""]},{""valor"":""USD"",""variantes"":[""dólares"",""US$""]}],
            ""banco"":[{""valor"":""BAC"",""codigo"":""102"",""variantes"":[""bac credomatic""]},{""valor"":""LAFISE"",""codigo"":""104""},{""valor"":""BANPRO"",""codigo"":""103""}]
        }";

        [Theory]
        [InlineData("gestion", "Inclusion", "Inclusion")]
        [InlineData("gestion", "  inclusión  ", "Inclusion")] // mayúsculas, tildes y espacios a los lados no cuentan
        [InlineData("gestion", "INCLUSIÓN", "Inclusion")]
        [InlineData("gestion", "Alta", "Inclusion")] // variante explícita
        [InlineData("gestion", "modificación", "Modificacion")] // el propio valor, con tilde
        [InlineData("tipoIdentificacion", "cedula   NACIONAL", "CNA")] // varios espacios internos cuentan como uno
        [InlineData("moneda", "c$", "COR")]
        [InlineData("moneda", "Dolares", "USD")]
        [InlineData("clasificacion", "ach", "ACH")]
        public void Un_valor_se_reconoce_sin_mirar_mayusculas_tildes_ni_espacios_y_por_sus_variantes_explicitas(string lista, string recibido, string esperado)
        {
            var valor = ListasPlantilla.DesdeJson(ListasValidas).Resolver(lista, recibido);
            Assert.NotNull(valor);
            Assert.Equal(esperado, valor.Valor);
            Assert.Null(valor.CodigoDeBanco);
        }

        [Theory]
        [InlineData("gestion", "Inclusiones")] // nada de parecidos
        [InlineData("gestion", "Inclu sion")]
        [InlineData("gestion", "ACH")] // es de otra lista
        [InlineData("moneda", "EUR")] // no está en el parámetro, aunque exista en el mundo
        [InlineData("clasificacion", "cheque.")]
        [InlineData("gestion", null)]
        [InlineData("gestion", "")]
        [InlineData("gestion", "   ")]
        public void Lo_que_no_esta_en_la_lista_no_se_adivina(string lista, string recibido)
        {
            Assert.Null(ListasPlantilla.DesdeJson(ListasValidas).Resolver(lista, recibido));
        }

        [Fact]
        public void Cada_banco_trae_su_codigo_de_tres_digitos()
        {
            var listas = ListasPlantilla.DesdeJson(ListasValidas);
            Assert.Equal("102", listas.Resolver("banco", "Bac Credomatic").CodigoDeBanco);
            Assert.Equal("BAC", listas.Resolver("banco", "bac").Valor);
            Assert.Equal("104", listas.Resolver("banco", "LAFISE").CodigoDeBanco);
            // "BAC" es banco y es clasificación: cada lista resuelve lo suyo.
            Assert.Null(listas.Resolver("clasificacion", "BAC").CodigoDeBanco);
        }

        [Fact]
        public void Pedir_una_lista_que_no_existe_es_un_error_de_programacion()
        {
            var listas = ListasPlantilla.DesdeJson(ListasValidas);
            Assert.Throws<ArgumentException>(() => listas.Resolver("numeroPlan", "x"));
            Assert.Throws<ArgumentException>(() => listas.Resolver("Gestion", "x")); // los nombres de lista son exactos
            Assert.Throws<ArgumentException>(() => listas.Resolver(null, "x"));
        }

        [Theory]
        [InlineData(null, "")]
        [InlineData("  ÁRBOL   ñandú \t C$ ", "arbol nandu c$")]
        [InlineData("İstanbul", "istanbul")] // minúsculas invariantes: no dependen de la cultura del servidor
        public void Normalizar_es_una_sola_funcion_y_no_depende_de_la_cultura(string texto, string esperado)
        {
            Assert.Equal(esperado, ListasPlantilla.Normalizar(texto));
        }

        public static IEnumerable<object[]> ListasMalCargadas()
        {
            string Con(string lista, string contenido) => ListasValidas.Replace(ExtraerLista(lista), $"\"{lista}\":{contenido}");
            yield return new object[] { "nulo", null };
            yield return new object[] { "en blanco", "  " };
            yield return new object[] { "no es JSON", "{gestion:" };
            yield return new object[] { "es un arreglo", "[]" };
            yield return new object[] { "falta una lista", ListasValidas.Replace(ExtraerLista("moneda") + ",", string.Empty) };
            yield return new object[] { "lista vacía", Con("moneda", "[]") };
            yield return new object[] { "lista nula", Con("moneda", "null") };
            yield return new object[] { "valor que no es del choice", Con("moneda", @"[{""valor"":""EUR""}]") };
            yield return new object[] { "valor con otra mayúscula que el enum", Con("moneda", @"[{""valor"":""usd""}]") };
            yield return new object[] { "valor que es un número del enum", Con("moneda", @"[{""valor"":""159460001""}]") };
            yield return new object[] { "valor en blanco", Con("moneda", @"[{""valor"":"" ""}]") };
            yield return new object[] { "elemento nulo", Con("moneda", @"[null]") };
            yield return new object[] { "valor repetido", Con("moneda", @"[{""valor"":""USD""},{""valor"":""USD""}]") };
            yield return new object[] { "variante ambigua entre dos valores", Con("moneda", @"[{""valor"":""COR"",""variantes"":[""pesos""]},{""valor"":""USD"",""variantes"":["" PESOS ""]}]") };
            yield return new object[] { "variante que pisa el valor de otro", Con("moneda", @"[{""valor"":""COR"",""variantes"":[""usd""]},{""valor"":""USD""}]") };
            yield return new object[] { "variante en blanco", Con("moneda", @"[{""valor"":""COR"",""variantes"":["" ""]}]") };
            yield return new object[] { "variante nula", Con("moneda", @"[{""valor"":""COR"",""variantes"":[null]}]") };
            yield return new object[] { "banco sin código", Con("banco", @"[{""valor"":""BAC""}]") };
            yield return new object[] { "código de dos dígitos", Con("banco", @"[{""valor"":""BAC"",""codigo"":""12""}]") };
            yield return new object[] { "código de cuatro dígitos", Con("banco", @"[{""valor"":""BAC"",""codigo"":""1020""}]") };
            yield return new object[] { "código con letras", Con("banco", @"[{""valor"":""BAC"",""codigo"":""1O2""}]") };
            yield return new object[] { "código con dígitos que no son ASCII", Con("banco", @"[{""valor"":""BAC"",""codigo"":""１０２""}]") };
            yield return new object[] { "dos bancos con el mismo código", Con("banco", @"[{""valor"":""BAC"",""codigo"":""102""},{""valor"":""LAFISE"",""codigo"":""102""}]") };
        }

        private static string ExtraerLista(string lista)
        {
            var inicio = ListasValidas.IndexOf($"\"{lista}\":[", StringComparison.Ordinal);
            var fin = ListasValidas.IndexOf("}]", inicio, StringComparison.Ordinal) + 2;
            return ListasValidas.Substring(inicio, fin - inicio);
        }

        [Theory]
        [MemberData(nameof(ListasMalCargadas))]
        public void Unas_listas_mal_cargadas_revientan_con_el_motivo_nunca_quedan_vacias_pero_validas(string caso, string json)
        {
            var ex = Assert.Throws<FormatException>(() => ListasPlantilla.DesdeJson(json));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message), caso);
        }

        [Fact]
        public void Una_variante_que_repite_a_su_propio_valor_no_es_ambigua()
        {
            var json = ListasValidas.Replace(@"{""valor"":""RUC""}", @"{""valor"":""RUC"",""variantes"":[""ruc"","" R U C ""]}");
            Assert.Equal("RUC", ListasPlantilla.DesdeJson(json).Resolver("tipoIdentificacion", "r u c").Valor);
        }

        // ------------------------------------------------------------------ plantilla.estructura: largos y formato de cada campo
        private static string Estructura(string campo)
        {
            return @"{""hoja"":""Datos"",""filaEncabezado"":12,""primeraFila"":13,""cantidadFilas"":100,""campos"":[" + campo + "]}";
        }

        [Fact]
        public void La_estructura_trae_por_cada_campo_sus_largos_y_su_formato_y_pueden_faltar()
        {
            var config = ConfiguracionPlantilla.DesdeJson(Estructura(
                @"{""nombre"":""numeroCuenta"",""columna"":""J"",""encabezado"":""Cuenta"",""largoMinimo"":1,""largoMaximo"":16,""formato"":""digitos""},"
                + @"{""nombre"":""numeroPlan"",""columna"":""D"",""encabezado"":""No. Plan"",""largoMaximo"":4,""formato"":""alfanumerico""},"
                + @"{""nombre"":""nombreBeneficiario"",""columna"":""E"",""encabezado"":""Nombre"",""formato"":""texto""},"
                + @"{""nombre"":""gestion"",""columna"":""C"",""encabezado"":""Gestion""}"));

            var cuenta = config.Campos[0];
            Assert.Equal(1, cuenta.LargoMinimo);
            Assert.Equal(16, cuenta.LargoMaximo);
            Assert.Equal(FormatoDeCampo.Digitos, cuenta.Formato);
            Assert.Null(config.Campos[1].LargoMinimo);
            Assert.Equal(4, config.Campos[1].LargoMaximo);
            Assert.Equal(FormatoDeCampo.Alfanumerico, config.Campos[1].Formato);
            Assert.Equal(FormatoDeCampo.Texto, config.Campos[2].Formato);
            Assert.Null(config.Campos[3].LargoMinimo);
            Assert.Null(config.Campos[3].LargoMaximo);
            Assert.Null(config.Campos[3].Formato);
        }

        [Theory]
        [InlineData(@"""formato"":""regex:^[0-9]+$""")] // nada de expresiones regulares en un parámetro
        [InlineData(@"""formato"":""Digitos""")] // la lista es cerrada y exacta
        [InlineData(@"""formato"":""numerico""")]
        [InlineData(@"""formato"":""""")]
        [InlineData(@"""largoMinimo"":-1")]
        [InlineData(@"""largoMaximo"":0")]
        [InlineData(@"""largoMinimo"":5,""largoMaximo"":4")]
        public void Un_largo_o_un_formato_mal_cargado_revienta_con_el_motivo(string propiedad)
        {
            var json = Estructura(@"{""nombre"":""numeroCuenta"",""columna"":""J"",""encabezado"":""Cuenta""," + propiedad + "}");
            var ex = Assert.Throws<FormatException>(() => ConfiguracionPlantilla.DesdeJson(json));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        [Fact]
        public void Un_minimo_igual_al_maximo_es_un_largo_exacto_y_vale()
        {
            var campo = ConfiguracionPlantilla.DesdeJson(Estructura(@"{""nombre"":""x"",""columna"":""J"",""encabezado"":""X"",""largoMinimo"":4,""largoMaximo"":4}")).Campos[0];
            Assert.Equal(4, campo.LargoMinimo);
            Assert.Equal(4, campo.LargoMaximo);
        }

        // ------------------------------------------------------------------ plantilla.obligatoriedad
        internal const string ObligatoriedadInicial = @"{""porDefecto"":""obligatorio"",""opcionales"":[{""campo"":""referencia""}]}";

        internal const string ObligatoriedadConReglas = @"{""porDefecto"":""obligatorio"",""opcionales"":[{""campo"":""referencia""}],""reglas"":[
            {""gestion"":""Exclusion"",""clasificacion"":""*"",""formato"":""*"",""opcionales"":[""moneda"",""banco""]},
            {""gestion"":""Exclusion"",""clasificacion"":""CK"",""formato"":""06"",""opcionales"":[""numeroCuenta"",""banco""]},
            {""gestion"":""*"",""clasificacion"":""BAC"",""formato"":""11"",""opcionales"":[""tipoIdentificacion""]}]}";

        [Fact]
        public void La_version_inicial_es_todo_obligatorio_salvo_referencia_para_cualquier_combinacion()
        {
            var o = ObligatoriedadPlantilla.DesdeJson(ObligatoriedadInicial);
            Assert.Equal(new[] { "referencia" }, o.CamposOpcionales(Gestion.Inclusion, Clasificacion.ACH, TipoDeFormatoDelPlan._11));
            Assert.Equal(new[] { "referencia" }, o.CamposOpcionales(null, null, null));
        }

        [Fact]
        public void Se_suman_los_opcionales_de_todas_las_reglas_que_calzan_y_el_asterisco_calza_con_todo()
        {
            var o = ObligatoriedadPlantilla.DesdeJson(ObligatoriedadConReglas);
            string[] De(Gestion? g, Clasificacion? c, TipoDeFormatoDelPlan? f) => o.CamposOpcionales(g, c, f).OrderBy(x => x, StringComparer.Ordinal).ToArray();

            Assert.Equal(new[] { "referencia" }, De(Gestion.Inclusion, Clasificacion.ACH, TipoDeFormatoDelPlan._10));
            Assert.Equal(new[] { "banco", "moneda", "referencia" }, De(Gestion.Exclusion, Clasificacion.ACH, TipoDeFormatoDelPlan._10));
            Assert.Equal(new[] { "banco", "moneda", "numeroCuenta", "referencia" }, De(Gestion.Exclusion, Clasificacion.CK, TipoDeFormatoDelPlan._06));
            Assert.Equal(new[] { "banco", "moneda", "referencia" }, De(Gestion.Exclusion, Clasificacion.CK, TipoDeFormatoDelPlan._10)); // la regla de CK es solo para formato 06
            Assert.Equal(new[] { "banco", "moneda", "referencia", "tipoIdentificacion" }, De(Gestion.Exclusion, Clasificacion.BAC, TipoDeFormatoDelPlan._11));
        }

        [Fact]
        public void Una_dimension_desconocida_solo_calza_con_asterisco_ante_la_duda_obligatorio()
        {
            var o = ObligatoriedadPlantilla.DesdeJson(ObligatoriedadConReglas);
            // Gestión desconocida: la regla de Exclusion no calza. Clasificación BAC + formato 11 sí: su gestión es "*".
            Assert.Equal(new[] { "referencia", "tipoIdentificacion" }, o.CamposOpcionales(null, Clasificacion.BAC, TipoDeFormatoDelPlan._11).OrderBy(x => x, StringComparer.Ordinal));
            // Exclusion con plan desconocido: calza la primera (formato "*") y NO la de formato 06.
            Assert.Equal(new[] { "banco", "moneda", "referencia" }, o.CamposOpcionales(Gestion.Exclusion, Clasificacion.CK, null).OrderBy(x => x, StringComparer.Ordinal));
        }

        [Fact]
        public void El_conjunto_es_nuevo_en_cada_llamada_nadie_afloja_el_parametro_desde_afuera()
        {
            var o = ObligatoriedadPlantilla.DesdeJson(ObligatoriedadInicial);
            o.CamposOpcionales(null, null, null).Add("numeroCuenta");
            Assert.Equal(new[] { "referencia" }, o.CamposOpcionales(null, null, null));
        }

        [Theory]
        [InlineData(null)]
        [InlineData(" ")]
        [InlineData("{")]
        [InlineData(@"{""opcionales"":[]}")] // falta porDefecto
        [InlineData(@"{""porDefecto"":""opcional""}")] // lo único que existe hoy es "obligatorio"
        [InlineData(@"{""porDefecto"":""Obligatorio""}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""opcionales"":[{""campo"":""cuenta""}]}")] // campo desconocido
        [InlineData(@"{""porDefecto"":""obligatorio"",""opcionales"":[{""campo"":""Referencia""}]}")] // los nombres son exactos
        [InlineData(@"{""porDefecto"":""obligatorio"",""opcionales"":[null]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""Baja"",""clasificacion"":""*"",""formato"":""*"",""opcionales"":[""banco""]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""Cheque"",""formato"":""*"",""opcionales"":[""banco""]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""*"",""formato"":""12"",""opcionales"":[""banco""]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""*"",""formato"":""6"",""opcionales"":[""banco""]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""clasificacion"":""*"",""formato"":""*"",""opcionales"":[""banco""]}]}")] // falta una dimensión: no se asume "*"
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""*"",""formato"":""*"",""opcionales"":[]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""*"",""formato"":""*""}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[{""gestion"":""*"",""clasificacion"":""*"",""formato"":""*"",""opcionales"":[""saldo""]}]}")]
        [InlineData(@"{""porDefecto"":""obligatorio"",""reglas"":[null]}")]
        public void Una_obligatoriedad_mal_cargada_revienta_con_el_motivo(string json)
        {
            var ex = Assert.Throws<FormatException>(() => ObligatoriedadPlantilla.DesdeJson(json));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
        }

        // ------------------------------------------------------------------ citar lo que escribió el cliente
        [Theory]
        [InlineData(null, "")]
        [InlineData("  Dolarez  ", "Dolarez")]
        [InlineData("uno\r\ndos\ttres cuatro cinco", "uno dos tres cuatro cinco")]
        [InlineData("a    b", "a b")]
        [InlineData("1234567890123456789012345678901234567890", "1234567890123456789012345678901234567890")] // 40 justos: entra
        [InlineData("1234567890123456789012345678901234567890X", "1234567890123456789012345678901234567890…")]
        public void Un_valor_del_cliente_se_cita_en_una_linea_sin_caracteres_de_control_y_acotado(string valor, string esperado)
        {
            Assert.Equal(esperado, MensajeAlCliente.Citar(valor));
            Assert.Equal(40, MensajeAlCliente.LargoMaximoDeCita);
        }
    }
}
