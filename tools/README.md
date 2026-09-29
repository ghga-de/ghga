# `tools/` — CLIs & jobs

Workspace members that are primarily command-line tools or Kubernetes jobs.

- `ghga-connector` and `ghga-datasteward-kit` are **external** CLIs (published to PyPI) **and**
  integration-test actors — they exercise the deployed system in the test bed
  ([ADR-0025](../docs/adrs/adr-0025-consolidate-into-monorepo.md)).
- Some tools are also deployable/services (e.g. `ghga-transpiler`, `ghga-validator`); capability
  is declared with `[tool.ghga]` markers, not by folder
  ([ADR-0033](../docs/adrs/adr-0033-capability-markers-and-placement.md)).
- `auth-km-jobs` generates/rotates JWK + Crypt4GH keys; in prod it is the rotation CronJob
  writing to Vault ([ADR-0035](../docs/adrs/adr-0035-secrets-and-tls.md)).
