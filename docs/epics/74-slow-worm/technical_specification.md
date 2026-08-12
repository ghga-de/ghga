# Hexkit Support for BSON UUIDs and Datetimes (Slow Worm)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope
### Outline:
The aim of this epic is to stop serializing UUIDs and datetime objects as strings in
`hexkit` and instead allow `pymongo` to serialize them to BSON directly, as decided in
the ADR "[UUID and Datetime Representation in MongoDB](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr011_uuids_datetimes_mongodb.md)".

The `hexkit` changes for this epic should be released with the
[Eurasian Blackbird](../75-eurasian-blackbird/technical_specification.md) `hexkit`
changes. 

### Included/Required:
- Update `hexkit` to remove string serialization for UUIDs and datetimes, as well as
  add support for BSON UUID and Date types in MongoDB providers.
- Update `hexkit` to replace `motor` with the async tools from `pymongo`.
- Rollout:
  - Update `ghga-service-commons`, then `ghga-event-schemas`, then other services:
    - Update to new `hexkit` version
    - Update references to `correlation_id` that are str-typed
    - Replace string UUIDs and Datetimes in tests and service code
    - Write migrations for all services that store UUIDs and Datetimes as strings
  
### Deployment Note:
The `NS`'s `notifications` collection should be dropped once deployment is
complete (see below).

## API Definitions:

### Payload Schemas for Events:

Models Containing String Datetimes or UUIDs in `ghga-event-schemas`:
- UploadDateModel
- FileUploadReceived
- FileUploadValidationSuccess
- FileUploadValidationFailure
- FileInternallyRegistered
- FileRegisteredForDownload
- NonStagedFileRequested
- FileStagedForDownload
- FileDownloadServed
- UserID
- User
- AccessRequestDetails
- UserIvaState


## Additional Implementation Details:

### Hexkit

Changes needed:
- Remove UUID and datetime-specific string serialization in the MongoDB provider
- Set MongoDB to use the correct UUID representation (Binary Subtype 4) in the provider.
- MongoDB stores dates as UTC. We already require dates to be in UTC, but we
  must continue to ensure values are in UTC before storing them in the database.
  We will have to set the `tz_aware` parameter to `True` when creating MongoClient
  instances to ensure that `pymongo` returns tz-aware datetimes that will always have a
  UTC timezone.
  This could be an optional config parameter defaulting to `True` or an opinionated,
  hardcoded choice for `hexkit`.
- Changes must be reflected in both `MongoKafkaDaoPublisherFactory.construct()` and
    `MongoDbDaoFactory.__init__()`.
- Adding or adapting tests to verify the new functionality. Tests should also verify
  that publishing DTOs to Kafka still works, especially in the case of the MongoKafka
  provider.
- Update Correlation ID canonical type to `UUID` (from `str`)
- The async client driver we've used for accessing MongoDB, `motor`, is being deprecated
  next year. The official recommendation is to move to `pymongo`'s asynchronous tools.
  This entails replacing usage of `motor`'s classes for clients, collections, databases,
  etc. with the async `pymongo` equivalents. Pymongo Async produces more verbose output
  if you don't clean up the connections (e.g. in tests), so there are some other
  changes involved beyond merely swapping the classes, but they are not too disruptive.
  For example, we can wrap client access in a context manager to close clients once
  we're finished with them. The work for replacing `motor` will have its own PR.

### Database Migrations:

We need to author migrations for any services storing str-based UUID or Datetime fields.
This not only includes models defined in `ghga-event-schemas` or the services 
themselves, but also any persisted event data due to the `created` field.
Stored correlation IDs have to be updated, too, though this primarily affects
outbox publishers. 

The `NS` currently stores correlation IDs as part of its idempotence
check, but that will be supplanted in the Eurasian Blackbird epic. As a result, it
shouldn't be migrated. If problematic, we can disable tests temporarily to satisfy CI 
checks until both epics are complete.

List of services that require migrations:
- IFRS
- FIS
- DCS
- WPS
- DLQS
- ARS
- Auth-Service (User Registry and Claims Repository)
- NOS

Other services don't need migrations, but do require being updated to the newest
version of `hexkit`.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1-2
