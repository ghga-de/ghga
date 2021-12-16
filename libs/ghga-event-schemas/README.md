


# Microservice Repository Template

This repo is a template for creating a new microservice.

The directories, files, and their structure herein are recommendations
from the GHGA Dev Team.

## Naming Conventions
The github repository contains only lowercase letters, numbers, and hyphens "-",
e.g.: `my-microservice`

The python package (and thus the source repository) contains underscores "_"
instead of hyphens, e.g.: `my_microservice`

The command-line script that is used to run the service, the docker repository
(published to docker hub), and the helm chart (not part of this repository) use the
same pattern as the repository name, e.g.: `my-microservice`
## Adapt to your service
This is just a template and needs some adaption to your specific use case.

Please search for **"please adapt"** comments. They will indicate all locations
that need modification. Once the adaptions are in place, please remove these #
comments.

The following should serve as a template for the final repo's README,
please adapt it accordingly (e.g. replace all occurences of `my-microservice` or `my_microservice` with the final package name and don't forget to adapt the links):

---

**\# please adapt the links of following badges:**
![tests](https://github.com/ghga-de/microservice-repository-template/actions/workflows/unit_and_int_tests.yaml/badge.svg)
[![codecov](https://codecov.io/gh/ghga-de/microservice-repository-template/branch/main/graph/badge.svg?token=GYH99Y71CK)](https://codecov.io/gh/ghga-de/microservice-repository-template)
# My-Microservice - A Short Description

A longer description explaining the use case of this service.

## Documentation:

An extensive documentation can be found [here](...) (coming soon).

## Quick Start
### Installation
We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/my-microservice):
```bash
# Please feel free to choose the version as needed:
docker pull ghga/my-microservice:<version>
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
# (Please feel free to adapt the name/tag.)
docker build -t ghga/my-microservice:<version> .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/my-microservice:<version>
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# to run the service:
my-microservice
```

### Configuration:
The [`./example-config.yaml`](./example-config.yaml) gives an overview of the available configuration options.
Please adapt it, rename it to `.my_microservice.yaml`, and place it to one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.my_microservice.yaml`)
- in your home directory (on unix: `~/.my_microservice.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `MY_MICROSERVICE_`,
e.g. for the `host` set an environment variable named `MY_MICROSERVICE_HOST`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
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
