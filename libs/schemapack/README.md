![tests](https://github.com/ghga-de/schemapack/actions/workflows/tests.yaml/badge.svg)
[![PyPI version shields.io](https://img.shields.io/pypi/v/schemapack.svg)](https://pypi.python.org/pypi/schemapack/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/schemapack.svg)](https://pypi.python.org/pypi/schemapack/)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/schemapack/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/schemapack?branch=main)

# schemapack

Make your JSON Schemas sociable and create linked data model.

## Installation
This package is available at PyPI:
https://pypi.org/project/schemapack

You can install it from there using:
```
pip install schemapack
```

## Development
For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode.

To use it, you have to have Docker as well as vscode with its "Remote - Containers"
extension (`ms-vscode-remote.remote-containers`) extension installed.
Then, you just have to open this repo in vscode and run the command
`Remote-Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formating
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, there is follwing convenience command available
(please type it in the integrated terminal of vscode):
- `dev_install` - install the lib with all development dependencies and pre-commit hooks
(please run that if you are starting the devcontainer for the first time
or if added any python dependencies to the [`./setup.cfg`](./setup.cfg))

## License
This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
