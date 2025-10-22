[![tests](https://github.com/ghga-de/schemapack/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/schemapack/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/schemapack/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/schemapack?branch=main)
[![PyPI version shields.io](https://img.shields.io/pypi/v/schemapack.svg)](https://pypi.python.org/pypi/schemapack/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/schemapack.svg)](https://pypi.python.org/pypi/schemapack/)

# Schemapack

Make your JSON Schemas sociable and create linked data models.

## Description

<!-- Please provide a short overview of the features of this service. -->

Schemapack is a library that defines a lightweight data modeling framework based on a schema description, a compatible data instance format, and the tooling that supports them. It introduces two main components: the schemapack, which describes linked data structures, and the datapack, which represents the data conforming to those structures. The tooling around `schemapack` and `datapack` focuses on loading, extraction, and validation, and supports partial extraction and data embedding operations. The Schemapack library includes a CLI component that provides access to core functionality via the command line.


## Installation

This package is available at PyPI:
https://pypi.org/project/schemapack

Install:
```
bash

pip install schemapack
```

Upgrade:
```
pip install --upgrade schemapack
```

## Usage

```
bash

schemapack --help


 Usage: schemapack [OPTIONS] COMMAND [ARGS]...

 Common arguments and options.


╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version                     Show the version of the library and exit.                                                        │
│ --install-completion          Install completion for the current shell.                                                        │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                 │
│ --help                        Show this message and exit.                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ validate              Validate a datapack against a schemapack.                                                                │
│ check-schemapack      Check if the provided JSON/YAML document complies with the schemapack specs.                             │
│ check-datapack        Check if the provided JSON/YAML document complies with the datapack specs.                               │
│ condense-schemapack   Writes a version of the provided schemapack with embedded content schemas to stdout.                     │
│ isolate-resource      Isolate a resource from the given datapack and write a datapack that is rooted to this resource to       │
│                       stdout.                                                                                                  │
│ isolate-class         Isolate a class from the given schemapack and write a condensed (with content schemas being embedded)    │
│                       schemapack that is rooted to this class to stdout.                                                       │
│ export-mermaid        Generate an entity relationship diagram based on the mermaid markup from the provided schemapack.        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```
## Quick Start


This example shows how to validate a `datapack.yaml` file against a `schemapack.yaml` using the `schemapack` Python library. The `schemapack` defines the schema and validation rules, while the `datapack` contains the actual data to be validated. The steps below demonstrate how to load both files and run validation with `SchemaPackValidator`.

```python

from pathlib import Path

from schemapack import SchemaPackValidator, load_datapack, load_schemapack

schemapack_path = Path("path/to/schemapack.yaml")
datapack_path = Path("path/to/datapack.yaml")

# load schemapack
schemapack = load_schemapack(schemapack_path)

# load datapack
datapack = load_datapack(datapack_path)

# validate datapack against schemapack
validator = SchemaPackValidator(schemapack=schemapack)
validator.validate(datapack=datapack)
```



## Documentation

- [SchemaPack specification](./docs/schemapack_spec.md)
- [DataPack specification](./docs/datapack_spec.md)
- [Data isolation](./docs/data_isolation.md)


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

This README file is auto-generated, please see [.readme_generation/README.md](./.readme_generation/README.md) for details.
