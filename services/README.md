# `services/` — deployable services

Workspace members that are deployed as container images and wired into the Helm charts.

Planned members (after import): `auth-service`, `access-request-service`,
`dataset-information-service`, `mass`, `notification-service`,
`notification-orchestration-service`, `work-package-service`, `well-known-value-service`,
`dlq-service`, `state-management-service`, `ghga-registry-service`,
`reverse-transpiler-service`, `em-transformation-service`,
`datahub-file-service`, and the file-services `dcs`, `ekss`, `fis`, `ifrs`, `pcs`, `ucs`
(flattened in from `file-services-backend`).

- Each service keeps a minimal `pyproject.toml` (name, version, build, `[tool.uv.sources]`,
  `[tool.ghga]`), and a `src/<pkg>/` layout with tests.
- Most services run as a **rest** + **consumer** pair — modelled in the chart as N Deployments
  sharing config with distinct `service_instance_id`s.
- `state-management-service` is **test-bed-only** and values-gated — never in demo/prod
  ([ADR-0008](../docs/adr/0008-state-management-service-testbed-only.md)).
