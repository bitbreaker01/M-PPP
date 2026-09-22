using System;
using System.Collections.Generic;
using System.Linq;
using System.ServiceModel;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Messages;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>
    /// 7.5: el doble en memoria de IOrganizationService. Es infraestructura de prueba, y por eso se prueba: un doble que miente
    /// (devuelve algo que Dataverse no devolvería, o calla lo que no sabe hacer) hace pasar en falso todo lo que se apoya en él.
    /// </summary>
    public class OrganizationServiceEnMemoriaAceptacion
    {
        private const string Plan = "sanic_mppp_tbl_plan";
        private const string Fila = "sanic_mppp_tbl_fila";

        private static Entity Entidad(string logicalName, Guid? id = null, params (string atributo, object valor)[] atributos)
        {
            var e = id.HasValue ? new Entity(logicalName, id.Value) : new Entity(logicalName);
            foreach (var (atributo, valor) in atributos)
            {
                e[atributo] = valor;
            }

            return e;
        }

        private static QueryExpression Consulta(string logicalName, params ConditionExpression[] condiciones)
        {
            var q = new QueryExpression(logicalName) { ColumnSet = new ColumnSet(true) };
            q.Criteria.Conditions.AddRange(condiciones);
            return q;
        }

        // ------------------------------------------------------------------ Create / Retrieve: copias
        [Fact]
        public void Create_asigna_id_si_viene_vacio_respeta_el_que_viene_y_guarda_una_copia()
        {
            var svc = new OrganizationServiceEnMemoria();
            var plan = Entidad(Plan, null, ("sanic_codigo", "0042"));

            var id = svc.Create(plan);
            plan["sanic_codigo"] = "CAMBIADO"; // mutar después no cambia lo guardado

            Assert.NotEqual(Guid.Empty, id);
            Assert.Equal("0042", svc.Retrieve(Plan, id, new ColumnSet(true))["sanic_codigo"]);

            var fijo = Guid.NewGuid();
            Assert.Equal(fijo, svc.Create(Entidad(Plan, fijo, ("sanic_codigo", "0006"))));
            Assert.Equal(2, svc.Registros(Plan).Count);
        }

        [Fact]
        public void Un_id_repetido_en_la_misma_entidad_falla_como_en_dataverse()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan));
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Create(Entidad(Plan, id)));
            svc.Create(Entidad(Fila, id)); // en otra entidad el mismo id es otro registro
        }

        [Fact]
        public void Retrieve_devuelve_solo_las_columnas_pedidas_y_siempre_id_y_nombre_logico_en_una_copia()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan, null, ("sanic_codigo", "0042"), ("sanic_moneda", new OptionSetValue(1))));

            var parcial = svc.Retrieve(Plan, id, new ColumnSet("sanic_codigo"));
            Assert.Equal(id, parcial.Id);
            Assert.Equal(Plan, parcial.LogicalName);
            Assert.True(parcial.Contains("sanic_codigo"));
            Assert.False(parcial.Contains("sanic_moneda"));

            parcial["sanic_codigo"] = "CAMBIADO";
            Assert.Equal("0042", svc.Retrieve(Plan, id, new ColumnSet(true))["sanic_codigo"]);
            Assert.NotSame(svc.Retrieve(Plan, id, new ColumnSet(true)), svc.Retrieve(Plan, id, new ColumnSet(true)));
        }

        [Fact]
        public void Retrieve_de_un_registro_que_no_existe_es_la_misma_falla_que_da_dataverse()
        {
            var svc = new OrganizationServiceEnMemoria();
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Retrieve(Plan, Guid.NewGuid(), new ColumnSet(true)));
            var id = svc.Create(Entidad(Plan));
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Retrieve(Fila, id, new ColumnSet(true))); // otra entidad
        }

        [Fact]
        public void Retrieve_por_clave_alternativa_busca_por_igualdad_de_esos_atributos()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan, null, ("sanic_codigo", "0042")));
            svc.Create(Entidad(Plan, null, ("sanic_codigo", "0006")));

            // Como en Dataverse: por Execute(RetrieveRequest) con un EntityReference que trae KeyAttributes en vez de Id.
            var porClave = new RetrieveRequest { Target = new EntityReference(Plan, "sanic_codigo", "0042"), ColumnSet = new ColumnSet(true) };
            Assert.Equal(id, ((RetrieveResponse)svc.Execute(porClave)).Entity.Id);

            var noExiste = new RetrieveRequest { Target = new EntityReference(Plan, "sanic_codigo", "9999"), ColumnSet = new ColumnSet(true) };
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Execute(noExiste));
        }

        // ------------------------------------------------------------------ Update / Delete
        [Fact]
        public void Update_fusiona_atributos_y_no_borra_los_que_no_vienen()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan, null, ("sanic_codigo", "0042"), ("sanic_moneda", new OptionSetValue(1))));

            svc.Update(Entidad(Plan, id, ("sanic_moneda", new OptionSetValue(2)), ("sanic_nuevo", "x")));

            var leido = svc.Retrieve(Plan, id, new ColumnSet(true));
            Assert.Equal("0042", leido["sanic_codigo"]);
            Assert.Equal(2, leido.GetAttributeValue<OptionSetValue>("sanic_moneda").Value);
            Assert.Equal("x", leido["sanic_nuevo"]);
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Update(Entidad(Plan, Guid.NewGuid(), ("a", 1))));
        }

        [Fact]
        public void Update_guarda_una_copia_y_un_valor_nulo_deja_el_atributo_en_nulo()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan, null, ("sanic_codigo", "0042")));
            var cambio = Entidad(Plan, id, ("sanic_codigo", null));
            svc.Update(cambio);
            cambio["sanic_codigo"] = "CAMBIADO";
            var leido = svc.Retrieve(Plan, id, new ColumnSet(true));
            Assert.True(leido.Contains("sanic_codigo"));
            Assert.Null(leido["sanic_codigo"]);
        }

        [Fact]
        public void Delete_borra_y_sobre_un_inexistente_falla()
        {
            var svc = new OrganizationServiceEnMemoria();
            var id = svc.Create(Entidad(Plan));
            svc.Delete(Plan, id);
            Assert.Empty(svc.Registros(Plan));
            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Delete(Plan, id));
        }

        // ------------------------------------------------------------------ RetrieveMultiple
        private static OrganizationServiceEnMemoria ConPlanes()
        {
            var svc = new OrganizationServiceEnMemoria();
            svc.Sembrar(Entidad(Plan, null, ("sanic_codigo", "0042"), ("sanic_moneda", new OptionSetValue(2)), ("statecode", new OptionSetValue(0)), ("sanic_orden", 3)));
            svc.Sembrar(Entidad(Plan, null, ("sanic_codigo", "0006"), ("sanic_moneda", new OptionSetValue(1)), ("statecode", new OptionSetValue(0)), ("sanic_orden", 1)));
            svc.Sembrar(Entidad(Plan, null, ("sanic_codigo", "00A1"), ("sanic_moneda", new OptionSetValue(2)), ("statecode", new OptionSetValue(1)), ("sanic_orden", 2)));
            return svc;
        }

        private static IEnumerable<string> Codigos(EntityCollection ec) => ec.Entities.Select(e => (string)e["sanic_codigo"]);

        [Fact]
        public void Sembrar_no_cuenta_como_llamada_y_retrievemultiple_si()
        {
            var svc = ConPlanes();
            Assert.Empty(svc.Llamadas);
            svc.RetrieveMultiple(Consulta(Plan));
            Assert.Single(svc.Llamadas);
            Assert.Equal(("RetrieveMultiple", Plan), (svc.Llamadas[0].Operacion, svc.Llamadas[0].Entidad));
        }

        [Fact]
        public void Equal_compara_por_valor_tambien_optionset_entityreference_y_money()
        {
            var svc = ConPlanes();
            var clienteId = Guid.NewGuid();
            svc.Sembrar(Entidad(Fila, null, ("sanic_planid", new EntityReference(Plan, clienteId)), ("sanic_monto", new Money(10m))));
            svc.Sembrar(Entidad(Fila, null, ("sanic_planid", new EntityReference(Plan, Guid.NewGuid())), ("sanic_monto", new Money(20m))));

            Assert.Equal(new[] { "0042" }, Codigos(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Equal, "0042")))));
            Assert.Equal(2, svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_moneda", ConditionOperator.Equal, 2))).Entities.Count);
            Assert.Equal(2, svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_moneda", ConditionOperator.Equal, new OptionSetValue(2)))).Entities.Count);
            Assert.Single(svc.RetrieveMultiple(Consulta(Fila, new ConditionExpression("sanic_planid", ConditionOperator.Equal, clienteId))).Entities);
            Assert.Single(svc.RetrieveMultiple(Consulta(Fila, new ConditionExpression("sanic_planid", ConditionOperator.Equal, new EntityReference(Plan, clienteId)))).Entities);
            Assert.Single(svc.RetrieveMultiple(Consulta(Fila, new ConditionExpression("sanic_monto", ConditionOperator.Equal, 10m))).Entities);
            Assert.Empty(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Equal, "0042 "))).Entities); // exacto
        }

        [Fact]
        public void In_null_notnull_y_notequal()
        {
            var svc = ConPlanes();
            svc.Sembrar(Entidad(Plan, null, ("sanic_codigo", "SINM")));

            Assert.Equal(new[] { "0042", "0006" }, Codigos(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.In, "0042", "0006")))));
            Assert.Equal(new[] { "0042", "0006" }, Codigos(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.In, new object[] { "0042", "0006", "ZZZZ" })))));
            Assert.Equal(new[] { "SINM" }, Codigos(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_moneda", ConditionOperator.Null)))));
            Assert.Equal(3, svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_moneda", ConditionOperator.NotNull))).Entities.Count);
            Assert.Equal(3, svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.NotEqual, "0042"))).Entities.Count);
        }

        [Fact]
        public void Varias_condiciones_son_and_y_los_filtros_anidados_respetan_su_operador()
        {
            var svc = ConPlanes();
            var activosEnUsd = Consulta(Plan, new ConditionExpression("statecode", ConditionOperator.Equal, 0), new ConditionExpression("sanic_moneda", ConditionOperator.Equal, 2));
            Assert.Equal(new[] { "0042" }, Codigos(svc.RetrieveMultiple(activosEnUsd)));

            var q = Consulta(Plan, new ConditionExpression("statecode", ConditionOperator.Equal, 0));
            var o = new FilterExpression(LogicalOperator.Or);
            o.AddCondition("sanic_codigo", ConditionOperator.Equal, "0006");
            o.AddCondition("sanic_codigo", ConditionOperator.Equal, "00A1"); // inactivo: lo saca el And de arriba
            q.Criteria.AddFilter(o);
            Assert.Equal(new[] { "0006" }, Codigos(svc.RetrieveMultiple(q)));
        }

        [Fact]
        public void Columnset_topcount_y_orders()
        {
            var svc = ConPlanes();
            var q = new QueryExpression(Plan) { ColumnSet = new ColumnSet("sanic_codigo"), TopCount = 2 };
            q.AddOrder("sanic_orden", OrderType.Descending);

            var ec = svc.RetrieveMultiple(q);

            Assert.Equal(new[] { "0042", "00A1" }, Codigos(ec));
            Assert.All(ec.Entities, e => Assert.False(e.Contains("sanic_moneda")));
            Assert.All(ec.Entities, e => Assert.Equal(Plan, e.LogicalName));
            Assert.Equal(Plan, ec.EntityName);

            q.Orders.Clear();
            q.AddOrder("sanic_codigo", OrderType.Ascending);
            q.TopCount = null;
            Assert.Equal(new[] { "0006", "0042", "00A1" }, Codigos(svc.RetrieveMultiple(q)));
        }

        [Fact]
        public void Una_consulta_sobre_una_entidad_sin_registros_devuelve_vacio_y_lo_que_se_devuelve_son_copias()
        {
            var svc = ConPlanes();
            Assert.Empty(svc.RetrieveMultiple(Consulta("sanic_mppp_tbl_cliente")).Entities);
            var ec = svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Equal, "0042")));
            ec.Entities[0]["sanic_codigo"] = "CAMBIADO";
            Assert.Equal(new[] { "0042" }, Codigos(svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Equal, "0042")))));
        }

        [Fact]
        public void Lo_que_el_doble_no_sabe_hacer_lo_dice_no_lo_simula()
        {
            var svc = ConPlanes();
            Assert.Throws<NotSupportedException>(() => svc.RetrieveMultiple(new FetchExpression("<fetch/>")));
            Assert.Throws<NotSupportedException>(() => svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Like, "00%"))));
            Assert.Throws<NotSupportedException>(() => svc.RetrieveMultiple(Consulta(Plan, new ConditionExpression("sanic_orden", ConditionOperator.GreaterThan, 1))));
            var conLink = Consulta(Plan);
            conLink.AddLink(Fila, "sanic_mppp_tbl_planid", "sanic_planid");
            Assert.Throws<NotSupportedException>(() => svc.RetrieveMultiple(conLink));
            var paginada = Consulta(Plan);
            paginada.PageInfo = new PagingInfo { Count = 10, PageNumber = 2 };
            Assert.Throws<NotSupportedException>(() => svc.RetrieveMultiple(paginada));
            Assert.Throws<NotSupportedException>(() => svc.Execute(new OrganizationRequest("WhoAmI")));
            Assert.Throws<NotSupportedException>(() => svc.Associate(Plan, Guid.NewGuid(), new Relationship("x"), new EntityReferenceCollection()));
            Assert.Throws<ArgumentNullException>(() => svc.RetrieveMultiple(null));
            Assert.Throws<ArgumentNullException>(() => svc.Create(null));
            Assert.Throws<ArgumentNullException>(() => svc.Execute(null));
        }

        // ------------------------------------------------------------------ Execute: lotes y transacción (diseno/03 §1 paso 6)
        private static ExecuteMultipleRequest Lote(bool continuar, bool respuestas, params OrganizationRequest[] requests)
        {
            var lote = new ExecuteMultipleRequest { Settings = new ExecuteMultipleSettings { ContinueOnError = continuar, ReturnResponses = respuestas }, Requests = new OrganizationRequestCollection() };
            lote.Requests.AddRange(requests);
            return lote;
        }

        [Fact]
        public void Executemultiple_ejecuta_en_orden_y_devuelve_las_respuestas_si_se_piden()
        {
            var svc = new OrganizationServiceEnMemoria();
            var r = (ExecuteMultipleResponse)svc.Execute(Lote(false, true, new CreateRequest { Target = Entidad(Fila, null, ("n", 1)) }, new CreateRequest { Target = Entidad(Fila, null, ("n", 2)) }));

            Assert.Equal(2, svc.Registros(Fila).Count);
            Assert.Equal(new[] { 1, 2 }, svc.Registros(Fila).Select(e => (int)e["n"]));
            Assert.Equal(2, r.Responses.Count);
            Assert.All(r.Responses, x => Assert.Null(x.Fault));
            Assert.All(r.Responses, x => Assert.IsType<CreateResponse>(x.Response));
            Assert.Equal(svc.Registros(Fila)[1].Id, ((CreateResponse)r.Responses[1].Response).id);
            Assert.False(r.IsFaulted);
            Assert.Equal(new[] { "ExecuteMultipleRequest" }, svc.Llamadas.Select(l => l.Operacion)); // el lote es UNA llamada
        }

        [Fact]
        public void Executemultiple_sin_respuestas_y_con_continueonerror_devuelve_solo_las_fallas()
        {
            var svc = new OrganizationServiceEnMemoria();
            var inexistente = new UpdateRequest { Target = Entidad(Fila, Guid.NewGuid(), ("n", 9)) };
            var r = (ExecuteMultipleResponse)svc.Execute(Lote(true, false, new CreateRequest { Target = Entidad(Fila, null, ("n", 1)) }, inexistente, new CreateRequest { Target = Entidad(Fila, null, ("n", 3)) }));

            Assert.Equal(2, svc.Registros(Fila).Count); // la tercera se hizo igual
            Assert.True(r.IsFaulted);
            var falla = Assert.Single(r.Responses);
            Assert.Equal(1, falla.RequestIndex);
            Assert.NotNull(falla.Fault);
        }

        [Fact]
        public void Executemultiple_sin_continueonerror_se_detiene_en_la_primera_falla()
        {
            var svc = new OrganizationServiceEnMemoria();
            var r = (ExecuteMultipleResponse)svc.Execute(Lote(false, true, new CreateRequest { Target = Entidad(Fila, null, ("n", 1)) }, new DeleteRequest { Target = new EntityReference(Fila, Guid.NewGuid()) }, new CreateRequest { Target = Entidad(Fila, null, ("n", 3)) }));

            Assert.Single(svc.Registros(Fila)); // la tercera NO se hizo
            Assert.True(r.IsFaulted);
            Assert.Equal(2, r.Responses.Count);
            Assert.Null(r.Responses[0].Fault);
            Assert.NotNull(r.Responses[1].Fault);
        }

        [Fact]
        public void Executetransaction_es_atomica_si_una_falla_no_queda_nada()
        {
            var svc = new OrganizationServiceEnMemoria();
            var previo = svc.Sembrar(Entidad(Fila, null, ("n", 0)));
            var tx = new ExecuteTransactionRequest { Requests = new OrganizationRequestCollection(), ReturnResponses = true };
            tx.Requests.Add(new CreateRequest { Target = Entidad(Fila, null, ("n", 1)) });
            tx.Requests.Add(new UpdateRequest { Target = Entidad(Fila, previo, ("n", 99)) });
            tx.Requests.Add(new DeleteRequest { Target = new EntityReference(Fila, Guid.NewGuid()) });

            Assert.Throws<FaultException<OrganizationServiceFault>>(() => svc.Execute(tx));

            Assert.Single(svc.Registros(Fila));
            Assert.Equal(0, svc.Registros(Fila)[0]["n"]); // el update se deshizo

            tx.Requests.RemoveAt(2);
            var r = (ExecuteTransactionResponse)svc.Execute(tx);
            Assert.Equal(2, r.Responses.Count);
            Assert.Equal(2, svc.Registros(Fila).Count);
            Assert.Equal(99, svc.Registros(Fila).Single(e => e.Id == previo)["n"]);
        }

        [Fact]
        public void Un_request_dentro_de_un_lote_que_el_doble_no_sabe_hacer_es_notsupported_no_una_falla_simulada()
        {
            var svc = new OrganizationServiceEnMemoria();
            Assert.Throws<NotSupportedException>(() => svc.Execute(Lote(true, true, new OrganizationRequest("WhoAmI"))));
        }

        [Fact]
        public void Retrieverequest_y_retrievemultiplerequest_por_execute_dan_lo_mismo_que_directo()
        {
            var svc = ConPlanes();
            var id = svc.Registros(Plan)[0].Id;
            var r1 = (RetrieveResponse)svc.Execute(new RetrieveRequest { Target = new EntityReference(Plan, id), ColumnSet = new ColumnSet("sanic_codigo") });
            Assert.Equal("0042", r1.Entity["sanic_codigo"]);
            var r2 = (RetrieveMultipleResponse)svc.Execute(new RetrieveMultipleRequest { Query = Consulta(Plan, new ConditionExpression("sanic_codigo", ConditionOperator.Equal, "0006")) });
            Assert.Single(r2.EntityCollection.Entities);
        }
    }
}
