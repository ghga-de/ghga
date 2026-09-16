# Correlation ID Implementation (Marabou Stork)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
The aim of this epic is to implement the functionality required to use interservice
correlation IDs for tracking request flows.
Please see the prototype [here](https://github.com/ghga-de/prototype-correlation-id).

### Included/Required:
- Generate Correlation ID in API Gateway
- Correlation ID Utilities in Hexkit
- Correlation ID in Kafka Event Header
- Middleware for FastAPI Apps
- Pilot Repositories

### Not Included:
- Updating services to use correlation IDs


## Additional Implementation Details:

### Generate Correlation ID in API Gateway
The API Gateway will need to be updated with functionality to ensure every request has
a correlation ID in the header.

### Correlation ID Utilities in Hexkit
In the prototype, we decided to use a ContextVar to store correlation IDs.
This ContextVar needs to be created in a top-level module in either `hexkit`
or `ghga-service-commons`. If it would be created in `ghga-service-commons`, then `hexkit`
would need to import from there and have `ghga-service-commons` as a dependency, which we
want to avoid since it should be a universal framework (also, we already have an inverse
dependency, so we would create a circular dependency). This means the ContextVar must be
created in `hexkit`, which should be added as a dependency in `ghga-service-commons[api]`.

The following are needed in `hexkit`:
- A function to create new correlation IDs.
- A ContextVar to store the correlation ID.
- An asynccontextmanager to set the correlation ID ContextVar to a given value,
yield it, and then reset it to its previous state (via a token that was created
when setting the value).
- A function to retrieve the value stored in the ContextVar for the current context
and raise an error if none is found.
- A function that validates a correlation ID value, raising an error if the value is
empty or does not have the expected format.

### Correlation ID in Kafka Event Header
There needs to be a way to supply the correlation ID as a Kafka event header.
If the correlation ID is not supplied, one should be generated,
but only if a flag has been explicitly set. Otherwise, an error should be raised.
To that end, `hexkit` needs to be updated so the correlation ID is retrieved
from the ContextVar for the current context and added as a header inside of the
`_publish_validated()` method of the `KafkaEventPublisher` class.
To support testing, a boolean parameter should be added to the `KafkaConfig` class.
The boolean should be used by `KafkaEventPublisher` to control the publishing behavior
so that either:
1. A valid correlation ID ContextVar value is required (raising an error otherwise), or
2. A valid correlation ID will be generated if the ContextVar's value is the empty string.
In both cases, an invalid ID should result in an error.

The `_consume_event()` method in the `KafkaEventSubscriber` class needs to be updated
to extract the correlation ID from the header, validate it (raising an error if
invalid), and set the ContextVar before calling `self._translator.consume()`
If the no header for correlation ID is found, the event should be ignored.

### Middleware for FastAPI Apps
A new middleware function for FastAPI apps should be added to `ghga-service-commons`
to validate correlation IDs upon receiving requests. All requests should have a
correlation ID already set by the gateway, so no logic is needed for ID generation.
If the correlation ID is missing or invalid, an error should be raised.
However, `ApiConfigBase` should get a new parameter to instruct the middleware to
generate a new ID (using the function from `hexkit`) rather than raising an error.
This way, testing can be carried out without an API gateway.
After getting the validated correlation ID, the middleware should set the correlation
ID ContextVar using the utility created in `hexkit`. Doing so will allow services to
retrieve the correlation ID from the ContextVar without any extra work.

### Pilot Repositories
A pair of repositories (which is to be determined) will be updated as part of this epic.
The purpose of this is to verify the aforementioned changes and identify any problems
before rolling out the changes to other services. This should include one repository that utilizes
a FastAPI app and a Kafka producer, and another that features a Kafka consumer to process events published by the former.

Examples of such pairings:
- `metldata` and Metadata Artifact Search Service (`mass`)
- File Ingest Service (`fis`) and the Internal File Registry Service (`ifrs`)
- Access Request Service (`ars`) and the Notification Service (`ns`)

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
