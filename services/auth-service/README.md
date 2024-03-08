[![tests](https://github.com/ghga-de/auth-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/auth-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/auth-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/auth-service?branch=main)

# Auth Service

Authentication adapter and services used for the GHGA data portal

## Description

<!-- Please provide a short overview of the features of this service. -->

This repository contains two services for the management, authentication and authorization of users of the GHGA data portal.

These two services are described in the following sections. The setting `run_auth_adapter` can be used to determine which of the two services will be started.

### Auth Adapter

The `auth_adapter` sub-package contains the authentication service used by the API gateway via the ExtAuth protocol.

If a `path_prefix` has been configured for the AuthService in the API gateway, then the `api_root_path` must be set accordingly.

### User Management

The `user_management` sub-package contains the user data management service.

The user management contains two APIs, the `users` API for the user registry, and the `claims` API for the claims repository. The setting `include_apis` can be used to specify which of the two APIs should be provided. For testing purposes, both APIs can be provided at the same time, but this is not recommended in production.


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/auth-service):
```bash
docker pull ghga/auth-service:2.0.0-alpha.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/auth-service:2.0.0-alpha.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/auth-service:2.0.0-alpha.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
auth_service --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- **`dataset_deletion_event_topic`** *(string)*: the topic of the event announcing dataset deletions. Default: `"metadata_datasets"`.

- **`dataset_deletion_event_type`** *(string)*: the type of the event announcing dataset deletions. Default: `"dataset_deleted"`.

- **`service_name`** *(string)*: Short name of this service. Default: `"auth_service"`.

- **`service_instance_id`** *(string)*: A string that uniquely identifies this instance across all instances of this service. This is included in log messages.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


- **`kafka_servers`** *(array)*: A list of connection strings to connect to Kafka bootstrap servers.

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

- **`kafka_ssl_password`** *(string)*: Optional password to be used for the client private key. Default: `""`.

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`claims_collection`** *(string)*: Name of the collection for user claims. Default: `"claims"`.

- **`users_collection`** *(string)*: Name of the collection for users. Default: `"users"`.

- **`user_tokens_collection`** *(string)*: Name of the collection for user tokens. Default: `"user_tokens"`.

- **`ivas_collection`** *(string)*: Name of the collection for IVAs. Default: `"ivas"`.

- **`db_connection_str`** *(string, format: password)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- **`db_name`** *(string)*: the name of the database located on the MongoDB server. Default: `"auth-db"`.


  Examples:

  ```json
  "auth-db"
  ```


  ```json
  "user-management"
  ```


  ```json
  "users-and-claims"
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


- **`totp_issuer`** *(string)*: Issuer name for TOTP provisioning URIs. Default: `"GHGA"`.

- **`totp_image`**: URL of the PNG image provided in the TOTP provisioning URIs. Default: `null`.

  - **Any of**

    - *string, format: uri*

    - *null*


  Examples:

  ```json
  "https://www.ghga.de/logo.png"
  ```


- **`totp_algorithm`**: Hash algorithm used for TOTP code generation. Default: `"sha1"`.

  - **All of**

    - : Refer to *[#/$defs/TOTPAlgorithm](#%24defs/TOTPAlgorithm)*.

- **`totp_digits`** *(integer)*: Number of digits used for the TOTP code. Minimum: `6`. Maximum: `12`. Default: `6`.

- **`totp_interval`** *(integer)*: Time interval in seconds for generating TOTP codes. Minimum: `10`. Maximum: `300`. Default: `30`.

- **`totp_tolerance`** *(integer)*: Number of intervals to check before and after the current time. Minimum: `0`. Maximum: `10`. Default: `1`.

- **`totp_attempts_per_code`** *(integer)*: Maximum number of attempts to verify an individual TOTP code. Minimum: `1`. Maximum: `10`. Default: `3`.

- **`totp_max_failed_attempts`** *(integer)*: Maximum number of consecutive failed attempts to verify TOTP codes. Minimum: `1`. Maximum: `100`. Default: `10`.

- **`totp_secret_size`** *(integer)*: Size of the Base32 encoded TOTP secrets. Minimum: `24`. Maximum: `256`. Default: `32`.

- **`totp_encryption_key`**: Base64 encoded key used to encrypt TOTP secrets. Default: `null`.

  - **Any of**

    - *string, format: password*

    - *null*

- **`session_id_bytes`** *(integer)*: Number of bytes to be used for a session ID. Default: `24`.

- **`csrf_token_bytes`** *(integer)*: Number of bytes to be used for a CSRF token. Default: `24`.

- **`session_timeout_seconds`** *(integer)*: Session timeout in seconds. Default: `3600`.

- **`session_max_lifetime_seconds`** *(integer)*: Maximum lifetime of a session in seconds. Default: `43200`.

- **`auth_key`**: internal public key for user management (key pair for auth adapter). Default: `null`.

  - **Any of**

    - *string*

    - *null*

- **`auth_algs`** *(array)*: A list of all algorithms used for signing GHGA internal tokens. Default: `["ES256"]`.

  - **Items** *(string)*

- **`auth_check_claims`** *(object)*: A dict of all GHGA internal claims that shall be verified. Default: `{"id": null, "name": null, "email": null, "iat": null, "exp": null}`.

- **`auth_map_claims`** *(object)*: A mapping of claims to attributes in the GHGA auth context. Can contain additional properties. Default: `{}`.

  - **Additional properties** *(string)*

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


- **`run_auth_adapter`** *(boolean)*: Run as auth adapter. Default: `false`.

- **`api_ext_path`** *(string)*: external API path for the user management as seen by the auth adapter. Default: `"/api/auth"`.

- **`auth_ext_keys`**: external public key set for auth adapter (not used for user management). Default: `null`.

  - **Any of**

    - *string*

    - *null*

- **`auth_ext_algs`** *(array)*: allowed algorithms for signing external tokens. Default: `["RS256", "ES256"]`.

  - **Items** *(string)*

- **`basic_auth_credentials`**: credentials for basic authentication, separated by whitespace. Default: `null`.

  - **Any of**

    - *string*

    - *null*

- **`basic_auth_realm`** *(string)*: realm for basic authentication. Default: `"GHGA Data Portal"`.

- **`allow_read_paths`** *(array)*: paths that are public or use their own authentication mechanism. Default: `["/.well-known/*", "/service-logo.png"]`.

  - **Items** *(string)*

- **`allow_write_paths`** *(array)*: paths for writing that use their own authentication mechanism. Default: `[]`.

  - **Items** *(string)*

- **`include_apis`** *(array)*: If not run as auth adapter, which APIs should be provided. If no APIs are specified, run the event consumer. Default: `["users"]`.

  - **Items** *(string)*: Must be one of: `["users", "claims"]`.

- **`add_as_data_stewards`** *(array)*: a list of external IDs of data stewards or user objects to seed the claims repository with. Default: `[]`.

  - **Items**

    - **Any of**

      - *string*

      - *object*

- **`oidc_authority_url`** *(string, format: uri)*: external OIDC authority URL used by the auth adapter. Default: `"https://proxy.aai.lifescience-ri.eu"`.

- **`oidc_userinfo_endpoint`**: external OIDC userinfo endpoint used by the auth adapter. Default: `"https://proxy.aai.lifescience-ri.eu/OIDC/userinfo"`.

  - **Any of**

    - *string, format: uri*

    - *null*

- **`oidc_client_id`** *(string)*: the registered OIDC client ID. Default: `"ghga-data-portal"`.

- **`organization_url`** *(string, format: uri)*: the URL used as source for internal claims. Default: `"https://ghga.de"`.

## Definitions


- <a id="%24defs/TOTPAlgorithm"></a>**`TOTPAlgorithm`** *(string)*: Hash algorithm used for TOTP code generation. Must be one of: `["sha1", "sha256", "sha512"]`.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.auth_service.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.auth_service.yaml`)
- in your home directory (on unix: `~/.auth_service.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `auth_service_`,
e.g. for the `host` set an environment variable named `auth_service_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](./openapi.yaml).

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
