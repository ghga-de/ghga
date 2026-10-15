# GHGA Archive Test Bed

## Documentation

This directory provides a test bed for running inter service integration tests for the microservices building the GHGA Archive application, and a couple of such tests for the most important user journeys and for testing security aspects.

## Quick Start

The test bed runs against the demo platform on a local kind cluster.
Set it up and run it with the `just` recipes described in the root README's [test bed walkthrough](../README.md#run-the-test-bed-locally).
It also runs against any deployment from outside, through the gateway alone; see [Running against a cluster](#running-against-a-cluster).

## Overview

The Archive Test Bed is designed for testing the GHGA Archive application through fundamental user journeys.
It involves a sequence of actions where data is first uploaded and subsequently downloaded.
The tests are executed starting from an empty state, with the download tests dependent on the setup created by the upload tests.
This necessitates a specific order of execution, achieved by numerically prefixing the feature files.

### Test Structure

The tests are written in **Behavior-Driven Development (BDD) Style** and are executable using [pytest](https://docs.pytest.org) with the [pytest-bdd](https://pytest-bdd.readthedocs.io) plugin.

Located in the `features` directory, the **feature files** are numerically prefixed to ensure correct execution order.
Each file contains multiple scenarios executed sequentially.
Corresponding step definitions are found in the `steps` directory.
Pytest fixtures are stored in the `fixtures` directory.

### Execution

- Use `just testbed` to run all tests.
- For specific steps, such as step 240, use `just testbed steps/test_240_*`.
- For specific group of tests, BDD tags (pytest markers) can also be used, e.g. `just testbed -m browse`.
- Use `just testbed-remote <config>` to run against the deployment a `tb.*.yaml` names, without the kind prelude; see [Running against a cluster](#running-against-a-cluster).

The suite reaches the application only through the gateway, and MongoDB, Kafka, S3 and Vault only through the state-management service.
It uses that service to reset state and also to read service databases when checking outcomes, so it is grey box rather than black box.

### Configuration

The Archive Test Bed can be configured through either **YAML file** or **environment variables**, with environment variables having higher priority.

The testbed itself is configured via the YAML file named by the environment variable `TB_CONFIG_YAML`.
`just testbed` sets it to `tb.kind.yaml`, the configuration for the kind cluster, and supplies the secrets as `TB_*` environment variables read from the cluster.
Alternative configurations can be saved as `tb.*.yaml` and activated the same way.

- **States:** `keep_state_in_db` stores the test states in the state-management database, the default, or in memory.
- **Additional Authentication:** `auth_basic` adds Basic authentication to the suite's own HTTP requests, except those to the state-management, purge-controller and DLQ services; the browser, the data steward kit and the connector do not send it yet.
  Set it as `TB_AUTH_BASIC` where the gateway asks for it.
- **Vault reset:** `allow_vault_reset` lets the clean slate delete the secrets under `vault_path`.
  It is off by default, because Vault holds secrets no other store keeps; enable it only where that path holds the suite's secrets alone, as `tb.kind.yaml` does.

### Running against a cluster

The suite reaches a deployment only through its gateway: the service APIs, the state-management service, and the three test doubles it asserts against, the test OIDC provider, the mail server and the lox24 SMS mock.
The one exception is the pre-signed S3 URLs the services hand to the connector, whose host must resolve from the runner.
A target deployment therefore provides:

- the state-management service behind the gateway, under the guardrails of [ADR-0030](../docs/adrs/adr-0030-state-management-service-testbed-only.md): a non-empty `db_prefix`, a `db_permissions` list naming the suite's databases, a Vault policy granting only the suite's secret path, and a Vault-issued token;
- the three doubles behind the gateway, where the original deployment served them under a `/test/` prefix;
- database, collection and event-type names that match the configuration, as `tb.kind.yaml` sets them for the kind cluster;
- the four service tokens and the FIS public key, and credentials where the gateway asks for Basic authentication.

Write a `tb.<env>.yaml` beside `tb.kind.yaml` holding URLs, database names, collection names and event-type names only, export the secrets, and run:

```bash
export TB_STATE_MANAGEMENT_TOKEN=… TB_PURGE_CONTROLLER_TOKEN=… TB_DLQ_TOKEN=… TB_UPLOAD_TOKEN=…
export TB_FIS_PUBKEY=… TB_USER_PRIVATE_CRYPT4GH_KEY=… TB_USER_PUBLIC_CRYPT4GH_KEY=…
export TB_AUTH_BASIC=user:password   # only where the gateway asks for it
just testbed-remote testbed/tb.<env>.yaml steps/test_001_health_check.py   # reachability first
just testbed-remote testbed/tb.<env>.yaml                                  # the whole suite
```

The recipe sets `TB_CONFIG_YAML`, writes the steward token for the data steward kit to `~/.ghga_data_steward_token.txt`, the default `dsk_token_path`, and removes it afterwards, and it stops before pytest when a variable is missing, naming it.
It never calls `kubectl`, forwards a port or edits `/etc/hosts`.
The health check alone walks every configured API, so it is the reachability test: a failure there is a routing or deployment question before it is a suite question.
The suite starts from an empty state and resets shared state as it goes, so run it against one deployment only once at a time.

On kind, `just testbed` runs this lane: it harvests the secrets from the cluster, forwards the mail server and the lox24 mock, which kind does not route through its gateway, and then calls `just testbed-remote testbed/tb.kind.yaml`.

## License

This test bed is free to use and modify according to the [Apache 2.0 License](./LICENSE).
