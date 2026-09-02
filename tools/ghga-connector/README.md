[![PyPI version shields.io](https://img.shields.io/pypi/v/ghga-connector.svg)](https://pypi.org/project/ghga-connector/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ghga-connector.svg)](https://pypi.org/project/ghga-connector/)

# GHGA Connector

GHGA Connector - A CLI client application for interacting with the GHGA system.

## Description

The GHGA Connector is a command line client facilitating interaction with the file storage infrastructure of GHGA.
To this end, it provides commands for the up- and download of files that interact with the RESTful APIs exposed by the Upload Controller Service (https://github.com/ghga-de/ghga/tree/main/services/ucs) and Download Controller Service (https://github.com/ghga-de/ghga/tree/main/services/dcs), respectively.

When uploading, the Connector expects an unencrypted file that is subsequently encrypted according to the Crypt4GH standard (https://www.ga4gh.org/news_item/crypt4gh-a-secure-method-for-sharing-human-genetic-data/) and only afterwards uploaded to the GHGA storage infrastructure.

When downloading, the resulting file is still encrypted in this manner and can be decrypted using the Connector's decrypt command.
As the user is expected to download multiple files, this command takes a directory location as input and an optional output directory location can be provided, creating the directory if it does not yet exist (defaulting to the current working directory, if none is provided).

Most of the commands need the submitter's private key that matches the public key announced to GHGA.
The private key is used for file encryption in the upload path and decryption of the work package access and work order tokens during download.
Additionally, the decrypt command needs the private key to decrypt the downloaded file.
If the private key is protected by a passphrase, the Connector prompts for it interactively (up to three attempts). The passphrase cannot be supplied via configuration.


## Installation

We recommend installing the latest version of the GHGA Connector using pip:
```bash
pip install -U ghga-connector
```

To run it from a checkout of this repository instead:
```bash
# Execute in the repo's root dir:
uv run ghga-connector --help
```

## Configuration

### Parameters

The Connector accepts the following configuration parameters:
- <a id="properties/client_exponential_backoff_max"></a>**`client_exponential_backoff_max`** *(integer)*: Maximum number of seconds to wait between retries when using exponential backoff retry strategies. The client timeout might need to be adjusted accordingly. Minimum: `0`. Default: `60`.
- <a id="properties/client_num_retries"></a>**`client_num_retries`** *(integer)*: Total number of attempts made per API call, so a value of 1 means no retries. Uploads are long-lived and cross the public internet, so the Connector allows more attempts than the service default. Minimum: `0`. Default: `5`.
- <a id="properties/client_retry_status_codes"></a>**`client_retry_status_codes`** *(array)*: List of status codes that should trigger retrying a request. Default: `[408, 429, 500, 502, 503, 504]`.
  - <a id="properties/client_retry_status_codes/items"></a>**Items** *(integer)*: Minimum: `0`.
- <a id="properties/client_reraise_from_retry_error"></a>**`client_reraise_from_retry_error`** *(boolean)*: Specifies if the exception wrapped in the final RetryError is reraised or the RetryError is returned as is. Default: `true`.
- <a id="properties/per_request_jitter"></a>**`per_request_jitter`** *(number)*: Max amount of jitter (in seconds) to add to each request. Minimum: `0`. Default: `0.0`.
- <a id="properties/retry_after_applicable_for_num_requests"></a>**`retry_after_applicable_for_num_requests`** *(integer)*: Amount of requests after which the stored delay from a 429 response is ignored again. Can be useful to adjust if concurrent requests are fired in quick succession. Exclusive minimum: `0`. Default: `1`.
- <a id="properties/max_concurrent_downloads"></a>**`max_concurrent_downloads`** *(integer)*: Number of parallel download tasks for file parts. Exclusive minimum: `0`. Default: `5`.
- <a id="properties/max_concurrent_uploads"></a>**`max_concurrent_uploads`** *(integer)*: Number of parallel upload tasks for file parts. Exclusive minimum: `0`. Default: `5`.
- <a id="properties/max_wait_time"></a>**`max_wait_time`** *(integer)*: Maximum time in seconds to wait before quitting without a download. Exclusive minimum: `0`. Default: `3600`.
- <a id="properties/part_size"></a>**`part_size`** *(integer)*: The part size to use for download. Exclusive minimum: `0`. Default: `67108864`.
- <a id="properties/wkvs_api_url"></a>**`wkvs_api_url`** *(string)*: URL to the root of the WKVS API. Should start with https://. Default: `"https://data.ghga.de/.well-known"`.

### Usage:

A template YAML file for configuring the Connector can be found at
[`./example_config.yaml`](https://github.com/ghga-de/ghga/blob/main/tools/ghga-connector/example_config.yaml).
Please adapt it, rename it to `.ghga_connector.yaml`, and place it in one of the following locations:
- in the current working directory where you run the Connector (on Linux: `./.ghga_connector.yaml`)
- in your home directory (on Linux: `~/.ghga_connector.yaml`)

The config YAML file will be automatically parsed by the Connector.

All parameters mentioned in the [`./example_config.yaml`](https://github.com/ghga-de/ghga/blob/main/tools/ghga-connector/example_config.yaml)
can also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ghga_connector_`,
e.g. for the `host` set an environment variable named `ghga_connector_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#secrets)
of the pydantic documentation.



## Architecture and Design:
This is a Python-based client enabling interaction with GHGA's file services.
Contrary to the design of the actual services, the client does not follow the triple-hexagonal architecture.
The client is roughly structured into three parts:

1. A command line interface using typer is provided at the highest level of the package, i.e. directly within the ghga_connector directory.
2. Functionality dealing with intermediate transformations, delegating work and handling state is provided within the core module.
3. core.api_calls provides abstractions over S3 and work package service interactions.


## Development

This package is a member of the [GHGA monorepo](https://github.com/ghga-de/ghga) and is
developed from the repository root rather than on its own. The repository ships a
devcontainer with the whole toolchain: open it in VS Code and run
`Remote-Containers: Reopen in Container`, or set the environment up directly with
`just sync`.

The usual tasks, run from the repository root (see
[ADR-0015](https://github.com/ghga-de/ghga/blob/main/docs/adr/0015-task-runner.md) for the
full recipe list):

```bash
just sync                        # install every member plus the shared dev toolchain
just test tools/ghga-connector   # this member's test suite
just lint                        # ruff check + format check across the workspace
```

## License

This repository is free to use and modify according to the
[Apache 2.0 License](https://github.com/ghga-de/ghga/blob/main/tools/ghga-connector/LICENSE).
