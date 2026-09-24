using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.ServiceModel;
using Microsoft.Crm.Sdk.Messages;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Messages;
using Microsoft.Xrm.Sdk.Query;

namespace Sanic.Mppp.Plugins.Tests.Dobles
{
    /// <summary>Una llamada que recibió el doble, para que las pruebas afirmen cuántas consultas hizo el código (diseno/03 §1 paso 6: nunca N+1).</summary>
    public sealed class LlamadaRegistrada
    {
        public LlamadaRegistrada(string operacion, string entidad)
        {
            Operacion = operacion;
            Entidad = entidad;
        }

        /// <summary>`Create`, `Retrieve`, `Update`, `Delete`, `RetrieveMultiple`, o el nombre del request de `Execute` (`ExecuteMultipleRequest`).</summary>
        public string Operacion { get; }

        /// <summary>El nombre lógico de la entidad, o nulo si la operación no es de una entidad.</summary>
        public string Entidad { get; }
    }

    /// <summary>
    /// Doble PROPIO de <see cref="IOrganizationService"/> (pieza 7.5; diseno/03 §8): un diccionario de entidades por nombre lógico
    /// e id. No es Dataverse: no valida metadatos, tipos, ni seguridad, y lo que no sabe hacer lo dice con
    /// <see cref="NotSupportedException"/> en vez de simular. Contrato (lo fijan las pruebas `OrganizationServiceEnMemoriaAceptacion`):
    ///  - guarda y devuelve COPIAS: mutar la entidad que se pasó o la que se recibió no cambia lo guardado;
    ///  - `Create` asigna el id si viene vacío y respeta el que viene; un id repetido en la misma entidad es una falla;
    ///  - `Retrieve` devuelve solo las columnas pedidas (`ColumnSet(true)` = todas) y siempre `Id` y `LogicalName`; un registro que
    ///    no existe es <see cref="System.ServiceModel.FaultException{OrganizationServiceFault}"/>, como en Dataverse;
    ///  - `Execute(RetrieveRequest)` con un `EntityReference` que trae `KeyAttributes` (clave alternativa) busca por igualdad de esos atributos;
    ///  - `Update` fusiona atributos (los que no vienen quedan); `Delete` borra; sobre un registro inexistente, falla;
    ///  - `RetrieveMultiple` solo con <see cref="QueryExpression"/>: `ConditionOperator` Equal, NotEqual, In, Null, NotNull, sobre
    ///    valores simples, <see cref="OptionSetValue"/> (por `Value`), <see cref="EntityReference"/> (por `Id`), <see cref="Money"/>
    ///    (por `Value`); filtros And/Or anidados; `TopCount`; `Orders`; y `ColumnSet`. Cualquier otra cosa (LinkEntities,
    ///    otros operadores, <see cref="FetchExpression"/>, paginación) es <see cref="NotSupportedException"/> que nombra qué faltó;
    ///  - `Execute`: <see cref="Microsoft.Xrm.Sdk.Messages.ExecuteMultipleRequest"/> (respeta `ContinueOnError` y `ReturnResponses`)
    ///    y <see cref="Microsoft.Xrm.Sdk.Messages.ExecuteTransactionRequest"/> (atómico: si una falla, no queda nada). Otro
    ///    request es <see cref="NotSupportedException"/>;
    ///  - COLUMNAS DE ARCHIVO: `InitializeFileBlocksDownload` y `DownloadBlock` leen el `byte[]` guardado en esa columna, para que
    ///    el código que baja un archivo se pueda probar sobre el mismo almacén que el resto. La inicialización devuelve
    ///    `FileSizeInBytes`, `FileName` (`<columna>.bin`) y un token; un registro o una columna SIN archivo es una falla del
    ///    servicio (lo que asumimos que hace Dataverse: está anotado en `diseno/PENDIENTES.md` §B para comprobar en Dev);
    ///    `DownloadBlock` con un token que no salió de una inicialización es una falla, y devuelve lo que haya desde `Offset`
    ///    (menos bytes que `BlockLength` si el archivo se termina, como la plataforma);
    ///  - `Associate`/`Disassociate`: <see cref="NotSupportedException"/>;
    ///  - registra cada llamada en <see cref="Llamadas"/>; <see cref="Registros"/> devuelve copias de lo guardado.
    ///  - TODO valor de atributo se copia, también los mutables del SDK (`byte[]`, `OptionSetValueCollection`, `EntityCollection`):
    ///    un tipo que no esté listado se presume mutable y se clona, o se rechaza con <see cref="NotSupportedException"/>;
    ///  - el atributo de la clave primaria (`<logicalname>id`) viene SIEMPRE en lo que se devuelve y sirve para filtrar, como en Dataverse;
    ///  - los TEXTOS en condiciones se comparan sin distinguir mayúsculas (Dataverse: "all filter conditions for string values are case
    ///    insensitive"); los espacios sí cuentan; `Distinct` no se simula (<see cref="NotSupportedException"/>).
    /// Los nombres lógicos y de atributos se comparan de forma ordinal, como los guarda Dataverse (en minúscula).
    /// </summary>
    public sealed class OrganizationServiceEnMemoria : IOrganizationService
    {
        // Un diccionario por entidad lógica; adentro, por id. Un List<Guid> paralelo guarda el orden de alta
        // porque Dictionary no promete orden estable frente a los Delete (y RetrieveMultiple sin Orders explícitos
        // tiene que devolver en orden de alta, como una tabla real recorrida por rowid).
        private readonly Dictionary<string, Dictionary<Guid, Entity>> _porEntidad = new Dictionary<string, Dictionary<Guid, Entity>>(StringComparer.Ordinal);
        private readonly Dictionary<string, List<Guid>> _ordenPorEntidad = new Dictionary<string, List<Guid>>(StringComparer.Ordinal);
        private readonly List<LlamadaRegistrada> _llamadas = new List<LlamadaRegistrada>();
        private readonly ReadOnlyCollection<LlamadaRegistrada> _llamadasSoloLectura;

