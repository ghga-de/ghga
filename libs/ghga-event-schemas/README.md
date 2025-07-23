[![tests](https://github.com/ghga-de/ghga-event-schemas/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/ghga-event-schemas/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/ghga-event-schemas/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/ghga-event-schemas?branch=main)

# Ghga Event Schemas

GHGA Event Schemas: A package that collects schemas used for events exchanged between GHGA service.

## Description

This package contains a collection of Pydantic-based models used to provide type-checked
and validated event schemas.


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/ghga-event-schemas):
```bash
docker pull ghga/ghga-event-schemas:10.0.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/ghga-event-schemas:10.0.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/ghga-event-schemas:10.0.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
ghga_event_schemas --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Short name of this service. Default: `"my_microservice"`.

- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service. This is included in log messages.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


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


- <a id="properties/host"></a>**`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.

- <a id="properties/port"></a>**`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- <a id="properties/auto_reload"></a>**`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.

- <a id="properties/workers"></a>**`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- <a id="properties/api_root_path"></a>**`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `""`.

- <a id="properties/openapi_url"></a>**`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `"/openapi.json"`.

- <a id="properties/docs_url"></a>**`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `"/docs"`.

- <a id="properties/cors_allowed_origins"></a>**`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_origins/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_origins/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_origins/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allow_credentials"></a>**`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allow_credentials/anyOf/0"></a>*boolean*

    - <a id="properties/cors_allow_credentials/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allowed_methods"></a>**`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_methods/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_methods/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_methods/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "*"
  ]
  ```


- <a id="properties/cors_allowed_headers"></a>**`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_headers/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_headers/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_headers/anyOf/1"></a>*null*


  Examples:

  ```json
  []
  ```


- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- <a id="properties/language"></a>**`language`** *(string)*: The language. Must be one of: "Greek", "Croatian", "French", or "German". Default: `"Croatian"`.


### Usage:

A template YAML for configuring the service can be found at
[`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.ghga_event_schemas.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.ghga_event_schemas.yaml`)
- in your home directory (on Linux: `~/.ghga_event_schemas.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ghga_event_schemas_`,
e.g. for the `host` set an environment variable named `ghga_event_schemas_host`
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
[`lock/requirements-dev.txt`](./lock/requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [.readme_generation/README.md](./.readme_generation/README.md)
for details.
