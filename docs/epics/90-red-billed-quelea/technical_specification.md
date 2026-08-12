# Support for Batch DAO Operations in Hexkit (Red-billed Quelea)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope

### Outline:

This epic aims to extend the `Dao` protocol in hexkit with batch methods that apply the existing  CRUD operations to several resources in a single call. 
The corresponding MongoDB provider will implement those methods and the in-memory DAO testing utility will be updated accordingly.

This will allow services to perform common bulk operations using one database round-trip per resource batch instead of one round-trip per resource.

### Included/Required:

- Extend the `Dao` protocol in `hexkit.protocols.dao` with four new methods, `insert_many`, `update_many`, `upsert_many` and `delete_many`, keeping the protocol backend-agnostic.
- Implement the four methods on the `MongoDbDao` provider in `hexkit.providers.mongodb.provider.dao`
- Extend the in-memory DAO provider so that it supports the new methods with equivalent semantics.

### Not included:

- Automatic chunking of very large documents. 
As with the current single resource variants, we don't chunk when we would exceed MongoDB's 16 MB request size.


## API Definitions

### DAO

The following methods are added to the existing `Dao` protocol. They are asynchronous like the rest of the protocol, share the same `Dto` type variable, and are kept provider-agnostic:

```python
class Dao(typing.Protocol[Dto]):

    async def insert_many(self, dtos: Collection[Dto]) -> None:
        """Insert multiple resources in a single call.

        Raises `BatchOperationError if any DTO's ID already exists or if any DTO would violate a unique index constraint on a field other than the ID.
        """

    async def update_many(self, dtos: Collection[Dto]) -> None:
        """Update multiple existing resources in a single call, matched by ID.

        Raises a `BatchOperationError` if any DTO's ID does not correspond to
        an existing resource or if any update would violate a unique index constraint on a field other than the ID.
        """


    async def upsert_many(self, dtos: Collection[Dto]) -> None:
        """Insert or update multiple resources in a single call, matched by ID.

        Raises a `BatchOperationError` if any upsert would violate a unique index constraint on a field other than the ID.
        """

    async def delete_many(self, ids: Collection[UUID4]) -> None:
        """Delete multiple resources by providing their IDs.

        If any unique ID does not correspond to an existing resource, it is presumed already deleted and silently ignored.
        """
```

Callers are expected to provide DTOs with distinct IDs and it might be beneficial to fail early, if incompatible DTOs exist in the same collection, before performing the actual call.
If deduplication is desired, this might need some logic that checks more than just the IDs.
The easier solution would be to just reject the operation if duplicate IDs exist, keeping the logic clean and simple.

The existing single-resource methods remain unchanged and are not re-implemented in terms of the batch methods, though nothing precludes using the new methods with single item lists to achieve compatible behavior.

An additional `BatchOperationError` will be introduced to wrap single failures within a batch operation, holding a dictionary of document IDs to error details, for handling by the caller.

## Implementation Details

New implementations for the protocol methods are added to `MongoDbDao` and reuse the existing `translate_pymongo_errors` context manager together with `_dto_to_document` and `_document_to_dto`.

As we don't get atomic guarantees around the batch operations in MongoDB, operation results need to be checked for what actually succeeded and might have failed.
For the non-delete operation this should return the document IDs for all failed operations inside a compound error encapsulating the corresponding error types (`ResourceAlreadyExistsError`/`ResourceNotFoundError`) from single resource variants.

Using the `ordered` argument (default) for batch operations would perform them in sequence and abort on the first failure encountered in a predictable manner, however,
not using it would allow to collect all failures instead and all successful operations to be performed.
For this implementation, the default should be inverted, but opting into it should be made possible via an argument.

`insert_many` and `delete_many` can delegate to `AsyncCollection.insert_many` and `AsyncCollection.delete_many`, respectively.

The update/upsert batch operations will be implemented analogously to the single resource variants, using `AsyncCollection.bulk_write` for batching and a list of `replace_one` for the operations passed to it.
The `BulkWriteError` potentially raised by this operation will also be wrapped/abstracted by the custom `BatchOperationError` for consistency.
`update_many` is not suitable, as it applies a single update specification to all documents matching the filter.

The in-memory DAO is extended with the same four methods, implemented by iterating the input collection and delegating to the existing single-resource operations.

## Human Resource/Time Estimation

Number of sprints required: 1

Number of developers required: 1
