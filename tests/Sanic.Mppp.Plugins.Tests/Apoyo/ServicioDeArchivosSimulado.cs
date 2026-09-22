using System;
using System.Collections.Generic;
using Microsoft.Crm.Sdk.Messages;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace Sanic.Mppp.Plugins.Tests.Apoyo
{
    /// <summary>
    /// Un IOrganizationService que SOLO responde `InitializeFileBlocksDownloadRequest` y `DownloadBlockRequest` para un archivo
    /// dado, y anota cada pedido. Todo lo demás es NotSupportedException. Sirve para probar `ArchivosDataverse` sin Dataverse.
    /// </summary>
    public sealed class ServicioDeArchivosSimulado : IOrganizationService
    {
        private readonly byte[] _archivo;
        private readonly string _token = Guid.NewGuid().ToString("N");

        public ServicioDeArchivosSimulado(byte[] archivo, long? tamanoAnunciado = null)
        {
            _archivo = archivo;
            TamanoAnunciado = tamanoAnunciado ?? archivo.Length;
        }

        /// <summary>Lo que la inicialización anuncia como `FileSizeInBytes` (se puede mentir para simular un archivo truncado).</summary>
        public long TamanoAnunciado { get; }

        public int Inicializaciones { get; private set; }

        public List<(long offset, long largo)> Bloques { get; } = new List<(long offset, long largo)>();

        public (string tabla, Guid id, string columna) UltimoObjetivo { get; private set; }

        public OrganizationResponse Execute(OrganizationRequest request)
        {
            switch (request)
            {
                case InitializeFileBlocksDownloadRequest ini:
                    Inicializaciones++;
                    UltimoObjetivo = (ini.Target.LogicalName, ini.Target.Id, ini.FileAttributeName);
                    return new InitializeFileBlocksDownloadResponse { ["FileContinuationToken"] = _token, ["FileSizeInBytes"] = TamanoAnunciado, ["FileName"] = "archivo.bin" };
                case DownloadBlockRequest bloque:
                    if (bloque.FileContinuationToken != _token)
                    {
                        throw new InvalidOperationException("token desconocido");
                    }

                    Bloques.Add((bloque.Offset, bloque.BlockLength));
                    var disponible = Math.Max(0, Math.Min(bloque.BlockLength, _archivo.Length - bloque.Offset));
                    var datos = new byte[disponible];
                    Array.Copy(_archivo, bloque.Offset, datos, 0, disponible);
                    return new DownloadBlockResponse { ["Data"] = datos };
                default:
                    throw new NotSupportedException(request.GetType().Name);
            }
        }

        public Guid Create(Entity entity) => throw new NotSupportedException();

        public Entity Retrieve(string entityName, Guid id, ColumnSet columnSet) => throw new NotSupportedException();

        public void Update(Entity entity) => throw new NotSupportedException();

        public void Delete(string entityName, Guid id) => throw new NotSupportedException();

        public void Associate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities) => throw new NotSupportedException();

        public void Disassociate(string entityName, Guid entityId, Relationship relationship, EntityReferenceCollection relatedEntities) => throw new NotSupportedException();

        public EntityCollection RetrieveMultiple(QueryBase query) => throw new NotSupportedException();
    }
}
