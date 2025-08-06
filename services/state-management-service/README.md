[![tests](https://github.com/ghga-de/state-management-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/state-management-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/state-management-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/state-management-service?branch=main)

# State Management Service

State Management Service - Provides a REST API for basic infrastructure technology state management.

## Description

This service is intended to aid testing of the GHGA Archive by providing a unified
API for managing state in infrastructure technologies such as MongoDB, S3, Apache Kafka,
and the Hashicorp Vault.

This service should **never** be deployed to production. It is *only* intended for use
in the Testing and Staging environments, where there is no access to real data.
Despite this, the services provides a way to restrict which databases and collections
can be accessed with this service through configuration, and a simple API key
(set in config) that can be used to authenticate requests.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/state-management-service):
```bash
docker pull ghga/state-management-service:4.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/state-management-service:4.1.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/state-management-service:4.1.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
sms --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/service_name"></a>**`service_name`** *(string)*: Short name of this service. Default: `"sms"`.

- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service. This is included in log messages.


  Examples:

  ```json
  "germany-bw-instance-001"
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


- <a id="properties/object_storages"></a>**`object_storages`** *(object, required)*: Can contain additional properties.

  - <a id="properties/object_storages/additionalProperties"></a>**Additional properties**: Refer to *[#/$defs/S3ObjectStorageNodeConfig](#%24defs/S3ObjectStorageNodeConfig)*.

- <a id="properties/vault_url"></a>**`vault_url`** *(string, required)*: URL for the Vault.


  Examples:

  ```json
  "http://vault:8200"
  ```


- <a id="properties/vault_secrets_mount_point"></a>**`vault_secrets_mount_point`** *(string)*: Name used to address the secret engine under a custom mount path. Default: `"secret"`.


  Examples:

  ```json
  "secret"
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

- <a id="properties/token_hashes"></a>**`token_hashes`** *(array, required)*: List of token hashes corresponding to the tokens that can be used to authenticate calls to this service. Hashes are made with SHA-256.

  - <a id="properties/token_hashes/items"></a>**Items** *(string)*


  Examples:

  ```json
  "7ad83b6b9183c91674eec897935bc154ba9ff9704f8be0840e77f476b5062b6e"
  ```


- <a id="properties/db_prefix"></a>**`db_prefix`** *(string, required)*: Prefix to add to all database names used in the SMS.


  Examples:

  ```json
  "testing-branch-name-"
  ```


- <a id="properties/allow_empty_prefix"></a>**`allow_empty_prefix`** *(boolean)*: Only set to True for local testing. If False, `db_prefix` cannot be empty. This is to prevent accidental deletion of others' data in shared environments, i.e. staging. Default: `false`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- <a id="properties/db_permissions"></a>**`db_permissions`** *(array)*: List of permissions that can be granted on a collection. Use * to signify 'all'. The format is '<db_name>.<collection_name>:<permissions>', e.g. 'db1.collection1.crud'. The permissions are 'r' for read and 'w' for write. '*' can be used to mean both read and write (or 'rw'). Deletion is a write operation. If db_permissions are not set, no operations are allowed on any database or collection. Default: `[]`.

  - <a id="properties/db_permissions/items"></a>**Items** *(string)*


  Examples:

  ```json
  "db1.coll1:r"
  ```


  ```json
  "db1.coll1:w"
  ```


  ```json
  "db1.coll1:rw"
  ```


  ```json
  "db1.coll1:*"
  ```


  ```json
  "db2.*:r"
  ```


  ```json
  "db3.*:*"
  ```


  ```json
  "*.*:r"
  ```


  ```json
  "*.*:*"
  ```


- <a id="properties/mongo_dsn"></a>**`mongo_dsn`** *(string, format: multi-host-uri, required)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/. Length must be at least 1.


  Examples:

  ```json
  "mongodb://localhost:27017"
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


- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.

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
[`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.sms.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.sms.yaml`)
- in your home directory (on Linux: `~/.sms.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `sms_`,
e.g. for the `host` set an environment variable named `sms_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](./openapi.yaml).

## Architecture and Design:
API calls to the State Management Service are authenticated through a configured API Key.

For each technology, REST API endpoints will be exposed, prefixed as follows:

| **Technology Name** | **Prefix**  |
|---------------------|-------------|
| MongoDB             | `/documents/`|
| Apache Kafka        | `/events/`  |
| S3                  | `/objects/` |
| Vault               | `/secrets/` |

Branch isolation is achieved in shared state technologies by the use of prefixes in,
for example, database names.
The `db_prefix` and `topic_prefix` config values are used so the prefixes must only be
specified once. They are applied to database and topic names automatically throughout
the SMS instance, establishing another means to restrict access.


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
[`lock/requirements-dev.txt`](./lock/requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [.readme_generation/README.md](./.readme_generation/README.md)
for details.
