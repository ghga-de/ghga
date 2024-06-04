[![tests](https://github.com/ghga-de/download-controller-service/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/download-controller-service/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/download-controller-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/download-controller-service?branch=main)

# Download Controller Service

Download Controller Service - a GA4GH DRS-compliant service for delivering files from S3 encrypted according to the GA4GH Crypt4GH standard.

## Description

This service implements the
[GA4GH DRS](https://github.com/ga4gh/data-repository-service-schemas) v1.0.0 for
serving files that where encrypted according to the
[GA4GH Crypt4GH](https://www.ga4gh.org/news/crypt4gh-a-secure-method-for-sharing-human-genetic-data/)
from S3-compatible object storages.

Thereby, only the `GET /objects/{object_id}` is implemented. It always returns
an access_method for the object via S3. This makes the second endpoint
`GET /objects/{object_id}/access/{access_id}` that
is contained in the DRS spec unnecessary. For more details see the OpenAPI spec
described below.

For authorization, a JSON web token is expected via Bearer Authentication that has a format
described [here](./dcs/core/auth_policies.py).

All files that can be requested are registered in a MongoDB database owned and
controlled by this service. Registration of new events happens through a Kafka event.

It serves pre-signed URLs to S3 objects located in a single so-called outbox bucket.
If the file is not already in the bucket when the user calls the object endpoint,
an event is published to request staging the file to the outbox. The staging has to
be carried out by a different service.

For more details on the events consumed and produced by this service, see the
configuration.

The DRS object endpoint serves files in an encrypted fashion as described by the
Crypt4GH standard, but without the evelope. A user-specific envelope can be requested
from the `GET /objects/{object_id}/envelopes` endpoint. The actual envelope creation
is delegated to another service via a RESTful call. Please see the configuration for
further details.


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/download-controller-service):
```bash
docker pull ghga/download-controller-service:1.3.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/download-controller-service:1.3.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/download-controller-service:1.3.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
dcs --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- **`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- **`service_name`** *(string)*: Default: `"dcs"`.

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

- **`files_to_register_topic`** *(string)*: The name of the topic to receive events informing about new files that shall be made available for download.


  Examples:

  ```json
  "internal_file_registry"
  ```


- **`files_to_register_type`** *(string)*: The type used for events informing about new files that shall be made available for download.


  Examples:

  ```json
  "file_registered"
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


- **`download_served_event_topic`** *(string)*: Name of the topic used for events indicating that a download of a specified file happened.


  Examples:

  ```json
  "file_downloads"
  ```


- **`download_served_event_type`** *(string)*: The type used for event indicating that a download of a specified file happened.


  Examples:

  ```json
  "donwload_served"
  ```


- **`unstaged_download_event_topic`** *(string)*: Name of the topic used for events indicating that a download was requested for a file that is not yet available in the outbox.


  Examples:

  ```json
  "file_downloads"
  ```


- **`unstaged_download_event_type`** *(string)*: The type used for event indicating that a download was requested for a file that is not yet available in the outbox.


  Examples:

  ```json
  "unstaged_download_requested"
  ```


- **`file_registered_event_topic`** *(string)*: Name of the topic used for events indicating that a file has been registered for download.


  Examples:

  ```json
  "file_downloads"
  ```


- **`file_registered_event_type`** *(string)*: The type used for event indicating that that a file has been registered for download.


  Examples:

  ```json
  "file_registered"
  ```


- **`file_deleted_event_topic`** *(string)*: Name of the topic used for events indicating that a file has been deleted.


  Examples:

  ```json
  "file_downloads"
  ```


- **`file_deleted_event_type`** *(string)*: The type used for events indicating that a file has been deleted.


  Examples:

  ```json
  "file_deleted"
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

- **`kafka_ssl_password`** *(string, format: password)*: Optional password to be used for the client private key. Default: `""`.

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


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


- **`drs_server_uri`** *(string)*: The base of the DRS URI to access DRS objects. Has to start with 'drs://' and end with '/'.


  Examples:

  ```json
  "drs://localhost:8080/"
  ```


- **`retry_access_after`** *(integer)*: When trying to access a DRS object that is not yet in the outbox, instruct to retry after this many seconds. Default: `120`.

- **`ekss_base_url`** *(string)*: URL containing host and port of the EKSS endpoint to retrieve personalized envelope from.


  Examples:

  ```json
  "http://ekss:8080/"
  ```


- **`presigned_url_expires_after`** *(integer)*: Expiration time in seconds for presigned URLS. Positive integer required. Exclusive minimum: `0`.


  Examples:

  ```json
  30
  ```


- **`cache_timeout`** *(integer)*: Time in days since last access after which a file present in the outbox should be unstaged and has to be requested from permanent storage again for the next request. Default: `7`.

- **`auth_key`** *(string)*: The GHGA internal public key for validating the token signature.


  Examples:

  ```json
  "{\"crv\": \"P-256\", \"kty\": \"EC\", \"x\": \"...\", \"y\": \"...\"}"
  ```


- **`auth_algs`** *(array)*: A list of all algorithms used for signing GHGA internal tokens. Default: `["ES256"]`.

  - **Items** *(string)*

- **`auth_check_claims`** *(object)*: A dict of all GHGA internal claims that shall be verified. Default: `{"type": null, "file_id": null, "user_id": null, "user_public_crypt4gh_key": null, "full_user_name": null, "email": null, "iat": null, "exp": null}`.

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


- **`api_route`** *(string)*: Default: `"/ga4gh/drs/v1"`.

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
Please adapt it, rename it to `.dcs.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.dcs.yaml`)
- in your home directory (on unix: `~/.dcs.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `dcs_`,
e.g. for the `host` set an environment variable named `dcs_host`
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
