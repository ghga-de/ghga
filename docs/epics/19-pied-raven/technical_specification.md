# File Encryption & Decryption Service Integration (Pied Crow)
**Epic Type:** Implementation Epic


## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/4AC2D
## User Journeys

Building on the [*18 - Hooded Crow*](../18-hooded-crow/technical_specification.md) epic, this epic aims to finish the work started on the encryption & decryption services, integrating them into the wider GHGA microservice landscape and resolving remaining questions and issues.

### 1. Enable Encryption Key Store service to use HashiCorp Vault for secure storage and retrieval of file secrets
File secrets are currently stored in a MongoDB attached to the Encryption Key Store.
For safe storage concerns this should be replaced with HashiCorp Vault instead.
The API should allow to store a secret and return a newly generated ID by which this secret can be retrieved.

Implementing this change includes multiple steps:

1. Eplore how to set up HashiCorp Vault for our use case - see also https://wiki.verbis.dkfz.de/x/SoKcCw for what has already been done
2. Explore how to connect, store and retrieve secrets
3. Implement a HashiCorp vault setup for development (.devcontainer) and testing (python-testcontainers).

### 2. Finalize request/response models and incoming/outgoing events
While models and events exist for all the necessary cross-service communication, some have a more prototypical character and might need updates to their definition based on spec compliance or practical concerns.
Those updates should be applied after all services can communicate with each other.
This includes moving (remaining) in-service event definitions to the https://github.com/ghga-de/ghga-event-schemas repository.

### 3. Provide a local testbed covering all services using docker-compose
As all services dealing with file upload/download/encryption/decryption interact with each other, either during upload or download, a local setup to test functionality across all services would be beneficial.
This would allow to capture issues early and replace mocks with actual data to see how well our microservice architecture performs.

The implementation of this journey consists of:
- a docker-compose for local deployment of all services along with relying infrastructure (MongoDB, HashiCorp Vault, Apache Kafka, LocalStack S3)
- one or more minimal test cases that set up certain states in the infrastructure and simulate a basic user journey involving all the services

## Optional User Journeys:
### Integrate with and adapt adjacent services
Both the Encryption Key Store and the Interrogation Room depend on (synchronous and asynchronous) communication with other services.
Interaction with the respective service on side of the caller/receiver is not implemented yet.
Check and adjust all of the following services:

1. Upload Controller - outbound event signaling file upload completed to Interrogation Room
2. Upload Controller - handling of failure event from Interrogation Room
3. Internal File Registry - handling of success event from Interrogation Room
4. Download Controller - request and receive envelope, attach envelope to outgoing file cotent
## User Journeys that are not part of this Epic:
### Decide on user public key propagation/storage/retrieval mechanism
Currently a user's public key is piped through the interrogation room into the encryption key store.
We need to discuss specifics of public key propagation and storage, as this permeates some of the models/events and issues like source of truth and expulsion of keys need to be resolved.
However, this might be more fitting to consider in conjunction with a refactoring step for integration with the auth story.

## API Definitions:

### RESTful/Synchronous:
[Encryption Key Store REST API](./api_definitions/rest/encryption_key_store.yml) - [Swagger UI](https://editor.swagger.io/?url=https://raw.githubusercontent.com/ghga-de/epic-docs/main/19-pied-raven/api_definitions/rest/encryption_key_store.yml) - This supersedes the 18 Hooded Crow version.

## Additional Implementation Details:


## Human Resource/Time Estimation:

Number of sprints required: 2-3

Number of developers required: 3
