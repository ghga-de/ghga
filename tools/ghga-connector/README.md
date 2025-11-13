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

A pre-built version is available on [Docker Hub](https://hub.docker.com/repository/docker/ghga/ghga-connector):
```bash
docker pull ghga/ghga-connector:1.7.3
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/ghga-connector:1.7.3 .
```

For production-ready deployment, we recommend using Kubernetes.
However for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is pre-configured:
docker run -p 8080:8080 ghga/ghga-connector:1.7.3 --help
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
- <a id="properties/client_cache_capacity"></a>**`client_cache_capacity`** *(integer)*: Maximum number of entries to store in the cache. Older entries are evicted once this limit is reached. Exclusive minimum: `0`. Default: `128`.

- <a id="properties/client_cache_ttl"></a>**`client_cache_ttl`** *(integer)*: Number of seconds after which a stored response is considered stale. Minimum: `0`. Default: `60`.

- <a id="properties/client_cacheable_methods"></a>**`client_cacheable_methods`** *(array)*: HTTP methods for which responses are allowed to be cached. Default: `["POST", "GET"]`.

  - <a id="properties/client_cacheable_methods/items"></a>**Items** *(string)*

- <a id="properties/client_cacheable_status_codes"></a>**`client_cacheable_status_codes`** *(array)*: HTTP response status code for which responses are allowed to be cached. Default: `[200, 201]`.

  - <a id="properties/client_cacheable_status_codes/items"></a>**Items** *(integer)*

- <a id="properties/client_exponential_backoff_max"></a>**`client_exponential_backoff_max`** *(integer)*: Maximum number of seconds to wait between retries when using exponential backoff retry strategies. The client timeout might need to be adjusted accordingly. Minimum: `0`. Default: `60`.

- <a id="properties/client_num_retries"></a>**`client_num_retries`** *(integer)*: Number of times to retry failed API calls. Minimum: `0`. Default: `3`.

- <a id="properties/client_retry_status_codes"></a>**`client_retry_status_codes`** *(array)*: List of status codes that should trigger retrying a request. Default: `[408, 429, 500, 502, 503, 504]`.

  - <a id="properties/client_retry_status_codes/items"></a>**Items** *(integer)*: Minimum: `0`.

- <a id="properties/client_reraise_from_retry_error"></a>**`client_reraise_from_retry_error`** *(boolean)*: Specifies if the exception wrapped in the final RetryError is reraised or the RetryError is returned as is. Default: `true`.

- <a id="properties/per_request_jitter"></a>**`per_request_jitter`** *(number)*: Max amount of jitter (in seconds) to add to each request. Minimum: `0`. Default: `0.0`.

- <a id="properties/retry_after_applicable_for_num_requests"></a>**`retry_after_applicable_for_num_requests`** *(integer)*: Amount of requests after which the stored delay from a 429 response is ignored again. Can be useful to adjust if concurrent requests are fired in quick succession. Exclusive minimum: `0`. Default: `1`.

- <a id="properties/max_concurrent_downloads"></a>**`max_concurrent_downloads`** *(integer)*: Number of parallel downloader tasks for file parts. Exclusive minimum: `0`. Default: `5`.

- <a id="properties/max_wait_time"></a>**`max_wait_time`** *(integer)*: Maximum time in seconds to wait before quitting without a download. Exclusive minimum: `0`. Default: `3600`.

- <a id="properties/part_size"></a>**`part_size`** *(integer)*: The part size to use for download. Exclusive minimum: `0`. Default: `16777216`.

- <a id="properties/wkvs_api_url"></a>**`wkvs_api_url`** *(string)*: URL to the root of the WKVS API. Should start with https://. Default: `"https://data.ghga.de/.well-known"`.


### Usage:

A template YAML file for configuring the service can be found at
[`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.ghga_connector.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.ghga_connector.yaml`)
- in your home directory (on Linux: `~/.ghga_connector.yaml`)

The config YAML file will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml)
can also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ghga_connector_`,
e.g. for the `host` set an environment variable named `ghga_connector_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
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

Inside the devcontainer, a command `dev_install` is available for convenience.
It installs the service with all development dependencies, and it installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`lock/requirements-dev.txt`](./lock/requirements-dev.txt), run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [.readme_generation/README.md](./.readme_generation/README.md)
for details.
