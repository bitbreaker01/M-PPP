using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using Microsoft.Xrm.Sdk;

namespace Sanic.Mppp.Plugins.Zzspikec05
{
    /// <summary>
    /// Backing plugin de la Custom API unica del spike C-05 parte B
    /// (sanic_mppp_capi_zzspikec05). Dispatch por el parametro "modo":
    ///
    ///   lector      -> abre con Open XML SDK el contenido de "excelbase64" (base64 de un
    ///                  .xlsx), ubica la hoja "Datos" y lee las filas desde la 13 en
    ///                  adelante. Responde las preguntas 1 (carga el SDK?) y 2 (tiempo).
    ///   atomicidad  -> crea un registro marcador en sanic_mppp_tbl_zzspike (con el nombre
    ///                  recibido en "excelbase64", reusado aqui como texto libre) y despues
    ///                  lanza una excepcion deliberada. Responde la pregunta 4.
    ///   actor       -> hace un Update con el servicio de SYSTEM sobre el registro
    ///                  "zzspikeid", lo que dispara ActorCaptureStep (PreOperation de
    ///                  Update). Responde la pregunta 5.
    ///   actorusuario -> igual que "actor" pero el Update lo hace con el servicio del
    ///                  usuario que llama (CreateOrganizationService(context.UserId)), no
    ///                  SYSTEM. Variante de control de la pregunta 5 bis (punto 4).
    ///
    /// Este dispatch por modo es una decision de mecanica del spike (no de producto): el
    /// contrato real de sanic_mppp_capi_validarsolicitud (diseno/03) no tiene "modo".
    /// </summary>
    public class SpikeApi : PluginBase
    {
        private const string TablaZzSpike = "sanic_mppp_tbl_zzspike";
        private const string HojaEsperada = "Datos";
        private const int PrimeraFilaDatos = 13;

        public SpikeApi(string unsecureConfiguration, string secureConfiguration)
            : base(typeof(SpikeApi))
        {
        }

        protected override void ExecuteDataversePlugin(ILocalPluginContext localPluginContext)
        {
            if (localPluginContext == null)
            {
                throw new ArgumentNullException(nameof(localPluginContext));
            }

            IPluginExecutionContext context = localPluginContext.PluginExecutionContext;

            if (!context.InputParameters.TryGetValue("modo", out object modoObj) || !(modoObj is string modo) || string.IsNullOrWhiteSpace(modo))
            {
                throw new InvalidPluginExecutionException("SPIKE: falta el parametro 'modo' (lector | atomicidad | actor).");
            }

            switch (modo)
            {
                case "lector":
                    EjecutarLector(localPluginContext, context);
                    return;
                case "atomicidad":
                    EjecutarAtomicidad(localPluginContext, context);
                    return;
                case "actor":
                    EjecutarActor(localPluginContext, context, usarSystem: true);
                    return;
                case "actorusuario":
                    EjecutarActor(localPluginContext, context, usarSystem: false);
                    return;
                default:
                    throw new InvalidPluginExecutionException($"SPIKE: modo desconocido '{modo}'.");
            }
        }

