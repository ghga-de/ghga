[![tests](https://github.com/ghga-de/metldata/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/metldata/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/metldata/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/metldata?branch=main)

# Metldata

metldata - A framework for handling metadata based on ETL, CQRS, and event sourcing.

## Description

Metldata is a framework for handling the entire lifetime of metadata by addressing the
a complex combination of challenges that makes it suitable especially for public
archives for sensitive data:

![Schematic reprensentation of challenges.](./images/challenges.png)
**Figure 1| Overview of the combination of challenges during metadata handling.**

### Immutability
It is guaranteed that data entries do not change over time making reproducibility
possible without having to rely on local snapshots.

### Accessibility
A stable accession is assigned to each resource. Together with the immutability
property, this guarantees that you will always get the same data when querying with the
same accession.

### Corrections, Improvements, Extensions

Even though data is stored in an immutable way, the metldata still allows for
corrections, improvements, and extensions of submitted data. This is achieved my not
just storing the current state of a submission but by persisting a version history.
Thereby, modifications are realized by issuing a new version of the submission without
affecting the content of existing versions.

### Transparency

The version history not only resolved the conflict between immutability and the need to
evolve and adapt data, it also make the changes transparent to user relying on the data.

### Multiple Representations

Often, the requirements regarding the structure and content of data differs depending
the use case and the audience. Metldata accounts for this by proving a configurable
workflow engine for transforming submitted metadata into multiple representation of that
data.

### GDPR Compliance

The GDPR gives data subjects the right to issue a request to delete data. Metldata
complies with this demand. Thereby, only entire versions of a submission can be deleted.
The associated accessions stay available so that user are informed that the associated
data is not available anymore. The guarantees for immutability and stability of
accessions are not violated, however, data might become unavailable.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/metldata):
```bash
docker pull ghga/metldata:3.2.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/metldata:3.2.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/metldata:3.2.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
metldata --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"metldata"`.

- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service. A globally unique Kafka client ID will be created by concatenating the service_name and the service_instance_id.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


- <a id="properties/log_format"></a>**`log_format`**: If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details. Default: `null`.

  - **Any of**

    - <a id="properties/log_format/anyOf/0"></a>*string*

    - <a id="properties/log_format/anyOf/1"></a>*null*


  Examples:

  ```json
  "%(timestamp)s - %(service)s - %(level)s - %(message)s"
  ```


  ```json
  "%(asctime)s - Severity: %(levelno)s - %(msg)s"
  ```


- <a id="properties/log_traceback"></a>**`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages. Default: `true`.

- <a id="properties/mongo_dsn"></a>**`mongo_dsn`** *(string, format: multi-host-uri, required)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/. Length must be at least 1.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- <a id="properties/db_name"></a>**`db_name`** *(string, required)*: Name of the database located on the MongoDB server.


  Examples:

  ```json
  "my-database"
  ```


- <a id="properties/mongo_timeout"></a>**`mongo_timeout`**: Timeout in seconds for API calls to MongoDB. The timeout applies to all steps needed to complete the operation, including server selection, connection checkout, serialization, and server-side execution. When the timeout expires, PyMongo raises a timeout exception. If set to None, the operation will not time out (default MongoDB behavior). Default: `null`.

  - **Any of**

    - <a id="properties/mongo_timeout/anyOf/0"></a>*integer*: Exclusive minimum: `0`.

    - <a id="properties/mongo_timeout/anyOf/1"></a>*null*


  Examples:

  ```json
  300
  ```


  ```json
  600
  ```


  ```json
  null
  ```


- <a id="properties/kafka_servers"></a>**`kafka_servers`** *(array, required)*: A list of connection strings to connect to Kafka bootstrap servers.

  - <a id="properties/kafka_servers/items"></a>**Items** *(string)*


  Examples:

  ```json
  [
      "localhost:9092"
  ]
  ```


- <a id="properties/kafka_security_protocol"></a>**`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. Must be one of: `["PLAINTEXT", "SSL"]`. Default: `"PLAINTEXT"`.

- <a id="properties/kafka_ssl_cafile"></a>**`kafka_ssl_cafile`** *(string)*: Certificate Authority file path containing certificates used to sign broker certificates. If a CA is not specified, the default system CA will be used if found by OpenSSL. Default: `""`.

- <a id="properties/kafka_ssl_certfile"></a>**`kafka_ssl_certfile`** *(string)*: Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity. Default: `""`.

- <a id="properties/kafka_ssl_keyfile"></a>**`kafka_ssl_keyfile`** *(string)*: Optional filename containing the client private key. Default: `""`.

- <a id="properties/kafka_ssl_password"></a>**`kafka_ssl_password`** *(string, format: password, write-only)*: Optional password to be used for the client private key. Default: `""`.

- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- <a id="properties/kafka_max_message_size"></a>**`kafka_max_message_size`** *(integer)*: The largest message size that can be transmitted, in bytes, before compression. Only services that have a need to send/receive larger messages should set this. When used alongside compression, this value can be set to something greater than the broker's `message.max.bytes` field, which effectively concerns the compressed message size. Exclusive minimum: `0`. Default: `1048576`.


  Examples:

  ```json
  1048576
  ```


  ```json
  16777216
  ```


- <a id="properties/kafka_compression_type"></a>**`kafka_compression_type`**: The compression type used for messages. Valid values are: None, gzip, snappy, lz4, and zstd. If None, no compression is applied. This setting is only relevant for the producer and has no effect on the consumer. If set to a value, the producer will compress messages before sending them to the Kafka broker. If unsure, zstd provides a good balance between speed and compression ratio. Default: `null`.

  - **Any of**

    - <a id="properties/kafka_compression_type/anyOf/0"></a>*string*: Must be one of: `["gzip", "snappy", "lz4", "zstd"]`.

    - <a id="properties/kafka_compression_type/anyOf/1"></a>*null*


  Examples:

  ```json
  null
  ```


  ```json
  "gzip"
  ```


  ```json
  "snappy"
  ```


  ```json
  "lz4"
  ```


  ```json
  "zstd"
  ```


- <a id="properties/kafka_max_retries"></a>**`kafka_max_retries`** *(integer)*: The maximum number of times to immediately retry consuming an event upon failure. Works independently of the dead letter queue. Minimum: `0`. Default: `0`.


  Examples:

  ```json
  0
  ```


  ```json
  1
  ```


  ```json
  2
  ```


  ```json
  3
  ```


  ```json
  5
  ```


- <a id="properties/kafka_enable_dlq"></a>**`kafka_enable_dlq`** *(boolean)*: A flag to toggle the dead letter queue. If set to False, the service will crash upon exhausting retries instead of publishing events to the DLQ. If set to True, the service will publish events to the DLQ topic after exhausting all retries. Default: `false`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- <a id="properties/kafka_dlq_topic"></a>**`kafka_dlq_topic`** *(string)*: The name of the topic used to resolve error-causing events. Default: `"dlq"`.


  Examples:

  ```json
  "dlq"
  ```


- <a id="properties/kafka_retry_backoff"></a>**`kafka_retry_backoff`** *(integer)*: The number of seconds to wait before retrying a failed event. The backoff time is doubled for each retry attempt. Minimum: `0`. Default: `0`.


  Examples:

  ```json
  0
  ```


  ```json
  1
  ```


  ```json
  2
  ```


  ```json
  3
  ```


  ```json
  5
  ```


- <a id="properties/resource_change_topic"></a>**`resource_change_topic`** *(string, required)*: Name of the topic used for events informing other services about resource changes, i.e. deletion or insertion.


  Examples:

  ```json
  "searchable_resources"
  ```


- <a id="properties/resource_deletion_type"></a>**`resource_deletion_type`** *(string, required)*: Type used for events indicating the deletion of a previously existing resource.


  Examples:

  ```json
  "searchable_resource_deleted"
  ```


- <a id="properties/resource_upsertion_type"></a>**`resource_upsertion_type`** *(string, required)*: Type used for events indicating the upsert of a resource.


  Examples:

  ```json
  "searchable_resource_upserted"
  ```


- <a id="properties/dataset_change_topic"></a>**`dataset_change_topic`** *(string, required)*: Name of the topic announcing, among other things, the list of files included in a new dataset.


  Examples:

  ```json
  "metadata_datasets"
  ```


- <a id="properties/dataset_deletion_type"></a>**`dataset_deletion_type`** *(string, required)*: Event type used for communicating dataset deletions.


  Examples:

  ```json
  "dataset_deleted"
  ```


- <a id="properties/dataset_upsertion_type"></a>**`dataset_upsertion_type`** *(string, required)*: Event type used for communicating dataset upsertions.


  Examples:

  ```json
  "dataset_upserted"
  ```


- <a id="properties/primary_artifact_name"></a>**`primary_artifact_name`** *(string, required)*: Name of the artifact from which the information for outgoing change events is derived.


  Examples:

  ```json
  "embedded_public"
  ```


- <a id="properties/primary_dataset_name"></a>**`primary_dataset_name`** *(string, required)*: Name of the resource class corresponding to the embedded_dataset slot.


  Examples:

  ```json
  "EmbeddedDataset"
  ```


- <a id="properties/host"></a>**`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.

- <a id="properties/port"></a>**`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- <a id="properties/auto_reload"></a>**`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.

- <a id="properties/workers"></a>**`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- <a id="properties/api_root_path"></a>**`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `""`.

- <a id="properties/openapi_url"></a>**`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `"/openapi.json"`.

- <a id="properties/docs_url"></a>**`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `"/docs"`.

- <a id="properties/cors_allowed_origins"></a>**`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_origins/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_origins/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_origins/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allow_credentials"></a>**`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allow_credentials/anyOf/0"></a>*boolean*

    - <a id="properties/cors_allow_credentials/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allowed_methods"></a>**`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_methods/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_methods/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_methods/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "*"
  ]
  ```


- <a id="properties/cors_allowed_headers"></a>**`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_headers/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_headers/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_headers/anyOf/1"></a>*null*


  Examples:

  ```json
  []
  ```


- <a id="properties/artifact_infos"></a>**`artifact_infos`** *(array, required)*: Information for artifacts to be queryable via the Artifacts REST API.

  - <a id="properties/artifact_infos/items"></a>**Items**: Refer to *[#/$defs/ArtifactInfo](#%24defs/ArtifactInfo)*.

- <a id="properties/loader_token_hashes"></a>**`loader_token_hashes`** *(array, required)*: Hashes of tokens used to authenticate for loading artifact.

  - <a id="properties/loader_token_hashes/items"></a>**Items** *(string)*

## Definitions


- <a id="%24defs/AnchorPoint"></a>**`AnchorPoint`** *(object)*: A model for describing an anchor point for the specified target class.

  - <a id="%24defs/AnchorPoint/properties/target_class"></a>**`target_class`** *(string, required)*: The name of the class to be targeted.

  - <a id="%24defs/AnchorPoint/properties/identifier_slot"></a>**`identifier_slot`** *(string, required)*: The name of the slot in the target class that is used as identifier.

  - <a id="%24defs/AnchorPoint/properties/root_slot"></a>**`root_slot`** *(string, required)*: The name of the slot in the root class used to link to the target class.

- <a id="%24defs/ArtifactInfo"></a>**`ArtifactInfo`** *(object)*: Model to describe general information on an artifact.
Please note, it does not contain actual artifact instances derived from specific
metadata.

  - <a id="%24defs/ArtifactInfo/properties/name"></a>**`name`** *(string, required)*: The name of the artifact.

  - <a id="%24defs/ArtifactInfo/properties/description"></a>**`description`** *(string, required)*: A description of the artifact.

  - <a id="%24defs/ArtifactInfo/properties/resource_classes"></a>**`resource_classes`** *(object, required)*: A dictionary of resource classes for this artifact. The keys are the names of the classes. The values are the corresponding class models. Can contain additional properties.

    - <a id="%24defs/ArtifactInfo/properties/resource_classes/additionalProperties"></a>**Additional properties**: Refer to *[#/$defs/ArtifactResourceClass](#%24defs/ArtifactResourceClass)*.

- <a id="%24defs/ArtifactResourceClass"></a>**`ArtifactResourceClass`** *(object)*: Model to describe a resource class of an artifact.

  - <a id="%24defs/ArtifactResourceClass/properties/name"></a>**`name`** *(string, required)*: The name of the metadata class.

  - <a id="%24defs/ArtifactResourceClass/properties/description"></a>**`description`**: A description of the metadata class. Default: `null`.

    - **Any of**

      - <a id="%24defs/ArtifactResourceClass/properties/description/anyOf/0"></a>*string*

      - <a id="%24defs/ArtifactResourceClass/properties/description/anyOf/1"></a>*null*

  - <a id="%24defs/ArtifactResourceClass/properties/anchor_point"></a>**`anchor_point`**: The anchor point for this metadata class. Refer to *[#/$defs/AnchorPoint](#%24defs/AnchorPoint)*.

  - <a id="%24defs/ArtifactResourceClass/properties/json_schema"></a>**`json_schema`** *(object, required)*: The JSON schema for this metadata class. Can contain additional properties.


### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.metldata.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.metldata.yaml`)
- in your home directory (on Linux: `~/.metldata.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `metldata_`,
e.g. for the `host` set an environment variable named `metldata_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.



## Architecture and Design:
The framework uses a combination of ETL, CQRS, and event sourcing. Currently it is
designed to mostly run as a CLI application for managing metadata on the local file
system. However, later, it will be translated into a microservice based-architecture.

### One Write and Multiple Read Representations

Instead of having just a single copy of metadata in a database that
supports all CRUD actions needed by all the different user groups, we
propose to follow the CQRS pattern by having one representation that is
optimized for write operations and multiple use case-specific
representations for querying metadata. Thereby, the write-specific
representation is the source of truth and fuels all read-specific
representations through an ETL process. In the following, the
read-specific representations are also referred to as artifacts.

This setup with one write and multiple read representation has the
following advantages:

- Different subsets of the entire metadata catalog can be prepared
  with the needs and the permissions of different user audiences in
  mind.
- It allows for independent scalability of read and write operations.
- The metadata can be packaged in multiple different formats required
  and optimized for different technologies and use cases, such as
  indexed searching with ElasticSearch vs. REST or GraphQL queries
  supported by MongoDB.
- Complex write-optimized representations, which are inconvenient for
  querying such as event histories, can be used as the source of
  truth.
- Often used metadata aggregations and summary statistics can be
  precomputed.
- Read-specific representations may contain rich annotations that are
  not immediately available in the write-specific representation. For
  instance, the write-specific representation may only contain one-way
  relationships between metadata elements (e.g. a sample might define
  a `has_experiment` attribute, while an experiment defines no
  `has_sample` attribute), however, a read-specific representation may
  contain two way relationships (e.g. a sample defines a
  `has_experiment` attribute and an experiment defines a `has_sample`
  attribute).

However, there are also disadvantages that are linked to this setup that
should be considered:

- The write and read representations are only eventually consistent.
- Adds more complexity than a CRUD setup.

### Submission-centric Store as The Source of Truth

In the write-specific representation, metadata is packaged into
submissions. Each submission is fully self-contained and linking between
metadata of different submissions is not possible. A submission can have
one of the following statuses:

- pending - the construction of the submission is in progress, the
  submitter may still change its content.
- in-review - the submitter declared the submission as complete and is
  waiting for it to be reviewed, however, both the submitter and the
  reviewer can set this submission back to pending to enable further
  changes.
- canceled - the submission was canceled before its completion, its
  content was deleted.
- completed - the submission has been reviewed and approved, the
  content of the submission is frozen, and accessions are generated
  for all relevant metadata elements.
- deprecated-prepublication - the submission was deprecated and it
  cannot be published anymore, however, its content is not deleted
  from the system.
- emptied-prepublication - the submission was deprecated and its
  content was deleted from the system, however, the accessions are not
  deleted.
- published - the submission was made available to other users.
- deprecated-postpublication - the submission was deprecated and it
  should not be used anymore, however, its content stays available to
  other users.
- hidden-postpublication - the submission was deprecated and its
  content is hidden from other users but it is not deleted from the
  system, the accessions stay available, the submission can be set to
  deprecated to make its content available again.
- emptied-postpublication - the submission was deprecated and its
  content was deleted from the system, however, the accessions stay
  available.

The following status transitions are allowed:

- pending -\> in-review
- pending -\> canceled
- in-review -\> completed
- in-review -\> canceled
- in-review -\> pending
- completed -\> published
- completed -\> deprecated-prepublication
- completed -\> emptied-prepublication
- deprecated-prepublication -\> emptied-prepublication
- published -\> deprecated-postpublication
- published -\> hidden-postpublication
- published -\> emptied-postpublication
- deprecated-postpublication -\> hidden-postpublication
- deprecated-postpublication -\> emptied-postpublication
- hidden-postpublication -\> deprecated-postpublication
- hidden-postpublication -\> emptied-postpublication

A deprecated submission may or may not be succeeded by a new submission.
Thereby, the new submission may reuse (a part of) the metadata from the
deprecated submission. The reused metadata including the already
existing accessions is copied over to the new submission so that the
contents of the deprecated submission and the new submission can be
handled independently, for instance, the deprecated submission being
emptied.

### Event Sourcing to Generate Artifacts

To implement the ETL processes that generate read-specific artifacts
from the write-specific representation explained above, we propose an
event-sourcing mechanism.

The creation and each status change of a given submission (and
accommodating changes to the submission\'s content) are translated into
events. The events are cumulative and idempotent so you only have to
consume the latest event for a given submission in order to get the
latest state of that submission and a replay of the events will lead to
the same result. Thus, the event history only needs to keep the latest
event for each submission as implemented in the compacted topics offered
by Apache Kafka.

Moreover, since submissions are self-contained and do not depend on the
content of other submissions, events of different submissions can be
processed independently.

Multiple transformations (as in the ETL pattern) are applied to these
so-called source events to generate altered metadata representations
that are in turn published as events. These derived events can be again
subjected to further transformations.

Finally, the derived events are subject to load operations (as in the
ETL pattern) that aggregate the events and bring them into queryable
format (an artifact) that is accessible to users through an API.

### Metadata Modeling and Model Updates

Metadata requirements are modeled using LinkML. Thereby, the metadata
model should take the whole metadata lifecycle into account so that it
can be used to validate metadata before and after the submission as well
as for all derived artifacts.

Updates to the metadata model are classified into minor and major ones.
For minor updates, existing submissions are automatically migrated. The
submission always stores metadata together with the used metadata model.
The migration is realized through scripts that migrate metadata from an
old version to a newer version. Multiple migration scripts may be
combined to obtain a metadata representation that complies with the
newest version. The migration can be implemented as a transformation
that is applied to the source events as explained above.


## Development

For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of VS Code
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as VS Code with its "Remote - Containers"
extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in VS Code and run the command
`Remote-Containers: Reopen in Container` from the VS Code "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant VS Code extensions pre-installed
- pre-configured linting and auto-formatting
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, a command `dev_install` is available for convenience.
It installs the service with all development dependencies, and it installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`./requirements-dev.txt`](./requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [`readme_generation.md`](./readme_generation.md)
for details.
