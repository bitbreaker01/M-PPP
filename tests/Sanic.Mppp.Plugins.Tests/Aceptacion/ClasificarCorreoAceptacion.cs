using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Api;
using Sanic.Mppp.Plugins.Correo;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.6b: el plugin liviano (diseno/03 §0, DF-08). Decide si el correo se procesa sin abrir el Excel.</summary>
    public class ClasificarCorreoAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 21, 16, 0, 0, DateTimeKind.Utc);

        // ------------------------------------------------------------------ un mundo armado sobre el doble
        private sealed class Mundo
        {
            public readonly OrganizationServiceEnMemoria Svc = new OrganizationServiceEnMemoria();
            public readonly ArchivosSimulados Archivos = new ArchivosSimulados();
            public readonly AvisosSimulados Avisos = new AvisosSimulados();
            public Guid Cliente, PlanA, Autorizado;

            public Mundo(string prefijos = @"[""FW:"",""FWD:"",""RV:"",""REENV:""]")
            {
                Cliente = Svc.Sembrar(Activo(Tablas.Cliente, ("sanic_nombre", "ACME")));
                PlanA = Svc.Sembrar(Activo(Tablas.Plan, ("sanic_codigo", "000A"), ("sanic_tipoformato", new OptionSetValue((int)TipoDeFormatoDelPlan._06)), ("sanic_moneda", new OptionSetValue((int)Moneda.COR)), ("sanic_clienteid", new EntityReference(Tablas.Cliente, Cliente))));
                Autorizado = Svc.Sembrar(Activo(Tablas.Autorizado, ("sanic_nombre", "ana@acme.com"), ("sanic_clienteid", new EntityReference(Tablas.Cliente, Cliente))));
                Svc.Sembrar(Activo(Tablas.AutorizacionPlan, ("sanic_autorizadoid", new EntityReference(Tablas.Autorizado, Autorizado)), ("sanic_planid", new EntityReference(Tablas.Plan, PlanA))));
                if (prefijos != null)
                {
                    Svc.Sembrar(Activo(Tablas.Parametro, ("sanic_nombre", ClasificarCorreo.ParametroPrefijosDeReenvio), ("sanic_version", 1), ("sanic_valor", prefijos)));
                }

                Regla(ReglasDelCorreo.EsCorreoNuevo, 10, null, EfectoDeLaRegla.EnviaARevision);
                Regla(ReglasDelCorreo.RemitenteReconocido, 20, ReglasDelCorreo.EsCorreoNuevo, EfectoDeLaRegla.EnviaARevision);
            }

            public Guid Regla(string codigo, int orden, string dependeDe, EfectoDeLaRegla efecto)
            {
                return Svc.Sembrar(Activo(Tablas.Regla, ("sanic_codigo", codigo), ("sanic_nivel", new OptionSetValue((int)NivelDeLaRegla.Correo)), ("sanic_orden", orden), ("sanic_dependede", dependeDe), ("sanic_efecto", new OptionSetValue((int)efecto))));
            }

            public Guid Solicitud(string remitente = "ana@acme.com", EstadoDeLaSolicitud estado = EstadoDeLaSolicitud.Ingresada, string eml = "Subject: Inclusiones\r\n\r\ncuerpo")
            {
                var id = Svc.Sembrar(new Entity(TablasHistorico.Solicitud)
                {
                    ["sanic_nombre"] = "MPPP-00000001", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)estado), ["sanic_remitente"] = remitente,
                    ["sanic_asunto"] = "Inclusiones", ["sanic_fecharecibido"] = Ahora, ["sanic_messageid"] = "<m@x>",
                });
                if (eml != null)
                {
                    Archivos.Archivos[(TablasHistorico.Solicitud, id, "sanic_correocrudo")] = Encoding.UTF8.GetBytes(eml);
                }

                return id;
            }

            public ResultadoDeClasificacion Correr(Guid solicitudId)
            {
                return new ClasificarCorreo(new SolicitudesDataverse(Svc), new CatalogosDataverse(Svc), Archivos, Avisos).Ejecutar(solicitudId, Ahora);
            }

            public Entity SolicitudGuardada(Guid id) => Svc.Retrieve(TablasHistorico.Solicitud, id, new ColumnSet(true));

            public EstadoDeLaSolicitud Estado(Guid id) => (EstadoDeLaSolicitud)SolicitudGuardada(id).GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value;

            public IList<Entity> Resultados(Guid id) => Svc.Registros(TablasHistorico.ResultadoRegla).Where(r => r.GetAttributeValue<EntityReference>("sanic_solicitudid").Id == id).OrderBy(r => (int)r["sanic_orden"]).ToList();

            public IList<Entity> Bitacora(Guid id) => Svc.Registros(TablasHistorico.Bitacora).Where(b => b.GetAttributeValue<EntityReference>("sanic_solicitudid").Id == id).ToList();

            private static Entity Activo(string tabla, params (string atributo, object valor)[] atributos)
            {
                var e = new Entity(tabla) { ["statecode"] = new OptionSetValue(0) };
                foreach (var (atributo, valor) in atributos)
                {
                    e[atributo] = valor;
                }

                return e;
            }
        }

        private sealed class ArchivosSimulados : IArchivos
        {
            public readonly Dictionary<(string, Guid, string), byte[]> Archivos = new Dictionary<(string, Guid, string), byte[]>();
            public readonly List<(string columna, int maximo)> Pedidos = new List<(string, int)>();
            public int DescargasCompletas;

            public byte[] Descargar(string tabla, Guid id, string columna, long maximoBytes)
            {
                DescargasCompletas++;
                return Archivos[(tabla, id, columna)];
            }

            public byte[] DescargarInicio(string tabla, Guid id, string columna, int maximoBytes)
            {
                Pedidos.Add((columna, maximoBytes));
                var todo = Archivos[(tabla, id, columna)];
                return todo.Take(maximoBytes).ToArray();
            }
        }

        private sealed class AvisosSimulados : IAvisos
        {
            public readonly List<(Guid solicitudId, string titulo, string cuerpo)> Enviados = new List<(Guid, string, string)>();

            public void AvisarAEjecutivos(Guid solicitudId, string titulo, string cuerpo) => Enviados.Add((solicitudId, titulo, cuerpo));
        }

        // ------------------------------------------------------------------ los cuatro finales
        [Fact]
        public void Un_correo_nuevo_de_un_remitente_autorizado_se_procesa_y_la_solicitud_sigue_en_ingresada()
        {
            var m = new Mundo();
            var id = m.Solicitud();

            var r = m.Correr(id);

            Assert.Equal((true, Clasificaciones.Nuevo, false), (r.Procesar, r.Clasificacion, r.YaProcesada));
            Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado(id));
            Assert.False(m.SolicitudGuardada(id).Contains("sanic_motivoclasificacion") && m.SolicitudGuardada(id)["sanic_motivoclasificacion"] != null);
            var resultados = m.Resultados(id);
            Assert.Equal(new[] { ReglasDelCorreo.EsCorreoNuevo, ReglasDelCorreo.RemitenteReconocido }, resultados.Select(x => (string)x["sanic_reglacodigo"]));
            Assert.All(resultados, x => Assert.Equal((int)ResultadoDeLaRegla.Cumplida, x.GetAttributeValue<OptionSetValue>("sanic_resultado").Value));
            Assert.All(resultados, x => Assert.Equal(Ahora, x["sanic_fechaevaluacion"]));
            Assert.All(resultados, x => Assert.True(x.Contains("sanic_reglaid"))); // el lookup a la regla, porque el catálogo la trae
            var evento = Assert.Single(m.Bitacora(id));
            Assert.Equal((int)EventoDeBitacora.CorreoClasificado, evento.GetAttributeValue<OptionSetValue>("sanic_evento").Value);
            Assert.Equal((int)OrigenDelEvento.CustomAPI, evento.GetAttributeValue<OptionSetValue>("sanic_origen").Value);
            Assert.Empty(m.Avisos.Enviados);
            Assert.Equal(0, m.Archivos.DescargasCompletas); // nunca baja el archivo entero
            Assert.Equal(("sanic_correocrudo", LectorDeCabeceras.TopeBytes), Assert.Single(m.Archivos.Pedidos));
        }

        [Theory]
        [InlineData("Subject: FW: Inclusiones\r\nIn-Reply-To: <a@b>\r\n\r\n")]
        [InlineData("Subject: fwd: Inclusiones\r\nReferences: <a@b>\r\n\r\n")]
        [InlineData("Subject:   rv: Inclusiones\r\nReferences: <a@b>\r\n\r\n")] // sin distinguir mayúsculas ni espacios
        [InlineData("Subject: =?utf-8?B?UlY6IEluY2x1c2nDs24=?=\r\nReferences: <a@b>\r\n\r\n")] // codificado
        public void Un_reenvio_se_procesa(string eml)
        {
            var m = new Mundo();
            var id = m.Solicitud(eml: eml);
            var r = m.Correr(id);
            Assert.Equal((true, Clasificaciones.Reenvio), (r.Procesar, r.Clasificacion));
            Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado(id));
        }

        [Theory]
        [InlineData("Subject: RE: Inclusiones\r\nIn-Reply-To: <a@b>\r\n\r\n")]
        [InlineData("Subject: Inclusiones\r\nReferences: <a@b>\r\n\r\n")] // sin prefijo de reenvío: es una respuesta
        [InlineData("Subject: FWD Inclusiones\r\nReferences: <a@b>\r\n\r\n")] // "FWD" sin los dos puntos no es el prefijo
        [InlineData("Subject: Inclusiones FW:\r\nReferences: <a@b>\r\n\r\n")] // el prefijo va al principio
        public void Una_respuesta_no_se_procesa_va_a_por_clasificar_con_su_motivo_y_avisa_a_los_ejecutivos(string eml)
        {
            var m = new Mundo();
            var id = m.Solicitud(eml: eml);

            var r = m.Correr(id);

            Assert.Equal((false, Clasificaciones.Respuesta, false), (r.Procesar, r.Clasificacion, r.YaProcesada));
            Assert.Equal(EstadoDeLaSolicitud.NoEsCorreoNuevo, m.Estado(id));
            var motivo = (string)m.SolicitudGuardada(id)["sanic_motivoclasificacion"];
            Assert.Contains("respuesta", motivo, StringComparison.OrdinalIgnoreCase);
            var resultados = m.Resultados(id);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, resultados[0].GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.Equal((int)ResultadoDeLaRegla.Omitida, resultados[1].GetAttributeValue<OptionSetValue>("sanic_resultado").Value); // depende de la anterior
            Assert.Single(m.Bitacora(id));
            var aviso = Assert.Single(m.Avisos.Enviados);
            Assert.Equal(id, aviso.solicitudId);
            Assert.False(string.IsNullOrWhiteSpace(aviso.titulo));
        }

        [Fact]
        public void Un_remitente_sin_ningun_plan_autorizado_queda_no_reconocida()
        {
            var m = new Mundo();
            var id = m.Solicitud(remitente: "nadie@otro.com");

            var r = m.Correr(id);

            Assert.Equal((false, Clasificaciones.RemitenteNoReconocido), (r.Procesar, r.Clasificacion));
            Assert.Equal(EstadoDeLaSolicitud.NoReconocida, m.Estado(id));
            Assert.Contains("autoriza", (string)m.SolicitudGuardada(id)["sanic_motivoclasificacion"], StringComparison.OrdinalIgnoreCase);
            var resultados = m.Resultados(id);
            Assert.Equal((int)ResultadoDeLaRegla.Cumplida, resultados[0].GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, resultados[1].GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.Single(m.Avisos.Enviados);
        }

        [Fact]
        public void El_remitente_se_reconoce_como_lo_guarda_dataverse_y_la_evidencia_no_cuenta()
        {
            var m = new Mundo();
            Assert.True(m.Correr(m.Solicitud(remitente: "  Ana@ACME.com ")).Procesar);
        }

        [Theory]
        [InlineData("esto no es un eml")]
        [InlineData("Subject: sin fin de cabeceras\r\n")]
        [InlineData("")]
        public void Cabeceras_ilegibles_van_a_por_clasificar_como_ilegible_y_no_se_responde(string eml)
        {
            var m = new Mundo();
            var id = m.Solicitud(eml: eml);

            var r = m.Correr(id);

            Assert.Equal((false, Clasificaciones.Ilegible), (r.Procesar, r.Clasificacion));
            Assert.Equal(EstadoDeLaSolicitud.NoEsCorreoNuevo, m.Estado(id));
            Assert.Contains("cabeceras", (string)m.SolicitudGuardada(id)["sanic_motivoclasificacion"], StringComparison.OrdinalIgnoreCase);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, m.Resultados(id)[0].GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.Single(m.Avisos.Enviados);
        }

        // ------------------------------------------------------------------ idempotencia (BP-PP-055)
        [Theory]
        [InlineData(EstadoDeLaSolicitud.NoReconocida)]
        [InlineData(EstadoDeLaSolicitud.EnProceso)]
        [InlineData(EstadoDeLaSolicitud.Cerrada)]
        public void Una_solicitud_que_ya_no_esta_en_ingresada_no_se_toca(EstadoDeLaSolicitud estado)
        {
            var m = new Mundo();
            var id = m.Solicitud(estado: estado);
            var llamadasAntes = m.Svc.Llamadas.Count;

            var r = m.Correr(id);

            Assert.Equal((false, true), (r.Procesar, r.YaProcesada));
            Assert.Null(r.Clasificacion);
            Assert.Equal(estado, m.Estado(id));
            Assert.Empty(m.Resultados(id));
            Assert.Empty(m.Bitacora(id));
            Assert.Empty(m.Archivos.Pedidos);
            Assert.Equal(1, m.Svc.Llamadas.Count - llamadasAntes); // solo la lectura
        }

        // ------------------------------------------------------------------ catálogos y errores reales
        [Fact]
        public void Sin_el_parametro_de_prefijos_o_con_uno_ilegible_es_un_error_real_y_nada_queda_a_medias()
        {
            foreach (var prefijos in new[] { null, "no es json", "{}", @"[""FW:"", 3]", @"["""", ""FW:""]" })
            {
                var m = new Mundo(prefijos);
                var id = m.Solicitud(eml: "Subject: FW: x\r\nReferences: <a@b>\r\n\r\n");
                var ex = Record.Exception(() => m.Correr(id));
                Assert.NotNull(ex);
                Assert.IsNotType<NullReferenceException>(ex);
                Assert.Empty(m.Resultados(id));
                Assert.Equal(EstadoDeLaSolicitud.Ingresada, m.Estado(id));
            }
        }

        [Fact]
        public void Un_catalogo_de_reglas_mal_armado_o_vacio_es_un_error_real()
        {
            var m = new Mundo();
            m.Regla("SIN_EVALUADOR", 30, null, EfectoDeLaRegla.EnviaARevision);
            Assert.Throws<ConfiguracionDeReglasInvalidaException>(() => m.Correr(m.Solicitud()));

            var vacio = new Mundo();
            foreach (var regla in vacio.Svc.Registros(Tablas.Regla))
            {
                vacio.Svc.Delete(Tablas.Regla, regla.Id);
            }

            Assert.Throws<ConfiguracionDeReglasInvalidaException>(() => vacio.Correr(vacio.Solicitud())); // sin reglas de Correo nadie decide: no se procesa a ciegas
        }

        [Fact]
        public void Una_regla_de_correo_con_efecto_rechaza_es_catalogo_mal_armado_no_se_le_responde_a_nadie()
        {
            var m = new Mundo();
            foreach (var regla in m.Svc.Registros(Tablas.Regla))
            {
                m.Svc.Delete(Tablas.Regla, regla.Id);
            }

            m.Regla(ReglasDelCorreo.EsCorreoNuevo, 10, null, EfectoDeLaRegla.Rechaza);
            Assert.Throws<ConfiguracionDeReglasInvalidaException>(() => m.Correr(m.Solicitud(eml: "Subject: RE: x\r\nReferences: <a@b>\r\n\r\n")));
        }

        [Fact]
        public void Los_argumentos_se_validan_y_la_fecha_tiene_que_ser_utc()
        {
            var m = new Mundo();
            var plugin = new ClasificarCorreo(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), m.Archivos, m.Avisos);
            Assert.Throws<ArgumentException>(() => plugin.Ejecutar(Guid.Empty, Ahora));
            Assert.Throws<ArgumentException>(() => plugin.Ejecutar(m.Solicitud(), DateTime.SpecifyKind(Ahora, DateTimeKind.Local)));
            Assert.Throws<ArgumentNullException>(() => new ClasificarCorreo(null, new CatalogosDataverse(m.Svc), m.Archivos, m.Avisos));
            Assert.Throws<ArgumentNullException>(() => new ClasificarCorreo(new SolicitudesDataverse(m.Svc), null, m.Archivos, m.Avisos));
            Assert.Throws<ArgumentNullException>(() => new ClasificarCorreo(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), null, m.Avisos));
            Assert.Throws<ArgumentNullException>(() => new ClasificarCorreo(new SolicitudesDataverse(m.Svc), new CatalogosDataverse(m.Svc), m.Archivos, null));
        }

        // ------------------------------------------------------------------ las reglas sueltas
        [Fact]
        public void Las_reglas_del_correo_sueltas_fallan_cerrado()
        {
            var prefijos = new List<string> { "FW:", "RV:" };
            var ninguno = new HashSet<Guid>();
            var alguno = new HashSet<Guid> { Guid.NewGuid() };
            var nuevo = ReglasDelCorreo.Evaluadores().Single(e => e.Codigo == ReglasDelCorreo.EsCorreoNuevo);
            var reconocido = ReglasDelCorreo.Evaluadores().Single(e => e.Codigo == ReglasDelCorreo.RemitenteReconocido);

            Assert.True(nuevo.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De("x", false, false), prefijos, ninguno)).Cumple);
            Assert.True(nuevo.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De(" fw: x", true, false), prefijos, ninguno)).Cumple);
            Assert.False(nuevo.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De("x", true, false), prefijos, ninguno)).Cumple);
            Assert.False(nuevo.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De("fw: x", true, false), new List<string>(), ninguno)).Cumple); // sin prefijos configurados, un reenvío no se distingue
            Assert.False(nuevo.Evaluar(new CorreoEnValidacion(CabecerasLeidas.Ilegibles(), prefijos, alguno)).Cumple);
            Assert.False(reconocido.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De("x", false, false), prefijos, ninguno)).Cumple);
            Assert.True(reconocido.Evaluar(new CorreoEnValidacion(CabecerasLeidas.De("x", false, false), prefijos, alguno)).Cumple);
            Assert.All(ReglasDelCorreo.Evaluadores(), e => Assert.Throws<ArgumentNullException>(() => e.Evaluar(null)));
            Assert.Throws<ArgumentNullException>(() => new CorreoEnValidacion(null, prefijos, alguno));
            Assert.Throws<ArgumentNullException>(() => new CorreoEnValidacion(CabecerasLeidas.Ilegibles(), null, alguno));
            Assert.Throws<ArgumentNullException>(() => new CorreoEnValidacion(CabecerasLeidas.Ilegibles(), prefijos, null));
        }
    }
}
