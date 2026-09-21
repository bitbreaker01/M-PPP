using System;

namespace Sanic.Mppp.Plugins.Validacion
{
    /// <summary>
    /// Arma el texto que lee el cliente del banco cuando una regla no se cumple (D-19, aprobador 2026-09-21). El catálogo trae una PLANTILLA
    /// (`sanic_mensajecliente`) que el negocio puede redactar sin tocar código; el evaluador trae su texto por defecto, los valores de los
    /// marcadores y la precisión del caso. Contrato (lo fijan las pruebas de aceptación `MensajeAlClienteAceptacion`):
    ///  - plantilla nula o en blanco → el texto por defecto del evaluador;
    ///  - un marcador es `{nombre}`, exacto (minúsculas, sin espacios); `{regla}` lo pone el motor y gana; los demás, el evaluador;
    ///  - una plantilla con CUALQUIER llave que no sea parte de un marcador que alguien sabe completar (`{plna}`, `{VALOR}`, `{ valor }`,
    ///    una `{` suelta) NO se usa: rige el texto por defecto. Un error de tipeo del negocio nunca le llega roto al cliente;
    ///  - un marcador conocido con valor nulo se completa con vacío; si el texto queda en blanco, rige el por defecto;
    ///  - los valores se insertan TAL CUAL y no se vuelven a expandir: vienen del Excel del cliente, que es hostil;
    ///  - la precisión, si hay, se agrega al final, separada por un espacio, en los dos casos;
    ///  - el resultado nunca es nulo ni en blanco.
    /// Función pura.
    /// </summary>
    public static class MensajeAlCliente
    {
        public static string Componer(string plantilla, Veredicto veredicto, string codigoDeRegla)
        {
            throw new NotImplementedException();
        }
    }
}
