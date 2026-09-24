using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Sanic.Mppp.Plugins.Datos;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// 7.10 (parte que faltaba, detectada el 2026-09-22): integridad del catálogo de Reglas. `Create` y `Update` de
    /// `sanic_mppp_tbl_regla`, PreOperation, síncrono; el `Update` lleva **pre-image** con `sanic_codigo`, `sanic_nivel`,
    /// `sanic_orden`, `sanic_dependede`, `sanic_efecto` y `statecode`.
    ///
    /// Por qué existe: el motor ya valida el catálogo en tiempo de ejecución y **falla cerrado**
    /// (<see cref="Validacion.ConfiguracionDeReglasInvalidaException"/>), así que un catálogo mal armado no corrompe nada.
    /// Pero sin este step, quien edita una regla en la app guarda sin error y rompe la validación de TODAS las solicitudes
    /// que entren hasta que alguien se dé cuenta. Este step convierte ese incidente en un mensaje al guardar.
    ///
    /// Contrato (lo fijan las pruebas `IntegridadDeReglaAceptacion`):
    ///  - la regla que se está guardando se arma mezclando la **pre-image con el `Target`** (en `Create` no hay pre-image):
    ///    así un `Update` parcial, que solo trae una columna, igual se valida ENTERO;
    ///  - corre para todos, **también para código de servidor**: el catálogo lo carga una persona o una migración, y un
    ///    catálogo mal armado tumba la validación de todas las solicitudes;
    ///  - **código con evaluador** (D-13): `sanic_codigo` tiene que tener un evaluador en el código Y del mismo nivel. Si no,
    ///    se rechaza nombrando los códigos válidos de ese nivel;
    ///  - **efecto según nivel** (D-20): `Envía a revisión` solo vale en Correo y Solicitud, **nunca** en Registro;
    ///  - **AUTORIZACION_CORREO_PLAN** (D-14): no admite otro efecto que `Rechaza`;
    ///  - **dependencias** (`02` §152): cada código de `sanic_dependede` tiene que existir como regla **activa**, ser del
    ///    **mismo nivel** y tener `sanic_orden` **estrictamente menor**. Una regla no puede depender de sí misma. El orden
    ///    estrictamente menor es lo que hace imposible un ciclo;
    ///  - **desactivar** (D-13): pasar `statecode` a Inactiva se rechaza si alguna regla **activa** del mismo nivel depende
    ///    de ella, y el mensaje **nombra quién depende**;
    ///  - `sanic_dependede` se parte por coma, tolerando espacios alrededor; las entradas vacías se ignoran. La comparación
    ///    es por código COMPLETO, nunca por subcadena: `PLAN_EXISTE` no cuenta como dependida por `PLAN_EXISTE_OTRO`;
    ///  - **una sola consulta** a Dataverse: las reglas activas del mismo nivel, una vez;
    ///  - un `Target` que no es de esta tabla no hace nada; un proveedor incompleto es
    ///    <see cref="InvalidPluginExecutionException"/>, nunca <see cref="NullReferenceException"/>;
    ///  - los mensajes los lee un **administrador técnico**, no un cliente del banco: pueden nombrar códigos y columnas.
    /// </summary>
    public sealed class IntegridadDeReglaStep : IPlugin
    {
        private const string Codigo = "sanic_codigo";
        private const string Nivel = "sanic_nivel";
        private const string Orden = "sanic_orden";
        private const string DependeDe = "sanic_dependede";
        private const string Efecto = "sanic_efecto";
        private const string Estado = "statecode";

        public void Execute(IServiceProvider serviceProvider)
        {
            if (!PlomeriaDePlataforma.Preparar(serviceProvider, out var contexto, out var servicio, out var target))
            {
                return;
            }

            if (!string.Equals(target.LogicalName, Tablas.Regla, StringComparison.Ordinal))
            {
                return;
            }

            // La regla que se está guardando se arma mezclando el Target con la pre-image: el Target pisa, lo que no
            // trae sale de la pre-image (en Create no hay pre-image, así que todo sale del Target).
            var codigo = ColumnaTexto(contexto, target, Codigo);
            var nivel = ColumnaNivel(contexto, target, Nivel);
            var orden = ColumnaEntero(contexto, target, Orden);
            var dependeDe = SepararDependeDe(ColumnaTexto(contexto, target, DependeDe));
            var efecto = ColumnaEfecto(contexto, target, Efecto);
            var estado = ColumnaEstado(contexto, target, Estado);

            // D-13: sanic_codigo tiene que tener un evaluador en el código, del mismo nivel.
            var codigosValidos = CodigosValidosDelNivel(nivel);
            if (codigo == null || !codigosValidos.Contains(codigo))
            {
                throw new InvalidPluginExecutionException(
                    $"No se puede guardar la regla: el código '{codigo}' no tiene un evaluador programado para el nivel '{nivel}'. " +
                    $"Los códigos válidos de ese nivel son: {string.Join(", ", codigosValidos)}.");
            }

            // D-20: "Envía a revisión" solo vale en Correo y Solicitud, nunca en Registro.
            if (nivel == NivelDeLaRegla.Registro && efecto == EfectoDeLaRegla.EnviaARevision)
            {
                throw new InvalidPluginExecutionException(
                    $"No se puede guardar la regla '{codigo}': el efecto 'Envía a revisión' no está permitido en el nivel Registro.");
            }

            // D-14: AUTORIZACION_CORREO_PLAN no admite otro efecto que Rechaza.
            if (string.Equals(codigo, Validacion.ReglasDeRegistro.AutorizacionCorreoPlan, StringComparison.Ordinal)
                && efecto != EfectoDeLaRegla.Rechaza)
            {
                throw new InvalidPluginExecutionException(
                    $"No se puede guardar la regla '{codigo}': solo admite el efecto 'Rechaza'.");
            }

            var vaADesactivarse = estado != Tablas.Activo;

            if (dependeDe.Count == 0 && !vaADesactivarse)
            {
                // Nada que consultar: ni dependencias propias que validar, ni una desactivación que revisar.
                return;
            }

            // Una sola consulta a Dataverse por ejecución: las reglas activas del mismo nivel.
            var catalogo = new CatalogosDataverse(servicio).ReglasActivasConId(nivel);

            // Dependencias: cada código de sanic_dependede tiene que existir como regla activa del mismo nivel, con
            // sanic_orden estrictamente menor.
            foreach (var codigoDependido in dependeDe)
            {
                // La autodependencia se rechaza por el CÓDIGO, antes de mirar ningún orden. No alcanza con confiar en
                // el chequeo de "orden estrictamente menor" (revisión de código, 2026-09-22): `catalogo` trae el estado
                // YA COMMITTEADO, o sea el orden VIEJO de esta misma regla. Si un solo Update sube el orden Y agrega la
                // autodependencia —editar dos celdas en una grilla y guardar—, la comparación sería "orden viejo >=
                // orden nuevo", daría false, y se guardaría un ciclo de tamaño uno que después tumba el motor.
                if (string.Equals(codigoDependido, codigo, StringComparison.Ordinal))
                {
                    throw new InvalidPluginExecutionException(
                        $"No se puede guardar la regla '{codigo}': no puede depender de sí misma.");
                }

                var encontrada = catalogo.FirstOrDefault(r => string.Equals(r.Definicion.Codigo, codigoDependido, StringComparison.Ordinal));
                if (encontrada == null)
                {
                    throw new InvalidPluginExecutionException(
                        $"No se puede guardar la regla '{codigo}': depende de '{codigoDependido}', que no existe como regla activa del nivel '{nivel}'.");
                }

                if (encontrada.Definicion.Orden >= orden)
                {
                    throw new InvalidPluginExecutionException(
                        $"No se puede guardar la regla '{codigo}' (orden {orden}): depende de '{codigoDependido}' (orden {encontrada.Definicion.Orden}), " +
                        "que no tiene un orden estrictamente menor.");
                }
            }

            // Desactivar: si alguna regla activa del mismo nivel (distinta de esta) depende de esta, no se puede.
            if (vaADesactivarse)
            {
                var dependientes = catalogo
                    .Where(r => r.Id != target.Id)
                    .Where(r => r.Definicion.DependeDe.Any(d => string.Equals(d, codigo, StringComparison.Ordinal)))
                    .Select(r => r.Definicion.Codigo)
                    .ToList();

                if (dependientes.Count > 0)
                {
                    throw new InvalidPluginExecutionException(
                        $"No se puede desactivar la regla '{codigo}': depende(n) de ella la(s) regla(s) activa(s) {string.Join(", ", dependientes)}.");
                }
            }
        }

        /// <summary>El valor de una columna de texto: del Target si lo trae, si no de la primera pre-image que lo trae
        /// (mismo criterio que <see cref="PlomeriaDeFila.ImagenQueTrae"/>, sin exigir que exista).</summary>
        private static string ColumnaTexto(IPluginExecutionContext contexto, Entity target, string columna)
        {
            return ValorDeColumna(contexto, target, columna) as string;
        }

        private static NivelDeLaRegla ColumnaNivel(IPluginExecutionContext contexto, Entity target, string columna)
        {
            return ValorDeColumna(contexto, target, columna) is OptionSetValue opcion ? (NivelDeLaRegla)opcion.Value : default;
        }

        private static EfectoDeLaRegla ColumnaEfecto(IPluginExecutionContext contexto, Entity target, string columna)
        {
            return ValorDeColumna(contexto, target, columna) is OptionSetValue opcion ? (EfectoDeLaRegla)opcion.Value : default;
        }

        private static int ColumnaEntero(IPluginExecutionContext contexto, Entity target, string columna)
        {
            return ValorDeColumna(contexto, target, columna) is int valor ? valor : default;
        }

        private static int ColumnaEstado(IPluginExecutionContext contexto, Entity target, string columna)
        {
            return ValorDeColumna(contexto, target, columna) is OptionSetValue opcion ? opcion.Value : Tablas.Activo;
        }

        private static object ValorDeColumna(IPluginExecutionContext contexto, Entity target, string columna)
        {
            if (target.Contains(columna))
            {
                return target[columna];
            }

            foreach (var imagen in contexto.PreEntityImages.Values)
            {
                if (imagen != null && imagen.Contains(columna))
                {
                    return imagen[columna];
                }
            }

            return null;
        }

        /// <summary>Los códigos con evaluador programado para ese nivel: cada nivel tiene su propio tipo de evaluador,
        /// así que se proyecta cada uno a `string` por separado.</summary>
        private static ISet<string> CodigosValidosDelNivel(NivelDeLaRegla nivel)
        {
            switch (nivel)
            {
                case NivelDeLaRegla.Correo:
                    return new HashSet<string>(Api.ReglasDelCorreo.Evaluadores().Select(e => e.Codigo), StringComparer.Ordinal);
                case NivelDeLaRegla.Solicitud:
                    return new HashSet<string>(Validacion.ReglasDelSobre.Evaluadores().Select(e => e.Codigo), StringComparer.Ordinal);
                case NivelDeLaRegla.Registro:
                    return new HashSet<string>(Validacion.ReglasDeRegistro.Evaluadores().Select(e => e.Codigo), StringComparer.Ordinal);
                default:
                    return new HashSet<string>(StringComparer.Ordinal);
            }
        }

        /// <summary>Parte por coma, recorta espacios y descarta entradas vacías. Nulo o en blanco: lista vacía.</summary>
        private static IList<string> SepararDependeDe(string crudo)
        {
            if (string.IsNullOrWhiteSpace(crudo))
            {
                return new List<string>();
            }

            return crudo.Split(',')
                .Select(parte => parte.Trim())
                .Where(parte => parte.Length > 0)
                .ToList();
        }
    }
}
