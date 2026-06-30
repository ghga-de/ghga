
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
