# GHGA Archive Test Bed

## Documentation

This repository provides a test bed for running inter service integration tests
for the microservices building the GHGA Archive application, and a couple of such
tests for the most important user journeys and for testing security aspects.

## Quick Start

For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of vscode
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as vscode with its "Dev Containers" extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in vscode and run the command
`Dev Containers: Open Folder in Container` or `Dev Containers: Reopen in Container` from the vscode "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies (databases, etc.)
- all relevant vscode extensions pre-installed
- pre-configured linting and auto-formatting
- a pre-configured debugger
- automatic license-header insertion

If you prefer not to use vscode, you could get a similar setup (without the editor specific features)
by running the following commands:

```bash
# Execute in the repo's root dir:
cd ./.devcontainer

# build and run the environment with docker-compose
docker-compose up

# attach to the main container:
# (you can open multiple shell sessions like this)
docker exec -it devcontainer_app_1 /bin/bash
```


## Overview

The Archive Test Bed is designed for testing the GHGA Archive application through fundamental user journeys. It involves a sequence of actions where data is first uploaded and subsequently downloaded. The tests are executed starting from an empty state, with the download tests dependent on the setup created by the upload tests. This necessitates a specific order of execution, achieved by numerically prefixing the feature files.

### Test Structure

The tests are written in **Behavior-Driven Development (BDD) Style** and are executable using [pytest](https://docs.pytest.org) with the [pytest-bdd](https://pytest-bdd.readthedocs.io) plugin.

Located in the `features` directory, the **feature files** are numerically prefixed to ensure correct execution order. Each file contains multiple scenarios executed sequentially. Corresponding step definitions are found in the `steps` directory. Pytest fixtures are stored in the `fixtures` directory.

### Execution

- Use `pytest -v` to run all tests.
- For specific steps, such as step 24, use `pytest steps/test_24_*`.
- For specific group of tests, BDD tags (pytest markers) can also be used, e.g. `pytest -m browse and metadata`.

### Modes of Operation

- **Black Box Testing:** This mode involves accessing the application solely through the official API via the API gateway. It's suitable for testing deployments in Kubernetes clusters.
    - Enable black box testing by setting `use_api_gateway` to `true`. Otherwise, white box testing is the default mode.
- **White Box Testing:** Here, the Test Bed also accesses foundational services (e.g., S3, Kafka, Mongo, Vault) to verify their states, including intermediate ones.

### Configuration

The Archive Test Bed can be configured through either **YAML file** or **environment variables**, with environment variables having higher priority.

- **Auth Adapter Settings:** The `use_auth_adapter` setting controls the usage of the auth adapter for token exchanges. It's mandatory in black box testing for external OIDC tokens.
- **States:** The `keep_state_in_db` setting determines whether to store test states in a database or in memory, with the latter being default for automated black box tests.
- **Additional Authentication:** The `auth_basic` setting is for passing basic authentication credentials, applicable only in black box testing.


### Advanced Configuration

When running the tests against a Kubernetes cluster, please ensure that names of databases, API URLs, and secrets match what is configured in the cluster.

- Relevant settings include `auth_basic`, `upload_token`, and `fis_pubkey`. Bucket names (`*_bucket`) and URLs (`*_url`) must also be consistent.

When running tests in a devcontainer with `docker-compose.yml`, **secrets are generated randomly and saved in `.env` files via the `set_env.sh` script**. These files are excluded from the repository.

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
