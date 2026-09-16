# Agent Instructions for `services/`

How we work on the deployable services. The repo-wide rules are in the root
[AGENTS.md](../AGENTS.md), what the directory is in its [README](README.md), and
[docs/agent-instructions.md](../docs/agent-instructions.md) says what belongs in which
file.

## Where to read

[docs/architecture/metadata-and-file-journeys.md](../docs/architecture/metadata-and-file-journeys.md)
is required reading before changing how a service produces or consumes events: it is how
metadata and files flow across the platform.

## Service patterns

- Match the member's existing patterns: hexkit ports/adapters, Pydantic settings-from-env
  config, dependency injection. Preserve them unless the change is about changing them,
  and check the [ADRs](../docs/adrs/) first if it is.
- hexkit's testcontainers-based testutils give the member's own suite real Kafka, MongoDB
  and S3, so persistence and event handling are unit-testable here. A flow that crosses
  services belongs in the [test bed](../testbed/AGENTS.md) instead.
