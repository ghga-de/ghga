# `services/` — deployable services

Workspace members that are deployed as container images and wired into the Helm charts.

`em-transformation-service` will join once the workspace moves to the metldata 5.x
schemapack line (see `scripts/migration/repos.tsv`).

- Each service keeps a minimal `pyproject.toml` (name, version, build, `[tool.uv.sources]`,
  `[tool.ghga]`), and a `src/<pkg>/` layout with tests.
- Most services run as a **rest** + **consumer** pair — modelled in the chart as N Deployments
  sharing config with distinct `service_instance_id`s.
- `state-management-service` is **test-bed-only** and values-gated — never in demo/prod
  ([ADR-0030](../docs/adrs/adr-0030-state-management-service-testbed-only.md)).
