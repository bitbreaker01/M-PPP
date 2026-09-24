using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Steps;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.8, 7.10 y 7.11: los steps sobre la plataforma (diseno/03 §5, diseno/04 §1).</summary>
    public class StepsDePlataformaAceptacion
    {
        private static readonly DateTime Ahora = new DateTime(2026, 9, 21, 18, 0, 0, DateTimeKind.Utc);

        private static (ContextoDePluginSimulado ctx, OrganizationServiceEnMemoria svc) Armar(
            string mensaje,
            Entity target,
            int depth = 1,
            bool identidadDeAplicacion = false,
            string upnDeQuienEscribe = null,
            string cuentaDeServicioDeclarada = null)
        {
            var svc = new OrganizationServiceEnMemoria();
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = mensaje;
            ctx.Contexto.Depth = depth;
            ctx.Contexto.PrimaryEntityName = target?.LogicalName;
            ctx.Contexto.InputParameters["Target"] = target;
            var usuario = new Entity(TablasNativas.Usuario) { ["fullname"] = "Quien escribe" };
            if (identidadDeAplicacion)
            {
                usuario["applicationid"] = Guid.NewGuid();
            }

            if (upnDeQuienEscribe != null)
            {
                usuario["domainname"] = upnDeQuienEscribe;
            }

            if (cuentaDeServicioDeclarada != null)
            {
                svc.Sembrar(new Entity(Tablas.Parametro)
                {
                    ["sanic_nombre"] = BaseDeStep.ParametroCuentaDeServicio,
                    ["sanic_version"] = 1,
                    ["sanic_valor"] = cuentaDeServicioDeclarada,
                    ["statecode"] = new OptionSetValue(Tablas.Activo)
                });
            }

            var id = svc.Sembrar(usuario);
            ctx.Contexto.InitiatingUserId = id;
            ctx.Contexto.UserId = id;
            return (ctx, svc);
        }

        private static Entity Fila(params (string columna, object valor)[] columnas)
        {
            var e = new Entity(ListaBlancaDeColumnas.Fila, Guid.NewGuid());
            foreach (var (c, v) in columnas)
            {
                e[c] = v;
            }

            return e;
        }

        // ------------------------------------------------------------------ 7.8 lista blanca
        [Fact]
        public void Una_persona_que_toca_una_columna_prohibida_no_guarda_y_el_error_la_nombra()
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_estado", new OptionSetValue(3)), ("sanic_numerocuenta", "999"), ("sanic_planid", new EntityReference("sanic_mppp_tbl_plan", Guid.NewGuid()))));

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new ListaBlancaStep().Execute(ctx));

            Assert.Contains("sanic_numerocuenta", ex.Message);
            Assert.Contains("sanic_planid", ex.Message);
            Assert.DoesNotContain("sanic_estado", ex.Message);
        }

        [Fact]
        public void Una_persona_que_solo_cambia_el_estado_y_el_mensaje_guarda_sin_problema()
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_estado", new OptionSetValue(4)), ("sanic_mensaje", "Rechazada por AS400")));
            new ListaBlancaStep().Execute(ctx);
        }

        /// <summary>
        /// Los steps trabajan con SYSTEM, no con quien llama (`diseno/04` §1, textual). Con la identidad de quien
        /// llama, NINGUNA persona podía transicionar una Fila: el step de transición lee `rpa.puedeaprobar` de la
        /// tabla Parametro, sobre la que la matriz no le da lectura a ningún rol de negocio. El entorno respondía
        /// "is missing prvReadsanic_mppp_tbl_parametro" (2026-09-23).
        ///
        /// Ninguna prueba lo detectaba porque el doble de `IOrganizationService` no modela privilegios: devuelve lo
        /// que se le pide, venga de quien venga. Esta fija la identidad; la que prueba el EFECTO de los privilegios
        /// es la suite de comportamiento contra el entorno (`herramientas/pruebas/`), que suplanta usuarios reales.
        /// </summary>
        [Fact]
        public void Los_steps_trabajan_como_system_y_no_como_quien_llama()
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_estado", new OptionSetValue(4))));

            new ListaBlancaStep().Execute(ctx);

            Assert.Null(ctx.UsuarioDelServicio);
            Assert.NotEqual(Guid.Empty, ctx.Contexto.UserId); // el contexto SÍ trae usuario: no se usa a propósito
        }

        [Theory]
        [InlineData(2, false)] // código de servidor: profundidad mayor que 1
        [InlineData(1, true)] // identidad de aplicación: la cuenta de servicio de los flujos, el RPA
        public void El_codigo_de_servidor_no_pasa_por_la_lista_blanca(int depth, bool identidadDeAplicacion)
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_numerocuenta", "999"), ("sanic_referencia", "x")), depth, identidadDeAplicacion);
            new ListaBlancaStep().Execute(ctx);
        }

        /// <summary>
        /// La cuenta de servicio de BAC es un usuario, no un service principal: `diseno/07-flujos.md` §33 declara esa
        /// excepción a BP-PP-122. Un usuario NO tiene `applicationid`, así que sin esta vía los cinco flujos entran a la
        /// lista blanca como si fueran una persona y no pueden escribir sus propias marcas de envío. Se declara por su UPN
        /// en el parámetro `servicio.cuenta` y no por su GUID, porque el GUID cambia de entorno en entorno y el UPN no.
        /// </summary>
        [Fact]
        public void La_cuenta_de_servicio_declarada_en_el_parametro_no_pasa_por_la_lista_blanca()
        {
            var (ctx, _) = Armar(
                "Update",
                Fila(("sanic_numerocuenta", "999"), ("sanic_referencia", "x")),
                upnDeQuienEscribe: "servicio.mppp@bac.com.ni",
                cuentaDeServicioDeclarada: "servicio.mppp@bac.com.ni");

            new ListaBlancaStep().Execute(ctx);
        }

        [Theory]
        [InlineData("SERVICIO.MPPP@BAC.COM.NI", "servicio.mppp@bac.com.ni")] // el UPN no distingue mayúsculas
        [InlineData("servicio.mppp@bac.com.ni", "  servicio.mppp@bac.com.ni  ")] // un valor con espacios al costado igual sirve
        public void El_UPN_se_compara_sin_distinguir_mayusculas_ni_espacios(string upn, string declarado)
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_numerocuenta", "999")), upnDeQuienEscribe: upn, cuentaDeServicioDeclarada: declarado);
            new ListaBlancaStep().Execute(ctx);
        }

        /// <summary>
        /// Lo que hace que esta vía no sea un agujero: sin parámetro no exime a nadie, y con parámetro exime SOLO a quien
        /// coincide. Un parámetro vacío o borrado devuelve el control a como estaba, nunca lo abre.
        /// </summary>
        [Theory]
        [InlineData("servicio.mppp@bac.com.ni", null)] // el parámetro no existe
        [InlineData("servicio.mppp@bac.com.ni", "")] // el parámetro existe pero está vacío
        [InlineData("servicio.mppp@bac.com.ni", "   ")] // solo espacios
        [InlineData("ejecutivo@bac.com.ni", "servicio.mppp@bac.com.ni")] // es otro usuario
        [InlineData(null, "servicio.mppp@bac.com.ni")] // quien escribe no tiene UPN
        public void Sin_parametro_o_con_otro_usuario_sigue_siendo_una_persona(string upn, string declarado)
        {
            var (ctx, _) = Armar("Update", Fila(("sanic_numerocuenta", "999")), upnDeQuienEscribe: upn, cuentaDeServicioDeclarada: declarado);

            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new ListaBlancaStep().Execute(ctx));
            Assert.Contains("sanic_numerocuenta", ex.Message);
        }

        [Fact]
        public void En_solicitud_rige_su_propia_lista_y_un_target_de_otra_tabla_o_mal_armado_no_hace_nada()
        {
            var solicitud = new Entity(ListaBlancaDeColumnas.Solicitud, Guid.NewGuid()) { ["sanic_acusecontenido"] = "<html/>" };
            var (ctx, _) = Armar("Update", solicitud);
            Assert.Throws<InvalidPluginExecutionException>(() => new ListaBlancaStep().Execute(ctx));

            var (ctxOtra, _) = Armar("Update", new Entity("sanic_mppp_tbl_plan", Guid.NewGuid()) { ["sanic_codigo"] = "0042" });
            new ListaBlancaStep().Execute(ctxOtra);

            var (ctxSinTarget, _) = Armar("Update", null);
            ctxSinTarget.Contexto.InputParameters["Target"] = "no soy una entidad";
            new ListaBlancaStep().Execute(ctxSinTarget);
        }

        // ------------------------------------------------------------------ 7.10 normalizar y validar
        [Theory]
        [InlineData("Create")]
        [InlineData("Update")]
        public void El_cliente_se_normaliza_antes_de_guardarse(string mensaje)
        {
            var cliente = new Entity(Tablas.Cliente, Guid.NewGuid()) { ["sanic_cifbac"] = "  1234 ", ["sanic_cifcom"] = "abc123xy9012" };
            var (ctx, _) = Armar(mensaje, cliente);

            new NormalizarYValidarStep().Execute(ctx);

            Assert.Equal("000001234", cliente["sanic_cifbac"]);
            Assert.Equal("ABC123XY9012", cliente["sanic_cifcom"]);
        }

        [Fact]
        public void Un_valor_que_no_cumple_su_formato_rechaza_el_guardado_con_el_motivo()
        {
            var (ctx, _) = Armar("Create", new Entity(Tablas.Plan, Guid.NewGuid()) { ["sanic_codigo"] = "00042" });
            var ex = Assert.Throws<InvalidPluginExecutionException>(() => new NormalizarYValidarStep().Execute(ctx));
            Assert.False(string.IsNullOrWhiteSpace(ex.Message));
            Assert.Contains("sanic_codigo", ex.Message);
        }

        [Fact]
        public void Lo_que_no_viene_en_el_target_no_se_toca_y_las_otras_tablas_tienen_su_columna()
        {
            var parcial = new Entity(Tablas.Cliente, Guid.NewGuid()) { ["sanic_cifbac"] = "7" };
            var (ctx, _) = Armar("Update", parcial);
            new NormalizarYValidarStep().Execute(ctx);
            Assert.Equal("000000007", parcial["sanic_cifbac"]);
            Assert.False(parcial.Contains("sanic_cifcom"));

            var autorizado = new Entity(Tablas.Autorizado, Guid.NewGuid()) { ["sanic_nombre"] = "  Ana@ACME.com " };
            var (ctxA, _) = Armar("Create", autorizado);
            new NormalizarYValidarStep().Execute(ctxA);
            Assert.Equal("ana@acme.com", autorizado["sanic_nombre"]);

            var parametro = new Entity(Tablas.Parametro, Guid.NewGuid()) { ["sanic_nombre"] = " Plantilla.Listas " };
            var (ctxP, _) = Armar("Create", parametro);
            new NormalizarYValidarStep().Execute(ctxP);
            Assert.Equal("plantilla.listas", parametro["sanic_nombre"]);
        }

        [Fact]
        public void El_codigo_de_servidor_tambien_normaliza_los_catalogos()
        {
            var plan = new Entity(Tablas.Plan, Guid.NewGuid()) { ["sanic_codigo"] = "a1" };
            var (ctx, _) = Armar("Create", plan, depth: 3);
            new NormalizarYValidarStep().Execute(ctx);
            Assert.Equal("00A1", plan["sanic_codigo"]);
        }

        // ------------------------------------------------------------------ 7.11 nombre calculado
        [Fact]
        public void El_nombre_del_plan_sale_del_codigo_y_del_cliente_con_una_sola_consulta()
        {
            var svcTmp = new OrganizationServiceEnMemoria();
            var clienteId = svcTmp.Sembrar(new Entity(Tablas.Cliente) { ["sanic_nombre"] = "ACME S.A." });
            var plan = new Entity(Tablas.Plan, Guid.NewGuid()) { ["sanic_codigo"] = "0042", ["sanic_clienteid"] = new EntityReference(Tablas.Cliente, clienteId) };
            var ctx = new ContextoDePluginSimulado(svcTmp, Ahora);
            ctx.Contexto.MessageName = "Create";
            ctx.Contexto.InputParameters["Target"] = plan;
            var llamadasAntes = svcTmp.Llamadas.Count;

            new NombreCalculadoStep().Execute(ctx);

            Assert.Equal("0042 - ACME S.A.", plan["sanic_nombre"]);
            Assert.Equal(1, svcTmp.Llamadas.Count - llamadasAntes);
        }

        [Fact]
        public void El_nombre_de_la_autorizacion_y_el_de_la_fila_salen_de_sus_lookups_y_lo_que_venga_se_pisa()
        {
            var svc = new OrganizationServiceEnMemoria();
            var autorizadoId = svc.Sembrar(new Entity(Tablas.Autorizado) { ["sanic_nombre"] = "ana@acme.com" });
            var planId = svc.Sembrar(new Entity(Tablas.Plan) { ["sanic_codigo"] = "0042" });
            var solicitudId = svc.Sembrar(new Entity(TablasHistorico.Solicitud) { ["sanic_nombre"] = "MPPP-00000123" });

            var autorizacion = new Entity(Tablas.AutorizacionPlan, Guid.NewGuid())
            {
                ["sanic_nombre"] = "lo que mande el cliente",
                ["sanic_autorizadoid"] = new EntityReference(Tablas.Autorizado, autorizadoId),
                ["sanic_planid"] = new EntityReference(Tablas.Plan, planId),
            };
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = "Create";
            ctx.Contexto.InputParameters["Target"] = autorizacion;
            new NombreCalculadoStep().Execute(ctx);
            Assert.Equal("ana@acme.com → 0042", autorizacion["sanic_nombre"]);

            var fila = new Entity(TablasHistorico.Fila, Guid.NewGuid())
            {
                ["sanic_numerofila"] = 7,
                ["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId),
            };
            var ctxFila = new ContextoDePluginSimulado(svc, Ahora);
            ctxFila.Contexto.MessageName = "Create";
            ctxFila.Contexto.InputParameters["Target"] = fila;
            new NombreCalculadoStep().Execute(ctxFila);
            Assert.Equal("MPPP-00000123-F07", fila["sanic_nombre"]);
        }

        [Fact]
        public void Si_el_codigo_de_servidor_ya_trae_el_nombre_de_la_fila_no_se_vuelve_a_leer_la_solicitud()
        {
            // Revisión de código, 2026-09-21: este step corre en el Create de CADA fila; leer la Solicitud por fila es el N+1
            // que el diseño prohíbe (03 §1 paso 6).
            var svc = new OrganizationServiceEnMemoria();
            var solicitudId = svc.Sembrar(new Entity(TablasHistorico.Solicitud) { ["sanic_nombre"] = "MPPP-00000123" });
            var fila = new Entity(TablasHistorico.Fila, Guid.NewGuid())
            {
                ["sanic_nombre"] = "MPPP-00000123-F07", ["sanic_numerofila"] = 7,
                ["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId),
            };
            var ctx = new ContextoDePluginSimulado(svc, Ahora);
            ctx.Contexto.MessageName = "Create";
            ctx.Contexto.Depth = 2; // código de servidor
            ctx.Contexto.InputParameters["Target"] = fila;
            var llamadasAntes = svc.Llamadas.Count;

            new NombreCalculadoStep().Execute(ctx);

            Assert.Equal("MPPP-00000123-F07", fila["sanic_nombre"]);
            Assert.Equal(llamadasAntes, svc.Llamadas.Count);

            // A una persona se le pisa igual, y ahí sí se lee la Solicitud.
            var dePersona = new Entity(TablasHistorico.Fila, Guid.NewGuid())
            {
                ["sanic_nombre"] = "LO QUE YO QUIERA", ["sanic_numerofila"] = 7,
                ["sanic_solicitudid"] = new EntityReference(TablasHistorico.Solicitud, solicitudId),
            };
            var (ctxPersona, svcPersona) = Armar("Create", dePersona);
            svcPersona.Sembrar(new Entity(TablasHistorico.Solicitud, solicitudId) { ["sanic_nombre"] = "MPPP-00000123" });
            new NombreCalculadoStep().Execute(ctxPersona);
            Assert.Equal("MPPP-00000123-F07", dePersona["sanic_nombre"]);
        }

        [Fact]
        public void Sin_el_lookup_que_hace_falta_no_se_inventa_un_nombre()
        {
            var (ctx, _) = Armar("Create", new Entity(Tablas.Plan, Guid.NewGuid()) { ["sanic_codigo"] = "0042" });
            Assert.Throws<InvalidPluginExecutionException>(() => new NombreCalculadoStep().Execute(ctx));

            var (ctxFila, _) = Armar("Create", new Entity(TablasHistorico.Fila, Guid.NewGuid()) { ["sanic_numerofila"] = 1 });
            Assert.Throws<InvalidPluginExecutionException>(() => new NombreCalculadoStep().Execute(ctxFila));
        }

        // ------------------------------------------------------------------ lo común
        [Fact]
        public void Un_proveedor_incompleto_no_revienta_con_una_referencia_nula()
        {
            foreach (IPlugin step in new IPlugin[] { new ListaBlancaStep(), new NormalizarYValidarStep(), new NombreCalculadoStep() })
            {
                Assert.Throws<InvalidPluginExecutionException>(() => step.Execute(null));
                var (ctx, _) = Armar("Update", Fila(("sanic_estado", new OptionSetValue(3))));
                ctx.DaContexto = false;
                Assert.Throws<InvalidPluginExecutionException>(() => step.Execute(ctx));
            }
        }

        [Fact]
        public void Quien_escribe_se_reconoce_por_profundidad_o_por_identidad_de_aplicacion()
        {
            var (persona, svcPersona) = Armar("Update", Fila());
            Assert.False(BaseDeStep.EsCodigoDeServidor(persona.Contexto, svcPersona));

            var (aplicacion, svcApp) = Armar("Update", Fila(), identidadDeAplicacion: true);
            Assert.True(BaseDeStep.EsCodigoDeServidor(aplicacion.Contexto, svcApp));

            var (anidado, svcAnidado) = Armar("Update", Fila(), depth: 2);
            var llamadasAntes = svcAnidado.Llamadas.Count;
            Assert.True(BaseDeStep.EsCodigoDeServidor(anidado.Contexto, svcAnidado));
            Assert.Equal(llamadasAntes, svcAnidado.Llamadas.Count); // con profundidad > 1 ni pregunta
        }
    }
}