        // Columnas de archivo: cada InitializeFileBlocksDownload guarda una COPIA de los bytes bajo un token nuevo,
        // para que DownloadBlock lea de ahí sin volver a tocar el registro (diseno/03 §8, contrato del doble).
        private readonly Dictionary<string, byte[]> _archivosPorToken = new Dictionary<string, byte[]>(StringComparer.Ordinal);

        public OrganizationServiceEnMemoria()
        {
            _llamadasSoloLectura = new ReadOnlyCollection<LlamadaRegistrada>(_llamadas);
        }

        /// <summary>Todas las llamadas recibidas, en orden. Lista de solo lectura sobre la real: se ve crecer.</summary>
        public IReadOnlyList<LlamadaRegistrada> Llamadas => _llamadasSoloLectura;

        /// <summary>Copias de lo guardado en esa entidad, en orden de alta. Vacío si no hay.</summary>
        public IList<Entity> Registros(string logicalName)
        {
            if (logicalName == null)
            {
                throw new ArgumentNullException(nameof(logicalName));
            }

            if (!_ordenPorEntidad.TryGetValue(logicalName, out var orden))
            {
                return new List<Entity>();
            }

            var tabla = _porEntidad[logicalName];
            return orden.Select(id => Clonar(tabla[id])).ToList();
        }

        /// <summary>Guarda una copia sin registrar llamada: para armar el estado inicial de una prueba. Asigna id si viene vacío.</summary>
        public Guid Sembrar(Entity entidad)
        {
            if (entidad == null)
            {
                throw new ArgumentNullException(nameof(entidad));
            }

            var id = entidad.Id != Guid.Empty ? entidad.Id : Guid.NewGuid();
            var copia = Clonar(entidad);
            copia.Id = id;
            FijarAtributoClavePrimaria(copia);

            var tabla = ObtenerOCrearTabla(entidad.LogicalName);
            var orden = ObtenerOCrearOrden(entidad.LogicalName);
            if (!tabla.ContainsKey(id))
            {
                orden.Add(id);
            }

            tabla[id] = copia;
            return id;
        }

        public Guid Create(Entity entity)
        {
            if (entity == null)
            {
                throw new ArgumentNullException(nameof(entity));
            }

            var id = CrearInterno(entity);
            RegistrarLlamada("Create", entity.LogicalName);
            return id;
        }

        public Entity Retrieve(string entityName, Guid id, ColumnSet columnSet)
        {
            if (entityName == null)
            {
                throw new ArgumentNullException(nameof(entityName));
            }

            if (columnSet == null)
            {
                throw new ArgumentNullException(nameof(columnSet));
            }

            var registro = ProyectarColumnas(BuscarObligatorio(entityName, id), columnSet);
            RegistrarLlamada("Retrieve", entityName);
            return registro;
        }

