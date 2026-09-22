using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Tests.Dobles;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.6b: los avisos dentro de la app (diseno/05 DA-08). Que nadie tenga el rol no puede tumbar la clasificación de un correo.</summary>
    public class AvisosDataverseAceptacion
    {
        private static readonly Guid Solicitud = Guid.NewGuid();

        private sealed class Mundo
        {
            public readonly OrganizationServiceEnMemoria Svc = new OrganizationServiceEnMemoria();
            public Guid Rol;

            public Mundo(bool conRol = true)
            {
                if (conRol)
                {
                    Rol = Svc.Sembrar(new Entity(TablasNativas.Rol) { ["name"] = TablasNativas.RolEjecutivo });
                }

                Svc.Sembrar(new Entity(TablasNativas.Rol) { ["name"] = "sr_mppp_supervisor" });
            }

            public Guid Usuario(string nombre, bool deshabilitado = false, bool conRol = true, bool otroRol = false)
            {
                var id = Svc.Sembrar(new Entity(TablasNativas.Usuario) { ["fullname"] = nombre, ["isdisabled"] = deshabilitado });
                if (conRol)
                {
                    Asignar(id, Rol);
                }

                if (otroRol)
                {
                    Asignar(id, Svc.Registros(TablasNativas.Rol).Single(r => (string)r["name"] == "sr_mppp_supervisor").Id);
                }

                return id;
            }

            public void Asignar(Guid usuario, Guid rol)
            {
                Svc.Sembrar(new Entity(TablasNativas.UsuarioRol) { ["systemuserid"] = new EntityReference(TablasNativas.Usuario, usuario), ["roleid"] = new EntityReference(TablasNativas.Rol, rol) });
            }

            public void Avisar(string titulo = "Correo sin procesar: solicitud MPPP-00000123", string cuerpo = "Motivo: es una respuesta.")
            {
                new AvisosDataverse(Svc).AvisarAEjecutivos(Solicitud, titulo, cuerpo);
            }
        }

        [Fact]
        public void Un_aviso_por_cada_ejecutivo_habilitado_con_numero_fijo_de_consultas()
        {
            var m = new Mundo();
            var ana = m.Usuario("Ana");
            var beto = m.Usuario("Beto", otroRol: true);
            m.Usuario("Carla", deshabilitado: true); // deshabilitada: no recibe
            m.Usuario("Dario", conRol: false, otroRol: true); // supervisor, no ejecutivo
            m.Asignar(ana, m.Rol); // el rol asignado dos veces: un solo aviso

            m.Avisar();

            var avisos = m.Svc.Registros(TablasNativas.Notificacion);
            Assert.Equal(2, avisos.Count);
            Assert.Equal(new[] { ana, beto }.OrderBy(g => g), avisos.Select(a => a.GetAttributeValue<EntityReference>("ownerid").Id).OrderBy(g => g));
            Assert.All(avisos, a => Assert.Equal(TablasNativas.Usuario, a.GetAttributeValue<EntityReference>("ownerid").LogicalName));
            Assert.All(avisos, a => Assert.Equal("Correo sin procesar: solicitud MPPP-00000123", a["title"]));
            Assert.All(avisos, a => Assert.Equal("Motivo: es una respuesta.", a["body"]));
            var consultas = m.Svc.Llamadas.Count(l => l.Operacion == "RetrieveMultiple");
            Assert.InRange(consultas, 1, 3);
        }

        [Theory]
        [InlineData(true)] // no existe el rol
        [InlineData(false)] // existe pero nadie lo tiene
        public void Sin_destinatarios_no_se_crea_nada_y_no_se_lanza(bool sinRol)
        {
            var m = new Mundo(conRol: !sinRol);
            if (!sinRol)
            {
                m.Usuario("Carla", deshabilitado: true);
            }

            m.Avisar();

            Assert.Empty(m.Svc.Registros(TablasNativas.Notificacion));
        }

        [Fact]
        public void Los_textos_se_recortan_al_largo_de_su_columna()
        {
            var m = new Mundo();
            m.Usuario("Ana");
            m.Avisar(new string('t', 500), new string('c', 5000));
            var aviso = m.Svc.Registros(TablasNativas.Notificacion).Single();
            Assert.Equal(TablasNativas.LargoTitulo, ((string)aviso["title"]).Length);
            Assert.Equal(TablasNativas.LargoCuerpo, ((string)aviso["body"]).Length);
        }

        [Fact]
        public void Un_aviso_sin_texto_o_sin_solicitud_es_un_error_de_programacion()
        {
            var m = new Mundo();
            m.Usuario("Ana");
            var avisos = new AvisosDataverse(m.Svc);
            Assert.Throws<ArgumentException>(() => avisos.AvisarAEjecutivos(Solicitud, " ", "cuerpo"));
            Assert.Throws<ArgumentException>(() => avisos.AvisarAEjecutivos(Solicitud, "titulo", null));
            Assert.Throws<ArgumentException>(() => avisos.AvisarAEjecutivos(Guid.Empty, "titulo", "cuerpo"));
            Assert.Empty(m.Svc.Llamadas);
            Assert.Throws<ArgumentNullException>(() => new AvisosDataverse(null));
        }
    }
}
