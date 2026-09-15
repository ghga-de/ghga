[![PyPI version shields.io](https://img.shields.io/pypi/v/ghga-service-commons.svg)](https://pypi.org/project/ghga-service-commons/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ghga-service-commons.svg)](https://pypi.org/project/ghga-service-commons/)

# ghga-service-commons
This Python library serves as a collection of common utilities used by
the microservices developed at German Human Genome-Phenome Archive (GHGA).

It collects boilerplate code for common functionalities such as API server setup,
authentication and authorization.

This library is primarily intended for internal use at GHGA and should
not be seen as a general-purpose microservice chassis.
However, if this library matches your specific needs as well,
please feel free to use it. It is open source.

# Installation
This package is available at PyPI:
https://pypi.org/project/ghga_service_commons

You can install it from there using:
```
pip install ghga_service_commons
```

Thereby, you may specify following extra(s):
- `api`: dependencies needed to use the API server functionalities
- `auth`: dependencies needed for dealing with authentication and authorization

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
just sync                            # install every member plus the shared dev toolchain
just test libs/ghga-service-commons  # this member's test suite
just lint                            # ruff check + format check across the workspace
```

## License
This repository is free to use and modify according to the [Apache 2.0 License](https://github.com/ghga-de/ghga/blob/main/libs/ghga-service-commons/LICENSE).