        public void Update(Entity entity)
        {
            if (entity == null)
            {
                throw new ArgumentNullException(nameof(entity));
            }

            ActualizarInterno(entity);
            RegistrarLlamada("Update", entity.LogicalName);
        }

        public void Delete(string entityName, Guid id)
        {
            if (entityName == null)
            {
                throw new ArgumentNullException(nameof(entityName));
            }

            BorrarInterno(entityName, id);
            RegistrarLlamada("Delete", entityName);
        }

        public OrganizationResponse Execute(OrganizationRequest request)
        {
            if (request == null)
            {
                throw new ArgumentNullException(nameof(request));
            }

            OrganizationResponse respuesta;
            string entidad;
            switch (request)
            {
                case ExecuteMultipleRequest lote:
                    respuesta = EjecutarLote(lote);
                    entidad = null;
                    break;
                case ExecuteTransactionRequest tx:
                    respuesta = EjecutarTransaccion(tx);
                    entidad = null;
                    break;
                default:
                    respuesta = ResolverRequest(request);
                    entidad = EntidadDe(request);
                    break;
            }

            // El lote y la transacción cuentan como UNA llamada: los requests que resuelven adentro (vía ResolverRequest)
            // nunca pasan por acá, así que no se registran aparte (diseno/03 §8, contrato del doble).
            RegistrarLlamada(request.GetType().Name, entidad);
            return respuesta;
        }

        public void Associate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities)
        {
            throw new NotSupportedException("El doble no simula Associate: el código de M-PPP no lo usa.");
        }

