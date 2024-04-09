[![tests](https://github.com/ghga-de/internal-file-registry-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/internal-file-registry-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/internal-file-registry-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/internal-file-registry-service?branch=main)

# Internal File Registry Service

Internal-File-Registry-Service - This service acts as a registry for the internal location and representation of files.

## Description

This service provides functionality to administer files stored in an S3-compatible
object storage.
All file-related metadata is stored in an internal mongodb database, owned and controlled
by this service.
It exposes no REST API enpoints and communicates with other services via events.

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

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/internal-file-registry-service):
```bash
docker pull ghga/internal-file-registry-service:1.3.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/internal-file-registry-service:1.3.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/internal-file-registry-service:1.3.0 --help
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
- **`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- **`service_name`** *(string)*: Default: `"internal_file_registry"`.

- **`service_instance_id`** *(string)*: A string that uniquely identifies this instance across all instances of this service. A globally unique Kafka client ID will be created by concatenating the service_name and the service_instance_id.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


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


- **`object_storages`** *(object)*: Can contain additional properties.

  - **Additional properties**: Refer to *[#/$defs/S3ObjectStorageNodeConfig](#%24defs/S3ObjectStorageNodeConfig)*.

- **`file_registered_event_topic`** *(string)*: Name of the topic used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "internal_file_registry"
  ```


- **`file_registered_event_type`** *(string)*: The type used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "file_registered"
  ```


- **`file_staged_event_topic`** *(string)*: Name of the topic used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "internal_file_registry"
  ```


- **`file_staged_event_type`** *(string)*: The type used for events indicating that a new file has been internally registered.


  Examples:

  ```json
  "file_staged_for_download"
  ```


- **`file_deleted_event_topic`** *(string)*: Name of the topic used for events indicating that a file has been deleted.


  Examples:

  ```json
  "internal_file_registry"
  ```


- **`file_deleted_event_type`** *(string)*: The type used for events indicating that a file has been deleted.


  Examples:

  ```json
  "file_deleted"
  ```


- **`files_to_register_topic`** *(string)*: The name of the topic to receive events informing about new files to register.


  Examples:

  ```json
  "file_interrogation"
  ```


- **`files_to_register_type`** *(string)*: The type used for events informing about new files to register.


  Examples:

  ```json
  "file_interrogation_success"
  ```


- **`files_to_stage_topic`** *(string)*: The name of the topic to receive events informing about files to stage.


  Examples:

  ```json
  "file_downloads"
  ```


- **`files_to_stage_type`** *(string)*: The type used for events informing about a file to be staged.


  Examples:

  ```json
  "file_stage_requested"
  ```


- **`files_to_delete_topic`** *(string)*: The name of the topic to receive events informing about files to delete.


  Examples:

  ```json
  "file_deletions"
  ```


- **`files_to_delete_type`** *(string)*: The type used for events informing about a file to be deleted.


  Examples:

  ```json
  "file_deletion_requested"
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

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when trying to publish an event without a valid correlation ID set for the context. If True, the a newly correlation ID will be generated and used in the event header. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`db_connection_str`** *(string, format: password)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- **`db_name`** *(string)*: Name of the database located on the MongoDB server.


  Examples:

  ```json
  "my-database"
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
Please adapt it, rename it to `.ifrs.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.ifrs.yaml`)
- in your home directory (on unix: `~/.ifrs.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ifrs_`,
e.g. for the `host` set an environment variable named `ifrs_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
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
