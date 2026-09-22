using System;
using System.Collections.Generic;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Respuesta
{
    /// <summary>
    /// Enmascarado de datos sensibles para lo que viaja por correo (DD-08: "nunca se devuelven identificación ni cuenta
    /// completas; la cuenta va enmascarada a 4 dígitos"). Una sola regla para los dos: se conservan los ÚLTIMOS CUATRO
    /// caracteres y el resto se reemplaza por asteriscos, uno por carácter (`123456789` → `*****6789`). Con cuatro caracteres o
    /// menos se enmascara todo (`****`, tantos como caracteres haya). Nulo o vacío → vacío. Se enmascara lo recibido tal cual,
    /// sin recortar ni limpiar: lo que se ve son siempre 4 caracteres, sean los que sean.
    /// </summary>
    public static class Enmascarado
    {
        public static string Cuenta(string numeroCuenta)
        {
            throw new NotImplementedException();
        }

        public static string Identificacion(string numeroIdentificacion)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>Lo que el acuse y la respuesta final muestran de cada fila. Sin SDK. Los datos vienen como están en `sanic_mppp_tbl_fila`.</summary>
    public sealed class FilaParaRespuesta
    {
        /// <summary>`sanic_numerofila`.</summary>
        public int NumeroFila { get; set; }

        /// <summary>El número de plan como lo escribió el cliente (`sanic_numeroplan` si se normalizó; si no, lo recibido). Puede ser nulo.</summary>
        public string NumeroPlan { get; set; }

        public string NombreBeneficiario { get; set; }

        /// <summary>COMPLETO, como está en la Fila: el armador lo enmascara. Nunca sale entero.</summary>
        public string NumeroCuenta { get; set; }

        /// <summary>COMPLETO, como está en la Fila: el armador lo enmascara. Nunca sale entero.</summary>
        public string NumeroIdentificacion { get; set; }

        public EstadoDeLaFila Estado { get; set; }

        /// <summary>`sanic_mensaje`: los motivos, ya redactados para el cliente. Puede ser nulo (fila sin motivos).</summary>
        public string Mensaje { get; set; }
    }

    /// <summary>Lo que el armador necesita de la Solicitud. Sin SDK.</summary>
    public sealed class SolicitudParaRespuesta
    {
        /// <summary>`sanic_nombre` (`MPPP-00000123`): la referencia que el cliente puede citar.</summary>
        public string Numero { get; set; }

        /// <summary>La fecha de recibido YA formateada para el cliente (la zona horaria la resuelve quien llama). Puede ser nula.</summary>
        public string FechaRecibidoTexto { get; set; }

        public EstadoDeLaSolicitud Estado { get; set; }

        /// <summary>Motivos de las reglas del sobre que fallaron (Razon de cada NoCumplida con efecto Rechaza), en orden. Vacío si el sobre pasó.</summary>
        public IList<string> MotivosDelSobre { get; set; }

        /// <summary>Las filas, en cualquier orden: el armador las ordena por número. Vacío si el sobre falló antes de leer.</summary>
        public IList<FilaParaRespuesta> Filas { get; set; }
    }

    /// <summary>
    /// Arma el cuerpo HTML de las dos comunicaciones al cliente (DD-08): el ACUSE al terminar la validación (diseno/03 §1
    /// pasos 4 y 7; DD-09) y la RESPUESTA FINAL al terminar el procesamiento (diseno/03 §4 "Cierre"). Función pura. Contrato
    /// (lo fijan las pruebas `ArmadorRespuestaAceptacion`):
    ///  - HTML completo y autocontenido (sin scripts, estilos externos ni imágenes), en español, con el número de la solicitud;
    ///  - TODO texto que venga del cliente o de las filas se escapa (el Excel es hostil): nunca sale una etiqueta sin escapar;
    ///  - la cuenta y la identificación salen SIEMPRE por <see cref="Enmascarado"/>; el valor completo no aparece nunca;
    ///  - las filas van en una tabla ordenada por número, con su estado en palabras del cliente y sus motivos;
    ///  - acuse de una Solicitud Rechazada (por el sobre o porque ninguna fila quedó Validada): texto de DD-09, expreso:
    ///    no hay nada que procesar, no recibirá otro correo por esta solicitud, corrija y reenvíe;
    ///  - acuse de una En proceso: las Validadas se procesan, las demás no, y recibirá una respuesta final;
    ///  - respuesta final de una Procesada: qué se hizo (Aprobada), qué no y por qué (Rechazada en AS400, Anulada, y las que
    ///    ya venían rechazadas de la validación);
    ///  - un estado que no corresponde a esa comunicación es un error de programación (<see cref="ArgumentException"/>).
    /// </summary>
    public static class ArmadorRespuesta
    {
        /// <summary>Palabras del cliente para cada estado de fila, sin códigos ni jerga.</summary>
        public static string EstadoParaElCliente(EstadoDeLaFila estado)
        {
            throw new NotImplementedException();
        }

        public static string Acuse(SolicitudParaRespuesta solicitud)
        {
            throw new NotImplementedException();
        }

        public static string RespuestaFinal(SolicitudParaRespuesta solicitud)
        {
            throw new NotImplementedException();
        }
    }
}
