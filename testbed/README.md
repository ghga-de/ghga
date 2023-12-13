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

## Usage and Configuration

The Archive Test Bed runs all fundamental user journeys supported by the GHGA Archive
application. Essentially, data is uploaded first and then the same data is downloaded
again. The tests start on an empty slate, and the state for the download tests is
created via the upload tests. Therefore the proper order of execution is important,
which is guaranteed by prefixing the features with numbers.

The tests in the Archive Test Bed are written in BDD style and can be executed with
[pytest](https://docs.pytest.org) via the
[pytest-bdd](https://pytest-bdd.readthedocs.io) plugin.
The feature files written in the Gherkin langue are inside in the `features` directory.
As already mentioned, they are prefixed with numbers so that they run in the proper
execution order. Each feature can contain several scenarios which run in the order in
which they appear in the feature files. The corresponding step files can be found in
the `steps` directory. Pytest fixtures are contained in the `fixtures` directory.

To run all tests in the Archive test bed, just run `pytest`. You can also run only
certain steps, e.g. step 24, by running `pytest steps/test_24_*`.

The Archive Test Bed supports two different modes of operation: black box testing
and white box testing. In the black box testing mode, the application is only accessed
using the official API via the API gateway. This can be used to test a deployment in a
Kubernetes cluster. In the white box testing mode, the Archive Test Bed also accesses
the foundational services (like S3, Kafka, Mongo, Vault) to test their expected states,
including intermediate states.

The testbed can be configured using a YAML file or environment variables, which always
take precedence. The black box testing mode is activated by setting `use_api_gateway`
to `true` in the configuration, otherwise the white box testing mode is used.

The setting `use_auth_adapter` can be set to `false` if the auth adapter shall not be
used to exchange external OIDC tokens with internal tokens. In black box testing mode,
the auth adapter must always be used, because internal tokens cannot be set from
outside. In order to provide the OIDC tokens, a test OIDC provider service is used.

The Archive Test Bed memorizes the current state of the tests in a test database, which
can be useful if you want to re-run tests starting with a certain step as a developer.
If you set `keep_state_in_db` to `false`, then the state is stored in memory only.
This is useful when black box tests are running automatically.

The setting `auth_basic` can be used to pass additional basic authentication credentials
which may be expected by the auth adapter. This can be only used with black box testing.

The other configuration settings define the names of the databases, used API URLs
and various secrets. If you are running the tests against a Kubernetes cluster, make
sure that these settings match what is configured there. The secrets that are relevant
here are stored in the settings `auth_basic`, `upload_token` and `fis_pubkey`.
Also, the names of the buckets (`*_bucket`) and URLs (`*_url`) must match.

If you run the tests against the devcontainer and the services set up in
`docker-compose.yml`, then the secrets will be created randomly before the containers
are started, and saved in corresponding `.env` files in the `set_env.sh` script.
These files are ignored in the repository.

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
