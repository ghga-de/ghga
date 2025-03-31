# Upload Controller Service

manages uploads to an S3 inbox bucket.

## Description

<!-- Please provide a short overview of the features of this service.-->

An extensive documentation can be found [here](...) (coming soon).


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/upload-controller-service):
```bash
docker pull ghga/upload-controller-service:5.0.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/upload-controller-service:5.0.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/upload-controller-service:5.0.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
ucs --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/file_upload_received_topic"></a>**`file_upload_received_topic`** *(string, required)*: The name of the topic used for FileUploadReceived events.


  Examples:

  ```json
  "received-file-uploads"
  ```


- <a id="properties/file_upload_received_type"></a>**`file_upload_received_type`** *(string, required)*: The name of the type used for FileUploadReceived events.


  Examples:

  ```json
  "file_upload_received"
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


- <a id="properties/file_interrogations_topic"></a>**`file_interrogations_topic`** *(string, required)*: The name of the topic use to publish file interrogation outcome events.


  Examples:

  ```json
  "file-interrogations"
  ```


- <a id="properties/interrogation_failure_type"></a>**`interrogation_failure_type`** *(string, required)*: The type used for events informing about failed file validations.


  Examples:

  ```json
  "file_interrogation_failed"
  ```


- <a id="properties/file_metadata_topic"></a>**`file_metadata_topic`** *(string, required)*: Name of the topic to receive new or changed metadata on files that shall be registered for uploaded.


  Examples:

  ```json
  "metadata"
  ```


- <a id="properties/file_metadata_type"></a>**`file_metadata_type`** *(string, required)*: The type used for events to receive new or changed metadata on files that are expected to be uploaded.


  Examples:

  ```json
  "file_metadata_upserted"
  ```


- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"ucs"`.

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


- <a id="properties/kafka_max_message_size"></a>**`kafka_max_message_size`** *(integer)*: The largest message size that can be transmitted, in bytes. Only services that have a need to send/receive larger messages should set this. Exclusive minimum: `0`. Default: `1048576`.


  Examples:

  ```json
  1048576
  ```


  ```json
  16777216
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


- <a id="properties/object_storages"></a>**`object_storages`** *(object, required)*: Can contain additional properties.

  - <a id="properties/object_storages/additionalProperties"></a>**Additional properties**: Refer to *[#/$defs/S3ObjectStorageNodeConfig](#%24defs/S3ObjectStorageNodeConfig)*.

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
    s3_session_token (Optional[str]):
        Optional part of credentials for login into the S3 service. See:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    aws_config_ini (Optional[Path]):
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


  - <a id="%24defs/S3Config/properties/s3_secret_access_key"></a>**`s3_secret_access_key`** *(string, format: password, required, write-only)*: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html.


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

  - <a id="%24defs/S3ObjectStorageNodeConfig/properties/credentials"></a>**`credentials`**: Refer to *[#/$defs/S3Config](#%24defs/S3Config)*.


### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.ucs.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.ucs.yaml`)
- in your home directory (on unix: `~/.ucs.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ucs_`,
e.g. for the `host` set an environment variable named `ucs_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](openapi.yaml).

## Architecture and Design:
<!-- Please provide an overview of the architecture and design of the code base.
Mention anything that deviates from the standard triple hexagonal architecture and
the corresponding structure. -->

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

Moreover, inside the devcontainer, a convenience commands `dev_install` is available.
It installs the service with all development dependencies, installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`./requirements-dev.txt`](./requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [`readme_generation.md`](./readme_generation.md)
for details.
