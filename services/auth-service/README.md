
[![tests](https://github.com/ghga-de/auth-service/actions/workflows/unit_and_int_tests.yaml/badge.svg)](https://github.com/ghga-de/auth-service/actions/workflows/unit_and_int_tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/auth-service/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/auth-service?branch=main)

# Auth Service

Authentication service for the GHGA data portal used by the API gateway via the ExtAuth protocol

## Description

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
docker pull ghga/auth-service:0.5.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/auth-service:0.5.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/auth-service:0.5.0 --help
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
- **`auth_key`** *(string)*

- **`auth_algs`** *(array)*: Default: `['ES256']`.

  - **Items** *(string)*

- **`auth_check_claims`** *(object)*: Default: `{'name': None, 'email': None, 'iat': None, 'exp': None}`.

- **`auth_map_claims`** *(object)*: Can contain additional properties. Default: `{}`.

  - **Additional Properties** *(string)*

- **`host`** *(string)*: IP of the host. Default: `127.0.0.1`.

- **`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- **`log_level`** *(string)*: Must be one of: `['critical', 'error', 'warning', 'info', 'debug', 'trace']`. Default: `debug`.

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

- **`service_name`** *(string)*: Default: `auth_service`.

- **`run_auth_adapter`** *(boolean)*: Default: `False`.

- **`api_ext_path`** *(string)*: Default: `/api/auth`.

- **`auth_ext_keys`** *(string)*

- **`auth_ext_algs`** *(array)*: Default: `['RS256', 'ES256']`.

  - **Items** *(string)*

- **`basic_auth_credentials`** *(string)*

- **`basic_auth_realm`** *(string)*: Default: `GHGA Data Portal`.

- **`public_paths`** *(array)*: Default: `['/.well-known/*', '/service-logo.png']`.

  - **Items** *(string)*

- **`include_apis`** *(array)*: Default: `['users']`.

  - **Items** *(string)*: Must be one of: `['users', 'claims']`.

- **`add_as_data_stewards`** *(array)*: Default: `[]`.

  - **Items** *(string)*

- **`oidc_authority_url`** *(string)*: Default: `https://proxy.aai.lifescience-ri.eu`.

- **`oidc_userinfo_endpoint`** *(string)*: Default: `https://proxy.aai.lifescience-ri.eu/OIDC/userinfo`.

- **`oidc_client_id`** *(string)*: Default: `ghga-data-portal`.

- **`organization_url`** *(string)*: Default: `https://ghga.de`.

- **`db_url`** *(string)*: Default: `mongodb://mongodb:27017`.

- **`db_name`** *(string)*: Default: `user-management`.

- **`users_collection`** *(string)*: Default: `users`.

- **`claims_collection`** *(string)*: Default: `claims`.


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
This repository contains Python-based services that are partially following the Triple Hexagonal Architecture pattern. The services use FastAPI and protocol/provider pairs provided by the [hexkit](https://github.com/ghga-de/hexkit) library.

This repository will be eventually refactored and split into three separate services.


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
