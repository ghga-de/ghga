# State Management Service (Monkfish)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
The [Archive Test Bed](https://github.com/ghga-de/archive-test-bed) needs a way to
manage the state of various infrastructure technologies such as MongoDB, Apache Kafka,
S3, and the secrets vault. Namely, the needs are twofold:
- To set a predefined state before running the tests, for example:
  - Empty or prepopulate databases
  - Publish or delete events
  - Add a secret to the vault
  - Populate object(s) to an S3 bucket
  - Etc.
- To examine the state of the aforementioned technologies after or in between tests
 (whitebox testing)

Right now, there's not a clean way to achieve these needs.
A dedicated service can offer a simple solution and allow test bed 
processes to programmatically seed, reset, modify and examine databases through a
single RESTful API.

This service should **never** be deployed to production. It is *only* intended for use
in the Testing and Staging environments, where there is no access to real data.  
Despite this, there should be a way to restrict which databases and collections can be
accessed with this service through configuration, and a simple API key (set in config)
that can be used to authenticate requests.

### Included/Required:

> [!NOTE]
> The first release of the State Management Service (SMS) will focus on the functionality
> required for MongoDB, with extension to cover other technologies following thereafter.

## MongoDB
The implementation of the SMS should include a token-secured RESTful API that interacts
with MongoDB. There should be configuration to control access to databases and collections,
as well as an API Key for authentication.

Access control for database/collection resources should occur on a whitelist basis, with
further specification for the individual permissions granted at the collection level
for create, read, update, and delete.

Since database names in the testing environment feature a prefix for isolation, the
config should have a `db_prefix` value. This will be prefixed to all supplied database
names, meaning the full name doesn't have to be supplied by the user in configuration,
making the configuration more readable. It will also be added to all database names
supplied as path parameters, so the prefix only needs to be used once and all database
name specifications will be branch-agnostic.

`*` should be used as a wildcard equivalent to 'allow all'.  
For example, using the wildcard to specify permissions for a collection will allow all
CRUD operations on the collection. Permissions could be set for an entire database by
using the wildcard as the collection name with the desired permissions. Setting both
the collection and permission values to the wildcard would enable all operations for
the entire database.

If no database/collections are listed, then no operations will be allowed, even if
`db_prefix` is specified.

## Apache Kafka, S3, Vault

Similar to the fixture state reset logic featured in `hexkit`, the utilities available
for Apache Kafka should enable deleting and publishing records (events) in a topic.  
The advantage over using Kafka UI is that the SMS centralized state management for other
technologies and can be used programmatically. Additionally, the presence of the API
Key means the test bed application itself doesn't have to know the credentials for
Kafka UI or S3.

For each technology, REST API endpoints will be exposed, prefixed as follows:

| **Technology Name** | **Prefix**  |
|---------------------|-------------|
| MongoDB             | `/docs/`    |
| Apache Kafka        | `/events/`  |
| S3                  | `/objects/` |
| Vault               | `/secrets/` |

The branch isolation provided by the `db_prefix` config property for MongoDB should be
mirrored for Apache Kafka with the use of a `topic_prefix` config property.  
The `topic_prefix` will be prepended to all topic names referenced in the SMS.  
This kind of branch isolation is not currently used for S3 or the Vault.

All requests will be authenticated with the configured API Key.

### Not included:
Object schema validation for MongoDB would be complex to add because the models can come from a
variety of sources (`ghga-event-schemas`, service-specific models, etc.), and keeping
this service in sync with those definitions, either through config or code, would
incur a cost outweighing the benefits provided by the service.

Similarly, access control lists like the one described for MongoDB will not be
included for the other technologies.


## API Definitions:

The following REST endpoints will be created for manipulating MongoDB.  
The endpoints for Apache Kafka, S3, and the Vault will be similar, and they will
be included in a update to this document in the near future.

- `GET /docs/{db-name}/{collection-name}`
  - *Returns all or some documents from the collection.*
  - Query string (optional):
    - Filter parameters to refine results, e.g. `user_id=123&role=supervisor` 
  - Authorization header: API Key (set in configuration)
  - Response body: list of resources in the collection matching the specified criteria
  - Response status: 
    - `200 OK`: Request successfully processed, results in response body
    - `401 Unauthorized`: auth error (not authenticated)
    - `403 Forbidden`: Authenticated, but config prevents operation
    on the specified collection.
- `PUT /docs/{db-name}/{collection-name}`
  - *Upserts the document(s) provided in the request body in the specified collection.*
  - Request body:
    - Single document to upsert, or array of documents for batch upsertion
  - Authorization header: API Key (set in configuration)
  - Response body: Empty
  - Response status:
    - `204 No Content`: Document(s) successfully upserted
    - `401 Unauthorized`: auth error (not authenticated)
    - `403 Forbidden`: Authenticated, but config prevents operation
    on the specified collection.
- `DELETE /docs/{db-name}/{collection-name}`
  - *Deletes all or some documents in the collection.*
  - Query string (optional):
    - Filter parameters to refine deletion, e.g. `user_id=123&name=keith`
  - Authorization header: API Key (set in configuration)
  - Response body: Empty
  - Response status: 
    - `204 No Content`: Document(s) did not exist or were successfully deleted
    - `401 Unauthorized`: Auth error (not authenticated)
    - `403 Forbidden`: Authenticated, but config prevents operation
    on the specified collection.


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
