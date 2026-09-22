using System;
using System.Linq;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Tests.Apoyo;
using Xunit;

namespace Sanic.Mppp.Plugins.Tests.Aceptacion
{
    /// <summary>7.6 Datos: descarga de columnas de archivo por bloques (LP-02: el tamaño se controla ANTES de bajar nada).</summary>
    public class ArchivosDataverseAceptacion
    {
        private static readonly Guid Id = Guid.NewGuid();

        private static byte[] Bytes(int n) => Enumerable.Range(0, n).Select(i => (byte)(i % 251)).ToArray();

        [Theory]
        [InlineData(0, 0)]
        [InlineData(1, 1)]
        [InlineData(ArchivosDataverse.TamanoDeBloque, 1)]
        [InlineData(ArchivosDataverse.TamanoDeBloque + 1, 2)]
        [InlineData(3 * ArchivosDataverse.TamanoDeBloque + 17, 4)]
        public void Descarga_completa_en_bloques_de_cuatro_mega_en_orden_con_una_sola_inicializacion(int tamano, int bloquesEsperados)
        {
            var archivo = Bytes(tamano);
            var svc = new ServicioDeArchivosSimulado(archivo);

            var leido = new ArchivosDataverse(svc).Descargar("sanic_mppp_tbl_solicitud", Id, "sanic_exceloriginal", 20L * 1024 * 1024);

            Assert.Equal(archivo, leido);
            Assert.Equal(1, svc.Inicializaciones);
            Assert.Equal(("sanic_mppp_tbl_solicitud", Id, "sanic_exceloriginal"), svc.UltimoObjetivo);
            Assert.Equal(bloquesEsperados, svc.Bloques.Count);
            long offset = 0;
            foreach (var (o, largo) in svc.Bloques)
            {
                Assert.Equal(offset, o);
                Assert.Equal(Math.Min(ArchivosDataverse.TamanoDeBloque, tamano - offset), largo);
                offset += largo;
            }
        }

        [Fact]
        public void Un_archivo_mas_pesado_que_el_maximo_no_baja_ni_un_bloque()
        {
            var svc = new ServicioDeArchivosSimulado(Bytes(10), tamanoAnunciado: 3_000_000);
            var ex = Assert.Throws<ArchivoExcedeElMaximoException>(() => new ArchivosDataverse(svc).Descargar("t", Id, "c", 2_000_000));
            Assert.Equal((3_000_000L, 2_000_000L), (ex.TamanoBytes, ex.MaximoBytes));
            Assert.Empty(svc.Bloques);
            Assert.Equal(1, svc.Inicializaciones);
            // Justo en el máximo entra.
            Assert.Equal(10, new ArchivosDataverse(new ServicioDeArchivosSimulado(Bytes(10))).Descargar("t", Id, "c", 10).Length);
        }

        [Fact]
        public void Menos_bytes_que_los_anunciados_es_un_archivo_truncado_y_no_se_procesa()
        {
            var svc = new ServicioDeArchivosSimulado(Bytes(100), tamanoAnunciado: 150);
            Assert.Throws<InvalidOperationException>(() => new ArchivosDataverse(svc).Descargar("t", Id, "c", 1000));
        }

        [Theory]
        [InlineData(1000, 256, 256)] // solo el inicio
        [InlineData(100, 256, 100)] // el archivo es más chico: todo, sin fallar
        [InlineData(0, 256, 0)]
        public void El_inicio_baja_un_solo_bloque_de_a_lo_sumo_el_maximo(int tamano, int maximo, int esperado)
        {
            var archivo = Bytes(tamano);
            var svc = new ServicioDeArchivosSimulado(archivo);

            var inicio = new ArchivosDataverse(svc).DescargarInicio("sanic_mppp_tbl_solicitud", Id, "sanic_correocrudo", maximo);

            Assert.Equal(archivo.Take(esperado), inicio);
            Assert.True(svc.Bloques.Count <= 1);
            if (svc.Bloques.Count == 1)
            {
                Assert.Equal(0, svc.Bloques[0].offset);
                Assert.True(svc.Bloques[0].largo <= maximo);
            }
        }

        [Fact]
        public void El_inicio_de_un_archivo_enorme_no_falla_por_tamano_ni_baja_de_mas()
        {
            var svc = new ServicioDeArchivosSimulado(Bytes(1000), tamanoAnunciado: 25L * 1024 * 1024);
            var inicio = new ArchivosDataverse(svc).DescargarInicio("t", Id, "c", 512);
            Assert.Equal(512, inicio.Length);
            Assert.Single(svc.Bloques);
        }

        [Fact]
        public void Los_argumentos_se_validan_antes_de_tocar_el_servicio()
        {
            var svc = new ServicioDeArchivosSimulado(Bytes(10));
            var archivos = new ArchivosDataverse(svc);
            Assert.Throws<ArgumentException>(() => archivos.Descargar(" ", Id, "c", 10));
            Assert.Throws<ArgumentException>(() => archivos.Descargar("t", Guid.Empty, "c", 10));
            Assert.Throws<ArgumentException>(() => archivos.Descargar("t", Id, null, 10));
            Assert.Throws<ArgumentException>(() => archivos.Descargar("t", Id, "c", 0));
            Assert.Throws<ArgumentException>(() => archivos.DescargarInicio("t", Id, "c", -1));
            Assert.Equal(0, svc.Inicializaciones);
            Assert.Throws<ArgumentNullException>(() => new ArchivosDataverse(null));
        }
    }
}
