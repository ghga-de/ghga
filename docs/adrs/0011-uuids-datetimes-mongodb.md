# UUID and Datetime Representation in MongoDB

Date: 2024-10-14

## Summary

In the context of **storing data in MongoDB**

facing **the need for efficient querying, data integrity, and performance improvements**

we decided for **leveraging MongoDB's support for storing advanced data types, like UUIDs and datetimes, as BSON objects**

and neglected **storing all data using simple JSON data types, e.g. ISO formatted datetime strings (as we did until now)**

to achieve **improved query performance, storage efficiency, consistency and data type preservation**

accepting that **this will require changes to the hexkit library and reformatting existing data.**

## Details

### Status

**proposed**

### Context & Requirements

First, some background information.

*Relevant Types:*
The Python data types discussed in this document include UUIDs and Dates.
We use UUID4 primarily but the exact UUID version is irrelevant for this discussion.
"Dates" will stand as shorthand for `datetime` and `UTCDatetime` (from `ghga-service-commons`).

*BSON and `pymongo`:*
MongoDB data is stored in a format called *BSON*, or, Binary JSON. It features
extensions that allow for the use of non-JSON-compatible data types, like dates.
Here is a link to the [BSON Spec](https://bsonspec.org/spec.html).
We don't have to worry about serializing data to and from BSON because `pymongo`
[does it for us](https://pymongo.readthedocs.io/en/stable/api/bson/index.html#module-bson).
`Pymongo` is the MongoDB driver for Python. When we establish a `MongoClient`
instance or carry out an operation on a collection, that is handled by `pymongo`.

*Serialization in `hexkit`:*
In `hexkit`, the MongoDB DAO provider allows us to carry out CRUD operations with documents.
For updates and insertions, the data transfer object (DTO) to be written is first run
through a short preparatory function, `dto_to_document()`, wherein the DTO values are
made JSON-compatible. Values that aren't JSON-compatible are currently converted to strings.
The resulting JSON-like object is what is actually given to `pymongo`. The important
takeaway here is that UUIDs and dates are not preserved as their original type because
they are not part of the JSON spec. Instead, they are given to `pymongo` as strings.

*Representation of UUIDs and Dates in Pydantic Models:*
Our current practice is to type-hint `id` fields on Pydantic models as strings. This
obviously makes sense if the ID is genuinely a string, but oftentimes it is actually a
UUID. Pydantic offers a [UUID4 type](https://docs.pydantic.dev/latest/api/types/#pydantic.types.UUID4)
for validating such values, but `hexkit` has only recently been modified to allow
UUID-typed fields for DTO Pydantic models. Regardless of the field's type, UUIDs will only
be processed by `pymongo` as strings right now because of the serialization processed
described in the paragraph above. Dates are similar.

Now, on to the proposed change:

The main issues we face with regard to UUIDs and dates include:
- Indexes for string UUIDs use roughly double the space required by binary UUIDs.
- In string format, dates cannot be (easily) sorted or compared in MongoDB queries.
  - Iso-formatted date strings can be sorted, but they are not compatible with date-specific
  MongoDB operations like `$dateAdd` or `$dateDiff` without first being cast to a string.
  This increases the complexity of writing and maintaining MongoDB queries containing
  date operations, but also reduces their performance.
- The Pydantic models in our application use `str`-typed date fields that depend on
  custom validation logic. This is directly influenced by our practice of storing dates
  as strings. The application-side string specification complicates validation.
- Storing UUIDs and dates as strings in MongoDB requires more space than the binary equivalents.
- Some minor effort is spent when creating new methods or models that work with these
  types because they must use the same string representation methods and validation
  checks as the rest of the codebase.
- Working with Python UUID and datetime types currently requires manual conversion and
  maintaining a mental model of the de-/serialization mechanism in `hexkit` `MongoDbDao`
  provider.
  - This is a disadvantage for `hexkit` developers as well as users of `hexkit` who write
  tests that might manually interact with the database. We are both.

*A final clarification:*
This ADR is not concerned with prescribing a standard for representing UUIDs or dates on
Pydantic models. If developers declare `foo_date: str` and `bar_id: str` in some places,
but `baz_date: UTCDatetime` and `qux_id: UUID4` in others, that's a separate discussion.
This ADR is about modifying `hexkit` to enable leveraging BSON support for UUIDs and dates.
In other words: When `hexkit` encounters a DTO containing a date or UUID value, what
should it do before passing the DTO's data to `pymongo`?

### Decision

We propose to stop converting DTOs' date- and UUID-typed fields to strings, which
results in pure JSON data, and instead pass them on to `pymongo` as they are so the
fields' data is stored as their respective BSON types. This requires modifications to
`hexkit`.

These changes mainly include:

- Set MongoDB to use the correct UUID representation (Binary Subtype 4) in the provider.
- MongoDB stores dates as UTC. We already require dates to be in UTC, but we
  must continue to ensure values are in UTC before storing them in the database.
  We will have to set the `tz_aware` parameter to `True` when creating MongoClient
  instances to ensure that `pymongo` returns unambiguous, tz-aware datetimes.
- Adding or adapting tests to verify the new functionality.

Existing Data:
A one-time data fix must be applied to migrate existing data to use the new formatting.
This will involve identifying the data, testing the migration process, and eventually
applying it to the production data. This data migration must be applied for all services
which currently use a database and which house data that contain dates and/or UUIDs in
BSON string representation. For the cleanest outcome, it makes the most sense for the
rollout of the new `hexkit` version to the services and the data migration(s)
to occur simultaneously.

### Consequences

Benefits:
- Improved Query Performance: Leveraging native data types allows MongoDB to use optimized
  indexes and query operators, resulting in faster query execution.
- Data Integrity and Validation: Storing data in its actual type (UUID or date) helps ensure
  only valid UUIDs and dates are stored, reducing the risk of data inconsistencies. This
  is a marginal benefit since we already do some validation, and the validation is not
  complex, but it is worth listing.
- Storage Efficiency: BSON dates and UUIDs are more compact than strings of the same data
  (128-bit unsigned integers for UUIDs, 64-bit integers for datetimes), decreasing
  storage requirements and index sizes.
- Sorting and Comparisons on Dates: No type-conversion is required to sort BSON dates or
  use any of the MongoDB operations available to use with dates, like `$dateDiff`.
- Developer experience: It's great to declare a UUID-typed field on a Pydantic
  model and know that the data remains the same roundtrip.
- Given that the metadata objects GHGA works with can be very large, a change that saves
  storage space and keeps documents further away from the 16 MB document limit of MongoDB
  is welcome when there are few disadvantages.

Drawbacks:
- Compatibility Issues: External systems or components that expect UUIDs and dates
  as strings may require adjustments or data conversion layers to ensure consistency.
  If two APIs return string representations of a date, we must ensure they both use
  the same conversion method (barring unique requirements, naturally).
- Codebase Adjustments: Modifications to existing code, tests, and documentation are
  necessary to support the new data handling approach, and would ideally be rolled out
  together to minimize the risk of problems. If we want to move a given service's DTO
  models over to UUID-typed fields, for example, then we will have to update the models
  and tests and apply a data fix. Not a big change for the service code though.
- Data migration: Ties with the point above, just from the database side.
  Existing data needs to be processed to use the new format. There is
  always a risk of data corruption when doing this, even with proper testing. We need to
  think about the various services and ensure their updates are coordinated in sync with
  the data migration.

### Alternatives

The primary alternative was to change nothing. We have implemented some flexibility
in `hexkit` so native UUIDs and datetimes can be used in queries without first being
converted in application code, but that was the extent of the "alternative". However,
the drawbacks enumerated above were enough to discourage this path.

### Addendum

This has since been implemented in `hexkit`. The MongoDB client is created with
`uuidRepresentation="standard"` and `tz_aware=True`, so that UUIDs and datetimes are
stored as their native BSON types and returned as timezone-aware values.
