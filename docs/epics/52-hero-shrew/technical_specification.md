# Outbox Pattern Refactoring (Hero Shrew)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).


## Scope
### Outline:
The outbox pattern must be applied to our microservices in order to back up Kafka events,
but not every event needs to be saved in the database. Rather, we can apply the outbox
pattern strategically by backing up just the initial events in a request flow.
The services that generate the first event in a request flow should be fitted
with outbox publishers, and the corresponding consumers of such events should be fitted
with outbox subscribers. By doing this, only the initial events need to be backed up. A
republishing and reprocessing of these events should then result in the re-creation of 
all transitive events, as far as idempotence allows.

The outbox pattern may be implemented to make information about domain objects available
to services beyond the primary owning service, but that is outside the scope of *this*
epic, which is concerned only with the implementation of the outbox subscriber as a
backup mechanism for Kafka events.

### Included/Required:
- Implementation of the outbox pattern in the following:
  - Download Controller Service
  - Upload Controller Service
  - Purge Controller Service
  - Internal File Registry Service
  - Interrogation Room Service
  - File Ingest Service
- Any modifications to other services required for the purpose of achieving idempotence
- Testing


## Additional Implementation Details:

The following services need the outbox *publisher* implemented for the listed events:

| Service             | Events                                                     |
|---------------------|------------------------------------------------------------|
| Upload Controller   | FileUploadReceived (consumed by the IRS)                   |
| Download Controller | NonStagedFileRequested (consumed by the IFRS)              |
| Purge Controller    | FileDeletionRequested (consumed by the IFRS, UCS, and DCS) |
| File Ingest         | FileUploadValidationSuccess (consumed by the IFRS)         |
| Interrogation Room  | FileUploadValidationSuccess (consumed by the IFRS)         |


The following services need the outbox *subscriber* implemented for the listed events:

| Service                | Events                 |
|------------------------|------------------------|
| Interrogation Room     | FileUploadReceived     |
| Internal File Registry | NonStagedFileRequested |
|                        | FileDeletionRequested  |
|                        | FileUploadValidationSuccess  |
| Download Controller    | FileDeletionRequested  |
| Upload Controller      | FileDeletionRequested  |



## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
