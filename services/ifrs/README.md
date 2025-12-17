# Internal File Registry Service

This service acts as a registry for the internal location and representation of files.

## Description

This service provides functionality to administer files stored in an S3-compatible
object storage.
All file-related metadata is stored in an internal mongodb database, owned and controlled
by this service.
It exposes no REST API endpoints and communicates with other services via events.

### Events consumed:

#### files_to_register
This event signals that there is a file to register in the database.
The file-related metadata from this event gets saved in the database and the file is
moved from the incoming staging bucket to the permanent storage.

#### files_to_stage
This event signals that there is a file that needs to be staged for download.
The file is then copied from the permanent storage to the outbox for the actual download.
### Events published:

#### file_internally_registered
This event is published after a file was registered in the database.
It contains all the file-related metadata that was provided by the files_to_register event.

#### file_staged_for_download
This event is published after a file was successfully staged to the outbox.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/internal-file-registry-service):
```bash
docker pull ghga/internal-file-registry-service:6.0.6
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/internal-file-registry-service:6.0.6 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/internal-file-registry-service:6.0.6 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
ifrs --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/enable_opentelemetry"></a>**`enable_opentelemetry`** *(boolean)*: If set to true, this will run necessary setup code.If set to false, environment variables are set that should also effectively disable autoinstrumentation. Default: `false`.

- <a id="properties/otel_trace_sampling_rate"></a>**`otel_trace_sampling_rate`** *(number)*: Determines which proportion of spans should be sampled. A value of 1.0 means all and is equivalent to the previous behaviour. Setting this to 0 will result in no spans being sampled, but this does not automatically set `enable_opentelemetry` to False. Minimum: `0`. Maximum: `1`. Default: `1.0`.

- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"ifrs"`.

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

