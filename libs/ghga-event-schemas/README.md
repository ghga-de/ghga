![tests](https://github.com/ghga-de/ghga-message-schemas/actions/workflows/unit_and_int_tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/ghga-de/ghga-message-schemas/branch/main/graph/badge.svg?token=GYH99Y71CK)](https://codecov.io/gh/ghga-de/ghga-message-schemas)
# GHGA Message Schemas
A package that collects schemas used for messaging between GHGA service.


## Quick Start
### Installation
This package is available at PyPI:
https://pypi.org/project/ghga-message-schemas

You can install it from there using:
```
pip install ghga-message-schemas
```

Thereby, you may specify following extra(s):
- `dev`: dependencies needed for development and testing

## Development
For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as vscode with its "Remote - Containers" extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in vscode and run the command
`Remote-Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formating
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, there if following convenience commands available
(please type it in the integrated terminal of vscode):
`dev_install` - installs the package with all development dependencies and installs pre-commit
(please run that if you are starting the devcontainer for the first time
or if you added any python dependencies to the [`./setup.cfg`](./setup.cfg))

If you prefer not to use vscode, you could get a similar setup (without the editor specific features)
by running the following commands:
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
