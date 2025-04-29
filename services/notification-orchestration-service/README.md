[![tests](https://github.com/ghga-de/notification-orchestration-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/notification-orchestration-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/notification-orchestration-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/notification-orchestration-service?branch=main)

# Notification Orchestration Service

The Notification Orchestration Service controls the creation of notification events.

## Description

<!-- Please provide a short overview of the features of this service. -->

The Notification Orchestration Service (NOS) uses data harvested from events published
by various services to form Notification events, which are subsequently consumed by the
Notification Service (NS) for dissemination.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/notification-orchestration-service):
```bash
docker pull ghga/notification-orchestration-service:4.0.2
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/notification-orchestration-service:4.0.2 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/notification-orchestration-service:4.0.2 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
nos --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
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


- <a id="properties/notification_topic"></a>**`notification_topic`** *(string, required)*: Name of the topic used for notification events.


  Examples:

  ```json
  "notifications"
  ```


- <a id="properties/notification_type"></a>**`notification_type`** *(string, required)*: The type used for notification events.


  Examples:

  ```json
  "notification"
  ```


- <a id="properties/user_topic"></a>**`user_topic`** *(string)*: The name of the topic containing user events. Default: `"users"`.

- <a id="properties/auth_topic"></a>**`auth_topic`** *(string, required)*: The name of the topic containing auth-related events.


  Examples:

  ```json
  "auth-events"
  ```


- <a id="properties/second_factor_recreated_type"></a>**`second_factor_recreated_type`** *(string, required)*: The event type for recreation of the second factor for authentication.


  Examples:

  ```json
  "second_factor_recreated"
  ```


- <a id="properties/iva_state_changed_topic"></a>**`iva_state_changed_topic`** *(string, required)*: The name of the topic containing IVA events.


  Examples:

  ```json
  "ivas"
  ```


- <a id="properties/iva_state_changed_type"></a>**`iva_state_changed_type`** *(string, required)*: The type to use for iva state changed events.


  Examples:

  ```json
  "iva_state_changed"
  ```


- <a id="properties/access_request_topic"></a>**`access_request_topic`** *(string, required)*: Name of the event topic used to consume access request events.


  Examples:

  ```json
  "access-requests"
  ```


- <a id="properties/access_request_denied_type"></a>**`access_request_denied_type`** *(string, required)*: The type to use for access request denied events.


  Examples:

  ```json
  "access_request_denied"
  ```


- <a id="properties/access_request_created_type"></a>**`access_request_created_type`** *(string, required)*: The type to use for access request created events.


  Examples:

  ```json
  "access_request_created"
  ```


- <a id="properties/access_request_allowed_type"></a>**`access_request_allowed_type`** *(string, required)*: The type to use for access request allowed events.


  Examples:

  ```json
  "access_request_allowed"
  ```


- <a id="properties/service_name"></a>**`service_name`** *(string)*: The Notification Orchestration Service controls the creation of notification events. Default: `"nos"`.

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


- <a id="properties/kafka_security_protocol"></a>**`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. Must be one of: `["PLAINTEXT", "SSL"]`. Default: `"PLAINTEXT"`.

- <a id="properties/kafka_ssl_cafile"></a>**`kafka_ssl_cafile`** *(string)*: Certificate Authority file path containing certificates used to sign broker certificates. If a CA is not specified, the default system CA will be used if found by OpenSSL. Default: `""`.

- <a id="properties/kafka_ssl_certfile"></a>**`kafka_ssl_certfile`** *(string)*: Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity. Default: `""`.

- <a id="properties/kafka_ssl_keyfile"></a>**`kafka_ssl_keyfile`** *(string)*: Optional filename containing the client private key. Default: `""`.

- <a id="properties/kafka_ssl_password"></a>**`kafka_ssl_password`** *(string, format: password, write-only)*: Optional password to be used for the client private key. Default: `""`.

- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context. If True, the a newly correlation ID will be generated and used in the event header. Default: `true`.


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


- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

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

- <a id="properties/central_data_stewardship_email"></a>**`central_data_stewardship_email`** *(string, required)*: The email address of the central data steward.

- <a id="properties/helpdesk_email"></a>**`helpdesk_email`** *(string, required)*: The email address of the GHGA Helpdesk.


### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.nos.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.nos.yaml`)
- in your home directory (on Linux: `~/.nos.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `nos_`,
e.g. for the `host` set an environment variable named `nos_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.



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
