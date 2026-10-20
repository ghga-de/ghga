# Agent Instructions for `services/`

How we work on the deployable services.
The repo-wide rules are in the root [AGENTS.md](../AGENTS.md), what the directory is in its [README](README.md), and [docs/agent-instructions.md](../docs/agent-instructions.md) says what belongs in which file.

## Where to read

[docs/architecture/metadata-and-file-journeys.md](../docs/architecture/metadata-and-file-journeys.md) is required reading before changing how a service produces or consumes events: it is how metadata and files flow across the platform.
Before changing which events a service publishes or subscribes to, read [the Kafka topology rule](../.claude/rules/kafka-topology.md): the cascades map is hand-maintained, so the same change updates it.
Before changing a model a service stores in MongoDB, read [the migrations rule](../.claude/rules/migrations.md): a changed document shape needs a migration.

## Service patterns

- Match the member's existing patterns: hexkit ports/adapters, Pydantic settings-from-env config, dependency injection.
  Preserve them unless the change is about changing them, and check the [ADRs](../docs/adrs/) first if it is.
- hexkit's testcontainers-based testutils give the member's own suite real Kafka, MongoDB and S3, so persistence and event handling are unit-testable here.
  A flow that crosses services belongs in the [test bed](../testbed/AGENTS.md) instead.
- For tests, copy a service with a joint fixture, such as `notification-orchestration-service` (`tests/fixtures/joint.py` and `test_config.yaml`); wps, the model for migrations, has neither.
  The member-root `conftest.py` finds `dev_config.yaml` only while the config prefix equals the package name.
- A new topic or event type goes into the config class, `dev_config.yaml`, the tests' config and the `_topics` block of `chart-values.yaml`, which writes the config value and the Kafka ACL both.
- The chart sets the database from `mongodb.dbName` in `chart-values.yaml` and drops any `config.db_name` there.
- A service whose DAO publishes through the outbox offers `publish-events`, which runs `publish_pending()` or, with `--all`, `republish()`.
- An endpoint that checks its own token, or none, must be in the auth adapter's `allow_read_paths` or `allow_write_paths` (`deploy/charts/ghga-demo/values.yaml`), or the ext-auth response blanks its `Authorization` header.
- A consumer is a second deployment of the image: an `alias` in `deploy/charts/ghga-demo/Chart.yaml` and its values block, such as `wps-consumer`.
- `just service-docs` takes up a new service once it has a `config_schema.json`, and writes its `openapi.yaml` only when one exists; create both empty first.
