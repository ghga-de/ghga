# General-Purpose Python Template

This is a general-purpose template for python packages and applications.

It features:

- A [devcontainer](https://containers.dev/)-based fully-configured development environment for vscode
- Tight linting and formatting using [Ruff](https://docs.astral.sh/ruff/)
- Static type checking using [mypy](https://www.mypy-lang.org/)
- Security scanning using [bandit](https://bandit.readthedocs.io/en/latest/)
- A structure for automated tests using [pytest](https://docs.pytest.org/en/7.4.x/)
- Dependency locking using [pip-tools](https://github.com/jazzband/pip-tools)
- Git hooks checking linting and formatting before committing using [pre-commit](https://pre-commit.com/)
- GitHub Actions for automating or checking all of the above

Here the intro to the template stops and the actual template for the readme of the microservice starts:

---
[![tests](https://github.com/kerstenbreuer/python-template/actions/workflows/tests.yaml/badge.svg)](https://github.com/kerstenbreuer/python-template/actions/workflows/tests.yaml)

# My Custom App

My-Custom-App - a short description

## Description

<!-- Please provide a short overview of the features of this service. -->

Here you should provide a short summary of the purpose of this microservice.

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
