using System;
using System.Collections.Generic;
using Microsoft.Xrm.Sdk;
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
    ///  - `Associate`/`Disassociate`: <see cref="NotSupportedException"/>;
    ///  - registra cada llamada en <see cref="Llamadas"/>; <see cref="Registros"/> devuelve copias de lo guardado.
    /// Los nombres lógicos y de atributos se comparan de forma ordinal, como los guarda Dataverse (en minúscula).
    /// </summary>
    public sealed class OrganizationServiceEnMemoria : IOrganizationService
    {
        /// <summary>Todas las llamadas recibidas, en orden. Lista de solo lectura sobre la real: se ve crecer.</summary>
        public IReadOnlyList<LlamadaRegistrada> Llamadas => throw new NotImplementedException();

        /// <summary>Copias de lo guardado en esa entidad, en orden de alta. Vacío si no hay.</summary>
        public IList<Entity> Registros(string logicalName)
        {
            throw new NotImplementedException();
        }

        /// <summary>Guarda una copia sin registrar llamada: para armar el estado inicial de una prueba. Asigna id si viene vacío.</summary>
        public Guid Sembrar(Entity entidad)
        {
            throw new NotImplementedException();
        }

        public Guid Create(Entity entity)
        {
            throw new NotImplementedException();
        }

        public Entity Retrieve(string entityName, Guid id, ColumnSet columnSet)
        {
            throw new NotImplementedException();
        }

        public void Update(Entity entity)
        {
            throw new NotImplementedException();
        }

        public void Delete(string entityName, Guid id)
        {
            throw new NotImplementedException();
        }

        public OrganizationResponse Execute(OrganizationRequest request)
        {
            throw new NotImplementedException();
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
            throw new NotImplementedException();
        }
    }
}
