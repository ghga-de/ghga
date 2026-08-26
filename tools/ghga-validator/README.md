
[![tests](https://github.com/ghga-de/ghga-validator/actions/workflows/unit_and_int_tests.yaml/badge.svg)](https://github.com/ghga-de/ghga-validator/actions/workflows/unit_and_int_tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/ghga-validator/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/ghga-validator?branch=main)

# Ghga Validator

GHGA Validator - A Python library and command line utility to validate metadata

## Description

<!-- Please provide a short overview of the features of this service.-->

ghga-validator is a Python library and command line utility to validate metadata
w.r.t. its compliance to the [GHGA Metadata
Model](github.com/ghga-de/ghga-metadata-schema). It takes metadata encoded in JSON of YAML format and produces a validation report in JSON format.


## Installation
We recommend installing the latest version of ghga-validator using pip:
```
pip install -U ghga-validator
```

## Usage

```
Usage: ghga-validator [OPTIONS]

  GHGA Validator

  ghga-validator is a command line utility to validate metadata w.r.t. its
  compliance to the GHGA Metadata Model. It takes metadata encoded in JSON of
  YAML format and produces a validation report in JSON format.

Options:
  -s, --schema PATH               Path to metadata schema (modelled using
                                  LinkML)  [required]
  -i, --input FILE                Path to submission file in JSON format to be
                                  validated  [required]
  -r, --report FILE               Path to resulting validation report
                                  [required]
  --target-class TEXT             The root class name
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.
  --help                          Show this message and exit.
```

## Development

This package is a member of the [GHGA monorepo](../../README.md) and is developed from the
repository root rather than on its own. The repository ships a devcontainer with the whole
toolchain: open it in VS Code and run `Remote-Containers: Reopen in Container`, or set the
environment up directly with `just sync`.

The usual tasks, run from the repository root (see
[ADR-0015](../../docs/adr/0015-task-runner.md) for the full recipe list):

```bash
just sync                        # install every member plus the shared dev toolchain
just test tools/ghga-validator   # this member's test suite
just lint                        # ruff check + format check across the workspace
```

## License
This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).
