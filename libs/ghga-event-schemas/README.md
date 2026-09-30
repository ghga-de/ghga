<!-- rumdl-disable MD013 -->
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
<!-- rumdl-enable MD013 -->

# GHGA Event Schemas

GHGA Event Schemas: A package that collects schemas used for events exchanged between GHGA service.

## Description

This package collects the Pydantic models for the events that GHGA services exchange over Kafka, so producer and consumer validate a payload against the same schema.

- `ghga_event_schemas.pydantic_` holds the event payload models.
- `ghga_event_schemas.configs` holds settings classes for the topic and event type names each event kind uses, which a service mixes into its own config.
- `ghga_event_schemas.validation.get_validated_payload()` checks a received payload against a model and raises `EventSchemaValidationError` when it does not match.

```python
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload

registered = get_validated_payload(payload, event_schemas.FileInternallyRegistered)
```

## Installation

The package is a library in the [GHGA monorepo](../../README.md) and is not published to PyPI.
Workspace members depend on it from source, and the platform images carry it; a service lists it under `dependencies` in its `pyproject.toml` and adds `ghga-event-schemas = { workspace = true }` under `[tool.uv.sources]`.

## Development

Work in the monorepo's dev container, as described in [Work inside the dev container](../../README.md#work-inside-the-dev-container).
Run the tests with `just test libs/ghga-event-schemas`, and the linters with `just lint`.
A change to a model changes the event contract between services, so check every consumer with `just affected`.

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
