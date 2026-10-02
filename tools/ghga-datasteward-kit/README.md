<!-- rumdl-disable MD013 -->
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
<!-- rumdl-enable MD013 -->

# GHGA Data Steward Kit

Utilities for data stewards interacting with GHGA infrastructure.

## Installation

The kit is not published to PyPI; the last release there is 5.4.3.
It ships with the platform release instead, and you run it from a checkout of a release tag, so that `uv.lock` at the tag pins the service and library versions it was tested with.
You need `git` and [uv](https://docs.astral.sh/uv/getting-started/installation/); uv fetches the matching Python itself.

Pick a `ghga/X.Y.Z` tag from the [releases](https://github.com/ghga-de/ghga/releases), then clone it and run the kit from the checkout:

```text
git clone --depth 1 --branch ghga/X.Y.Z https://github.com/ghga-de/ghga.git
cd ghga
uv run --locked ghga-datasteward-kit --help
```

With `--locked`, uv refuses to run rather than resolve versions other than the pinned ones.
The first run creates the environment in `.venv`, and later runs reuse it.
To move to another release, clone that tag afresh.

## Step by Step Guide

The kit covers the metadata path only.
Files are uploaded with the [GHGA Connector](../ghga-connector) into an upload box and mapped to metadata in the data portal, neither of which involves this kit.

### Metadata Preparation

The data steward kit has no functionality to help with metadata preparation, however, it is still described here for completeness of the workflow.

To define metadata for a submission, you have two options:

**Option 1:** Use an excel spreadsheet (please do not use Google Spreadsheets because of data protection).
Templates are in the [metadata schema repository](https://github.com/ghga-de/ghga-metadata-schema/tree/main/spreadsheets).
You may validate the metadata by:

1. Running the [GHGA Metadata Transpiler](https://github.com/ghga-de/ghga-transpiler) to generate JSON (as in Option 2).
2. Run the [GHGA Metadata Validator](https://github.com/ghga-de/ghga-validator/) on the produced JSON.

**Option 2:** Directly specify the metadata using JSON compliant with our [LinkML schema](https://github.com/ghga-de/ghga-metadata-schema/blob/main/src/schema/submission.yaml).
Validation of the metadata can be achieved using the [GHGA Metadata Validator](https://github.com/ghga-de/ghga-validator/).

Once your spreadsheet or JSON file have passed validation, you may send the metadata to the Central Data Steward.

### Central Data Steward

The Central Data Steward is responsible for ingesting the metadata into the running system.
This is performed with the following steps:

1. **Generate credentials**: Central data stewards need credentials for authentication with GHGA Central Services.
   To create these credentials the `ghga-datasteward-kit generate-credentials` command is used.
   Please see [this section](#generate-credentials) for further details.
2. **Transpile Metadata Spreadsheet**: If the Local Data Steward provided a metadata spreadsheet, this spreadsheet has to be first transpiled to the JSON format using the `ghga-datasteward-kit metadata transpile` command.
   Please see [this section](#metadata) for further details.
3. **Include in Submission Registry**: The submission JSON is included in a submission registry on the local file system using the `ghga-datasteward-kit metadata submit` command.
   Please see [this section](#metadata) for further details.
4. **Produce Metadata Artifacts**: A transformation workflow is run on all submissions in the submission registry to produce multiple query-specific metadata artifacts using the `ghga-datasteward-kit metadata transform` command.
   Please see [this section](#metadata) for further details.
5. **Publish Metadata**: To publish all metadata artifacts of all submissions to the running system so that they are available on the GHGA website, the `ghga-datasteward-kit load` command can be used.

## Details per Command

An overview of all commands is provided using:

```text
ghga-datasteward-kit --help
```

The following paragraphs provide additional help for using the different commands.

### metadata

*To be performed by Central Data Stewards only.*

The metadata label groups metadata related commands.

Some of them require a configuration file as described in the [metadata config](./metadata_config.md).

### load

*To be performed by Central Data Stewards only.*

The load command makes files and metadata available to user in the running system.

It needs a configuration parameters as described in the [load config](./load_config.md).

### generate-credentials

A command to generate a token/hash pair for interacting with GHGA Central services.

The generated token file should not be moved to a different system and never be shared with another user.
The token hash (**not the token*) must be shared with the GHGA Central Operation Team.
This process has to be done only once per data steward and system (if a data steward is working with multiple compute environments, one set of credentials per environment should be created).

## Development

For setting up the development environment, we rely on the [devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode in combination with Docker Compose.

To use it, you have to have Docker Compose as well as vscode with its "Remote - Containers" extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in vscode and run the command `Remote-Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:

- infrastructural dependencies (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formating
- a pre-configured debugger
- automatic license-header insertion

If you prefer not to use vscode, you could get a similar setup (without the editor specific features) by running the following commands:

``` bash
# Execute in the repo's root dir:
cd ./.devcontainer

# build and run the environment with docker-compose
docker-compose up

# attach to the main container:
# (you can open multiple shell sessions like this)
docker exec -it devcontainer_app_1 /bin/bash
```

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
