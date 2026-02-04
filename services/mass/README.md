[![tests](https://github.com/ghga-de/mass/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/mass/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/mass/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/mass?branch=main)

# Mass

Metadata Artifact Search Service - A service for searching metadata artifacts and filtering results.

## Description

The Metadata Artifact Search Service uses search parameters to look for metadata.

### Quick Overview of API
The API provides two not strictly RESTful endpoints:

One endpoint ("GET /search-options") will return an overview of all metadata classes
that can be targeted by a search.

The actual search endpoint ("GET /search") can be used to search for these target classes
using keywords. Hits will be reported in the context of the selected target class.
This means that target classes will be reported that match the specified search query,
however, the target class might contain embedded other classes and the match might
occur in these embedded classes, too.

Along with the hits, facet options are reported that can be used to filter down the hits by
performing the same search query again but with specific facet selections being set.

The search endpoint supports pagination to deal with a large number of search results.
Facet options can help avoid having to rely on this feature by filtering down the number
of hits to a single page.

For more information see the OpenAPI spec linked below.


## Installation

We recommend using the provided Docker container.

A pre-built version is available on [Docker Hub](https://hub.docker.com/repository/docker/ghga/mass):
```bash
docker pull ghga/mass:6.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/mass:6.1.0 .
```

For production-ready deployment, we recommend using Kubernetes.
However for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is pre-configured:
docker run -p 8080:8080 ghga/mass:6.1.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
mass --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.
- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"mass"`.
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
- <a id="properties/searchable_classes"></a>**`searchable_classes`** *(object, required)*: A collection of searchable_classes with facetable and selected fields. Can contain additional properties.
  - <a id="properties/searchable_classes/additionalProperties"></a>**Additional properties**: Refer to *[#/$defs/SearchableClass](#%24defs/SearchableClass)*.
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

- <a id="properties/kafka_servers"></a>**`kafka_servers`** *(array, required)*: A list of connection strings to connect to Kafka bootstrap servers.
  - <a id="properties/kafka_servers/items"></a>**Items** *(string)*

  Examples:
  ```json
  [
      "localhost:9092"
  ]
  ```

- <a id="properties/kafka_security_protocol"></a>**`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. Must be one of: "PLAINTEXT" or "SSL". Default: `"PLAINTEXT"`.
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
    - <a id="properties/kafka_compression_type/anyOf/0"></a>*string*: Must be one of: "gzip", "snappy", "lz4", or "zstd".
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

- <a id="properties/host"></a>**`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.
- <a id="properties/port"></a>**`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.
- <a id="properties/auto_reload"></a>**`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.
- <a id="properties/workers"></a>**`workers`** *(integer)*: Number of workers processes to run. Default: `1`.
- <a id="properties/timeout_keep_alive"></a>**`timeout_keep_alive`** *(integer)*: The time in seconds to keep an idle connection open for subsequent requests before closing it. This value should be higher than the timeout used by any client or reverse proxy to avoid premature connection closures. Default: `90`.

  Examples:
  ```json
  5
  ```

  ```json
  90
  ```

  ```json
  5400
  ```

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

- <a id="properties/cors_allowed_headers"></a>**`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all request headers. The Accept, Accept-Language, Content-Language, Content-Type and some are always allowed for CORS requests. Default: `null`.
  - **Any of**
    - <a id="properties/cors_allowed_headers/anyOf/0"></a>*array*
      - <a id="properties/cors_allowed_headers/anyOf/0/items"></a>**Items** *(string)*
    - <a id="properties/cors_allowed_headers/anyOf/1"></a>*null*

  Examples:
  ```json
  []
  ```

- <a id="properties/cors_exposed_headers"></a>**`cors_exposed_headers`**: A list of HTTP response headers that should be exposed for cross-origin responses. Defaults to []. Note that you can NOT use ['*'] to expose all response headers. The Cache-Control, Content-Language, Content-Length, Content-Type, Expires, Last-Modified and Pragma headers are always exposed for CORS responses. Default: `null`.
  - **Any of**
    - <a id="properties/cors_exposed_headers/anyOf/0"></a>*array*
      - <a id="properties/cors_exposed_headers/anyOf/0/items"></a>**Items** *(string)*
    - <a id="properties/cors_exposed_headers/anyOf/1"></a>*null*

  Examples:
  ```json
  []
  ```

## Definitions

- <a id="%24defs/FieldLabel"></a>**`FieldLabel`** *(object)*: Contains the field name and corresponding user-friendly name.
  - <a id="%24defs/FieldLabel/properties/key"></a>**`key`** *(string, required)*: The raw field name, such as study.type.
  - <a id="%24defs/FieldLabel/properties/name"></a>**`name`** *(string)*: A user-friendly name for the field (leave empty to use the key). Default: `""`.
- <a id="%24defs/SearchableClass"></a>**`SearchableClass`** *(object)*: Represents a searchable artifact or resource type.
  - <a id="%24defs/SearchableClass/properties/description"></a>**`description`** *(string, required)*: A brief description of the resource type.
  - <a id="%24defs/SearchableClass/properties/facetable_fields"></a>**`facetable_fields`** *(array)*: A list of the facetable fields for the resource type (leave empty to not use faceting, use dotted notation for nested fields). Default: `[]`.
    - <a id="%24defs/SearchableClass/properties/facetable_fields/items"></a>**Items**: Refer to *[#/$defs/FieldLabel](#%24defs/FieldLabel)*.
  - <a id="%24defs/SearchableClass/properties/selected_fields"></a>**`selected_fields`** *(array)*: A list of the returned fields for the resource type (leave empty to return all, use dotted notation for nested fields). Default: `[]`.
    - <a id="%24defs/SearchableClass/properties/selected_fields/items"></a>**Items**: Refer to *[#/$defs/FieldLabel](#%24defs/FieldLabel)*.

### Usage:

A template YAML file for configuring the service can be found at
[`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.mass.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.mass.yaml`)
- in your home directory (on Linux: `~/.mass.yaml`)

The config YAML file will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml)
can also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `mass_`,
e.g. for the `host` set an environment variable named `mass_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](./openapi.yaml).

## Architecture and Design:
This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.

This service is currently designed to work with MongoDB and uses an aggregation pipeline to produce search results.

Typical sequence of events is as follows:

1. Requests are received by the API, then directed to the QueryHandler in the core.

2. From there, the configuration is consulted to retrieve any facetable and selected fields for the searched resource class.

3. The search parameters and facet fields are passed to the Aggregator, which builds and runs the aggregation pipeline on the appropriate collection. The aggregation pipeline is a series of stages run in sequence:
   1. Run a text match using the query string.
   2. Apply a sort based on the IDs.
   3. Apply any filters supplied in the search parameters.
   4. Extract the facets.
   5. Keep only selected fields if some have been specified.
   6. Transform the results structure into {facets, hits, hit count}.

4. Once retrieved in the Aggregator, the results are passed back to the QueryHandler where they are shoved into a QueryResults Pydantic model for validation before finally being sent back to the API.


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

Inside the devcontainer, a command `dev_install` is available for convenience.
It installs the service with all development dependencies, and it installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`lock/requirements-dev.txt`](./lock/requirements-dev.txt), run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [.readme_generation/README.md](./.readme_generation/README.md)
for details.
