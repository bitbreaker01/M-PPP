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
    /// Las ocho reglas semilla de nivel Registro (diseno/03 §1 paso 5), con lo que cerró el aprobador el 2026-09-21: D-14
    /// (autorización), D-17 (referencia de formato 11), D-18 (listas, largos y formato, obligatoriedad) y D-19 (mensajes).
    /// Se prueban POR el motor con el catálogo semilla y también sueltas (el catálogo es editable).
    /// El resultado de las ocho se resume en una palabra, en el orden de la semilla: C cumplida, N no cumplida, O omitida.
    /// </summary>
    public class ReglasDeRegistroAceptacion
    {
        // LISTAS · LARGOS · PLAN · F11_ACH · OBLIG · REF_11 · MONEDA · AUTORIZACION
        private static readonly (string codigo, string[] dependeDe)[] Semilla =
        {
            (ReglasDeRegistro.ListasValidas, new string[0]),
            (ReglasDeRegistro.LargosYFormato, new string[0]),
            (ReglasDeRegistro.PlanExiste, new string[0]),
            (ReglasDeRegistro.Formato11SoloAch, new[] { ReglasDeRegistro.PlanExiste, ReglasDeRegistro.ListasValidas }),
            (ReglasDeRegistro.Obligatoriedad, new[] { ReglasDeRegistro.PlanExiste, ReglasDeRegistro.ListasValidas }),
            (ReglasDeRegistro.ReferenciaFormato11, new[] { ReglasDeRegistro.Formato11SoloAch, ReglasDeRegistro.Obligatoriedad }),
            (ReglasDeRegistro.MonedaDelPlan, new[] { ReglasDeRegistro.PlanExiste, ReglasDeRegistro.ListasValidas }),
            (ReglasDeRegistro.AutorizacionCorreoPlan, new[] { ReglasDeRegistro.PlanExiste }),
        };

        private static readonly Guid Plan42 = Guid.Parse("00000000-0000-0000-0000-000000000042");
        private static readonly Guid Plan06 = Guid.Parse("00000000-0000-0000-0000-000000000006");
        private static readonly Guid PlanA1 = Guid.Parse("00000000-0000-0000-0000-0000000000a1");

        private const string Cuenta = "123456789";
        private const string Identificacion = "0011234567890A";

        private static readonly Dictionary<string, string> Columnas = CamposDeFila.Todos()
            .Select((campo, i) => (campo, columna: ((char)('C' + i)).ToString()))
            .ToDictionary(x => x.campo, x => x.columna);

        private static readonly Dictionary<string, string> Encabezados = new Dictionary<string, string>
        {
            ["gestion"] = "Gestion", ["clasificacion"] = "Clasificacion", ["tipoIdentificacion"] = "Tipo de identificacion", ["moneda"] = "Moneda", ["banco"] = "Banco",
            ["numeroPlan"] = "No. Plan", ["nombreBeneficiario"] = "Nombre del beneficiario", ["numeroIdentificacion"] = "No. Identificacion",
            ["numeroCuenta"] = "No. Cuenta", ["referencia"] = "Referencia",
        };

        private static ConfiguracionPlantilla Estructura(Action<List<CampoPlantilla>> cambio = null)
        {
            var campos = CamposDeFila.Todos().Select(c => new CampoPlantilla { Nombre = c, Columna = Columnas[c], EncabezadoEsperado = Encabezados[c] }).ToList();
            void Limites(string campo, int? min, int? max, FormatoDeCampo? formato)
            {
                var c = campos.Single(x => x.Nombre == campo);
                (c.LargoMinimo, c.LargoMaximo, c.Formato) = (min, max, formato);
            }

            // Largos de la plantilla vigente (diseno/02 §2.5): Nombre ≤44 · Identificación 1–16 · Referencia ≤20 · Cuenta 1–16.
            Limites("numeroPlan", 1, 4, FormatoDeCampo.Alfanumerico);
            Limites("nombreBeneficiario", null, 44, FormatoDeCampo.Texto);
            Limites("numeroIdentificacion", 1, 16, FormatoDeCampo.Alfanumerico);
            Limites("numeroCuenta", 1, 16, FormatoDeCampo.Digitos);
            Limites("referencia", null, 20, null);
            cambio?.Invoke(campos);
            return new ConfiguracionPlantilla { Hoja = "Datos", FilaEncabezado = 12, PrimeraFila = 13, CantidadFilas = 100, Campos = campos };
        }

        private static IList<PlanDelCatalogo> Planes()
        {
            return new List<PlanDelCatalogo>
            {
                new PlanDelCatalogo(Plan42, "0042", TipoDeFormatoDelPlan._11, Moneda.USD),
                new PlanDelCatalogo(Plan06, "0006", TipoDeFormatoDelPlan._06, Moneda.COR),
                new PlanDelCatalogo(PlanA1, "00A1", TipoDeFormatoDelPlan._10, Moneda.USD),
            };
        }

        /// <summary>El remitente: vigente sobre 0042; activa pero SIN evidencia sobre 0006; nada sobre 00A1.</summary>
        private static CatalogosDeValidacion Catalogos(string obligatoriedad = ParametrosDePlantillaAceptacion.ObligatoriedadInicial)
        {
            return new CatalogosDeValidacion(
                Estructura(),
                ListasPlantilla.DesdeJson(ParametrosDePlantillaAceptacion.ListasValidas),
                ObligatoriedadPlantilla.DesdeJson(obligatoriedad),
                Planes(),
                new Dictionary<Guid, bool> { [Plan42] = true, [Plan06] = false });
        }

        /// <summary>Una fila buena (Inclusion · ACH · plan 0042, formato 11, USD) con los cambios que pida cada prueba. Un valor nulo = la celda no vino.</summary>
        private static FilaEnValidacion Fila(CatalogosDeValidacion catalogos, params (string campo, string valor)[] cambios)
        {
            var porCampo = new Dictionary<string, string>
            {
                ["gestion"] = "Inclusion", ["clasificacion"] = "ACH", ["tipoIdentificacion"] = "CNA", ["moneda"] = "USD", ["banco"] = "BAC",
                ["numeroPlan"] = "42", ["nombreBeneficiario"] = "Juan Perez", ["numeroIdentificacion"] = Identificacion, ["numeroCuenta"] = Cuenta,
            };
            foreach (var (campo, valor) in cambios)
            {
                porCampo[campo] = valor;
            }

            var valores = porCampo.Where(p => p.Value != null).ToDictionary(p => Columnas[p.Key], p => p.Value);
            return new FilaEnValidacion(new FilaPlantilla { NumeroFilaExcel = 15, NumeroOrden = 3, Valores = valores }, catalogos);
        }

        private static FilaEnValidacion Fila(params (string campo, string valor)[] cambios) => Fila(Catalogos(), cambios);

        private static IList<ResultadoDeRegla> Correr(FilaEnValidacion fila, IDictionary<string, string> mensajes = null)
        {
            var reglas = Semilla.Select((r, i) => new DefinicionDeRegla
            {
                Codigo = r.codigo,
                Orden = (i + 1) * 10,
                DependeDe = r.dependeDe,
                Efecto = EfectoDeLaRegla.Rechaza,
                MensajeCliente = mensajes != null && mensajes.TryGetValue(r.codigo, out var m) ? m : null,
            }).ToList();
            return new MotorDeReglas<FilaEnValidacion>(ReglasDeRegistro.Evaluadores()).Evaluar(reglas, fila);
        }

        private static string Letras(IEnumerable<ResultadoDeRegla> rs)
        {
            return string.Concat(rs.Select(r => r.Resultado == ResultadoDeLaRegla.Cumplida ? "C" : r.Resultado == ResultadoDeLaRegla.NoCumplida ? "N" : "O"));
        }

        private static string Razon(IEnumerable<ResultadoDeRegla> rs, string codigo) => rs.Single(r => r.Codigo == codigo).Razon;

        private static Veredicto Suelta(string codigo, FilaEnValidacion fila) => ReglasDeRegistro.Evaluadores().Single(e => e.Codigo == codigo).Evaluar(fila);

        // ------------------------------------------------------------------ el cableado
        [Fact]
        public void Hay_un_evaluador_por_cada_regla_semilla_de_registro_y_el_codigo_de_la_autorizacion_es_uno_solo()
        {
            var unos = ReglasDeRegistro.Evaluadores();
            Assert.Equal(Semilla.Select(s => s.codigo).OrderBy(c => c, StringComparer.Ordinal), unos.Select(e => e.Codigo).OrderBy(c => c, StringComparer.Ordinal));
            Assert.Empty(unos.Intersect(ReglasDeRegistro.Evaluadores()));
            Assert.Equal(EstadosPorReglas.CodigoAutorizacion, ReglasDeRegistro.AutorizacionCorreoPlan);
            Assert.All(unos, e => Assert.Throws<ArgumentNullException>(() => e.Evaluar(null)));
        }

        // ------------------------------------------------------------------ la fila buena, y lo que el plugin guarda de ella
        [Fact]
        public void Una_fila_buena_cumple_las_ocho_queda_validada_y_trae_todo_lo_que_se_guarda()
        {
            var fila = Fila(("referencia", "  REF-DEL-CLIENTE  "));

            var rs = Correr(fila);

            Assert.Equal("CCCCCCCC", Letras(rs));
            Assert.Equal(EstadoDeLaFila.Validada, EstadosPorReglas.DeLaFila(rs));
            Assert.Equal(3, fila.NumeroFila);
            Assert.Equal((Gestion.Inclusion, Clasificacion.ACH, TipoDeIdentificacion.CNA, Moneda.USD, Banco.BAC), (fila.Gestion, fila.Clasificacion, fila.TipoIdentificacion, fila.Moneda, fila.Banco));
            Assert.Equal("102", fila.CodigoDeBanco);
            Assert.Equal("0042", fila.NumeroPlanNormalizado);
            Assert.Equal(Plan42, fila.Plan.Id);
            Assert.Equal("  REF-DEL-CLIENTE  ", fila.ReferenciaRecibida); // tal cual vino
            Assert.Equal("10200000000123456789", fila.ReferenciaConstruida); // D-17: 3 del banco + la cuenta con ceros a la izquierda hasta 17
            Assert.Equal(fila.ReferenciaConstruida, fila.ReferenciaQueRige); // formato 11: rige la construida, sin mirar la recibida (DD-10)
            Assert.Equal(20, fila.ReferenciaQueRige.Length);
            Assert.Equal("Juan Perez", fila.Recibido("nombreBeneficiario"));
            Assert.Equal("Nombre del beneficiario", fila.Encabezado("nombreBeneficiario"));
        }

        [Fact]
        public void La_fila_es_una_vista_da_lo_mismo_sin_que_corra_ninguna_regla_y_las_veces_que_se_le_pida()
        {
            var fila = Fila(("gestion", " ALTA "), ("numeroPlan", " a1 "), ("moneda", "dólares"));
            Assert.Equal(Gestion.Inclusion, fila.Gestion);
            Assert.Equal("00A1", fila.NumeroPlanNormalizado);
            Assert.Equal(PlanA1, fila.Plan.Id);
            Assert.Equal(Moneda.USD, fila.Moneda);
            Assert.Equal("ALTA", fila.Recibido("gestion"));
            Assert.Same(fila.Plan, fila.Plan);
            Assert.Throws<ArgumentException>(() => fila.Recibido("saldo"));
            Assert.Throws<ArgumentException>(() => fila.Encabezado("Gestion"));
        }

        [Fact]
        public void En_formatos_06_y_10_no_se_deriva_nada_rige_la_recibida_aunque_venga_vacia()
        {
            var con = Fila(("numeroPlan", "6"), ("moneda", "COR"), ("clasificacion", "CK"), ("referencia", "  REF-1  "));
            Assert.Null(con.ReferenciaConstruida);
            Assert.Equal("REF-1", con.ReferenciaQueRige);
            Assert.Equal("  REF-1  ", con.ReferenciaRecibida);

            var sin = Fila(("numeroPlan", "A1"));
            Assert.Equal(string.Empty, sin.ReferenciaQueRige);
            Assert.Null(sin.ReferenciaRecibida);
            Assert.Equal("CCCCCCC", Letras(Correr(sin)).Substring(0, 7)); // la referencia vacía no rechaza (DD-15, DD-16)

            Assert.Null(Fila(("numeroPlan", "9999")).ReferenciaQueRige); // sin plan no hay referencia que rija
        }

        // ------------------------------------------------------------------ LISTAS_VALIDAS
        [Fact]
        public void Un_valor_que_no_esta_en_su_lista_falla_cita_lo_recibido_deja_la_columna_vacia_y_omite_a_las_que_dependen()
        {
            var fila = Fila(("moneda", "Dolarez"), ("banco", "BAK"));

            var rs = Correr(fila);

            Assert.Equal("NCCOOOOC", Letras(rs));
            Assert.Null(fila.Moneda);
            Assert.Null(fila.Banco);
            Assert.Null(fila.CodigoDeBanco);
            Assert.Equal(Gestion.Inclusion, fila.Gestion); // las demás listas no se tocan
            var razon = Razon(rs, ReglasDeRegistro.ListasValidas);
            Assert.Contains("Moneda", razon);
            Assert.Contains("Dolarez", razon);
            Assert.Contains("Banco", razon);
            Assert.Contains("BAK", razon);
            Assert.DoesNotContain("Gestion", razon);
            Assert.Equal(EstadoDeLaFila.RechazadaEnValidacion, EstadosPorReglas.DeLaFila(rs));
        }

        [Fact]
        public void Una_lista_vacia_no_es_un_valor_invalido_es_asunto_de_la_obligatoriedad()
        {
            var rs = Correr(Fila(("moneda", "  "), ("tipoIdentificacion", null)));
            Assert.Equal("CCCCNOCC", Letras(rs));
            var razon = Razon(rs, ReglasDeRegistro.Obligatoriedad);
            Assert.Contains("Moneda", razon);
            Assert.Contains("Tipo de identificacion", razon);
        }

        [Fact]
        public void Un_valor_hostil_en_una_lista_se_cita_acotado_y_en_una_linea()
        {
            var hostil = "{regla}\r\n" + new string('Z', 3000);
            var razon = Razon(Correr(Fila(("gestion", hostil))), ReglasDeRegistro.ListasValidas);
            Assert.True(razon.Length <= MensajeAlCliente.LargoMaximo);
            Assert.Contains(MensajeAlCliente.Citar(hostil), razon);
            Assert.DoesNotContain("\n", razon);
            Assert.DoesNotContain(ReglasDeRegistro.ListasValidas, razon); // "{regla}" venía del cliente: no se expande
        }

        [Fact]
        public void El_negocio_puede_redactar_el_mensaje_de_las_listas_con_campo_y_valor()
        {
            var mensajes = new Dictionary<string, string> { [ReglasDeRegistro.ListasValidas] = "Revise {campo}: no aceptamos {valor}." };
            var razon = Razon(Correr(Fila(("moneda", "Dolarez")), mensajes), ReglasDeRegistro.ListasValidas);
            Assert.StartsWith("Revise Moneda: no aceptamos Dolarez.", razon);
        }

        // ------------------------------------------------------------------ LARGOS_Y_FORMATO
        [Theory]
        [InlineData("nombreBeneficiario", 44, true)]
        [InlineData("nombreBeneficiario", 45, false)]
        [InlineData("numeroCuenta", 16, true)]
        [InlineData("numeroCuenta", 17, false)]
        [InlineData("numeroIdentificacion", 16, true)]
        [InlineData("numeroIdentificacion", 17, false)]
        [InlineData("referencia", 20, true)]
        [InlineData("referencia", 21, false)]
        public void Los_largos_se_miden_sobre_lo_recibido_sin_espacios_a_los_lados(string campo, int largo, bool cumple)
        {
            var valor = "   " + new string('7', largo) + "   ";
            Assert.Equal(cumple, Suelta(ReglasDeRegistro.LargosYFormato, Fila((campo, valor))).Cumple);
        }

        [Theory]
        [InlineData("numeroCuenta", "12A456")] // digitos: solo 0-9
        [InlineData("numeroCuenta", "12 456")]
        [InlineData("numeroCuenta", "12-456")]
        [InlineData("numeroCuenta", "１２３４")] // dígitos que no son ASCII
        [InlineData("numeroCuenta", "١٢٣٤")]
        [InlineData("numeroIdentificacion", "001-123456-0000A")] // alfanumerico: sin guiones ni espacios
        [InlineData("numeroIdentificacion", "001 123456")]
        [InlineData("numeroIdentificacion", "ÑANDU123")] // alfanumerico es ASCII
        [InlineData("numeroPlan", "A-1")]
        public void El_formato_es_una_lista_cerrada_y_ascii(string campo, string valor)
        {
            Assert.False(Suelta(ReglasDeRegistro.LargosYFormato, Fila((campo, valor))).Cumple);
        }

        [Fact]
        public void Un_campo_vacio_no_falla_por_largo_minimo_y_uno_sin_limites_no_se_mira()
        {
            Assert.True(Suelta(ReglasDeRegistro.LargosYFormato, Fila(("numeroCuenta", " "), ("numeroIdentificacion", null), ("numeroPlan", ""))).Cumple);
            Assert.True(Suelta(ReglasDeRegistro.LargosYFormato, Fila(("gestion", new string('x', 500)))).Cumple); // gestion no tiene largos: eso es de LISTAS_VALIDAS
        }

        [Fact]
        public void El_mensaje_de_largos_nombra_cada_campo_por_su_encabezado_y_nunca_cita_la_cuenta_ni_la_identificacion()
        {
            var cuentaLarga = "99887766554433221100";
            var idMala = "ID-SECRETA-123-456-789";
            var rs = Correr(Fila(("numeroCuenta", cuentaLarga), ("numeroIdentificacion", idMala), ("nombreBeneficiario", new string('n', 60))));

            Assert.Equal("N", Letras(rs).Substring(1, 1));
            var razon = Razon(rs, ReglasDeRegistro.LargosYFormato);
            Assert.Contains("No. Cuenta", razon);
            Assert.Contains("No. Identificacion", razon);
            Assert.Contains("Nombre del beneficiario", razon);
            Assert.Contains("44", razon); // le dice el límite que pasó
            Assert.DoesNotContain("numeroCuenta", razon); // al cliente se le habla con SUS nombres
            Assert.All(rs.Where(r => r.Razon != null), r =>
            {
                Assert.DoesNotContain(cuentaLarga, r.Razon);
                Assert.DoesNotContain("99887766", r.Razon);
                Assert.DoesNotContain(idMala, r.Razon);
                Assert.DoesNotContain("SECRETA", r.Razon);
            });
        }

        // ------------------------------------------------------------------ PLAN_EXISTE
        [Theory]
        [InlineData("42", "0042")]
        [InlineData("0042", "0042")]
        [InlineData("  42  ", "0042")]
        [InlineData("a1", "00A1")]
        [InlineData("00a1", "00A1")]
        [InlineData("6", "0006")]
        public void El_numero_de_plan_se_normaliza_antes_de_buscarlo(string recibido, string normalizado)
        {
            var fila = Fila(("numeroPlan", recibido));
            Assert.Equal(normalizado, fila.NumeroPlanNormalizado);
            Assert.NotNull(fila.Plan);
            Assert.True(Suelta(ReglasDeRegistro.PlanExiste, fila).Cumple);
        }

        [Theory]
        [InlineData("9999", "9999")] // bien escrito, pero no existe (o está inactivo: no viene en el catálogo)
        [InlineData("O042", "O042")] // una O no es un cero: nunca se adivina un plan parecido
        [InlineData("00042", null)] // cinco caracteres: no se recorta
        [InlineData("4 2", null)]
        [InlineData("42.0", null)]
        [InlineData("４２", null)] // dígitos que no son ASCII
        [InlineData("", null)]
        [InlineData(null, null)]
        public void Un_plan_que_no_existe_no_se_adivina(string recibido, string normalizado)
        {
            var fila = Fila(("numeroPlan", recibido));
            Assert.Equal(normalizado, fila.NumeroPlanNormalizado);
            Assert.Null(fila.Plan);
            var veredicto = Suelta(ReglasDeRegistro.PlanExiste, fila);
            Assert.False(veredicto.Cumple);
            Assert.False(string.IsNullOrWhiteSpace(veredicto.Razon));
        }

        [Fact]
        public void Sin_plan_se_omite_todo_lo_que_depende_de_el_y_el_mensaje_cita_lo_que_escribio_el_cliente()
        {
            var rs = Correr(Fila(("numeroPlan", "9999")));
            Assert.Equal("CCNOOOOO", Letras(rs));
            Assert.Contains("9999", Razon(rs, ReglasDeRegistro.PlanExiste));
            Assert.Equal(EstadoDeLaFila.RechazadaEnValidacion, EstadosPorReglas.DeLaFila(rs)); // la autorización quedó Omitida: no es Sin autorización
        }

        // ------------------------------------------------------------------ FORMATO_11_SOLO_ACH
        [Theory]
        [InlineData("42", "ACH", true)]
        [InlineData("42", "BAC", false)] // plan formato 11 (DD-17)
        [InlineData("42", "CK", false)]
        [InlineData("42", "", false)] // formato 11 sin clasificación: no se puede dar por bueno
        [InlineData("42", "Transferencia", false)]
        [InlineData("6", "CK", true)] // los otros formatos admiten cualquier clasificación
        [InlineData("A1", "BAC", true)]
        [InlineData("A1", "", true)]
        [InlineData("9999", "ACH", false)] // suelta y sin plan: no se puede comprobar
        public void Un_plan_formato_11_solo_admite_ach(string plan, string clasificacion, bool cumple)
        {
            Assert.Equal(cumple, Suelta(ReglasDeRegistro.Formato11SoloAch, Fila(("numeroPlan", plan), ("clasificacion", clasificacion))).Cumple);
        }

        [Fact]
        public void Si_el_formato_11_no_es_ach_la_referencia_queda_omitida_y_lo_demas_sigue()
        {
            var rs = Correr(Fila(("clasificacion", "BAC")));
            Assert.Equal("CCCNCOCC", Letras(rs));
            Assert.Contains("0042", Razon(rs, ReglasDeRegistro.Formato11SoloAch));
        }

        // ------------------------------------------------------------------ OBLIGATORIEDAD
        [Fact]
        public void En_la_version_inicial_todo_es_obligatorio_salvo_la_referencia_y_el_mensaje_nombra_lo_que_falta()
        {
            var rs = Correr(Fila(("nombreBeneficiario", "   "), ("numeroCuenta", null)));
            Assert.Equal("CCCCNOCC", Letras(rs));
            var razon = Razon(rs, ReglasDeRegistro.Obligatoriedad);
            Assert.Contains("Nombre del beneficiario", razon);
            Assert.Contains("No. Cuenta", razon);
            Assert.DoesNotContain("Referencia", razon);
            Assert.DoesNotContain("Moneda", razon);
        }

        [Fact]
        public void La_matriz_de_obligatoriedad_manda_por_gestion_clasificacion_y_formato_del_plan()
        {
            var catalogos = Catalogos(ParametrosDePlantillaAceptacion.ObligatoriedadConReglas);
            // Exclusion: moneda y banco son opcionales. En un plan formato 10 no hay nada más que pedir.
            var exclusion = Fila(catalogos, ("gestion", "Exclusion"), ("numeroPlan", "A1"), ("moneda", null), ("banco", null));
            Assert.True(Suelta(ReglasDeRegistro.Obligatoriedad, exclusion).Cumple);
            // La misma fila como Inclusion: faltan los dos.
            var inclusion = Fila(catalogos, ("gestion", "Inclusion"), ("numeroPlan", "A1"), ("moneda", null), ("banco", null));
            Assert.False(Suelta(ReglasDeRegistro.Obligatoriedad, inclusion).Cumple);
            // La regla de Exclusion + CK + formato 06 suma la cuenta; en formato 10 no calza.
            Assert.True(Suelta(ReglasDeRegistro.Obligatoriedad, Fila(catalogos, ("gestion", "Exclusion"), ("clasificacion", "CK"), ("numeroPlan", "6"), ("numeroCuenta", null))).Cumple);
            Assert.False(Suelta(ReglasDeRegistro.Obligatoriedad, Fila(catalogos, ("gestion", "Exclusion"), ("clasificacion", "CK"), ("numeroPlan", "A1"), ("numeroCuenta", null))).Cumple);
        }

        [Fact]
        public void Suelta_con_una_dimension_desconocida_la_obligatoriedad_solo_afloja_lo_que_afloja_el_asterisco()
        {
            var catalogos = Catalogos(ParametrosDePlantillaAceptacion.ObligatoriedadConReglas);
            // Gestión inválida: la regla de Exclusion no calza, así que moneda vuelve a ser obligatoria.
            Assert.False(Suelta(ReglasDeRegistro.Obligatoriedad, Fila(catalogos, ("gestion", "Exclusiones"), ("moneda", null))).Cumple);
            // Un valor de lista INVÁLIDO no cuenta como "vino": la columna queda vacía (DD-01).
            Assert.False(Suelta(ReglasDeRegistro.Obligatoriedad, Fila(("moneda", "Dolarez"))).Cumple);
            // Plan inexistente con todo lo demás completo: no falta ningún campo (que el plan no exista lo dice PLAN_EXISTE).
            Assert.True(Suelta(ReglasDeRegistro.Obligatoriedad, Fila(("numeroPlan", "9999"))).Cumple);
        }

        // ------------------------------------------------------------------ REFERENCIA_FORMATO_11 (D-17)
        [Theory]
        [InlineData("1", "BAC", "10200000000000000001")]
        [InlineData("1234567890123456", "LAFISE", "10401234567890123456")] // 16, el máximo de la plantilla
        [InlineData("12345678901234567", "BANPRO", "10312345678901234567")] // 17: entra justo en los 20
        [InlineData("  123  ", "BAC", "10200000000000000123")]
        [InlineData("0000", "BAC", "10200000000000000000")]
        public void La_referencia_de_formato_11_es_el_codigo_del_banco_mas_la_cuenta_rellena_a_la_izquierda_hasta_17(string cuenta, string banco, string esperada)
        {
            var fila = Fila(("numeroCuenta", cuenta), ("banco", banco), ("referencia", "OTRA-COSA"));
            Assert.Equal(esperada, fila.ReferenciaConstruida);
            Assert.Equal(esperada, fila.ReferenciaQueRige);
            Assert.Equal("OTRA-COSA", fila.ReferenciaRecibida);
            Assert.True(Suelta(ReglasDeRegistro.ReferenciaFormato11, fila).Cumple);
        }

        [Theory]
        [InlineData("123456789012345678", "BAC")] // 18: no entra
        [InlineData("12A4", "BAC")]
        [InlineData("12-34", "BAC")]
        [InlineData("１２３", "BAC")]
        [InlineData("", "BAC")]
        [InlineData(null, "BAC")]
        [InlineData("123", "BAK")] // banco inválido: no hay código
        [InlineData("123", "")]
        public void Si_la_referencia_de_formato_11_no_se_puede_armar_la_regla_no_se_cumple_y_no_queda_ninguna_referencia(string cuenta, string banco)
        {
            var fila = Fila(("numeroCuenta", cuenta), ("banco", banco));
            Assert.Null(fila.ReferenciaConstruida);
            Assert.Null(fila.ReferenciaQueRige); // jamás cae a la recibida en formato 11
            var veredicto = Suelta(ReglasDeRegistro.ReferenciaFormato11, fila);
            Assert.False(veredicto.Cumple);
            if (!string.IsNullOrEmpty(cuenta))
            {
                Assert.DoesNotContain(cuenta, veredicto.Razon + veredicto.Precision);
            }
        }

        [Theory]
        [InlineData("6", "COR", true)] // formatos 06 y 10: siempre se cumple, no deriva nada (DD-15)
        [InlineData("A1", "USD", true)]
        [InlineData("9999", "USD", false)] // suelta y sin plan: no se puede comprobar
        public void En_los_otros_formatos_la_regla_de_referencia_siempre_se_cumple_aunque_la_cuenta_sea_cualquier_cosa(string plan, string moneda, bool cumple)
        {
            var fila = Fila(("numeroPlan", plan), ("moneda", moneda), ("numeroCuenta", "NO-ES-UNA-CUENTA-DE-FORMATO-11"));
            Assert.Equal(cumple, Suelta(ReglasDeRegistro.ReferenciaFormato11, fila).Cumple);
        }

        // ------------------------------------------------------------------ MONEDA_DEL_PLAN
        [Theory]
        [InlineData("42", "USD", true)]
        [InlineData("42", "dólares", true)]
        [InlineData("42", "COR", false)]
        [InlineData("6", "COR", true)]
        [InlineData("6", "USD", false)]
        [InlineData("42", "", true)] // sin moneda no hay nada que contradiga al plan: si era obligatoria lo dice OBLIGATORIEDAD
        [InlineData("42", "Dolarez", false)] // suelta con una moneda inválida: no se puede comprobar
        [InlineData("9999", "USD", false)] // suelta y sin plan
        public void La_moneda_de_la_cuenta_es_la_del_plan(string plan, string moneda, bool cumple)
        {
            Assert.Equal(cumple, Suelta(ReglasDeRegistro.MonedaDelPlan, Fila(("numeroPlan", plan), ("moneda", moneda))).Cumple);
        }

        [Fact]
        public void El_mensaje_de_moneda_nombra_el_plan()
        {
            var rs = Correr(Fila(("moneda", "COR")));
            Assert.Equal("CCCCCCNC", Letras(rs));
            Assert.Contains("0042", Razon(rs, ReglasDeRegistro.MonedaDelPlan));
        }

        // ------------------------------------------------------------------ AUTORIZACION_CORREO_PLAN
        [Fact]
        public void Sin_autorizacion_sobre_el_plan_la_fila_queda_sin_autorizacion_y_el_mensaje_dice_cual_de_los_dos_casos_es()
        {
            var sinNada = Correr(Fila(("numeroPlan", "A1")));
            Assert.Equal("CCCCCCCN", Letras(sinNada));
            Assert.Equal(EstadoDeLaFila.SinAutorizacion, EstadosPorReglas.DeLaFila(sinNada));
            var razonSinNada = Razon(sinNada, ReglasDeRegistro.AutorizacionCorreoPlan);
            Assert.Contains("00A1", razonSinNada);
            Assert.DoesNotContain("evidencia", razonSinNada);

            var sinEvidencia = Correr(Fila(("numeroPlan", "6"), ("moneda", "COR"), ("clasificacion", "CK")));
            Assert.Equal("CCCCCCCN", Letras(sinEvidencia));
            Assert.Equal(EstadoDeLaFila.SinAutorizacion, EstadosPorReglas.DeLaFila(sinEvidencia));
            var razonSinEvidencia = Razon(sinEvidencia, ReglasDeRegistro.AutorizacionCorreoPlan);
            Assert.Contains("0006", razonSinEvidencia);
            Assert.Contains("evidencia", razonSinEvidencia);
        }

        [Fact]
        public void El_caso_de_la_autorizacion_va_en_la_precision_asi_no_se_pierde_cuando_el_negocio_redacta_el_texto_general()
        {
            var mensajes = new Dictionary<string, string> { [ReglasDeRegistro.AutorizacionCorreoPlan] = "Su correo no puede gestionar el plan {plan}." };
            var razon = Razon(Correr(Fila(("numeroPlan", "6"), ("moneda", "COR"), ("clasificacion", "CK")), mensajes), ReglasDeRegistro.AutorizacionCorreoPlan);
            Assert.StartsWith("Su correo no puede gestionar el plan 0006.", razon);
            Assert.Contains("evidencia", razon);
        }

        [Fact]
        public void Suelta_y_sin_plan_la_autorizacion_nunca_se_da_por_buena()
        {
            Assert.False(Suelta(ReglasDeRegistro.AutorizacionCorreoPlan, Fila(("numeroPlan", "9999"))).Cumple);
            Assert.True(Suelta(ReglasDeRegistro.AutorizacionCorreoPlan, Fila()).Cumple);
        }

        [Fact]
        public void Sin_autorizacion_y_ademas_con_otra_falla_gana_sin_autorizacion_y_el_mensaje_lleva_los_dos_motivos()
        {
            var rs = Correr(Fila(("numeroPlan", "A1"), ("nombreBeneficiario", new string('n', 60))));
            Assert.Equal("CNCCCCCN", Letras(rs));
            Assert.Equal(EstadoDeLaFila.SinAutorizacion, EstadosPorReglas.DeLaFila(rs));
            Assert.Equal(2, EstadosPorReglas.MotivosDeLaFila(rs).Count);
        }

        // ------------------------------------------------------------------ todos los mensajes
        [Fact]
        public void Todo_mensaje_por_defecto_es_para_el_cliente_sin_codigos_de_regla_sin_llaves_sin_nombres_internos_y_acotado()
        {
            var filas = new[]
            {
                Fila(("gestion", "X"), ("clasificacion", "Y"), ("numeroCuenta", "ABC"), ("numeroPlan", "9999")),
                Fila(("clasificacion", "BAC"), ("moneda", "COR"), ("nombreBeneficiario", null)),
                Fila(("numeroPlan", "A1"), ("numeroCuenta", new string('9', 30))),
                Fila(("banco", null), ("numeroCuenta", "12A")),
            };
            var nombresInternos = CamposDeFila.Todos().Where(c => c.Any(char.IsUpper)).ToList(); // numeroPlan, tipoIdentificacion…

            foreach (var evaluador in ReglasDeRegistro.Evaluadores())
            {
                foreach (var fila in filas)
                {
                    var veredicto = evaluador.Evaluar(fila);
                    if (veredicto.Cumple)
                    {
                        continue;
                    }

                    var texto = MensajeAlCliente.Componer(null, veredicto, evaluador.Codigo);
                    Assert.False(string.IsNullOrWhiteSpace(texto));
                    Assert.True(texto.Length <= MensajeAlCliente.LargoMaximo);
                    Assert.DoesNotContain("_", texto);
                    Assert.DoesNotContain("{", texto);
                    Assert.DoesNotContain("\n", texto);
                    Assert.All(nombresInternos, n => Assert.DoesNotContain(n, texto));
                }
            }
        }

        // ------------------------------------------------------------------ los catálogos
        [Fact]
        public void Los_catalogos_mal_armados_son_un_error_real_no_una_regla_fallida()
        {
            var listas = ListasPlantilla.DesdeJson(ParametrosDePlantillaAceptacion.ListasValidas);
            var obligatoriedad = ObligatoriedadPlantilla.DesdeJson(ParametrosDePlantillaAceptacion.ObligatoriedadInicial);
            var autorizaciones = new Dictionary<Guid, bool>();
            CatalogosDeValidacion Con(ConfiguracionPlantilla e, IEnumerable<PlanDelCatalogo> p) => new CatalogosDeValidacion(e, listas, obligatoriedad, p, autorizaciones);

            Assert.Throws<ArgumentNullException>(() => new CatalogosDeValidacion(null, listas, obligatoriedad, Planes(), autorizaciones));
            Assert.Throws<ArgumentNullException>(() => new CatalogosDeValidacion(Estructura(), null, obligatoriedad, Planes(), autorizaciones));
            Assert.Throws<ArgumentNullException>(() => new CatalogosDeValidacion(Estructura(), listas, null, Planes(), autorizaciones));
            Assert.Throws<ArgumentNullException>(() => new CatalogosDeValidacion(Estructura(), listas, obligatoriedad, null, autorizaciones));
            Assert.Throws<ArgumentNullException>(() => new CatalogosDeValidacion(Estructura(), listas, obligatoriedad, Planes(), null));

            Assert.Throws<ArgumentException>(() => Con(Estructura(c => c.RemoveAt(9)), Planes())); // falta un campo
            Assert.Throws<ArgumentException>(() => Con(Estructura(c => c.Add(new CampoPlantilla { Nombre = "saldo", Columna = "Z", EncabezadoEsperado = "Saldo" })), Planes()));
            Assert.Throws<ArgumentException>(() => Con(Estructura(c => c[0].Nombre = null), Planes()));
            Assert.Throws<ArgumentException>(() => Con(Estructura(c => c[0].Nombre = "Gestion"), Planes())); // los nombres son exactos

            Assert.Throws<ArgumentException>(() => Con(Estructura(), new PlanDelCatalogo[] { null }));
            Assert.Throws<ArgumentException>(() => Con(Estructura(), new[] { new PlanDelCatalogo(Plan42, "42", TipoDeFormatoDelPlan._11, Moneda.USD) })); // sin normalizar
            Assert.Throws<ArgumentException>(() => Con(Estructura(), new[] { new PlanDelCatalogo(Plan42, "00a1", TipoDeFormatoDelPlan._11, Moneda.USD) }));
            Assert.Throws<ArgumentException>(() => Con(Estructura(), new[] { new PlanDelCatalogo(Plan42, null, TipoDeFormatoDelPlan._11, Moneda.USD) }));
            Assert.Throws<ArgumentException>(() => Con(Estructura(), Planes().Concat(new[] { new PlanDelCatalogo(Guid.NewGuid(), "0042", TipoDeFormatoDelPlan._06, Moneda.COR) })));

            Assert.Empty(Letras(new MotorDeReglas<FilaEnValidacion>(ReglasDeRegistro.Evaluadores()).Evaluar(new DefinicionDeRegla[0], new FilaEnValidacion(new FilaPlantilla { NumeroOrden = 1, Valores = new Dictionary<string, string>() }, Con(Estructura(), new PlanDelCatalogo[0])))));
        }

        [Fact]
        public void Los_catalogos_no_cambian_aunque_cambie_lo_que_se_les_paso()
        {
            var planes = Planes();
            var autorizaciones = new Dictionary<Guid, bool> { [Plan42] = true };
            var catalogos = new CatalogosDeValidacion(
                Estructura(), ListasPlantilla.DesdeJson(ParametrosDePlantillaAceptacion.ListasValidas),
                ObligatoriedadPlantilla.DesdeJson(ParametrosDePlantillaAceptacion.ObligatoriedadInicial), planes, autorizaciones);

            planes.Clear();
            autorizaciones[Plan42] = false;
            autorizaciones[PlanA1] = true;

            Assert.Equal(Plan42, catalogos.PlanPorCodigo("0042").Id);
            Assert.Null(catalogos.PlanPorCodigo("42")); // se busca el código exacto, ya normalizado
            Assert.Null(catalogos.PlanPorCodigo(null));
            Assert.True(catalogos.AutorizacionSobre(Plan42));
            Assert.Null(catalogos.AutorizacionSobre(PlanA1));
            Assert.Equal("No. Cuenta", catalogos.Campo("numeroCuenta").EncabezadoEsperado);
            Assert.Throws<ArgumentException>(() => catalogos.Campo("saldo"));
        }

        [Fact]
        public void Una_fila_o_unos_catalogos_nulos_son_un_error_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => new FilaEnValidacion(null, Catalogos()));
            Assert.Throws<ArgumentNullException>(() => new FilaEnValidacion(new FilaPlantilla { NumeroOrden = 1, Valores = new Dictionary<string, string>() }, null));
            // Una fila sin valores (Valores nulo) se lee como todo vacío: que no haya filas vacías es asunto del lector.
            var vacia = new FilaEnValidacion(new FilaPlantilla { NumeroOrden = 1, Valores = null }, Catalogos());
            Assert.Equal(string.Empty, vacia.Recibido("gestion"));
            Assert.Null(vacia.Plan);
        }
    }
}