        // Pregunta 1 (LA pregunta) y pregunta 2 (tiempo). Frontera de confianza unica con el
        // SDK de terceros (mismo patron que LP-01 en diseno/03 #7, aunque esta API no
        // implementa las reglas LP completas: alcanza con abrir el libro y leer la ventana).
        private void EjecutarLector(ILocalPluginContext localPluginContext, IPluginExecutionContext context)
        {
            if (!context.InputParameters.TryGetValue("excelbase64", out object excelObj) || !(excelObj is string excelBase64) || string.IsNullOrEmpty(excelBase64))
            {
                throw new InvalidPluginExecutionException("SPIKE lector: falta el parametro 'excelbase64'.");
            }

            // Ventana explicita (LP-04 simplificado): sin esto, la plantilla real se lee
            // completa hasta su ultima fila con formato (cientos de filas en blanco), no los
            // "25 filas" que pide la pregunta 2. -1 (o ausente) = sin tope, para depurar.
            int? cantidadFilas = null;
            if (context.InputParameters.TryGetValue("cantidadfilas", out object cantidadObj) && cantidadObj is int cantidadInt && cantidadInt > 0)
            {
                cantidadFilas = cantidadInt;
            }

            localPluginContext.Trace($"SPIKE lector: decodificando base64 y abriendo con Open XML SDK (ventana={(cantidadFilas.HasValue ? cantidadFilas.Value.ToString() : "sin tope")})");

            var cronometro = Stopwatch.StartNew();
            int filasLeidas;
            int celdasTocadas = 0;

            try
            {
                byte[] bytes = Convert.FromBase64String(excelBase64);

                using (var memoria = new MemoryStream(bytes))
                using (SpreadsheetDocument documento = SpreadsheetDocument.Open(memoria, isEditable: false))
                {
                    WorkbookPart workbookPart = documento.WorkbookPart;
                    Sheet hojaDatos = workbookPart.Workbook.Descendants<Sheet>()
                        .FirstOrDefault(s => s.Name != null
                            && string.Equals(s.Name.Value.Trim(), HojaEsperada, StringComparison.OrdinalIgnoreCase));

                    if (hojaDatos == null)
                    {
                        throw new InvalidOperationException($"no se encontro la hoja '{HojaEsperada}'");
                    }

                    var worksheetPart = (WorksheetPart)workbookPart.GetPartById(hojaDatos.Id);
                    SheetData sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>();
                    SharedStringTable sst = workbookPart.SharedStringTablePart?.SharedStringTable;

                    filasLeidas = 0;
                    uint ultimaFilaVentana = cantidadFilas.HasValue
                        ? (uint)(PrimeraFilaDatos + cantidadFilas.Value - 1)
                        : uint.MaxValue;

                    foreach (Row fila in sheetData.Elements<Row>())
                    {
                        if (fila.RowIndex == null || fila.RowIndex.Value < PrimeraFilaDatos)
                        {
                            continue;
                        }

                        if (fila.RowIndex.Value > ultimaFilaVentana)
                        {
                            break;
                        }

                        filasLeidas++;

                        // Materializa de verdad (no solo cuenta filas): toca cada celda de la
                        // fila para que el tiempo medido incluya el costo real de leer valores,
                        // no solo de recorrer la estructura.
                        foreach (Cell celda in fila.Elements<Cell>())
                        {
                            ValorDeCelda(celda, sst);
                            celdasTocadas++;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                // Frontera unica con el SDK de terceros: cualquier excepcion (de formato, de
                // Open XML, de I/O) se reporta como error del archivo, nunca se propaga cruda.
                throw new InvalidPluginExecutionException($"SPIKE lector: archivo invalido o SDK no disponible: {ex.GetType().Name}: {ex.Message}", ex);
            }

            cronometro.Stop();

            context.OutputParameters["resultado"] =
                $"lector OK: {filasLeidas} filas leidas desde '{HojaEsperada}' (fila {PrimeraFilaDatos} en adelante), {celdasTocadas} celdas tocadas";
            context.OutputParameters["milisegundos"] = (int)cronometro.ElapsedMilliseconds;

            localPluginContext.Trace($"SPIKE lector: {filasLeidas} filas, {cronometro.ElapsedMilliseconds} ms");
        }

        private static string ValorDeCelda(Cell celda, SharedStringTable sst)
        {
            if (celda == null)
            {
                return null;
            }

            if (celda.DataType != null && celda.DataType.Value == CellValues.InlineString)
            {
                return celda.InlineString?.Text?.Text;
            }

            if (celda.CellValue == null)
            {
                return null;
            }

            string texto = celda.CellValue.InnerText;

            if (celda.DataType != null && celda.DataType.Value == CellValues.SharedString && sst != null)
            {
                if (int.TryParse(texto, out int indice))
                {
                    var item = sst.ElementAtOrDefault(indice) as SharedStringItem;
                    return item?.InnerText;
                }
            }

            return texto;
        }

        // Pregunta 4: atomicidad. Crea un registro marcador y despues lanza una excepcion
        // deliberada. Si diseno/03 #1 paso 2 tiene razon, el Create se revierte con la
        // transaccion: medir.py comprueba esto consultando el marcador despues.
        private void EjecutarAtomicidad(ILocalPluginContext localPluginContext, IPluginExecutionContext context)
        {
            if (!context.InputParameters.TryGetValue("excelbase64", out object marcadorObj) || !(marcadorObj is string marcador) || string.IsNullOrWhiteSpace(marcador))
            {
                throw new InvalidPluginExecutionException("SPIKE atomicidad: falta el parametro 'excelbase64' (reusado como nombre del marcador).");
            }

            var registro = new Entity(TablaZzSpike);
            registro["sanic_nombre"] = marcador;

            Guid idCreado = localPluginContext.InitiatingUserService.Create(registro);
            localPluginContext.Trace($"SPIKE atomicidad: creado {idCreado}, lanzando excepcion deliberada");

            throw new InvalidPluginExecutionException(
                $"SPIKE atomicidad: excepcion deliberada tras crear el marcador '{marcador}' (id {idCreado}). " +
                "Si la transaccion es atomica, este registro NO debe persistir.");
        }

        // Pregunta 5 / 5 bis: actor. Hace un Update sobre el registro indicado (con SYSTEM o
        // con el usuario que llama, segun usarSystem), cambiando sanic_clave (atributo de
        // filtro del step ActorCaptureStep) para dispararlo. Antes del Update, deja el actor
        // real (InitiatingUserId de ESTE contexto, el de la Custom API) en SharedVariables
        // bajo la clave "zz_actor" -- la hipotesis del punto 3 es que ActorCaptureStep puede
        // leerla desde el SharedVariables de algun ParentContext de su cadena. El step anota
        // todo lo que ve (UserId, InitiatingUserId, cadena de ParentContext, SharedVariables)
        // en sanic_actorcapturado / sanic_actordetalle.
        private void EjecutarActor(ILocalPluginContext localPluginContext, IPluginExecutionContext context, bool usarSystem)
        {
            if (!context.InputParameters.TryGetValue("zzspikeid", out object idObj) || !(idObj is Guid zzspikeId) || zzspikeId == Guid.Empty)
            {
                throw new InvalidPluginExecutionException("SPIKE actor: falta el parametro 'zzspikeid' (Guid del registro a actualizar).");
            }

            context.SharedVariables["zz_actor"] = context.InitiatingUserId.ToString();

            IOrganizationService servicio = usarSystem
                ? localPluginContext.OrgSvcFactory.CreateOrganizationService(null)
                : localPluginContext.OrgSvcFactory.CreateOrganizationService(context.UserId);

            var registro = new Entity(TablaZzSpike, zzspikeId);
            registro["sanic_clave"] = "actor-trigger-" + Guid.NewGuid().ToString("N");

            servicio.Update(registro);

            string etiqueta = usarSystem ? "SYSTEM" : "usuario que llama (context.UserId)";
            context.OutputParameters["resultado"] =
                $"actor OK: Update ejecutado con {etiqueta} sobre {zzspikeId}. Detalle del PreOperation anidado en sanic_actorcapturado/sanic_actordetalle.";
            context.OutputParameters["milisegundos"] = 0;

            localPluginContext.Trace($"SPIKE actor: Update con {etiqueta} sobre {zzspikeId} completado. InitiatingUserId de esta Custom API: {context.InitiatingUserId}");
        }
    }
}