        public void Disassociate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities)
        {
            throw new NotSupportedException("El doble no simula Disassociate: el código de M-PPP no lo usa.");
        }

        public EntityCollection RetrieveMultiple(QueryBase query)
        {
            if (query == null)
            {
                throw new ArgumentNullException(nameof(query));
            }

            var consulta = RequerirQueryExpression(query);
            var resultado = ConsultarInterno(consulta);
            RegistrarLlamada("RetrieveMultiple", consulta.EntityName);
            return resultado;
        }

        // ------------------------------------------------------------------ Implementación interna (sin registrar llamada;
        // la usan tanto los métodos públicos como Execute/ExecuteMultiple/ExecuteTransaction, para que un request dentro
        // de un lote no cuente como llamada aparte).

        private Guid CrearInterno(Entity entity)
        {
            var id = entity.Id != Guid.Empty ? entity.Id : Guid.NewGuid();
            var tabla = ObtenerOCrearTabla(entity.LogicalName);
            if (tabla.ContainsKey(id))
            {
                throw Falla($"Ya existe un registro de '{entity.LogicalName}' con id {id}.");
            }

            var copia = Clonar(entity);
            copia.Id = id;
            FijarAtributoClavePrimaria(copia);
            tabla[id] = copia;
            ObtenerOCrearOrden(entity.LogicalName).Add(id);
            return id;
        }

        private void ActualizarInterno(Entity entity)
        {
            var registro = BuscarObligatorio(entity.LogicalName, entity.Id);
            foreach (var atributo in entity.Attributes)
            {
                registro[atributo.Key] = ClonarValor(atributo.Value);
            }

            // La clave primaria no la manda quien actualiza (Dataverse no la deja tocar); la reponemos por si
            // el merge la pisó, así queda siempre correcta para filtrar (diseno/03 §8, revisión de código).
            FijarAtributoClavePrimaria(registro);
        }

        /// <summary>Como en Dataverse, el atributo de la clave primaria (`&lt;logicalname&gt;id`) siempre está en lo guardado.</summary>
        private static void FijarAtributoClavePrimaria(Entity entidad)
        {
            entidad[entidad.LogicalName + "id"] = entidad.Id;
        }

        private void BorrarInterno(string entityName, Guid id)
        {
            BuscarObligatorio(entityName, id);
            _porEntidad[entityName].Remove(id);
            _ordenPorEntidad[entityName].Remove(id);
        }

        private OrganizationResponse ResolverRequest(OrganizationRequest request)
        {
            switch (request)
            {
                case CreateRequest r:
                    {
                        var id = CrearInterno(r.Target);
                        var resp = new CreateResponse();
                        resp.Results["id"] = id;
                        return resp;
                    }

                case RetrieveRequest r:
                    {
                        var registro = r.Target.KeyAttributes != null && r.Target.KeyAttributes.Count > 0
                            ? BuscarPorClave(r.Target.LogicalName, r.Target.KeyAttributes)
                            : BuscarObligatorio(r.Target.LogicalName, r.Target.Id);
                        var resp = new RetrieveResponse();
                        resp.Results["Entity"] = ProyectarColumnas(registro, r.ColumnSet ?? new ColumnSet(true));
                        return resp;
                    }

                case UpdateRequest r:
                    ActualizarInterno(r.Target);
                    return new UpdateResponse();

                case DeleteRequest r:
                    BorrarInterno(r.Target.LogicalName, r.Target.Id);
                    return new DeleteResponse();

                case RetrieveMultipleRequest r:
                    {
                        var consulta = RequerirQueryExpression(r.Query);
                        var resp = new RetrieveMultipleResponse();
                        resp.Results["EntityCollection"] = ConsultarInterno(consulta);
                        return resp;
                    }

                case InitializeFileBlocksDownloadRequest r:
                    return IniciarDescargaDeArchivo(r);

                case DownloadBlockRequest r:
                    return DescargarBloqueDeArchivo(r);

                default:
                    throw new NotSupportedException($"El doble no simula el request '{request.RequestName}': no está entre los pocos mensajes que el código de M-PPP usa (diseno/03 §8).");
            }
        }

        /// <summary>Registro y columna sin `byte[]`: falla del servicio, no un archivo vacío (diseno/03 §8, PENDIENTES §B).</summary>
        private InitializeFileBlocksDownloadResponse IniciarDescargaDeArchivo(InitializeFileBlocksDownloadRequest pedido)
        {
            var registro = BuscarObligatorio(pedido.Target.LogicalName, pedido.Target.Id);
            if (!registro.Contains(pedido.FileAttributeName) || !(registro[pedido.FileAttributeName] is byte[] bytes))
            {
                throw Falla($"La columna '{pedido.FileAttributeName}' de '{pedido.Target.LogicalName}' no tiene un archivo.");
            }

            var copia = new byte[bytes.Length];
            Array.Copy(bytes, copia, bytes.Length);
            var token = Guid.NewGuid().ToString("N");
            _archivosPorToken[token] = copia;

            var respuesta = new InitializeFileBlocksDownloadResponse();
            respuesta.Results["FileSizeInBytes"] = (long)copia.Length;
            respuesta.Results["FileName"] = pedido.FileAttributeName + ".bin";
            respuesta.Results["FileContinuationToken"] = token;
            return respuesta;
        }

        /// <summary>Token que no salió de una inicialización: falla del servicio. Si existe, copia desde Offset, a lo sumo BlockLength.</summary>
        private DownloadBlockResponse DescargarBloqueDeArchivo(DownloadBlockRequest pedido)
        {
            if (pedido.FileContinuationToken == null || !_archivosPorToken.TryGetValue(pedido.FileContinuationToken, out var bytes))
            {
                throw Falla("El token de continuación no corresponde a una descarga de archivo iniciada.");
            }

            var disponible = Math.Max(0L, Math.Min(pedido.BlockLength, bytes.Length - pedido.Offset));
            var datos = new byte[disponible];
            Array.Copy(bytes, pedido.Offset, datos, 0, disponible);

            var respuesta = new DownloadBlockResponse();
            respuesta.Results["Data"] = datos;
            return respuesta;
        }

        private static string EntidadDe(OrganizationRequest request)
        {
            switch (request)
            {
                case CreateRequest r: return r.Target?.LogicalName;
                case RetrieveRequest r: return r.Target?.LogicalName;
                case UpdateRequest r: return r.Target?.LogicalName;
                case DeleteRequest r: return r.Target?.LogicalName;
                case RetrieveMultipleRequest r: return (r.Query as QueryExpression)?.EntityName;
                case InitializeFileBlocksDownloadRequest r: return r.Target?.LogicalName;
                default: return null;
            }
        }

        private ExecuteMultipleResponse EjecutarLote(ExecuteMultipleRequest lote)
        {
            var items = new ExecuteMultipleResponseItemCollection();
            for (var i = 0; i < lote.Requests.Count; i++)
            {
                try
                {
                    var respuesta = ResolverRequest(lote.Requests[i]);
                    if (lote.Settings.ReturnResponses)
                    {
                        items.Add(new ExecuteMultipleResponseItem { RequestIndex = i, Response = respuesta });
                    }
                }
                catch (FaultException<OrganizationServiceFault> ex)
                {
                    items.Add(new ExecuteMultipleResponseItem { RequestIndex = i, Fault = ex.Detail });
                    if (!lote.Settings.ContinueOnError)
                    {
                        break;
                    }
                }
            }

            var salida = new ExecuteMultipleResponse();
            salida.Results["Responses"] = items;
            // IsFaulted no se calcula solo del lado del cliente (Results es un diccionario plano, como con "id" en
            // CreateResponse): lo calcula el servidor real y acá lo simulamos a partir de los ítems con Fault.
            salida.Results["IsFaulted"] = items.Any(i => i.Fault != null);
            return salida;
        }

        private ExecuteTransactionResponse EjecutarTransaccion(ExecuteTransactionRequest tx)
        {
            var respaldo = CopiarEstado();
            var respuestas = new OrganizationResponseCollection();
            try
            {
                foreach (var request in tx.Requests)
                {
                    var respuesta = ResolverRequest(request);
                    if (tx.ReturnResponses == true)
                    {
                        respuestas.Add(respuesta);
                    }
                }
            }
            catch (FaultException<OrganizationServiceFault>)
            {
                RestaurarEstado(respaldo);
                throw;
            }

            var salida = new ExecuteTransactionResponse();
            salida.Results["Responses"] = respuestas;
            return salida;
        }

        // ------------------------------------------------------------------ Almacén: acceso, clonado y respaldo/restauración

        private Dictionary<Guid, Entity> ObtenerOCrearTabla(string logicalName)
        {
            if (!_porEntidad.TryGetValue(logicalName, out var tabla))
            {
                tabla = new Dictionary<Guid, Entity>();
                _porEntidad[logicalName] = tabla;
            }

            return tabla;
        }

        private List<Guid> ObtenerOCrearOrden(string logicalName)
        {
            if (!_ordenPorEntidad.TryGetValue(logicalName, out var orden))
            {
                orden = new List<Guid>();
                _ordenPorEntidad[logicalName] = orden;
            }

            return orden;
        }

        private Entity BuscarObligatorio(string entityName, Guid id)
        {
            if (_porEntidad.TryGetValue(entityName, out var tabla) && tabla.TryGetValue(id, out var registro))
            {
                return registro;
            }

            throw Falla($"No existe el registro '{entityName}' con id {id}.");
        }

        private Entity BuscarPorClave(string logicalName, KeyAttributeCollection claves)
        {
            if (_porEntidad.TryGetValue(logicalName, out var tabla))
            {
                foreach (var registro in tabla.Values)
                {
                    var coincide = true;
                    foreach (var clave in claves)
                    {
                        if (!registro.Contains(clave.Key) || !ValoresIguales(Normalizar(registro[clave.Key]), Normalizar(clave.Value)))
                        {
                            coincide = false;
                            break;
                        }
                    }

                    if (coincide)
                    {
                        return registro;
                    }
                }
            }

            throw Falla($"No existe el registro '{logicalName}' con esa clave alternativa.");
        }

        private (Dictionary<string, Dictionary<Guid, Entity>> Tablas, Dictionary<string, List<Guid>> Ordenes) CopiarEstado()
        {
            var tablas = new Dictionary<string, Dictionary<Guid, Entity>>(StringComparer.Ordinal);
            foreach (var porTabla in _porEntidad)
            {
                var copiaTabla = new Dictionary<Guid, Entity>();
                foreach (var registro in porTabla.Value)
                {
                    copiaTabla[registro.Key] = Clonar(registro.Value);
                }

                tablas[porTabla.Key] = copiaTabla;
            }

            var ordenes = new Dictionary<string, List<Guid>>(StringComparer.Ordinal);
            foreach (var porOrden in _ordenPorEntidad)
            {
                ordenes[porOrden.Key] = new List<Guid>(porOrden.Value);
            }

            return (tablas, ordenes);
        }

        private void RestaurarEstado((Dictionary<string, Dictionary<Guid, Entity>> Tablas, Dictionary<string, List<Guid>> Ordenes) respaldo)
        {
            _porEntidad.Clear();
            foreach (var porTabla in respaldo.Tablas)
            {
                _porEntidad[porTabla.Key] = porTabla.Value;
            }

            _ordenPorEntidad.Clear();
            foreach (var porOrden in respaldo.Ordenes)
            {
                _ordenPorEntidad[porOrden.Key] = porOrden.Value;
            }
        }

        private static Entity Clonar(Entity entidad)
        {
            var copia = new Entity(entidad.LogicalName, entidad.Id);
            foreach (var atributo in entidad.Attributes)
            {
                copia[atributo.Key] = ClonarValor(atributo.Value);
            }

            return copia;
        }

        private static object ClonarValor(object valor)
        {
            switch (valor)
            {
                case null:
                    return null;
                case OptionSetValue optionSet:
                    return new OptionSetValue(optionSet.Value);
                case EntityReference referencia:
                    var copiaReferencia = new EntityReference(referencia.LogicalName, referencia.Id) { Name = referencia.Name };
                    if (referencia.KeyAttributes != null)
                    {
                        foreach (var clave in referencia.KeyAttributes)
                        {
                            copiaReferencia.KeyAttributes[clave.Key] = clave.Value;
                        }
                    }

                    return copiaReferencia;
                case Money dinero:
                    return new Money(dinero.Value);
                case Entity anidada:
                    return Clonar(anidada);
                case EntityReferenceCollection coleccion:
                    var copiaColeccion = new EntityReferenceCollection();
                    foreach (var referenciaHija in coleccion)
                    {
                        copiaColeccion.Add((EntityReference)ClonarValor(referenciaHija));
                    }

                    return copiaColeccion;
                case byte[] bytes:
                    // Revisión de código, 2026-09-21: byte[] es mutable (archivos) y se compartía por referencia.
                    var copiaBytes = new byte[bytes.Length];
                    Array.Copy(bytes, copiaBytes, bytes.Length);
                    return copiaBytes;
                case OptionSetValueCollection multi:
                    // Multiselección: mismo problema que byte[], y cada OptionSetValue adentro también se clona.
                    var copiaMulti = new OptionSetValueCollection();
                    foreach (var item in multi)
                    {
                        copiaMulti.Add(new OptionSetValue(item.Value));
                    }

                    return copiaMulti;
                case EntityCollection coleccionEntidades:
                    // Igual que Entity: se comparte por referencia si no se clona cada entidad adentro.
                    var copiaColeccionEntidades = new EntityCollection(coleccionEntidades.Entities.Select(Clonar).ToList())
                    {
                        EntityName = coleccionEntidades.EntityName,
                        MoreRecords = coleccionEntidades.MoreRecords,
                        PagingCookie = coleccionEntidades.PagingCookie,
                        TotalRecordCount = coleccionEntidades.TotalRecordCount,
                        TotalRecordCountLimitExceeded = coleccionEntidades.TotalRecordCountLimitExceeded,
                    };

                    return copiaColeccionEntidades;
                default:
                    // Solo los tipos inmutables conocidos se comparten sin riesgo: cualquier otro tipo se presume
                    // mutable y el doble no miente simulando una copia que no hace (diseno/03 §8).
                    var tipo = valor.GetType();
                    if (valor is string || valor is bool || valor is byte || valor is sbyte || valor is short || valor is ushort
                        || valor is int || valor is uint || valor is long || valor is ulong || valor is float || valor is double
                        || valor is decimal || valor is Guid || valor is DateTime || tipo.IsEnum)
                    {
                        return valor;
                    }

                    throw new NotSupportedException($"El doble no sabe copiar el tipo '{tipo.FullName}': agregalo a ClonarValor si hace falta simularlo (diseno/03 §8).");
            }
        }

        private static Entity ProyectarColumnas(Entity origen, ColumnSet columnSet)
        {
            var copia = Clonar(origen);
            var atributoClave = copia.LogicalName + "id";

            if (columnSet.AllColumns)
            {
                copia[atributoClave] = copia.Id;
                return copia;
            }

            var proyectada = new Entity(copia.LogicalName, copia.Id);
            foreach (var columna in columnSet.Columns)
            {
                if (copia.Contains(columna))
                {
                    proyectada[columna] = copia[columna];
                }
            }

            // Como Id/LogicalName: el atributo de la clave primaria viene siempre, aunque no se haya pedido
            // (diseno/03 §8, revisión de código: "el atributo de la clave primaria viene SIEMPRE...").
            proyectada[atributoClave] = copia.Id;
            return proyectada;
        }

        // ------------------------------------------------------------------ RetrieveMultiple: filtro, orden, columnas y top

        private static QueryExpression RequerirQueryExpression(QueryBase query)
        {
            if (query is QueryExpression consulta)
            {
                return consulta;
            }

            throw new NotSupportedException($"El doble solo simula RetrieveMultiple con QueryExpression, no con '{query.GetType().Name}'.");
        }

        private EntityCollection ConsultarInterno(QueryExpression query)
        {
            if (query.LinkEntities != null && query.LinkEntities.Count > 0)
            {
                throw new NotSupportedException("El doble no simula LinkEntities: armá la consulta sin join (diseno/03 §8).");
            }

            if (query.PageInfo != null && (query.PageInfo.Count > 0 || query.PageInfo.PageNumber > 1 || !string.IsNullOrEmpty(query.PageInfo.PagingCookie)))
            {
                throw new NotSupportedException("El doble no simula paginación (PageInfo): traé todo con TopCount o filtrá más (diseno/03 §8).");
            }

            if (query.Distinct)
            {
                throw new NotSupportedException("El doble no simula Distinct: quitalo de la consulta (diseno/03 §8).");
            }

            var candidatos = _porEntidad.TryGetValue(query.EntityName, out var tabla)
                ? (IEnumerable<Entity>)tabla.Values
                : Array.Empty<Entity>();

            var filtrados = candidatos.Where(e => CumpleFiltro(e, query.Criteria));

            IEnumerable<Entity> ordenados;
            if (query.Orders != null && query.Orders.Count > 0)
            {
                ordenados = OrdenarPor(filtrados, query.Orders);
            }
            else
            {
                // Sin Orders explícitos: orden de alta, como una tabla recorrida por rowid. Se arma un diccionario
                // de posición UNA vez en vez de orden.IndexOf(e.Id) dentro del OrderBy (eso era O(n) por elemento
                // ordenado, es decir O(n²) en total; diseno/03 §1 paso 6, revisión de código).
                var orden = _ordenPorEntidad.TryGetValue(query.EntityName, out var listaOrden) ? listaOrden : new List<Guid>();
                var posicion = new Dictionary<Guid, int>(orden.Count);
                for (var i = 0; i < orden.Count; i++)
                {
                    posicion[orden[i]] = i;
                }

                ordenados = filtrados.OrderBy(e => posicion[e.Id]);
            }

            if (query.TopCount.HasValue)
            {
                ordenados = ordenados.Take(query.TopCount.Value);
            }

            var columnSet = query.ColumnSet ?? new ColumnSet(true);
            var resultado = new EntityCollection { EntityName = query.EntityName };
            resultado.Entities.AddRange(ordenados.Select(e => ProyectarColumnas(e, columnSet)));
            return resultado;
        }

        private static bool CumpleFiltro(Entity entidad, FilterExpression filtro)
        {
            if (filtro == null)
            {
                return true;
            }

            var resultados = new List<bool>();
            if (filtro.Conditions != null)
            {
                resultados.AddRange(filtro.Conditions.Select(c => CumpleCondicion(entidad, c)));
            }

            if (filtro.Filters != null)
            {
                resultados.AddRange(filtro.Filters.Select(f => CumpleFiltro(entidad, f)));
            }

            if (resultados.Count == 0)
            {
                return true;
            }

            return filtro.FilterOperator == LogicalOperator.Or ? resultados.Any(x => x) : resultados.All(x => x);
        }

        private static bool CumpleCondicion(Entity entidad, ConditionExpression condicion)
        {
            var valorEntidad = entidad.Contains(condicion.AttributeName) ? entidad[condicion.AttributeName] : null;
            var normalizadoEntidad = Normalizar(valorEntidad);

            switch (condicion.Operator)
            {
                case ConditionOperator.Equal:
                    return ValoresIguales(normalizadoEntidad, Normalizar(ValorUnico(condicion)));
                case ConditionOperator.NotEqual:
                    return !ValoresIguales(normalizadoEntidad, Normalizar(ValorUnico(condicion)));
                case ConditionOperator.Null:
                    return valorEntidad == null;
                case ConditionOperator.NotNull:
                    return valorEntidad != null;
                case ConditionOperator.In:
                    return ValoresDeIn(condicion).Any(v => ValoresIguales(normalizadoEntidad, Normalizar(v)));
                default:
                    throw new NotSupportedException($"El doble no simula el operador '{condicion.Operator}' (atributo '{condicion.AttributeName}'; diseno/03 §8).");
            }
        }

        private static object ValorUnico(ConditionExpression condicion) => condicion.Values.Count > 0 ? condicion.Values[0] : null;

        /// <summary>
        /// Los valores de un `In`, SIN aplanar. Antes este doble aplanaba los arreglos anidados, y esa permisividad
        /// escondió un defecto real durante toda la construcción: un `In` al que se le pasa el arreglo entero como UN
        /// valor pasaba verde acá y reventaba en Dataverse con *"expected argument(s) of type 'System.Guid' but
        /// received 'System.Object[]'"* (prueba de humo en Dev, 2026-09-22).
        ///
        /// Un doble más permisivo que la plataforma es peor que no tener doble: da confianza falsa. Así que acá se
        /// falla igual que allá, con el mismo mensaje.
        /// </summary>
        private static IEnumerable<object> ValoresDeIn(ConditionExpression condicion)
        {
            foreach (var valor in condicion.Values)
            {
                if (valor is System.Collections.IEnumerable && !(valor is string))
                {
                    throw new InvalidOperationException(
                        $"Condition for attribute '{condicion.AttributeName}': expected a scalar argument but received " +
                        $"'{valor.GetType()}'. Un `In` recibe sus valores UNO POR UNO (el parámetro es `params object[]`), " +
                        "nunca el arreglo entero como un solo valor. Dataverse rechaza esto mismo en tiempo de ejecución.");
                }

                yield return valor;
            }
        }

        private static object Normalizar(object valor)
        {
            switch (valor)
            {
                case null: return null;
                case OptionSetValue optionSet: return optionSet.Value;
                case EntityReference referencia: return referencia.Id;
                case Money dinero: return dinero.Value;
                default: return valor;
            }
        }

        private static bool ValoresIguales(object a, object b)
        {
            if (a == null || b == null)
            {
                return a == null && b == null;
            }

            if (a is string textoA && b is string textoB)
            {
                // Microsoft Learn, "Query data using the SDK for .NET": las condiciones de texto no distinguen
                // mayúsculas en Dataverse (los espacios sí cuentan, por eso no se recorta nada acá).
                return string.Equals(textoA, textoB, StringComparison.OrdinalIgnoreCase);
            }

            return a.Equals(b);
        }

        private static IEnumerable<Entity> OrdenarPor(IEnumerable<Entity> entidades, IEnumerable<OrderExpression> orders)
        {
            IOrderedEnumerable<Entity> ordenado = null;
            foreach (var orden in orders)
            {
                object Clave(Entity e) => Normalizar(e.Contains(orden.AttributeName) ? e[orden.AttributeName] : null);

                if (ordenado == null)
                {
                    ordenado = orden.OrderType == OrderType.Descending
                        ? entidades.OrderByDescending(Clave, ComparadorNulosPrimero.Instancia)
                        : entidades.OrderBy(Clave, ComparadorNulosPrimero.Instancia);
                }
                else
                {
                    ordenado = orden.OrderType == OrderType.Descending
                        ? ordenado.ThenByDescending(Clave, ComparadorNulosPrimero.Instancia)
                        : ordenado.ThenBy(Clave, ComparadorNulosPrimero.Instancia);
                }
            }

            return ordenado ?? entidades;
        }

        private void RegistrarLlamada(string operacion, string entidad)
        {
            _llamadas.Add(new LlamadaRegistrada(operacion, entidad));
        }

        private static FaultException<OrganizationServiceFault> Falla(string mensaje)
        {
            return new FaultException<OrganizationServiceFault>(new OrganizationServiceFault { Message = mensaje }, new FaultReason(mensaje));
        }

        /// <summary>Comparer<object>.Default no acepta nulos: este wrapper los trata como "menor que cualquier valor" (diseno/03 §8, Orders).</summary>
        private sealed class ComparadorNulosPrimero : IComparer<object>
        {
            public static readonly ComparadorNulosPrimero Instancia = new ComparadorNulosPrimero();

            public int Compare(object x, object y)
            {
                if (x == null && y == null)
                {
                    return 0;
                }

                if (x == null)
                {
                    return -1;
                }

                if (y == null)
                {
                    return 1;
                }

                return Comparer<object>.Default.Compare(x, y);
            }
        }
    }
}
