# `tools/` — CLIs & jobs

Workspace members that are primarily command-line tools or Kubernetes jobs.

Planned members (after import): `ghga-connector`, `ghga-datasteward-kit`, `ghga-transpiler`,
`ghga-validator`, `auth-km-jobs`.

- `ghga-connector` and `ghga-datasteward-kit` are **external** CLIs (published to PyPI) **and**
  integration-test actors — they exercise the deployed system in the test bed
  ([ADR-0003](../docs/adr/0003-repository-scope.md)).
- Some tools are also deployable/services (e.g. `ghga-transpiler`, `ghga-validator`); capability
  is declared with `[tool.ghga]` markers, not by folder
  ([ADR-0014](../docs/adr/0014-capability-markers-and-placement.md)).
- `auth-km-jobs` generates/rotates JWK + Crypt4GH keys; in prod it is the rotation CronJob
  writing to Vault ([ADR-0016](../docs/adr/0016-secrets-and-tls.md)).
