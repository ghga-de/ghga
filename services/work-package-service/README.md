
[![tests](https://github.com/ghga-de/work-package-service/actions/workflows/unit_and_int_tests.yaml/badge.svg)](https://github.com/ghga-de/work-package-service/actions/workflows/unit_and_int_tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/work-package-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/work-package-service?branch=main)

# Work Package Service

Work Package Service

## Description

The work package service allows creating work packages for downloading or
uploading dataset files and provides an authorization mechanism for these tasks
by issuing access and work order tokens.

### API endpoints:

#### `POST /work-packages`

Creates a work package.

- auth header: internal access token
- request body:
  - `dataset_id`: string (the ID of a dataset)
  - `type`: enum (download/upload)
  - `file_ids`: array of strings  (null = all files of the dataset)
  - `user_public_crypt4gh_key`: string (the user's public Crypt4GH key)
- response body:
  - `id`: string (the ID of the created work package)
  - `token`: string (encrypted work and base64 encoded package access token)

####  `GET /work-packages/{work_package_id}`

Gets details on the specified work package.

- auth header: work package access token

#### `POST /work-packages/{work_package_id}/files/{file_id}/work-order-tokens`

 Creates an encrypted work order token for the specified work package and file.

- auth header: work package access token

#### `GET /users/{user_id}/datasets`

Gets a list of all dataset IDs that can be downloaded by the user.

- auth header: internal access token with the user context


## Installation
We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/work-package-service):
```bash
docker pull ghga/work-package-service:0.1.4
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/work-package-service:0.1.4 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/work-package-service:0.1.4 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
wps --help
```

## Configuration
### Parameters

The service requires the following configuration parameters:
- **`datasets_collection`** *(string)*: The name of the database collection for datasets. Default: `datasets`.

- **`work_packages_collection`** *(string)*: The name of the database collection for work packages. Default: `workPackages`.

- **`work_package_valid_days`** *(integer)*: How many days a work package (and its access token) stays valid. Default: `30`.

- **`work_package_signing_key`** *(string)*: The private key for signing work order tokens.

- **`db_connection_str`** *(string)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.

- **`db_name`** *(string)*: Default: `work-packages`.

- **`service_name`** *(string)*: Default: `wps`.

- **`service_instance_id`** *(string)*: A string that uniquely identifies this instance across all instances of this service. A globally unique Kafka client ID will be created by concatenating the service_name and the service_instance_id.

- **`kafka_servers`** *(array)*: A list of connection strings to connect to Kafka bootstrap servers.

  - **Items** *(string)*

- **`dataset_change_event_topic`** *(string)*: Name of the topic for events that inform about datasets.

- **`dataset_upsertion_event_type`** *(string)*: The type of events that inform about new and changed datasets.

- **`dataset_deletion_event_type`** *(string)*: The type of events that inform about deleted datasets.

- **`download_access_url`** *(string)*: URL pointing to the internal download access API.

- **`auth_key`** *(string)*: The GHGA internal public key for validating the token signature.

- **`auth_algs`** *(array)*: A list of all algorithms used for signing GHGA internal tokens. Default: `['ES256']`.

  - **Items** *(string)*

- **`auth_check_claims`** *(object)*: A dict of all GHGA internal claims that shall be verified. Default: `{'name': None, 'email': None, 'iat': None, 'exp': None}`.

- **`auth_map_claims`** *(object)*: A mapping of claims to attributes in the GHGA auth context. Can contain additional properties. Default: `{}`.

  - **Additional Properties** *(string)*

- **`host`** *(string)*: IP of the host. Default: `127.0.0.1`.

- **`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- **`log_level`** *(string)*: Controls the verbosity of the log. Must be one of: `['critical', 'error', 'warning', 'info', 'debug', 'trace']`. Default: `info`.

- **`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `False`.

- **`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- **`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `/`.

- **`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `/openapi.json`.

- **`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `/docs`.

- **`cors_allowed_origins`** *(array)*: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin.

  - **Items** *(string)*

- **`cors_allow_credentials`** *(boolean)*: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified.

- **`cors_allowed_methods`** *(array)*: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods.

  - **Items** *(string)*

- **`cors_allowed_headers`** *(array)*: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests.

  - **Items** *(string)*


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.wps.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.wps.yaml`)
- in your home directory (on unix: `~/.wps.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `wps_`,
e.g. for the `host` set an environment variable named `wps_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](./openapi.yaml).

## Architecture and Design:
This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.


## Development
For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as vscode with its "Remote - Containers"
extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in vscode and run the command
`Remote-Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formating
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, a convenience commands `dev_install` is available.
It installs the service with all development dependencies, installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./setup.cfg`](./setup.cfg) or the
[`./requirements-dev.txt`](./requirements-dev.txt), please run it again.

## License
This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## Readme Generation
This readme is autogenerate, please see [`readme_generation.md`](./readme_generation.md)
for details.
