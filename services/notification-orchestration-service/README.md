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

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/notification-orchestration-service):
```bash
docker pull ghga/notification-orchestration-service:2.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/notification-orchestration-service:2.1.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/notification-orchestration-service:2.1.0 --help
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
- **`db_connection_str`** *(string, format: password, required)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- **`db_name`** *(string, required)*: Name of the database located on the MongoDB server.


  Examples:

  ```json
  "my-database"
  ```


- **`notification_event_topic`** *(string, required)*: Name of the topic used for notification events.


  Examples:

  ```json
  "notifications"
  ```


- **`notification_event_type`** *(string, required)*: The type used for notification events.


  Examples:

  ```json
  "notification"
  ```


- **`user_events_topic`** *(string)*: The name of the topic containing user events. Default: `"users"`.

- **`access_request_events_topic`** *(string, required)*: Name of the event topic used to consume access request events.


  Examples:

  ```json
  "access_requests"
  ```


- **`access_request_created_event_type`** *(string, required)*: The type to use for access request created events.


  Examples:

  ```json
  "access_request_created"
  ```


- **`access_request_allowed_event_type`** *(string, required)*: The type to use for access request allowed events.


  Examples:

  ```json
  "access_request_allowed"
  ```


- **`access_request_denied_event_type`** *(string, required)*: The type to use for access request denied events.


  Examples:

  ```json
  "access_request_denied"
  ```


- **`file_registered_event_topic`** *(string, required)*: The name of the topic containing internal file registration events.


  Examples:

  ```json
  "internal_file_registry"
  ```


- **`file_registered_event_type`** *(string, required)*: The type used for events detailing internally file registrations.


  Examples:

  ```json
  "file_registered"
  ```


- **`iva_state_changed_event_topic`** *(string, required)*: The name of the topic containing IVA events.


  Examples:

  ```json
  "ivas"
  ```


- **`iva_state_changed_event_type`** *(string, required)*: The type to use for iva state changed events.


  Examples:

  ```json
  "iva_state_changed"
  ```


- **`second_factor_recreated_event_topic`** *(string, required)*: The name of the topic containing second factor recreation events.


  Examples:

  ```json
  "auth"
  ```


- **`second_factor_recreated_event_type`** *(string, required)*: The event type for recreation of the second factor for authentication.


  Examples:

  ```json
  "second_factor_recreated"
  ```


- **`service_name`** *(string)*: The Notification Orchestration Service controls the creation of notification events. Default: `"nos"`.

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

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context. If True, the a newly correlation ID will be generated and used in the event header. Default: `true`.


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

- **`central_data_stewardship_email`** *(string, required)*: The email address of the central data steward.

- **`helpdesk_email`** *(string, required)*: The email address of the GHGA Helpdesk.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.nos.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.nos.yaml`)
- in your home directory (on unix: `~/.nos.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `nos_`,
e.g. for the `host` set an environment variable named `nos_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
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
