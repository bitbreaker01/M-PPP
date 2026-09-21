using System;
using System.Collections.Generic;
using Sanic.Mppp.Plugins.Dominio;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>
    /// Los diez campos de una fila de la plantilla, con el nombre que llevan en `plantilla.estructura` (`campos[].nombre`), en
    /// `plantilla.obligatoriedad` y en el código. Es la ÚNICA lista: un nombre que no esté acá es un parámetro mal cargado.
    /// </summary>
    public static class CamposDeFila
    {
        public const string Gestion = "gestion";
        public const string Clasificacion = "clasificacion";
        public const string TipoIdentificacion = "tipoIdentificacion";
        public const string Moneda = "moneda";
        public const string Banco = "banco";
        public const string NumeroPlan = "numeroPlan";
        public const string NombreBeneficiario = "nombreBeneficiario";
        public const string NumeroIdentificacion = "numeroIdentificacion";
        public const string NumeroCuenta = "numeroCuenta";
        public const string Referencia = "referencia";

        /// <summary>Los diez, en el orden de arriba. Lista nueva en cada llamada.</summary>
        public static IList<string> Todos()
        {
            throw new NotImplementedException();
        }

        /// <summary>Los que se validan contra `plantilla.listas`: gestion, clasificacion, tipoIdentificacion, moneda y banco.</summary>
        public static IList<string> DeLista()
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>Un valor aceptado de una lista, ya resuelto.</summary>
    public sealed class ValorDeLista
    {
        public ValorDeLista(string valor, string codigoDeBanco)
        {
            Valor = valor;
            CodigoDeBanco = codigoDeBanco;
        }

        /// <summary>El valor canónico: es EXACTAMENTE el nombre del miembro del enum del choice (`Inclusion`, `ACH`, `USD`, `BAC`, `CNA`).</summary>
        public string Valor { get; }

        /// <summary>Solo en la lista de bancos: el código de 3 dígitos (DD-10). En las demás, nulo.</summary>
        public string CodigoDeBanco { get; }
    }

    /// <summary>
    /// Parámetro `plantilla.listas` (D-18a, aprobador 2026-09-21). Forma:
    /// {"gestion":[{"valor":"Inclusion","variantes":["inclusión","alta"]}],"clasificacion":[…],"tipoIdentificacion":[…],"moneda":[…],
    ///  "banco":[{"valor":"BAC","codigo":"102","variantes":["bac credomatic"]}]}
    /// Las claves son los nombres de <see cref="CamposDeFila.DeLista"/>. La comparación no distingue mayúsculas, tildes (ni ñ de n),
    /// ni espacios al inicio y al final, y trata varios espacios seguidos como uno. Las variantes son EXPLÍCITAS: nada de parecidos.
    /// Un parámetro mal cargado es <see cref="FormatException"/> con el motivo (nunca una lista "vacía pero válida"):
    /// JSON ilegible; falta una de las cinco listas o está vacía; un `valor` que no es el nombre exacto de un miembro del enum de
    /// su choice; un `valor` repetido; una variante (o un valor) que, normalizada, apunta a DOS valores distintos de la misma lista;
    /// una variante en blanco; un banco sin `codigo` de exactamente 3 dígitos ASCII; dos bancos con el mismo código.
    /// NO usa System.Text.Json: DataContractJsonSerializer.
    /// </summary>
    public sealed class ListasPlantilla
    {
        private ListasPlantilla()
        {
        }

        public static ListasPlantilla DesdeJson(string json)
        {
            throw new NotImplementedException();
        }

        /// <summary>
        /// El valor aceptado que corresponde a lo que escribió el cliente, o nulo si no corresponde a ninguno (también si vino
        /// nulo o en blanco). <paramref name="lista"/> es uno de <see cref="CamposDeFila.DeLista"/>; otro nombre es
        /// <see cref="ArgumentException"/>.
        /// </summary>
        public ValorDeLista Resolver(string lista, string recibido)
        {
            throw new NotImplementedException();
        }

        /// <summary>La forma en que se comparan dos textos de lista: minúsculas invariantes, sin tildes, sin espacios a los lados, espacios internos de a uno. Nulo → vacío.</summary>
        public static string Normalizar(string texto)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// Parámetro `plantilla.obligatoriedad` (D-18c): una lista de excepciones sobre "todo obligatorio". Forma:
    /// {"porDefecto":"obligatorio","opcionales":[{"campo":"referencia"}],
    ///  "reglas":[{"gestion":"Exclusion","clasificacion":"*","formato":"*","opcionales":["moneda","banco"]}]}
    /// `gestion` y `clasificacion`: nombre exacto del miembro del enum, o `*`. `formato`: `06`, `10`, `11` o `*`. Los campos son
    /// de <see cref="CamposDeFila.Todos"/>. `reglas` puede faltar o venir vacía; `opcionales` también.
    /// <see cref="FormatException"/> con el motivo si: JSON ilegible; `porDefecto` distinto de `obligatorio` (es lo único que
    /// existe hoy: otra cosa no se interpreta); un campo, gestión, clasificación o formato desconocido; una regla sin alguna de
    /// sus tres dimensiones; una regla sin opcionales.
    /// </summary>
    public sealed class ObligatoriedadPlantilla
    {
        private ObligatoriedadPlantilla()
        {
        }

        public static ObligatoriedadPlantilla DesdeJson(string json)
        {
            throw new NotImplementedException();
        }

        /// <summary>
        /// Los campos que NO son obligatorios para esa combinación: los opcionales generales más los de TODAS las reglas que
        /// calzan. Una dimensión desconocida (nulo: el valor de la fila no era válido, o el plan no existe) solo calza con `*`:
        /// ante la duda, obligatorio. Conjunto nuevo en cada llamada.
        /// </summary>
        public ISet<string> CamposOpcionales(Gestion? gestion, Clasificacion? clasificacion, TipoDeFormatoDelPlan? formato)
        {
            throw new NotImplementedException();
        }
    }
}
