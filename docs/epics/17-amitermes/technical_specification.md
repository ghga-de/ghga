# Hexagonal File Service Refactoring (Amitermes)

**Epic Type:** Implementation Epic

## Scope

Hexagonal refactoring of File Services to:
- Migrate to Apache Kafka and MongoDB
- Execute asynchronously
- Update domain logic
- Achieve consistency between services

## Implementation Details

The following services will be affected:
- Upload Controller Service (UCS)
- DRS3 / Download Controller Service (DCS)
- Internal File Registry Service (IFRS)

In addition to that, changes to following repositories will be required:
- hexkit
- ghga-message-schemas / ghga-event-schemas

Refactoring aims:
- [ghga-message-schemas] rename the repo to ghga-event-schemas
- [DRS3] rename the repo to Download Repository Service (DCS)
- [DCS] migrate from pyramid to FastAPI
- [DCS] use httpyexpect to format exceptions
- migrate all services from PostgreSQL to MongoDB
- migrate all services form RabbitMQ to Apache Kafka
- use triple hexagonal components for interactions with the Database, the Event Broker,
and the Object Storage
- [hexkit] add multipart copy method to the Object Storage Protocol and corresponding
  providers
- [hexkit] add schema validation before sending and upon receiving events
- harmonize the domain logic of all services with the [File Validation and Encryption 
  Concept](https://github.com/ghga-de/arch_concepts/blob/main/file_validation_and_encryption.md):
  - use SHA-256-based content ID as file identifiers
  - adapt event schemas
  - [IFRS] perform a multipart copy between buckets when registering new files as part
    of an upload or staging files as part of a download

### Not Included
- file encryption or validation-specific logic
- authentication and authorization


## Time Estimation

- Start: September 27th
- Due: October 14th

(Overlapping with the Annual Meeting.)
