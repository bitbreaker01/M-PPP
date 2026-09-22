using System;
using System.Collections.Generic;

namespace Sanic.Mppp.Plugins.Steps
{
    /// <summary>
    /// La lista blanca de columnas (diseno/04 §1; diseno/03 §5): `W` en Dataverse es sobre la fila entera, así que el control de
    /// qué puede tocar una persona es este step, no el formulario. Contrato (lo fijan las pruebas `ReglasDeStepsAceptacion`):
    ///  - en Fila una persona solo puede mandar `sanic_estado` y `sanic_mensaje`; en Solicitud, `sanic_requiererevision` y
    ///    `sanic_estadoprocesamiento`;
    ///  - una tabla que no está en la lista no se controla acá (el step no se registra sobre ella): devuelve vacío;
    ///  - los nombres de columna se comparan como los manda Dataverse (minúscula, ordinal);
    ///  - devuelve TODAS las columnas no permitidas, ordenadas, para que el mensaje del error las nombre a todas;
    ///  - la columna primaria (`<tabla>id`) que el SDK incluye en el `Target` no cuenta como intento de escritura.
    /// </summary>
    public static class ListaBlancaDeColumnas
    {
        public const string Fila = "sanic_mppp_tbl_fila";
        public const string Solicitud = "sanic_mppp_tbl_solicitud";

        /// <summary>Las columnas del `Target` que esa tabla NO admite de una persona. Vacío si todo está permitido.</summary>
        public static IList<string> ColumnasNoPermitidas(string tabla, IEnumerable<string> columnasDelTarget)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// Normalización y validación de los catálogos antes de guardarlos (diseno/03 §5; diseno/02 §2.1, §2.2, §2.3, §2.5).
    /// Cada método devuelve el valor YA normalizado, o lanza <see cref="ArgumentException"/> con un motivo para quien está
    /// cargando el catálogo (lo lee una persona en la app, no un cliente del banco). Un valor nulo o en blanco no se normaliza:
    /// devuelve nulo, y que sea obligatorio lo exige la plataforma con la columna requerida.
    /// </summary>
    public static class Normalizacion
    {
        /// <summary>`sanic_cifbac`: solo dígitos ASCII, relleno con ceros a la izquierda hasta 9. Más de 9 dígitos, o algo que no sea dígito, es error.</summary>
        public static string CifBac(string valor)
        {
            throw new NotImplementedException();
        }

        /// <summary>`sanic_cifcom`: en mayúscula; tiene que quedar `^[A-Z0-9 ]{9}\d{3}$` (12 caracteres exactos).</summary>
        public static string CifCom(string valor)
        {
            throw new NotImplementedException();
        }

        /// <summary>`sanic_codigo` de Plan: en mayúscula y relleno con ceros a la izquierda hasta 4; tiene que quedar `^[A-Z0-9]{4}$`.</summary>
        public static string CodigoDePlan(string valor)
        {
            throw new NotImplementedException();
        }

        /// <summary>`sanic_nombre` de Autorizado: sin espacios a los lados y en minúscula; tiene que tener forma de correo (algo@algo.algo, sin espacios ni dos arrobas).</summary>
        public static string CorreoAutorizado(string valor)
        {
            throw new NotImplementedException();
        }

        /// <summary>`sanic_nombre` de Parametro: en minúscula, sin espacios a los lados; solo letras ASCII, dígitos y puntos, sin puntos al principio, al final ni repetidos.</summary>
        public static string NombreDeParametro(string valor)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// Los nombres calculados que llena un step PreOperation en el `Create` (diseno/03 §5; diseno/02). No aplica a Autorizado ni
    /// a Parametro, donde la primaria es la clave de negocio (BP-PP-192). Cada uno se recorta al largo de su columna.
    /// </summary>
    public static class NombreCalculado
    {
        /// <summary>Plan: `<codigo> - <cliente>`, T(100). Sin nombre de cliente, solo el código.</summary>
        public static string DePlan(string codigo, string nombreDelCliente)
        {
            throw new NotImplementedException();
        }

        /// <summary>AutorizacionPlan: `<correo> → <plan>`, T(400).</summary>
        public static string DeAutorizacionPlan(string correo, string codigoDePlan)
        {
            throw new NotImplementedException();
        }

        /// <summary>Fila: `<solicitud>-F<nn>`, T(120), con el número de fila en dos dígitos como mínimo.</summary>
        public static string DeFila(string numeroDeSolicitud, int numeroDeFila)
        {
            throw new NotImplementedException();
        }
    }
}
