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

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/state-management-service):
```bash
docker pull ghga/state-management-service:1.4.1
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/state-management-service:1.4.1 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/state-management-service:1.4.1 --help
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
- **`service_name`** *(string)*: Short name of this service. Default: `"sms"`.

- **`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service. This is included in log messages.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


- **`kafka_servers`** *(array, required)*: A list of connection strings to connect to Kafka bootstrap servers.

  - **Items** *(string)*


  Examples:

  ```json
  [
      "localhost:9092"
  ]
  ```


- **`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. Must be one of: `["PLAINTEXT", "SSL"]`. Default: `"PLAINTEXT"`.

- **`kafka_ssl_cafile`** *(string)*: Certificate Authority file path containing certificates used to sign broker certificates. If a CA is not specified, the default system CA will be used if found by OpenSSL. Default: `""`.

- **`kafka_ssl_certfile`** *(string)*: Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity. Default: `""`.

- **`kafka_ssl_keyfile`** *(string)*: Optional filename containing the client private key. Default: `""`.

- **`kafka_ssl_password`** *(string, format: password)*: Optional password to be used for the client private key. Default: `""`.

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`kafka_max_message_size`** *(integer)*: The largest message size that can be transmitted, in bytes. Only services that have a need to send/receive larger messages should set this. Exclusive minimum: `0`. Default: `1048576`.


  Examples:

  ```json
  1048576
  ```


  ```json
  16777216
  ```


- **`object_storages`** *(object, required)*: Can contain additional properties.

  - **Additional properties**: Refer to *[#/$defs/S3ObjectStorageNodeConfig](#%24defs/S3ObjectStorageNodeConfig)*.

- **`vault_url`** *(string, required)*: URL for the Vault.


  Examples:

  ```json
  "http://vault:8200"
  ```


- **`vault_token`** *(string, required)*: Token for the Vault.


  Examples:

  ```json
  "dev-token"
  ```


- **`vault_secrets_mount_point`** *(string)*: Name used to address the secret engine under a custom mount path. Default: `"secret"`.


  Examples:

  ```json
  "secret"
  ```


- **`token_hashes`** *(array, required)*: List of token hashes corresponding to the tokens that can be used to authenticate calls to this service. Hashes are made with SHA-256.

  - **Items** *(string)*


  Examples:

  ```json
  "7ad83b6b9183c91674eec897935bc154ba9ff9704f8be0840e77f476b5062b6e"
  ```


- **`db_prefix`** *(string, required)*: Prefix to add to all database names used in the SMS.


  Examples:

  ```json
  "testing-branch-name-"
  ```


- **`allow_empty_prefix`** *(boolean)*: Only set to True for local testing. If False, `db_prefix` cannot be empty. This is to prevent accidental deletion of others' data in shared environments, i.e. staging. Default: `false`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`db_permissions`** *(array)*: List of permissions that can be granted on a collection. Use * to signify 'all'. The format is '<db_name>.<collection_name>:<permissions>', e.g. 'db1.collection1.crud'. The permissions are 'r' for read and 'w' for write. '*' can be used to mean both read and write (or 'rw'). Deletion is a write operation. If db_permissions are not set, no operations are allowed on any database or collection. Default: `[]`.

  - **Items** *(string)*


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


- **`db_connection_str`** *(string, format: password, required)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- **`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- **`log_format`**: If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details. Default: `null`.

  - **Any of**

    - *string*

    - *null*


  Examples:

  ```json
  "%(timestamp)s - %(service)s - %(level)s - %(message)s"
  ```


  ```json
  "%(asctime)s - Severity: %(levelno)s - %(msg)s"
  ```


- **`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages. Default: `true`.

- **`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.

- **`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- **`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.

- **`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- **`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `""`.

- **`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `"/openapi.json"`.

- **`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `"/docs"`.

- **`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- **`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. Default: `null`.

  - **Any of**

    - *boolean*

    - *null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- **`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


  Examples:

  ```json
  [
      "*"
  ]
  ```


- **`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


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

  - **`s3_endpoint_url`** *(string, required)*: URL to the S3 API.


    Examples:

    ```json
    "http://localhost:4566"
    ```


  - **`s3_access_key_id`** *(string, required)*: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html.


    Examples:

    ```json
    "my-access-key-id"
    ```


  - **`s3_secret_access_key`** *(string, format: password, required)*: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html.


    Examples:

    ```json
    "my-secret-access-key"
    ```


  - **`s3_session_token`**: Part of credentials for login into the S3 service. See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html. Default: `null`.

    - **Any of**

      - *string, format: password*

      - *null*


    Examples:

    ```json
    "my-session-token"
    ```


  - **`aws_config_ini`**: Path to a config file for specifying more advanced S3 parameters. This should follow the format described here: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file. Default: `null`.

    - **Any of**

      - *string, format: path*

      - *null*


    Examples:

    ```json
    "~/.aws/config"
    ```


- <a id="%24defs/S3ObjectStorageNodeConfig"></a>**`S3ObjectStorageNodeConfig`** *(object)*: Configuration for one specific object storage node and one bucket in it.<br>  The bucket is the main bucket that the service is responsible for. Cannot contain additional properties.

  - **`bucket`** *(string, required)*

  - **`credentials`**: Refer to *[#/$defs/S3Config](#%24defs/S3Config)*.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.sms.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.sms.yaml`)
- in your home directory (on unix: `~/.sms.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `sms_`,
e.g. for the `host` set an environment variable named `sms_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
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
