[![tests](https://github.com/ghga-de/ghga-connector/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/ghga-connector/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/ghga-connector/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/ghga-connector?branch=main)

# Ghga Connector

GHGA Connector - A CLI client application for interacting with the GHGA system.

## Description

The GHGA Connector is a command line client facilitating interaction with the file storage infrastructure of GHGA.
To this end, it provides commands for the up- and download of files that interact with the RESTful APIs exposed by the Upload Controller Service (https://github.com/ghga-de/upload-controller-service) and Download Controller Service (https://github.com/ghga-de/download-controller-service), respectively.

When uploading, the Connector expects an unencrypted file that is subsequently encrypted according to the Crypt4GH standard (https://www.ga4gh.org/news_item/crypt4gh-a-secure-method-for-sharing-human-genetic-data/) and only afterwards uploaded to the GHGA storage infrastructure.

When downloading, the resulting file is still encrypted in this manner and can be decrypted using the Connector's decrypt command.
As the user is expected to download multiple files, this command takes a directory location as input and an optional output directory location can be provided, creating the directory if it does not yet exist (defaulting to the current working directory, if none is provided).

Most of the commands need the submitter's private key that matches the public key announced to GHGA.
The private key is used for file encryption in the upload path and decryption of the work package access and work order tokens during download.
Additionally, the decrypt command needs the private key to decrypt the downloaded file.


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/ghga-connector):
```bash
docker pull ghga/ghga-connector:1.6.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/ghga-connector:1.6.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/ghga-connector:1.6.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
ghga_connector --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- **`max_concurrent_downloads`** *(integer)*: Number of parallel downloader tasks for file parts. Exclusive minimum: `0`. Default: `5`.

- **`max_retries`** *(integer)*: Number of times to retry failed API calls. Minimum: `0`. Default: `5`.

- **`max_wait_time`** *(integer)*: Maximum time in seconds to wait before quitting without a download. Exclusive minimum: `0`. Default: `3600`.

- **`part_size`** *(integer)*: The part size to use for download. Exclusive minimum: `0`. Default: `16777216`.

- **`wkvs_api_url`** *(string)*: URL to the root of the WKVS API. Should start with https://. Default: `"https://data.ghga.de/.well-known"`.

- **`exponential_backoff_max`** *(integer)*: Maximum number of seconds to wait for when using exponential backoff retry strategies. Minimum: `0`. Default: `60`.

- **`retry_status_codes`** *(array)*: List of status codes that should trigger retrying a request. Default: `[408, 500, 502, 503, 504]`.

  - **Items** *(integer)*: Minimum: `0`.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.ghga_connector.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.ghga_connector.yaml`)
- in your home directory (on unix: `~/.ghga_connector.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ghga_connector_`,
e.g. for the `host` set an environment variable named `ghga_connector_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.



## Architecture and Design:
This is a Python-based client enabling interaction with GHGA's file services.
Contrary to the design of the actual services, the client does not follow the triple-hexagonal architecture.
The client is roughly structured into three parts:

1. A command line interface using typer is provided at the highest level of the package, i.e. directly within the ghga_connector directory.
2. Functionality dealing with intermediate transformations, delegating work and handling state is provided within the core module.
3. core.api_calls provides abstractions over S3 and work package service interactions.


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
