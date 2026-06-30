# ADR-0013 — Adopt and evolve the existing `ghga-common` chart library + generator

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
A goal is "Helm charts are a product of this repo." GHGA already has a mature chart system in
the `charts/` repo: a Bitnami-`common`-based library chart `base/ghga-common` (Deployment,
Service, ServiceAccount, HTTPRoute, DestinationRule, NetworkPolicy, KafkaUser, HPA, CronJob/Job,
Vault Agent injection — i.e. the whole binding contract), and a generator
`src/create_charts.py` that stamps one chart per service from `src/values/<svc>.yaml` +
`charts_app_versions.yaml`. The brief was to use this knowledge **critically**, not to copy it.

## Decision
**Adopt** `ghga-common` + the generator into the monorepo rather than building charts from
scratch, with these deliberate changes:
- **Move** the chart library + generator into the monorepo under `deploy/`; charts become a
  build product of the workspace.
- **DRY the generator against workspace metadata**: derive image repo/version and capability
  flags from each member's `pyproject.toml`/`[tool.ghga]`
  ([ADR-0014](0014-capability-markers-and-placement.md)) and co-locate per-service chart values
  with the service, instead of a separate `src/values/` tree duplicating facts.
- **Prune** the dead Emissary `Mapping`/`AuthService` paths (migrated to Gateway API).
- **Do not** carry over the `istio-ext-authz-sync` Job into the self-contained path
  ([ADR-0012](0012-self-contained-edge-envoy-gateway.md)).
- **Keep the secret-consumption shape toggleable**: Vault Agent for prod, plain
  env-from-Secret for the demo ([ADR-0016](0016-secrets-and-tls.md)).
- `devops-kubernetes-hub` **stays** as the GitOps/platform layer (edge, auth, per-env); it is
  not absorbed.

## Consequences
- Large head-start; the proven binding contract and CRD emission come for free.
- A Bitnami-`common` dependency and its surface come along — accepted; pruned where dead.
- The generator must learn to read workspace metadata; per-service values move next to services.
- Releasing charts uses the per-component tag scheme
  ([ADR-0004](0004-versioning-and-release-by-tag.md)).

## Alternatives considered
- **Build a fresh app chart.** Rejected: months of work to re-derive a battle-tested chart.
- **Adopt `charts/` verbatim.** Rejected: keeps the Emissary cruft, the sync Job, and the
  duplicated `src/values/` instead of workspace-derived metadata.
