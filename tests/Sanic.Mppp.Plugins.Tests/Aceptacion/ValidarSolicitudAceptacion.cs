using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Api;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Plantilla;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// 7.7: la Custom API de validación (diseno/03 §1), de punta a punta sobre el doble. Es la pieza que junta todo: parámetros,
    /// reglas del sobre, lector, reglas de registro, acuse y cierre.
    /// </summary>
    public class ValidarSolicitudAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 21, 17, 0, 0, DateTimeKind.Utc);
        private const string Hoja = "Datos";

        // La ventana: encabezado en la fila 12, datos desde la 13, 100 filas. Columnas C..L, en el orden de CamposDeFila.
        private static readonly string[] Columnas = { "C", "D", "E", "F", "G", "H", "I", "J", "K", "L" };

        private static readonly Dictionary<string, string> Encabezados = new Dictionary<string, string>
        {
            ["gestion"] = "Gestion", ["clasificacion"] = "Clasificacion", ["tipoIdentificacion"] = "Tipo de identificacion", ["moneda"] = "Moneda",
            ["banco"] = "Banco", ["numeroPlan"] = "No. Plan", ["nombreBeneficiario"] = "Nombre del beneficiario",
            ["numeroIdentificacion"] = "No. Identificacion", ["numeroCuenta"] = "No. Cuenta", ["referencia"] = "Referencia",
        };

        private static string Estructura()
        {
            var campos = CamposDeFila.Todos().Select((c, i) =>
            {
                var limites = c == "numeroCuenta" ? @",""largoMinimo"":1,""largoMaximo"":16,""formato"":""digitos"""
                    : c == "numeroPlan" ? @",""largoMinimo"":1,""largoMaximo"":4,""formato"":""alfanumerico"""
                    : c == "nombreBeneficiario" ? @",""largoMaximo"":44,""formato"":""texto"""
                    : string.Empty;
                return $@"{{""nombre"":""{c}"",""columna"":""{Columnas[i]}"",""encabezado"":""{Encabezados[c]}""{limites}}}";
            });
            return @"{""hoja"":""" + Hoja + @""",""filaEncabezado"":12,""primeraFila"":13,""cantidadFilas"":100,""campos"":[" + string.Join(",", campos) + "]}";
        }

        /// <summary>Una plantilla con las filas que se le pidan: cada fila es el valor de cada campo, en el orden de `CamposDeFila.Todos()`.</summary>
        private static byte[] Excel(params string[][] filas)
        {
            var b = new ConstructorXlsxDePrueba(Hoja);
            foreach (var campo in CamposDeFila.Todos().Select((c, i) => (c, i)))
            {
                b.ConTexto($"{Columnas[campo.i]}12", Encabezados[campo.c]);
            }

            for (var f = 0; f < filas.Length; f++)
            {
                for (var c = 0; c < filas[f].Length; c++)
                {
                    if (!string.IsNullOrEmpty(filas[f][c]))
                    {
                        b.ConTexto($"{Columnas[c]}{13 + f}", filas[f][c]);
                    }
                }
            }

            return b.Bytes();
        }

        private static string[] Fila(string plan = "0042", string cuenta = "123456789", string nombre = "Juan Perez", string moneda = "USD", string gestion = "Inclusion")
        {
            return new[] { gestion, "ACH", "CNA", moneda, "BAC", plan, nombre, "0011234567890", cuenta, string.Empty };
        }

        private sealed class Mundo
        {
            public readonly OrganizationServiceEnMemoria Svc = new OrganizationServiceEnMemoria();
            public readonly ArchivosDeMemoria Archivos = new ArchivosDeMemoria();
            public readonly LectorQueCuenta Lector = new LectorQueCuenta();
            public Guid SolicitudId;

            public Mundo(byte[] excel, int adjuntos = 1, int excels = 1, EstadoDeLaSolicitud estado = EstadoDeLaSolicitud.Ingresada, bool conParametros = true, string obligatoriedad = null)
            {
                Entity Activo(string tabla, params (string, object)[] atributos)
                {
                    var e = new Entity(tabla) { ["statecode"] = new OptionSetValue(0) };
                    foreach (var (a, v) in atributos)
                    {
                        e[a] = v;
                    }

                    return e;
                }

                var cliente = Svc.Sembrar(Activo(Tablas.Cliente, ("sanic_nombre", "ACME")));
                PlanId = Svc.Sembrar(Activo(Tablas.Plan, ("sanic_codigo", "0042"), ("sanic_tipoformato", new OptionSetValue((int)TipoDeFormatoDelPlan._11)), ("sanic_moneda", new OptionSetValue((int)Moneda.USD)), ("sanic_clienteid", new EntityReference(Tablas.Cliente, cliente))));
                var autorizado = Svc.Sembrar(Activo(Tablas.Autorizado, ("sanic_nombre", "ana@acme.com"), ("sanic_clienteid", new EntityReference(Tablas.Cliente, cliente))));
                Svc.Sembrar(Activo(Tablas.AutorizacionPlan, ("sanic_autorizadoid", new EntityReference(Tablas.Autorizado, autorizado)), ("sanic_planid", new EntityReference(Tablas.Plan, PlanId))));

                if (conParametros)
                {
                    Parametro(ValidarSolicitud.ParametroEstructura, Estructura());
                    Parametro(ValidarSolicitud.ParametroListas, ParametrosDePlantillaAceptacion.ListasValidas);
                    Parametro(ValidarSolicitud.ParametroObligatoriedad, obligatoriedad ?? ParametrosDePlantillaAceptacion.ObligatoriedadInicial);
                    Parametro(ValidarSolicitud.ParametroLimites, @"{""maximoBytesComprimido"":2097152,""maximoBytesDescomprimido"":20971520}");
                }

                var sobre = new[] { ReglasDelSobre.TraeAdjunto, ReglasDelSobre.AdjuntoEsExcel, ReglasDelSobre.UnSoloExcel, ReglasDelSobre.EstructuraPlantilla, ReglasDelSobre.TieneFilas };
                for (var i = 0; i < sobre.Length; i++)
                {
                    Svc.Sembrar(Activo(Tablas.Regla, ("sanic_codigo", sobre[i]), ("sanic_nivel", new OptionSetValue((int)NivelDeLaRegla.Solicitud)), ("sanic_orden", (i + 1) * 10),
                        ("sanic_dependede", i == 0 ? null : sobre[i - 1]), ("sanic_efecto", new OptionSetValue((int)EfectoDeLaRegla.Rechaza))));
                }

                var registro = new (string codigo, string dependeDe)[]
                {
                    (ReglasDeRegistro.ListasValidas, null), (ReglasDeRegistro.LargosYFormato, null), (ReglasDeRegistro.PlanExiste, null),
                    (ReglasDeRegistro.Formato11SoloAch, ReglasDeRegistro.PlanExiste + "," + ReglasDeRegistro.ListasValidas),
                    (ReglasDeRegistro.Obligatoriedad, ReglasDeRegistro.PlanExiste + "," + ReglasDeRegistro.ListasValidas),
                    (ReglasDeRegistro.ReferenciaFormato11, ReglasDeRegistro.Formato11SoloAch + "," + ReglasDeRegistro.Obligatoriedad),
                    (ReglasDeRegistro.MonedaDelPlan, ReglasDeRegistro.PlanExiste + "," + ReglasDeRegistro.ListasValidas),
                    (ReglasDeRegistro.AutorizacionCorreoPlan, ReglasDeRegistro.PlanExiste),
                };
                for (var i = 0; i < registro.Length; i++)
                {
                    Svc.Sembrar(Activo(Tablas.Regla, ("sanic_codigo", registro[i].codigo), ("sanic_nivel", new OptionSetValue((int)NivelDeLaRegla.Registro)), ("sanic_orden", (i + 1) * 10),
                        ("sanic_dependede", registro[i].dependeDe), ("sanic_efecto", new OptionSetValue((int)EfectoDeLaRegla.Rechaza))));
                }

                SolicitudId = Svc.Sembrar(new Entity(TablasHistorico.Solicitud)
                {
                    ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)estado), ["sanic_remitente"] = "ana@acme.com",
                    ["sanic_asunto"] = "Inclusiones", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
                    ["sanic_cantidadadjuntos"] = adjuntos, ["sanic_cantidadexcel"] = excels,
                    ["sanic_filastotales"] = 7, ["sanic_filasvalidas"] = 5, ["sanic_filasrechazadas"] = 2,
                });
                if (excel != null)
                {
                    Archivos.Contenido[ValidarSolicitud.ColumnaExcel] = excel;
                }
            }

            public Guid PlanId { get; }

            public void Parametro(string nombre, string valor, int version = 1)
            {
                Svc.Sembrar(new Entity(Tablas.Parametro) { ["statecode"] = new OptionSetValue(0), ["sanic_nombre"] = nombre, ["sanic_version"] = version, ["sanic_valor"] = valor });
            }

            public ResultadoDeValidacion Correr()
            {
                return new ValidarSolicitud(new SolicitudesDataverse(Svc), new CatalogosDataverse(Svc), Archivos, Lector).Ejecutar(SolicitudId, Ahora);
            }

            public Entity Solicitud() => Svc.Retrieve(TablasHistorico.Solicitud, SolicitudId, new ColumnSet(true));

            public EstadoDeLaSolicitud Estado() => (EstadoDeLaSolicitud)Solicitud().GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value;

            public IList<Entity> Filas() => Svc.Registros(TablasHistorico.Fila).OrderBy(f => (int)f["sanic_numerofila"]).ToList();

            public IList<Entity> Resultados() => Svc.Registros(TablasHistorico.ResultadoRegla).OrderBy(r => (int)r["sanic_orden"]).ToList();

            public IList<Entity> Bitacora() => Svc.Registros(TablasHistorico.Bitacora);
        }

        private sealed class ArchivosDeMemoria : IArchivos
        {
            public readonly Dictionary<string, byte[]> Contenido = new Dictionary<string, byte[]>();
            public readonly List<(string columna, long maximo)> Descargas = new List<(string, long)>();

            public byte[] Descargar(string tabla, Guid id, string columna, long maximoBytes)
            {
                Descargas.Add((columna, maximoBytes));
                if (!Contenido.TryGetValue(columna, out var bytes))
                {
                    throw new InvalidOperationException("no hay archivo en esa columna");
                }

                if (bytes.LongLength > maximoBytes)
                {
                    throw new ArchivoExcedeElMaximoException(bytes.LongLength, maximoBytes);
                }

                return bytes;
            }

            public byte[] DescargarInicio(string tabla, Guid id, string columna, int maximoBytes) => throw new NotSupportedException("la validación baja el Excel completo");
        }

        /// <summary>El lector real, envuelto para contar cuántas veces se abre el Excel.</summary>
        private sealed class LectorQueCuenta : ILectorPlantilla
        {
            private readonly LectorOpenXml _real = new LectorOpenXml();

            public int Lecturas { get; private set; }

            public ResultadoLecturaPlantilla Leer(System.IO.Stream excel, ConfiguracionPlantilla configuracion)
            {
                Lecturas++;
                return _real.Leer(excel, configuracion);
            }

            public ResultadoLecturaPlantilla Leer(byte[] excel, ConfiguracionPlantilla configuracion)
            {
                Lecturas++;
                return _real.Leer(excel, configuracion);
            }
        }

        // ------------------------------------------------------------------ el camino completo
        [Fact]
        public void Una_plantilla_con_filas_buenas_y_malas_deja_la_solicitud_en_proceso_con_todo_guardado()
        {
            var m = new Mundo(Excel(
                Fila(),
                Fila(plan: "9999"), // el plan no existe
                Fila(moneda: "COR"), // la moneda no es la del plan
                Fila(cuenta: "12A")));

            var r = m.Correr();

            Assert.Equal((EstadoDeLaSolicitud.EnProceso, false, 4, 1, 3), (r.Estado, r.YaProcesada, r.FilasTotales, r.FilasValidas, r.FilasRechazadas));
            Assert.Equal(EstadoDeLaSolicitud.EnProceso, m.Estado());

            var solicitud = m.Solicitud();
            Assert.Equal((4, 1, 3), (solicitud["sanic_filastotales"], solicitud["sanic_filasvalidas"], solicitud["sanic_filasrechazadas"]));
            Assert.Equal(Ahora, solicitud["sanic_fechavalidada"]);
            Assert.Equal("estructura=1;listas=1;obligatoriedad=1", solicitud["sanic_versionparametros"]);
            var acuse = (string)solicitud["sanic_acusecontenido"];
            Assert.Contains("MPPP-00000123", acuse);
            Assert.Contains("<table", acuse);
            Assert.DoesNotContain("123456789", acuse); // la cuenta va enmascarada (DD-08)

            var filas = m.Filas();
            Assert.Equal(new[] { 1, 2, 3, 4 }, filas.Select(f => (int)f["sanic_numerofila"]));
            Assert.Equal((int)EstadoDeLaFila.Validada, filas[0].GetAttributeValue<OptionSetValue>("sanic_estado").Value);
            Assert.Equal(m.PlanId, filas[0].GetAttributeValue<EntityReference>("sanic_planid").Id);
            Assert.Equal("10200000000123456789", filas[0]["sanic_referencia"]); // D-17: la construida
            Assert.Equal("MPPP-00000123-F01", filas[0]["sanic_nombre"]); // ya calculado: el step no vuelve a leer la Solicitud
            Assert.All(filas.Skip(1), f => Assert.Equal((int)EstadoDeLaFila.RechazadaEnValidacion, f.GetAttributeValue<OptionSetValue>("sanic_estado").Value));
            Assert.All(filas.Skip(1), f => Assert.False(string.IsNullOrWhiteSpace((string)f["sanic_mensaje"])));
            Assert.False(filas[0].Contains("sanic_mensaje"));

            // El historial regla por regla es del SOBRE (02 §3.3): las cinco, ninguna de registro.
            Assert.Equal(5, m.Resultados().Count);
            Assert.All(m.Resultados(), x => Assert.Equal((int)ResultadoDeLaRegla.Cumplida, x.GetAttributeValue<OptionSetValue>("sanic_resultado").Value));
            var evento = Assert.Single(m.Bitacora());
            Assert.Equal((int)EventoDeBitacora.ValidacionTerminada, evento.GetAttributeValue<OptionSetValue>("sanic_evento").Value);
            Assert.Equal(1, m.Lector.Lecturas); // el Excel se abre UNA sola vez
        }

        [Fact]
        public void Los_catalogos_se_cargan_una_vez_por_ejecucion_nunca_una_consulta_por_fila()
        {
            var filas = Enumerable.Range(0, 30).Select(i => Fila(cuenta: (100000 + i).ToString())).ToArray();
            var m = new Mundo(Excel(filas));

            var r = m.Correr();

            Assert.Equal(30, r.FilasValidas);
            var consultas = m.Svc.Llamadas.Count(l => l.Operacion == "RetrieveMultiple");
            Assert.InRange(consultas, 1, 12); // 4 parámetros + 2 niveles de reglas + planes + autorizaciones (hasta 4)
            Assert.Equal(30, m.Svc.Llamadas.Count(l => l.Operacion == "Create" && l.Entidad == TablasHistorico.Fila));
            Assert.All(m.Filas(), f => Assert.StartsWith("MPPP-00000123-F", (string)f["sanic_nombre"]));
        }

        // ------------------------------------------------------------------ el sobre corta antes de leer filas
        [Fact]
        public void Sin_adjunto_la_solicitud_queda_rechazada_y_el_excel_nunca_se_abre()
        {
            var m = new Mundo(Excel(Fila()), adjuntos: 0, excels: 0);

            var r = m.Correr();

            Assert.Equal((EstadoDeLaSolicitud.Rechazada, 0, 0, 0), (r.Estado, r.FilasTotales, r.FilasValidas, r.FilasRechazadas));
            Assert.Equal(EstadoDeLaSolicitud.Rechazada, m.Estado());
            Assert.Empty(m.Filas());
            Assert.Equal(0, m.Lector.Lecturas);
            Assert.Empty(m.Archivos.Descargas);
            var acuse = (string)m.Solicitud()["sanic_acusecontenido"];
            Assert.Contains("nada que procesar", acuse, StringComparison.OrdinalIgnoreCase);
            var resultados = m.Resultados();
            Assert.Equal(5, resultados.Count);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, resultados[0].GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.All(resultados.Skip(1), x => Assert.Equal((int)ResultadoDeLaRegla.Omitida, x.GetAttributeValue<OptionSetValue>("sanic_resultado").Value));
            Assert.Single(m.Bitacora());
        }

        [Fact]
        public void Una_plantilla_que_no_es_la_vigente_rechaza_con_los_motivos_del_lector_y_sin_detalle_tecnico()
        {
            var otra = new ConstructorXlsxDePrueba("OtraHoja").ConTexto("C12", "Cualquier cosa").Bytes();
            var m = new Mundo(otra);

            var r = m.Correr();

            Assert.Equal(EstadoDeLaSolicitud.Rechazada, r.Estado);
            Assert.Equal(1, m.Lector.Lecturas);
            Assert.Empty(m.Filas());
            var acuse = (string)m.Solicitud()["sanic_acusecontenido"];
            Assert.DoesNotContain("OpenXml", acuse);
            Assert.DoesNotContain("Exception", acuse);
            var estructura = m.Resultados().Single(x => (string)x["sanic_reglacodigo"] == ReglasDelSobre.EstructuraPlantilla);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, estructura.GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
        }

        [Fact]
        public void Una_plantilla_vigente_pero_sin_filas_rechaza_por_tiene_filas()
        {
            var m = new Mundo(Excel());
            var r = m.Correr();
            Assert.Equal((EstadoDeLaSolicitud.Rechazada, 0), (r.Estado, r.FilasTotales));
            var tieneFilas = m.Resultados().Single(x => (string)x["sanic_reglacodigo"] == ReglasDelSobre.TieneFilas);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, tieneFilas.GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
        }

        [Fact]
        public void Si_ninguna_fila_queda_validada_la_solicitud_se_rechaza_igual_con_sus_filas_guardadas()
        {
            var m = new Mundo(Excel(Fila(plan: "9999"), Fila(cuenta: "12A")));

            var r = m.Correr();

            Assert.Equal((EstadoDeLaSolicitud.Rechazada, 2, 0, 2), (r.Estado, r.FilasTotales, r.FilasValidas, r.FilasRechazadas));
            Assert.Equal(2, m.Filas().Count);
            var acuse = (string)m.Solicitud()["sanic_acusecontenido"];
            Assert.Contains("nada que procesar", acuse, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("<table", acuse);
        }

        [Fact]
        public void Un_excel_mas_pesado_que_el_limite_rechaza_por_estructura_no_revienta()
        {
            var m = new Mundo(Excel(Fila()));
            m.Parametro(ValidarSolicitud.ParametroLimites, @"{""maximoBytesComprimido"":10,""maximoBytesDescomprimido"":20}", version: 2);

            var r = m.Correr();

            Assert.Equal(EstadoDeLaSolicitud.Rechazada, r.Estado);
            Assert.Empty(m.Filas());
            Assert.Equal(0, m.Lector.Lecturas); // ni se abre: el tamaño se controla antes (LP-02)
        }

        // ------------------------------------------------------------------ idempotencia y errores
        [Theory]
        [InlineData(EstadoDeLaSolicitud.EnProceso)]
        [InlineData(EstadoDeLaSolicitud.Rechazada)]
        [InlineData(EstadoDeLaSolicitud.Cerrada)]
        public void Una_solicitud_que_ya_no_esta_en_ingresada_devuelve_lo_guardado_sin_tocar_nada(EstadoDeLaSolicitud estado)
        {
            var m = new Mundo(Excel(Fila()), estado: estado);
            var llamadasAntes = m.Svc.Llamadas.Count;

            var r = m.Correr();
            var llamadasDelPlugin = m.Svc.Llamadas.Count - llamadasAntes;

            Assert.Equal((estado, true, 7, 5, 2), (r.Estado, r.YaProcesada, r.FilasTotales, r.FilasValidas, r.FilasRechazadas));
            Assert.Empty(m.Filas());
            Assert.Empty(m.Resultados());
            Assert.Empty(m.Bitacora());
            Assert.Equal(0, m.Lector.Lecturas);
            Assert.Equal(1, llamadasDelPlugin);
        }

        [Theory]
        [InlineData(ValidarSolicitud.ParametroEstructura)]
        [InlineData(ValidarSolicitud.ParametroListas)]
        [InlineData(ValidarSolicitud.ParametroObligatoriedad)]
        [InlineData(ValidarSolicitud.ParametroLimites)]
        public void Un_parametro_que_falta_es_un_error_real_y_nada_queda_a_medias(string cual)
        {
            var m = new Mundo(Excel(Fila()), conParametros: false);
            foreach (var otro in new[] { ValidarSolicitud.ParametroEstructura, ValidarSolicitud.ParametroListas, ValidarSolicitud.ParametroObligatoriedad, ValidarSolicitud.ParametroLimites }.Where(p => p != cual))
            {
                m.Parametro(otro, otro == ValidarSolicitud.ParametroEstructura ? Estructura()
                    : otro == ValidarSolicitud.ParametroListas ? ParametrosDePlantillaAceptacion.ListasValidas
                    : otro == ValidarSolicitud.ParametroObligatoriedad ? ParametrosDePlantillaAceptacion.ObligatoriedadInicial
                    : @"{""maximoBytesComprimido"":2097152,""maximoBytesDescomprimido"":20971520}");
            }

            var ex = Record.Exception(() => m.Correr());

            Assert.NotNull(ex);
            Assert.IsNotType<NullReferenceException>(ex);
            Assert.Contains(cual, ex.Message);
            Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado());
            Assert.Empty(m.Filas());
            Assert.Empty(m.Resultados());
        }

        [Fact]
        public void Un_parametro_mal_cargado_tambien_es_un_error_real()
        {
            var m = new Mundo(Excel(Fila()));
            m.Parametro(ValidarSolicitud.ParametroListas, "{no es json", version: 2);
            Assert.ThrowsAny<Exception>(() => m.Correr());
            Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado());
        }

        [Fact]
        public void La_version_de_los_parametros_es_la_activa_mas_alta_de_cada_uno()
        {
            var m = new Mundo(Excel(Fila()));
            m.Parametro(ValidarSolicitud.ParametroListas, ParametrosDePlantillaAceptacion.ListasValidas, version: 7);
            m.Parametro(ValidarSolicitud.ParametroEstructura, Estructura(), version: 3);

            m.Correr();

            Assert.Equal("estructura=3;listas=7;obligatoriedad=1", m.Solicitud()["sanic_versionparametros"]);
        }

        [Fact]
        public void El_resumen_es_una_linea_para_el_run_history_sin_datos_del_cliente()
        {
            var m = new Mundo(Excel(Fila(nombre: "Juan Secreto Perez"), Fila(plan: "9999")));
            var r = m.Correr();
            Assert.False(string.IsNullOrWhiteSpace(r.Resumen));
            Assert.DoesNotContain("\n", r.Resumen);
            Assert.DoesNotContain("Secreto", r.Resumen);
            Assert.DoesNotContain("123456789", r.Resumen);
            Assert.Contains("2", r.Resumen);
        }

        [Fact]
        public void Los_argumentos_se_validan_y_la_fecha_tiene_que_ser_utc()
        {
            var m = new Mundo(Excel(Fila()));
            var api = new ValidarSolicitud(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), m.Archivos, m.Lector);
            Assert.Throws<ArgumentException>(() => api.Ejecutar(Guid.Empty, Ahora));
            Assert.Throws<ArgumentException>(() => api.Ejecutar(m.SolicitudId, DateTime.SpecifyKind(Ahora, DateTimeKind.Local)));
            Assert.Throws<ArgumentNullException>(() => new ValidarSolicitud(null, new CatalogosDataverse(m.Svc), m.Archivos, m.Lector));
            Assert.Throws<ArgumentNullException>(() => new ValidarSolicitud(new SolicitudesDataverse(m.Svc), null, m.Archivos, m.Lector));
            Assert.Throws<ArgumentNullException>(() => new ValidarSolicitud(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), null, m.Lector));
            Assert.Throws<ArgumentNullException>(() => new ValidarSolicitud(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), m.Archivos, null));
        }

        [Fact]
        public void Un_catalogo_de_reglas_mal_armado_es_un_error_real_antes_de_escribir_nada()
        {
            var m = new Mundo(Excel(Fila()));
            m.Svc.Sembrar(new Entity(Tablas.Regla)
            {
                ["statecode"] = new OptionSetValue(0), ["sanic_codigo"] = "SIN_EVALUADOR", ["sanic_nivel"] = new OptionSetValue((int)NivelDeLaRegla.Solicitud),
                ["sanic_orden"] = 99, ["sanic_efecto"] = new OptionSetValue((int)EfectoDeLaRegla.Rechaza),
            });

            Assert.Throws<ConfiguracionDeReglasInvalidaException>(() => m.Correr());
            Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado());
            Assert.Empty(m.Resultados());
        }
    }
}
