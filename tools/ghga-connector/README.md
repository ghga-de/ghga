![tests](https://github.com/ghga-de/ghga-connector/actions/workflows/unit_and_int_tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/ghga-de/ghga-connector/branch/main/graph/badge.svg?token=GYH99Y71CK)](https://codecov.io/gh/ghga-de/ghga-connector)
# GHGA-Connector

A CLI - Client to perform up- and download operations to and from a local GHGA Node.

## Documentation:

An extensive documentation can be found [here](...) (coming soon).

## Quick Start:
### Installation
This package is available at PyPI: https://pypi.org/project/ghga_connector

You can install it from there using:

```
pip install ghga_connector
```

### Using the CLI:

To get help on the command line interface, type:
```
ghga_connector --help
```

### Configuration:
The [`./example-config.yaml`](./example-config.yaml) gives an overview of the available configuration options.
Please adapt it and choose one of the following options for injecting it into the service:
- specify the path to via the `GHGA_CONNECTOR_CONFIG_YAML` env variable
- rename it to `.ghga_connector.yaml` and place it into one of the following locations:
  - the current working directory were you are execute the service (on unix: `./.ghga_connector.yaml`)
  - your home directory (on unix: `~/.ghga_connector.yaml`)

The config yaml will be automatically parsed by the service.

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ghga_connector_`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

For using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.


## Development
For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as vscode with its "Remote - Containers" extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in vscode and run the command
`Remote-Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formating
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, there are two convenience commands available
(please type them in the integrated terminal of vscode):
- `dev_install` - install the service with all development dependencies,
installs pre-commit, and applies any migration scripts to the test database
(please run that if you are starting the devcontainer for the first time
or if you added any python dependencies to the [`./setup.cfg`](./setup.cfg))
- `dev_launcher` - starts the service with the development config yaml
(located in the `./.devcontainer/` dir)

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
