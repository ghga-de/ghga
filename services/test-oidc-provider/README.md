
[![tests](https://github.com/ghga-de/test-oidc-provider/actions/workflows/unit_and_int_tests.yaml/badge.svg)](https://github.com/ghga-de/test-oidc-provider/actions/workflows/unit_and_int_tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/test-oidc-provider/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/test-oidc-provider?branch=main)

# Test Oidc Provider

Test OpenID Connect provider

## Description

This repository contains a dummy OpenID Connect provider (OP)
that can be user for testing purposes.

It provides the .well-known endpoint and the UserInfo endpoint,
plus an endpoint that can be used by test applications to create access tokens.


## Installation
We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/test-oidc-provider):
```bash
docker pull ghga/test-oidc-provider:0.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/test-oidc-provider:0.1.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/test-oidc-provider:0.1.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
top --help
```

## Configuration
### Parameters

The service requires the following configuration parameters:
- **`issuer`** *(string)*: test issuer URL. Default: `https://test-op.org`.

- **`user_domain`** *(string)*: domain name of the home organization of the test users. Default: `home.org`.

- **`client_id`** *(string)*: test client ID. Default: `test-client`.

- **`valid_seconds`** *(integer)*: default expiration time of access tokens in seconds. Default: `3600`.

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

- **`service_name`** *(string)*: Short name of this service. Default: `top`.

- **`service_url`** *(string)*: External base URL of this service. Default: `https://top`.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.top.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.top.yaml`)
- in your home directory (on unix: `~/.top.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `top_`,
e.g. for the `host` set an environment variable named `top_host`
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
