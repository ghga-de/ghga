# File Ingest Service

A lightweight service to propagate file upload metadata to the GHGA file backend services

## Description

The File Ingest Service provides an endpoint to populate the Encryption Key Store,
Internal File Registry and Download Controller with output metadata from the S3 upload
script at https://github.com/ghga-de/data-steward-scripts/blob/main/src/s3_upload.py.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/file-ingest-service):
```bash
docker pull ghga/file-ingest-service:9.0.6
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/file-ingest-service:9.0.6 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/file-ingest-service:9.0.6 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
fis --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/enable_opentelemetry"></a>**`enable_opentelemetry`** *(boolean)*: If set to true, this will run necessary setup code.If set to false, environment variables are set that should also effectively disable autoinstrumentation. Default: `false`.

- <a id="properties/otel_trace_sampling_rate"></a>**`otel_trace_sampling_rate`** *(number)*: Determines which proportion of spans should be sampled. A value of 1.0 means all and is equivalent to the previous behaviour. Setting this to 0 will result in no spans being sampled, but this does not automatically set `enable_opentelemetry` to False. Minimum: `0`. Maximum: `1`. Default: `1.0`.

- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"fis"`.

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

- <a id="properties/vault_url"></a>**`vault_url`** *(string, required)*: URL of the vault instance to connect to.


  Examples:

  ```json
  "http://127.0.0.1.8200"
  ```


- <a id="properties/vault_role_id"></a>**`vault_role_id`**: Vault role ID to access a specific prefix. Default: `null`.

  - **Any of**

    - <a id="properties/vault_role_id/anyOf/0"></a>*string, format: password*

    - <a id="properties/vault_role_id/anyOf/1"></a>*null*


  Examples:

  ```json
  "example_role"
  ```


- <a id="properties/vault_secret_id"></a>**`vault_secret_id`**: Vault secret ID to access a specific prefix. Default: `null`.

  - **Any of**

    - <a id="properties/vault_secret_id/anyOf/0"></a>*string, format: password*

    - <a id="properties/vault_secret_id/anyOf/1"></a>*null*


  Examples:

  ```json
  "example_secret"
  ```


- <a id="properties/vault_verify"></a>**`vault_verify`**: SSL certificates (CA bundle) used to verify the identity of the vault, or True to use the default CAs, or False for no verification. Default: `true`.

  - **Any of**

    - <a id="properties/vault_verify/anyOf/0"></a>*boolean*

    - <a id="properties/vault_verify/anyOf/1"></a>*string*


  Examples:

  ```json
  "/etc/ssl/certs/my_bundle.pem"
  ```


- <a id="properties/vault_path"></a>**`vault_path`** *(string, required)*: Path without leading or trailing slashes where secrets should be stored in the vault.

- <a id="properties/vault_secrets_mount_point"></a>**`vault_secrets_mount_point`** *(string)*: Name used to address the secret engine under a custom mount path. Default: `"secret"`.


  Examples:

  ```json
  "secret"
  ```


- <a id="properties/vault_kube_role"></a>**`vault_kube_role`**: Vault role name used for Kubernetes authentication. Default: `null`.

  - **Any of**

    - <a id="properties/vault_kube_role/anyOf/0"></a>*string*

    - <a id="properties/vault_kube_role/anyOf/1"></a>*null*


  Examples:

  ```json
  "file-ingest-role"
  ```


- <a id="properties/vault_auth_mount_point"></a>**`vault_auth_mount_point`**: Adapter specific mount path for the corresponding auth backend. If none is provided, the default is used. Default: `null`.

  - **Any of**

    - <a id="properties/vault_auth_mount_point/anyOf/0"></a>*string*

    - <a id="properties/vault_auth_mount_point/anyOf/1"></a>*null*


  Examples:

  ```json
  null
  ```


  ```json
  "approle"
  ```


  ```json
  "kubernetes"
  ```


- <a id="properties/service_account_token_path"></a>**`service_account_token_path`** *(string, format: path)*: Path to service account token used by kube auth adapter. Default: `"/var/run/secrets/kubernetes.io/serviceaccount/token"`.

- <a id="properties/private_key_path"></a>**`private_key_path`** *(string, format: path, required)*: Path to the Crypt4GH private key file of the keypair whose public key is used to encrypt the payload.

- <a id="properties/private_key_passphrase"></a>**`private_key_passphrase`**: Passphrase needed to read the content of the private key file. Only needed if the private key is encrypted. Default: `null`.

  - **Any of**

    - <a id="properties/private_key_passphrase/anyOf/0"></a>*string*

    - <a id="properties/private_key_passphrase/anyOf/1"></a>*null*

- <a id="properties/token_hashes"></a>**`token_hashes`** *(array, required)*: List of token hashes corresponding to the tokens that can be used to authenticate calls to this service.

  - <a id="properties/token_hashes/items"></a>**Items** *(string)*

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


- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context. If True, a new correlation ID will be generated and used in the event header. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
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


- <a id="properties/file_validations_collection"></a>**`file_validations_collection`** *(string)*: The name of the collection used to store FileUploadValidationSuccess events. Default: `"fileValidations"`.


  Examples:

  ```json
  "fileValidations"
  ```



### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.fis.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.fis.yaml`)
- in your home directory (on Linux: `~/.fis.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `fis_`,
e.g. for the `host` set an environment variable named `fis_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
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
