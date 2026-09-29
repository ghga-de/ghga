# Notification Orchestration Service

The Notification Orchestration Service controls the creation of notification events.

## Description

<!-- Please provide a short overview of the features of this service. -->

The Notification Orchestration Service (NOS) uses data harvested from events published by various services to form Notification events, which are subsequently consumed by the Notification Service (NS) for dissemination.

## Installation

Each GHGA platform release publishes the service as a container image on [Docker Hub](https://hub.docker.com/r/ghga/nos), tagged with the platform version:

```bash
docker pull ghga/nos:<platform-version>
```

To build the image yourself, run this from the repository root:

```bash
docker build -f docker/Dockerfile --build-arg PACKAGE=nos --build-arg EXECUTABLE=nos -t ghga/nos .
```

The entrypoint starts the service, which reads its settings as described under [Configuration](#configuration):

```bash
docker run -p 8080:8080 ghga/nos:<platform-version>
```

For Kubernetes, use the Helm chart [`nos`](../../deploy/charts/nos/README.md):

```bash
helm install nos oci://registry-1.docker.io/ghga/nos-chart
```

To run the service without a container, start it from the repository root in the workspace environment:

```bash
uv run nos
```

## Configuration

### Parameters

The service requires the following configuration parameters:

- <a id="properties/mongo_dsn"></a>**`mongo_dsn`** *(string, format: multi-host-uri, required)*: MongoDB connection string.
  Might include credentials.
  For more information see: <https://naiveskill.com/mongodb-connection-string/>.
  Length must be at least 1.

  Examples:

  ```json
  "mongodb://localhost:27017"
  ```

- <a id="properties/db_name"></a>**`db_name`** *(string, required)*: Name of the database located on the MongoDB server.

  Examples:

  ```json
  "my-database"
  ```

- <a id="properties/mongo_timeout"></a>**`mongo_timeout`**: Timeout in seconds for API calls to MongoDB.
  The timeout applies to all steps needed to complete the operation, including server selection, connection checkout, serialization, and server-side execution.
  When the timeout expires, PyMongo raises a timeout exception.
  If set to None, the operation will not time out (default MongoDB behavior).
  Default: `null`.
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

- <a id="properties/migration_max_wait_sec"></a>**`migration_max_wait_sec`**: The maximum number of seconds to wait for migrations to complete before raising an error.
  Default: `null`.
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

- <a id="properties/notification_topic"></a>**`notification_topic`** *(string, required)*: Name of the topic used for notification events.

  Examples:

  ```json
  "notifications"
  ```

- <a id="properties/email_notification_type"></a>**`email_notification_type`** *(string, required)*: The type used for email notification events.

  Examples:

  ```json
  "email_notification"
  ```

- <a id="properties/sms_notification_type"></a>**`sms_notification_type`** *(string, required)*: The type used for SMS notification events.

  Examples:

  ```json
  "sms_notification"
  ```

- <a id="properties/access_request_topic"></a>**`access_request_topic`** *(string, required)*: Name of the event topic containing access request events.

  Examples:

  ```json
  "access-requests"
  ```

- <a id="properties/user_topic"></a>**`user_topic`** *(string)*: The name of the topic containing user events.
  Default: `"users"`.
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

- <a id="properties/iva_state_changed_type"></a>**`iva_state_changed_type`** *(string, required)*: The type to use for IVA state changed events.

  Examples:

  ```json
  "iva_state_changed"
  ```

- <a id="properties/iva_send_code_type"></a>**`iva_send_code_type`** *(string, required)*: The type to use for IVA send code events.

  Examples:

  ```json
  "iva_send_code"
  ```

- <a id="properties/service_name"></a>**`service_name`** *(string)*: The Notification Orchestration Service controls the creation of notification events.
  Default: `"nos"`.
- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service.
  This is included in log messages.

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

- <a id="properties/kafka_security_protocol"></a>**`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers.
  Valid values are: PLAINTEXT, SSL.
  Must be one of: "PLAINTEXT" or "SSL".
  Default: `"PLAINTEXT"`.
- <a id="properties/kafka_ssl_cafile"></a>**`kafka_ssl_cafile`** *(string)*: Certificate Authority file path containing certificates used to sign broker certificates.
  If a CA is not specified, the default system CA will be used if found by OpenSSL.
  Default: `""`.
- <a id="properties/kafka_ssl_certfile"></a>**`kafka_ssl_certfile`** *(string)*: Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity.
  Default: `""`.
- <a id="properties/kafka_ssl_keyfile"></a>**`kafka_ssl_keyfile`** *(string)*: Optional filename containing the client private key.
  Default: `""`.
- <a id="properties/kafka_ssl_password"></a>**`kafka_ssl_password`** *(string, format: password, write-only)*: Optional password to be used for the client private key.
  Default: `""`.
- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context.
  If True, a new correlation ID will be generated and used in the event header.
  Default: `true`.

  Examples:

  ```json
  true
  ```

  ```json
  false
  ```

- <a id="properties/kafka_max_message_size"></a>**`kafka_max_message_size`** *(integer)*: The largest message size that can be transmitted, in bytes, before compression.
  Only services that have a need to send/receive larger messages should set this.
  When used alongside compression, this value can be set to something greater than the broker's `message.max.bytes` field, which effectively concerns the compressed message size.
  Exclusive minimum: `0`.
  Default: `1048576`.

  Examples:

  ```json
  1048576
  ```

  ```json
  16777216
  ```

- <a id="properties/kafka_compression_type"></a>**`kafka_compression_type`**: The compression type used for messages.
  Valid values are: None, gzip, snappy, lz4, and zstd.
  If None, no compression is applied.
  This setting is only relevant for the producer and has no effect on the consumer.
  If set to a value, the producer will compress messages before sending them to the Kafka broker.
  If unsure, zstd provides a good balance between speed and compression ratio.
  Default: `null`.
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

- <a id="properties/kafka_max_retries"></a>**`kafka_max_retries`** *(integer)*: The maximum number of times to immediately retry consuming an event upon failure.
  Works independently of the dead letter queue.
  Minimum: `0`.
  Default: `0`.

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

- <a id="properties/kafka_enable_dlq"></a>**`kafka_enable_dlq`** *(boolean)*: A flag to toggle the dead letter queue.
  If set to False, the service will crash upon exhausting retries instead of publishing events to the DLQ.
  If set to True, the service will publish events to the DLQ topic after exhausting all retries.
  Default: `false`.

  Examples:

  ```json
  true
  ```

  ```json
  false
  ```

- <a id="properties/kafka_dlq_topic"></a>**`kafka_dlq_topic`** *(string)*: The name of the topic used to resolve error-causing events.
  Default: `"dlq"`.

  Examples:

  ```json
  "dlq"
  ```

- <a id="properties/kafka_retry_backoff"></a>**`kafka_retry_backoff`** *(integer)*: The number of seconds to wait before retrying a failed event.
  The backoff time is doubled for each retry attempt.
  Minimum: `0`.
  Default: `0`.

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

- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture.
  Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE".
  Default: `"INFO"`.
- <a id="properties/log_format"></a>**`log_format`**: If set, will replace JSON formatting with the specified string format.
  If not set, has no effect.
  In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details.
  Default: `null`.
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

- <a id="properties/log_traceback"></a>**`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages.
  Default: `true`.
- <a id="properties/central_data_stewardship_email"></a>**`central_data_stewardship_email`** *(string, required)*: The email address of the central data steward.
- <a id="properties/helpdesk_email"></a>**`helpdesk_email`** *(string, required)*: The email address of the GHGA Helpdesk.
- <a id="properties/portal_url"></a>**`portal_url`** *(string, format: uri)*: The URL of the GHGA data portal.
  Length must be between 1 and 2083 (inclusive).
  Default: `"https://data.ghga.de/"`.

### Usage

A template YAML file for configuring the service can be found at [`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.nos.yaml`, and place it in one of the following locations:

- in the current working directory where you execute the service (on Linux: `./.nos.yaml`)
- in your home directory (on Linux: `~/.nos.yaml`)

The config YAML file will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml) can also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `nos_`, e.g. for the `host` set an environment variable named `nos_host` (you may use both upper or lower cases, however, it is standard to define all env variables in upper cases).

To use file secrets, please refer to the [corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support) of the pydantic documentation.

## Architecture and Design
<!-- Please provide an overview of the architecture and design of the code base.
Mention anything that deviates from the standard triple hexagonal architecture and
the corresponding structure. -->

This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the [hexkit](https://github.com/ghga-de/ghga/tree/main/libs/hexkit) library.

## Development

The service is a member of the [GHGA monorepo](../../README.md), which provides the development environment: work in its dev container, as described in [Work inside the dev container](../../README.md#work-inside-the-dev-container).
Run the service's tests with `just test services/notification-orchestration-service`, and the linters with `just lint`.

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
