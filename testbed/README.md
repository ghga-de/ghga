# GHGA Archive Test Bed

## Documentation

This directory provides a test bed for running inter service integration tests
for the microservices building the GHGA Archive application, and a couple of such
tests for the most important user journeys and for testing security aspects.

## Quick Start

The test bed runs against the demo platform on a local kind cluster. Set it up and run it
with the `just` recipes described in the root README's
[test bed walkthrough](../README.md#run-the-test-bed-locally).

## Overview

The Archive Test Bed is designed for testing the GHGA Archive application through fundamental user journeys. It involves a sequence of actions where data is first uploaded and subsequently downloaded. The tests are executed starting from an empty state, with the download tests dependent on the setup created by the upload tests. This necessitates a specific order of execution, achieved by numerically prefixing the feature files.

### Test Structure

The tests are written in **Behavior-Driven Development (BDD) Style** and are executable using [pytest](https://docs.pytest.org) with the [pytest-bdd](https://pytest-bdd.readthedocs.io) plugin.

Located in the `features` directory, the **feature files** are numerically prefixed to ensure correct execution order. Each file contains multiple scenarios executed sequentially. Corresponding step definitions are found in the `steps` directory. Pytest fixtures are stored in the `fixtures` directory.

### Execution

- Use `just testbed` to run all tests.
- For specific steps, such as step 240, use `just testbed steps/test_240_*`.
- For specific group of tests, BDD tags (pytest markers) can also be used, e.g. `just testbed -m browse`.

### Modes of Operation

- **Black Box Testing:** This mode involves accessing the application solely through the official API via the API gateway. It's suitable for testing deployments in Kubernetes clusters.
    - Enable black box testing by setting `black_box_mode` to `true`. Otherwise, white box testing is the default mode.
- **White Box Testing:** Here, the Test Bed also accesses foundational services (e.g., S3, Kafka, Mongo, Vault) to verify their states, including intermediate ones.

### Configuration

The Archive Test Bed can be configured through either **YAML file** or **environment variables**, with environment variables having higher priority.

The testbed itself is configured via the YAML file named by the environment variable `TB_CONFIG_YAML`. `just testbed` sets it to `tb.kind.yaml`, the configuration for the kind cluster, and supplies the secrets as `TB_*` environment variables read from the cluster. Alternative configurations can be saved as `tb.*.yaml` and activated the same way.

- **States:** The `keep_state_in_db` setting determines whether to store test states in a database or in memory, with the latter being default for automated black box tests.
- **Additional Authentication:** The `auth_basic` setting is for passing basic authentication credentials, applicable only in black box testing.

### Advanced Configuration

When running the tests against a Kubernetes cluster, please ensure that names of databases, API URLs, and secrets match what is configured in the cluster.

- Relevant settings include `auth_basic`, `upload_token`, and `fis_pubkey`. Bucket names (`*_bucket`) and URLs (`*_url`) must also be consistent.


## License

This test bed is free to use and modify according to the [Apache 2.0 License](./LICENSE).
