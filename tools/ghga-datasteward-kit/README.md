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
   If the submission has been submitted before and only gained files since, use the `ghga-datasteward-kit metadata amend` command instead, so that the accessions already assigned are kept.
   Please see [this section](#metadata-amend) for further details.
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

#### metadata amend

Adds to a submission that has already been accessioned, keeping its existing accessions.

Use this, not a second `metadata submit`, whenever a submission gains files.
A second `submit` creates a new submission with a fresh set of accessions, which breaks every reference to the files already ingested from that submission.
In the legacy upload path the file accession is also the file's storage ID, and the identifiers derived from it cannot be recovered.

**The command is not limited to files.**
It replaces the whole content of the submission and treats every metadata class alike: the study, its datasets, samples, experiments and individuals all keep, gain or lose accessions by the same alias matching.
Nothing in the tool restricts an amendment to added files — that is a rule for the people using it, not one it enforces.

Two consequences worth knowing before you run it:

- A field changed on a resource that already has an accession is **not** an accession change, so it does not appear in the report and raises no prompt.
  It is written through, keeps its accession, and the next `load` updates that resource in the running system.
  Correcting metadata this way works; it just will not be flagged.
- Renaming or removing the alias of any resource, a study or dataset included, drops its accession exactly as it would for a file.
  That is what the confirmation question is for.
- An alias listed twice within one class is reported and needs confirmation, even when nothing is dropped.
  An alias identifies a resource, so the repeats share a single accession however much their other fields differ: the transform stamps that one accession on every row, and the next `load` keys them all to one resource, so only one survives.
  Nothing upstream rejects a duplicate — not the transpiler, not the schema check, not `submit` — so the report marks whether the repeated rows are identical or differ, and the differing ones are the damaging case.
  Fix those in the metadata rather than amending around them.

Amend deliberately when the change is more than added files, and read the report rather than relying on the prompt to stop you.

```text
ghga-datasteward-kit metadata amend \
  --submission-id <id> \
  --metadata-path <metadata JSON> \
  --config-path <metadata config YAML>
```

Aliases that already have an accession keep it, and only new aliases get new accessions.
The command reports what it will do before writing anything.
It asks for confirmation when the amendment would drop accessions, or when it would preserve none at all, since both usually mean the wrong submission or the wrong aliases.
That question cannot be skipped, by design: a dropped accession removes resources from the running system on the next `load`.

Such an amendment can only be applied from a terminal.
There is no `--yes`, and the prompt cannot be answered through a pipe either: when stdin is not a terminal the command refuses and changes nothing, rather than reading an answer nobody typed.
An amendment that drops nothing and preserves something is not affected, so adding files stays scriptable.

Dropping an accession is not just a local change: the next `load` removes the corresponding resources from the running system.

The submission's own record in the submission store is what makes this work: its `accession_map` is the only place an alias is tied to an accession.
Keep that store backed up.

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
