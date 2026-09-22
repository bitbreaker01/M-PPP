using System;
using System.Collections.Generic;
using System.Linq;
using System.ServiceModel;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Sanic.Mppp.Plugins.Validacion;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.6 Datos: la Solicitud y su unidad histórica (diseno/02 §3). Nombres de columnas letra por letra del diccionario.</summary>
    public class SolicitudesDataverseAceptacion
    {
        private static readonly DateTime Fecha = new DateTime(2026, 9, 21, 15, 30, 0, DateTimeKind.Utc);

        private static Guid Sembrar(OrganizationServiceEnMemoria svc, Action<Entity> cambio = null)
        {
            var s = new Entity(TablasHistorico.Solicitud)
            {
                ["sanic_nombre"] = "MPPP-00000123", ["sanic_estadoprocesamiento"] = new OptionSetValue((int)EstadoDeLaSolicitud.Ingresada),
                ["sanic_remitente"] = "ana@acme.com", ["sanic_asunto"] = "Inclusiones", ["sanic_fecharecibido"] = Fecha,
                ["sanic_cantidadadjuntos"] = 2, ["sanic_cantidadexcel"] = 1, ["sanic_messageid"] = "<x@y>",
            };
            cambio?.Invoke(s);
            return svc.Sembrar(s);
        }

        // ------------------------------------------------------------------ leer
        [Fact]
        public void Leer_trae_lo_que_los_plugins_usan_en_una_sola_llamada()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);

            var s = new SolicitudesDataverse(svc).Leer(id);

            Assert.Single(svc.Llamadas);
            Assert.Equal((id, "MPPP-00000123", EstadoDeLaSolicitud.Ingresada, "ana@acme.com", "Inclusiones", Fecha, 2, 1), (s.Id, s.Numero, s.Estado, s.Remitente, s.Asunto, s.FechaRecibido, s.CantidadAdjuntos, s.CantidadExcel));
            Assert.Null(s.VersionParametros);
        }

        [Fact]
        public void Los_conteos_vacios_son_cero_y_lo_inexistente_o_intraducible_falla()
        {
            var svc = new OrganizationServiceEnMemoria();
            var sinConteos = Sembrar(svc, e => { e.Attributes.Remove("sanic_cantidadadjuntos"); e.Attributes.Remove("sanic_cantidadexcel"); e["sanic_asunto"] = null; });
            var s = new SolicitudesDataverse(svc).Leer(sinConteos);
            Assert.Equal((0, 0), (s.CantidadAdjuntos, s.CantidadExcel));
            Assert.Null(s.Asunto);

            Assert.Throws<FaultException<OrganizationServiceFault>>(() => new SolicitudesDataverse(svc).Leer(Guid.NewGuid()));
            var estadoRaro = Sembrar(svc, e => e["sanic_estadoprocesamiento"] = new OptionSetValue(999));
            var ex = Assert.Throws<InvalidOperationException>(() => new SolicitudesDataverse(svc).Leer(estadoRaro));
            Assert.Contains("sanic_estadoprocesamiento", ex.Message);
            Assert.Contains(estadoRaro.ToString(), ex.Message);
            var sinRemitente = Sembrar(svc, e => e["sanic_remitente"] = null);
            Assert.Throws<InvalidOperationException>(() => new SolicitudesDataverse(svc).Leer(sinRemitente));
        }

        // ------------------------------------------------------------------ escribir en la solicitud
        [Fact]
        public void Cerrar_la_validacion_es_un_update_con_exactamente_sus_columnas()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            new SolicitudesDataverse(svc).CerrarValidacion(id, new CierreDeValidacion
            {
                Estado = EstadoDeLaSolicitud.EnProceso, FechaValidada = Fecha, FilasTotales = 3, FilasValidas = 1, FilasRechazadas = 2, AcuseContenido = "<html/>", VersionParametros = "listas=3",
            });

            Assert.Equal(new[] { "Update" }, svc.Llamadas.Skip(0).Select(l => l.Operacion));
            var s = svc.Retrieve(TablasHistorico.Solicitud, id, new ColumnSet(true));
            Assert.Equal((int)EstadoDeLaSolicitud.EnProceso, s.GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value);
            Assert.Equal(Fecha, s["sanic_fechavalidada"]);
            Assert.Equal((3, 1, 2), (s["sanic_filastotales"], s["sanic_filasvalidas"], s["sanic_filasrechazadas"]));
            Assert.Equal("<html/>", s["sanic_acusecontenido"]);
            Assert.Equal("listas=3", s["sanic_versionparametros"]);
            Assert.Equal("ana@acme.com", s["sanic_remitente"]); // lo demás no se toca
        }

        [Fact]
        public void Clasificar_escribe_estado_y_motivo_recortado_a_300()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            new SolicitudesDataverse(svc).Clasificar(id, new ClasificacionDelCorreo { Estado = EstadoDeLaSolicitud.NoReconocida, Motivo = new string('m', 500) });
            var s = svc.Retrieve(TablasHistorico.Solicitud, id, new ColumnSet(true));
            Assert.Equal((int)EstadoDeLaSolicitud.NoReconocida, s.GetAttributeValue<OptionSetValue>("sanic_estadoprocesamiento").Value);
            Assert.Equal(300, ((string)s["sanic_motivoclasificacion"]).Length);
            Assert.Throws<ArgumentNullException>(() => new SolicitudesDataverse(svc).Clasificar(id, null));
        }

        // ------------------------------------------------------------------ filas
        private static FilaParaGuardar Fila(int n, EstadoDeLaFila estado = EstadoDeLaFila.Validada, Guid? plan = null)
        {
            return new FilaParaGuardar
            {
                NumeroFila = n, Gestion = Gestion.Inclusion, Clasificacion = Clasificacion.ACH, Moneda = Moneda.USD, TipoIdentificacion = TipoDeIdentificacion.CNA, Banco = Banco.BAC,
                NumeroPlan = "0042", PlanId = plan, NombreBeneficiario = "Juan Perez", NumeroIdentificacion = "001", NumeroCuenta = "123", Referencia = "10200000000000000123",
                ReferenciaRecibida = "  x ", Estado = estado, Mensaje = null, FechaValidada = Fecha,
            };
        }

        [Fact]
        public void Las_filas_se_guardan_en_lotes_con_sus_columnas_y_los_nulos_no_se_mandan()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var plan = Guid.NewGuid();
            var invalida = Fila(2, EstadoDeLaFila.RechazadaEnValidacion);
            invalida.Moneda = null;
            invalida.PlanId = null;
            invalida.Mensaje = new string('m', 5000);

            new SolicitudesDataverse(svc).GuardarFilas(id, new[] { Fila(1, plan: plan), invalida });

            Assert.Equal(new[] { "ExecuteMultipleRequest" }, svc.Llamadas.Select(l => l.Operacion));
            var filas = svc.Registros(TablasHistorico.Fila).OrderBy(f => (int)f["sanic_numerofila"]).ToList();
            Assert.Equal(2, filas.Count);
            var f1 = filas[0];
            Assert.Equal(id, f1.GetAttributeValue<EntityReference>("sanic_solicitudid").Id);
            Assert.Equal(TablasHistorico.Solicitud, f1.GetAttributeValue<EntityReference>("sanic_solicitudid").LogicalName);
            Assert.Equal(plan, f1.GetAttributeValue<EntityReference>("sanic_planid").Id);
            Assert.Equal(Tablas.Plan, f1.GetAttributeValue<EntityReference>("sanic_planid").LogicalName);
            Assert.Equal((int)Gestion.Inclusion, f1.GetAttributeValue<OptionSetValue>("sanic_gestion").Value);
            Assert.Equal((int)Clasificacion.ACH, f1.GetAttributeValue<OptionSetValue>("sanic_clasificacion").Value);
            Assert.Equal((int)Moneda.USD, f1.GetAttributeValue<OptionSetValue>("sanic_moneda").Value);
            Assert.Equal((int)TipoDeIdentificacion.CNA, f1.GetAttributeValue<OptionSetValue>("sanic_tipoidentificacion").Value);
            Assert.Equal((int)Banco.BAC, f1.GetAttributeValue<OptionSetValue>("sanic_banco").Value);
            Assert.Equal("0042", f1["sanic_numeroplan"]);
            Assert.Equal(("Juan Perez", "001", "123", "10200000000000000123", "  x "), (f1["sanic_nombrebeneficiario"], f1["sanic_numeroidentificacion"], f1["sanic_numerocuenta"], f1["sanic_referencia"], f1["sanic_referenciarecibida"]));
            Assert.Equal((int)EstadoDeLaFila.Validada, f1.GetAttributeValue<OptionSetValue>("sanic_estado").Value);
            Assert.Equal(Fecha, f1["sanic_fechavalidada"]);
            Assert.False(f1.Contains("sanic_mensaje"));
            Assert.False(f1.Contains("sanic_nombre")); // calculado por la plataforma

            var f2 = filas[1];
            Assert.False(f2.Contains("sanic_moneda"));
            Assert.False(f2.Contains("sanic_planid"));
            Assert.Equal(4000, ((string)f2["sanic_mensaje"]).Length);
        }

        [Fact]
        public void Mas_filas_que_el_tamano_de_lote_van_en_varios_lotes_y_ninguna_se_pierde()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var n = TablasHistorico.TamanoDeLote * 2 + 5;
            new SolicitudesDataverse(svc).GuardarFilas(id, Enumerable.Range(1, n).Select(i => Fila(i)));
            Assert.Equal(3, svc.Llamadas.Count);
            Assert.Equal(n, svc.Registros(TablasHistorico.Fila).Count);
            Assert.Equal(Enumerable.Range(1, n), svc.Registros(TablasHistorico.Fila).Select(f => (int)f["sanic_numerofila"]).OrderBy(x => x));
        }

        [Fact]
        public void Sin_filas_no_hay_llamadas_y_una_lista_nula_es_un_error_de_programacion()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var repo = new SolicitudesDataverse(svc);
            repo.GuardarFilas(id, new FilaParaGuardar[0]);
            repo.GuardarResultados(id, new ResultadoDeRegla[0], new Dictionary<string, Guid>(), Fecha);
            Assert.Empty(svc.Llamadas);
            Assert.Throws<ArgumentNullException>(() => repo.GuardarFilas(id, null));
            Assert.Throws<ArgumentNullException>(() => repo.GuardarResultados(id, null, new Dictionary<string, Guid>(), Fecha));
            Assert.Throws<ArgumentNullException>(() => repo.GuardarResultados(id, new ResultadoDeRegla[0], null, Fecha));
            Assert.Throws<ArgumentException>(() => repo.GuardarFilas(Guid.Empty, new[] { Fila(1) }));
        }

        // ------------------------------------------------------------------ resultados de regla
        [Fact]
        public void Los_resultados_del_sobre_se_guardan_con_la_foto_del_efecto_y_el_lookup_a_la_regla_si_se_conoce()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var reglaId = Guid.NewGuid();
            var resultados = new[]
            {
                new ResultadoDeRegla("TRAE_ADJUNTO", 10, ResultadoDeLaRegla.NoCumplida, new string('r', 3000), EfectoDeLaRegla.Rechaza),
                new ResultadoDeRegla("ADJUNTO_ES_EXCEL", 20, ResultadoDeLaRegla.Omitida, "La bloqueó TRAE_ADJUNTO.", EfectoDeLaRegla.Advierte),
                new ResultadoDeRegla("OTRA", 30, ResultadoDeLaRegla.Cumplida, null, EfectoDeLaRegla.Rechaza),
            };

            new SolicitudesDataverse(svc).GuardarResultados(id, resultados, new Dictionary<string, Guid> { ["TRAE_ADJUNTO"] = reglaId }, Fecha);

            Assert.Equal(new[] { "ExecuteMultipleRequest" }, svc.Llamadas.Select(l => l.Operacion));
            var guardados = svc.Registros(TablasHistorico.ResultadoRegla).OrderBy(r => (int)r["sanic_orden"]).ToList();
            Assert.Equal(3, guardados.Count);
            var r1 = guardados[0];
            Assert.Equal(id, r1.GetAttributeValue<EntityReference>("sanic_solicitudid").Id);
            Assert.Equal("TRAE_ADJUNTO", r1["sanic_reglacodigo"]);
            Assert.Equal(reglaId, r1.GetAttributeValue<EntityReference>("sanic_reglaid").Id);
            Assert.Equal(Tablas.Regla, r1.GetAttributeValue<EntityReference>("sanic_reglaid").LogicalName);
            Assert.Equal((int)ResultadoDeLaRegla.NoCumplida, r1.GetAttributeValue<OptionSetValue>("sanic_resultado").Value);
            Assert.Equal(2000, ((string)r1["sanic_razon"]).Length);
            Assert.Equal((int)EfectoDeLaRegla.Rechaza, r1.GetAttributeValue<OptionSetValue>("sanic_efectoaplicado").Value);
            Assert.Equal(10, r1["sanic_orden"]);
            Assert.Equal(Fecha, r1["sanic_fechaevaluacion"]);
            Assert.False(r1.Contains("sanic_nombre"));
            Assert.False(guardados[1].Contains("sanic_reglaid"));
            Assert.Equal((int)EfectoDeLaRegla.Advierte, guardados[1].GetAttributeValue<OptionSetValue>("sanic_efectoaplicado").Value);
            Assert.False(guardados[2].Contains("sanic_razon"));
        }

        [Fact]
        public void Si_un_alta_del_lote_falla_se_lanza_la_falla_del_servicio()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var fallador = new ServicioQueFallaEnElSegundoCreate(svc);
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => new SolicitudesDataverse(fallador).GuardarFilas(id, new[] { Fila(1), Fila(2) }));
        }

        /// <summary>Envuelve al doble y hace fallar el segundo `CreateRequest` de un lote, como haría Dataverse ante un dato inválido.</summary>
        private sealed class ServicioQueFallaEnElSegundoCreate : IOrganizationService
        {
            private readonly OrganizationServiceEnMemoria _real;

            public ServicioQueFallaEnElSegundoCreate(OrganizationServiceEnMemoria real)
            {
                _real = real;
            }

            public OrganizationResponse Execute(OrganizationRequest request)
            {
                if (request is Microsoft.Xrm.Sdk.Messages.ExecuteMultipleRequest lote && lote.Requests.Count >= 2)
                {
                    lote.Requests[1] = new Microsoft.Xrm.Sdk.Messages.DeleteRequest { Target = new EntityReference(TablasHistorico.Fila, Guid.NewGuid()) };
                }

                return _real.Execute(request);
            }

            public Guid Create(Entity entity) => _real.Create(entity);

            public Entity Retrieve(string entityName, Guid id, ColumnSet columnSet) => _real.Retrieve(entityName, id, columnSet);

            public void Update(Entity entity) => _real.Update(entity);

            public void Delete(string entityName, Guid id) => _real.Delete(entityName, id);

            public void Associate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities) => throw new NotSupportedException();

            public void Disassociate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities) => throw new NotSupportedException();

            public EntityCollection RetrieveMultiple(QueryBase query) => _real.RetrieveMultiple(query);
        }

        // ------------------------------------------------------------------ bitácora
        [Fact]
        public void Un_evento_de_bitacora_es_un_create_con_sus_columnas_y_los_textos_recortados()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = Sembrar(svc);
            var eventoId = new SolicitudesDataverse(svc).RegistrarEvento(id, Fecha, EventoDeBitacora.ValidacionTerminada, OrigenDelEvento.CustomAPI, 0, new string('a', 300), new string('d', 20000));

            Assert.Equal(new[] { "Create" }, svc.Llamadas.Select(l => l.Operacion));
            var b = svc.Retrieve(TablasHistorico.Bitacora, eventoId, new ColumnSet(true));
            Assert.Equal(id, b.GetAttributeValue<EntityReference>("sanic_solicitudid").Id);
            Assert.Equal(Fecha, b["sanic_fechaevento"]);
            Assert.Equal((int)EventoDeBitacora.ValidacionTerminada, b.GetAttributeValue<OptionSetValue>("sanic_evento").Value);
            Assert.Equal((int)OrigenDelEvento.CustomAPI, b.GetAttributeValue<OptionSetValue>("sanic_origen").Value);
            Assert.Equal(0, b["sanic_numerofila"]);
            Assert.Equal(200, ((string)b["sanic_actortexto"]).Length);
            Assert.Equal(10000, ((string)b["sanic_detalle"]).Length);
            Assert.False(b.Contains("sanic_nombre"));

            var sinActor = new SolicitudesDataverse(svc).RegistrarEvento(id, Fecha, EventoDeBitacora.Ingresada, OrigenDelEvento.MPPPING, 3, null, "x");
            Assert.False(svc.Retrieve(TablasHistorico.Bitacora, sinActor, new ColumnSet(true)).Contains("sanic_actortexto"));
        }

        [Fact]
        public void Un_servicio_nulo_es_un_error_de_programacion()
        {
            Assert.Throws<ArgumentNullException>(() => new SolicitudesDataverse(null));
        }
    }
}