- <a id="properties/object_storages"></a>**`object_storages`** *(object, required)*: Can contain additional properties.

  - <a id="properties/object_storages/additionalProperties"></a>**Additional properties**: Refer to *[#/$defs/S3ObjectStorageNodeConfig](#%24defs/S3ObjectStorageNodeConfig)*.

- <a id="properties/file_internally_registered_topic"></a>**`file_internally_registered_topic`** *(string, required)*: Name of the topic used for events indicating that a file has been registered for download.


  Examples:

  ```json
  "file-registrations"
  ```


  ```json
  "file-registrations-internal"
  ```


- <a id="properties/file_internally_registered_type"></a>**`file_internally_registered_type`** *(string, required)*: The type used for event indicating that that a file has been registered for download.


  Examples:

  ```json
  "file_internally_registered"
  ```


- <a id="properties/file_deleted_topic"></a>**`file_deleted_topic`** *(string, required)*: Name of the topic used for events indicating that a file has been deleted.


  Examples:

  ```json
  "file-deletions"
  ```


- <a id="properties/file_deleted_type"></a>**`file_deleted_type`** *(string, required)*: The type used for events indicating that a file has been deleted.


  Examples:

  ```json
  "file_deleted"
  ```


- <a id="properties/file_staged_topic"></a>**`file_staged_topic`** *(string, required)*: Name of the topic used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "file-stagings"
  ```


- <a id="properties/file_staged_type"></a>**`file_staged_type`** *(string, required)*: The type used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "file_staged_for_download"
  ```


- <a id="properties/file_interrogations_topic"></a>**`file_interrogations_topic`** *(string, required)*: The name of the topic use to publish file interrogation outcome events.


  Examples:

  ```json
  "file-interrogations"
  ```


- <a id="properties/interrogation_success_type"></a>**`interrogation_success_type`** *(string, required)*: The type used for events informing about successful file validations.


  Examples:

  ```json
  "file_interrogation_success"
  ```


- <a id="properties/file_deletion_request_topic"></a>**`file_deletion_request_topic`** *(string, required)*: The name of the topic to receive events informing about files to delete.


  Examples:

  ```json
  "file-deletion-requests"
  ```


- <a id="properties/file_deletion_request_type"></a>**`file_deletion_request_type`** *(string, required)*: The type used for events indicating that a request to delete a file has been received.


  Examples:

  ```json
  "file_deletion_requested"
  ```


- <a id="properties/files_to_stage_topic"></a>**`files_to_stage_topic`** *(string, required)*: Name of the topic used for events indicating that a download was requested for a file that is not yet available in the outbox.


  Examples:

  ```json
  "file-staging-requests"
  ```


- <a id="properties/files_to_stage_type"></a>**`files_to_stage_type`** *(string, required)*: The type used for non-staged file request events.


  Examples:

  ```json
  "file_staging_requested"
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

- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context. If True, a new correlation ID will be generated and used in the event header. Default: `true`.


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


- <a id="properties/db_version_collection"></a>**`db_version_collection`** *(string, required)*: The name of the collection containing DB version information for this service.


  Examples:

  ```json
  "ifrsDbVersions"
  ```


- <a id="properties/migration_wait_sec"></a>**`migration_wait_sec`** *(integer, required)*: The number of seconds to wait before checking the DB version again.


  Examples:

  ```json
  5
  ```


  ```json
  30
  ```


  ```json
  180
  ```


- <a id="properties/migration_max_wait_sec"></a>**`migration_max_wait_sec`**: The maximum number of seconds to wait for migrations to complete before raising an error. Default: `null`.

  - **Any of**

    - <a id="properties/migration_max_wait_sec/anyOf/0"></a>*integer*

    - <a id="properties/migration_max_wait_sec/anyOf/1"></a>*null*


  Examples:

  ```json
  null
  ```


  ```json
  300
  ```


  ```json
  600
  ```


  ```json
  3600
  ```


## Definitions


- <a id="%24defs/S3Config"></a>**`S3Config`** *(object)*: S3-specific config params.
Inherit your config class from this class if you need
to talk to an S3 service in the backend.<br>  Args:
    s3_endpoint_url (str): The URL to the S3 endpoint.
    s3_access_key_id (str):
        Part of credentials for login into the S3 service. See:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    s3_secret_access_key (str):
        Part of credentials for login into the S3 service. See:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    s3_session_token (str | None):
        Optional part of credentials for login into the S3 service. See:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    aws_config_ini (Path | None):
        Path to a config file for specifying more advanced S3 parameters.
        This should follow the format described here:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file
        Defaults to None. Cannot contain additional properties.

  - <a id="%24defs/S3Config/properties/s3_endpoint_url"></a>**`s3_endpoint_url`** *(string, required)*: URL to the S3 API.


    Examples:

    ```json
    "http://localhost:4566"
    ```


  - <a id="%24defs/S3Config/properties/s3_access_key_id"></a>**`s3_access_key_id`** *(string, required)*: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html.


    Examples:

    ```json
    "my-access-key-id"
    ```


  - <a id="%24defs/S3Config/properties/s3_secret_access_key"></a>**`s3_secret_access_key`** *(string, format: password, required and write-only)*: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html.


    Examples:

    ```json
    "my-secret-access-key"
    ```


  - <a id="%24defs/S3Config/properties/s3_session_token"></a>**`s3_session_token`**: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html. Default: `null`.

    - **Any of**

      - <a id="%24defs/S3Config/properties/s3_session_token/anyOf/0"></a>*string, format: password*

      - <a id="%24defs/S3Config/properties/s3_session_token/anyOf/1"></a>*null*


    Examples:

    ```json
    "my-session-token"
    ```


  - <a id="%24defs/S3Config/properties/aws_config_ini"></a>**`aws_config_ini`**: Path to a config file for specifying more advanced S3 parameters. This should follow the format described here: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file. Default: `null`.

    - **Any of**

      - <a id="%24defs/S3Config/properties/aws_config_ini/anyOf/0"></a>*string, format: path*

      - <a id="%24defs/S3Config/properties/aws_config_ini/anyOf/1"></a>*null*


    Examples:

    ```json
    "~/.aws/config"
    ```


- <a id="%24defs/S3ObjectStorageNodeConfig"></a>**`S3ObjectStorageNodeConfig`** *(object)*: Configuration for one specific object storage node and one bucket in it.<br>  The bucket is the main bucket that the service is responsible for. Cannot contain additional properties.

  - <a id="%24defs/S3ObjectStorageNodeConfig/properties/bucket"></a>**`bucket`** *(string, required)*

  - <a id="%24defs/S3ObjectStorageNodeConfig/properties/credentials"></a>**`credentials`** *(required)*: Refer to *[#/$defs/S3Config](#%24defs/S3Config)*.


### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.ifrs.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.ifrs.yaml`)
- in your home directory (on Linux: `~/.ifrs.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ifrs_`,
e.g. for the `host` set an environment variable named `ifrs_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.



## Architecture and Design:
This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.


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
