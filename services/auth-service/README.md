[![tests](https://github.com/ghga-de/auth-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/auth-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/auth-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/auth-service?branch=main)

# Auth Service

Authentication adapter and services used for the GHGA data portal

## Description

<!-- Please provide a short overview of the features of this service. -->

This repository contains two services for the management, authentication and authorization of users of the GHGA data portal.

These two services are described in the following sections. The setting `provide_apis` can be used to determine which of the services will be started and which APIs these services should provide. The setting `run_consumer` should be set for the service instance that runs as an event consumer.

### Auth Adapter

The `auth_adapter` sub-package contains the authentication service used by the API gateway via the ExtAuth protocol. It is started when `provide_apis` contains the value `ext_auth`. No other APIs can be provided in that case.

If a `path_prefix` has been configured for the AuthService in the API gateway, then the `api_root_path` must be set accordingly.

Note that the Auth Adapter carries out a dual role in our architecture, by communicating directly with the client in order to establish user sessions and enroll TOTP, and also regulating access to the backend while modifying authorization headers. This utilises the [ExtAuth](https://www.getambassador.io/docs/edge-stack/latest/topics/running/services/ext-authz) protocol used by Envoy-based proxies like Emissary-ingress. It does not work with Nginx-based proxies like Ingress-Nginx, because the protocol for external authentication used by `http_auth_request_module` works in a slightly different way that prevents this dual-use of the Auth Apater.

Emissary-ingress does not forward all authorization headers by default, therefore the additional headers must be configured for the `AuthService` like this:

```yaml
  allowed_request_headers:
  - x-authorization
  - x-csrf-token
  allowed_authorization_headers:
  - cookie
  - x-authorization
  - x-csrf-token
  - x-session
```

The `x-authorization` header is only needed when an additional HTTP Basic Auth is used on top of the OIDC based authentication. Only the default `authorization` header actually needs to be modified by the Auth Adapter. However, for security purposes the Auth Adapter also empties the authorization headers that it consumes and evaluates itself and which are therefore not needed by the backend. Therefore, these are also specified as response headers.

### User Management

The `user_management` sub-package contains the user data management service which is run when `provide_apis` does not contain `ext_auth`.

The user management services can provide two APIs, the (public) `users` API for the user registry, and the (internal) `claims` API for the claims repository. The setting `provide_apis` can be used to specify which of the two APIs should be provided. For testing purposes, both APIs can be provided at the same time, but this is not recommended in production. If no API is specified, then only an health endpoint is provided.


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/auth-service):
```bash
docker pull ghga/auth-service:3.0.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/auth-service:3.0.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/auth-service:3.0.0 --help
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
- **`auth_events_topic`** *(string)*: The name of the topic for authentication related events. Default: `"auth"`.

- **`second_factor_recreated_event_type`** *(string)*: The event type for recreation of the second factor for authentication. Default: `"second_factor_recreated"`.

- **`iva_state_changed_topic`** *(string, required)*: The name of the topic containing IVA events.


  Examples:

  ```json
  "ivas"
  ```


- **`iva_state_changed_type`** *(string, required)*: The type to use for iva state changed events.


  Examples:

  ```json
  "iva_state_changed"
  ```


- **`dataset_change_topic`** *(string)*: the topic of the event announcing dataset deletions. Default: `"metadata_datasets"`.

- **`dataset_deletion_type`** *(string)*: the type of the event announcing dataset deletions. Default: `"dataset_deleted"`.

- **`dataset_upsertion_type`** *(string, required)*: Type used for events announcing a new dataset overview.


  Examples:

  ```json
  "dataset_created"
  ```


- **`claims_collection`** *(string)*: Name of the collection for user claims. Default: `"claims"`.

- **`user_topic`** *(string)*: The name of the topic containing user events. Default: `"users"`.

- **`users_collection`** *(string)*: Name of the collection for users. Default: `"users"`.

- **`user_tokens_collection`** *(string)*: Name of the collection for user tokens. Default: `"user_tokens"`.

- **`ivas_collection`** *(string)*: Name of the collection for IVAs. Default: `"ivas"`.

- **`service_name`** *(string)*: Short name of this service. Default: `"auth_service"`.

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


- **`kafka_max_retries`** *(integer)*: The maximum number of times to immediately retry consuming an event upon failure. Works independently of the dead letter queue. Minimum: `0`. Default: `0`.


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


- **`kafka_enable_dlq`** *(boolean)*: A flag to toggle the dead letter queue. If set to False, the service will crash upon exhausting retries instead of publishing events to the DLQ. If set to True, the service will publish events to the DLQ topic after exhausting all retries. Default: `false`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`kafka_dlq_topic`** *(string)*: The name of the topic used to resolve error-causing events. Default: `"dlq"`.


  Examples:

  ```json
  "dlq"
  ```


- **`kafka_retry_backoff`** *(integer)*: The number of seconds to wait before retrying a failed event. The backoff time is doubled for each retry attempt. Minimum: `0`. Default: `0`.


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


- **`mongo_dsn`** *(string, format: multi-host-uri, required)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


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


- **`mongo_timeout`**: Timeout in seconds for API calls to MongoDB. The timeout applies to all steps needed to complete the operation, including server selection, connection checkout, serialization, and server-side execution. When the timeout expires, PyMongo raises a timeout exception. If set to None, the operation will not time out (default MongoDB behavior). Default: `null`.

  - **Any of**

    - *integer*: Exclusive minimum: `0`.

    - *null*


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

- **`max_iva_verification_attempts`** *(integer)*: Maximum number of verification attempts for an IVA. Default: `10`.

- **`totp_issuer`** *(string)*: Issuer name for TOTP provisioning URIs. Default: `"GHGA"`.

- **`totp_image`**: URL of the PNG image provided in the TOTP provisioning URIs. Default: `null`.

  - **Any of**

    - *string, format: uri*

    - *null*


  Examples:

  ```json
  "https://www.ghga.de/logo.png"
  ```


- **`totp_algorithm`**: Refer to *[#/$defs/TOTPAlgorithm](#%24defs/TOTPAlgorithm)*. Default: `"sha1"`.

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


- **`api_ext_path`** *(string)*: external API path for the auth related endpoints (user, session and TOTP management). Default: `"/api/auth"`.

- **`auth_ext_keys`**: external public key set for auth adapter (used only by the auth adapter, determined using OIDC discovery if None). Default: `null`.

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

- **`provide_apis`** *(array)*: Which REST APIs should be provided. Default: `[]`.

  - **Items** *(string)*: Must be one of: `["ext_auth", "users", "claims"]`.


  Examples:

  ```json
  "[\"ext_auth\"]"
  ```


  ```json
  "[\"users\"]"
  ```


  ```json
  "[\"claims\"]"
  ```


- **`run_consumer`** *(boolean)*: Whether the service should run as an event consumer. Default: `false`.


  Examples:

  ```json
  "false"
  ```


  ```json
  "true"
  ```


- **`add_as_data_stewards`** *(array)*: A list of of data stewards to seed the claims repository with. All other data steward claims will be removed. This is only used with the claims API. Default: `[]`.

  - **Items**: Refer to *[#/$defs/UserWithIVA](#%24defs/UserWithIVA)*.

- **`oidc_authority_url`** *(string, format: uri)*: external OIDC authority URL used by the auth adapter. Default: `"https://login.aai.lifescience-ri.eu/oidc/"`.

- **`oidc_issuer`** *(string)*: external OIDC issuer for access tokens used by the auth adapter (URL format with or without end slash, determined using OIDC discovery if empty). Default: `"https://login.aai.lifescience-ri.eu/oidc/"`.

- **`oidc_userinfo_endpoint`**: external OIDC userinfo endpoint used by the auth adapter (determined using OIDC discovery if None). Default: `"https://login.aai.lifescience-ri.eu/oidc/userinfo"`.

  - **Any of**

    - *string, format: uri*

    - *null*

- **`oidc_client_id`** *(string)*: the registered OIDC client ID. Default: `"ghga-data-portal"`.

- **`organization_url`** *(string, format: uri)*: the URL used as source for internal claims. Default: `"https://ghga.de"`.

## Definitions


- <a id="%24defs/IvaType"></a>**`IvaType`** *(string)*: The type of IVA. Must be one of: `["Phone", "Fax", "PostalAddress", "InPerson"]`.

- <a id="%24defs/TOTPAlgorithm"></a>**`TOTPAlgorithm`** *(string)*: Hash algorithm used for TOTP code generation. Must be one of: `["sha1", "sha256", "sha512"]`.

- <a id="%24defs/UserWithIVA"></a>**`UserWithIVA`** *(object)*: User with external ID and associated IVA. Cannot contain additional properties.

  - **`ext_id`** *(string, required)*: The external ID of the user.

  - **`name`** *(string, required)*: The full name of the user.

  - **`email`** *(string, required)*: The email address of the user.

  - **`iva_type`**: The type of the validation address of the user. Refer to *[#/$defs/IvaType](#%24defs/IvaType)*.

  - **`iva_value`** *(string, required)*: The actual validation address of the user.


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
