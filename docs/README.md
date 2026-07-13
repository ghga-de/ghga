# GHGA Monorepo — Planning Docs

Planning artifacts for consolidating GHGA's ~28 maintained repositories into one polyglot
monorepo (Python `uv` workspace + Angular front end) that builds Helm charts and runs its
integration tests on Kubernetes.

> Status: **planning**. No source has been imported yet. These documents capture the agreed
> design and the executable migration plan, to be reviewed before any code movement.

## Start here
- **[architecture/overview.md](architecture/overview.md)** — the target architecture (layout,
  uv workspace, versioning, Helm, test bed, CI/CD), key tensions and their resolutions.
- **[architecture/metadata-and-file-journeys.md](architecture/metadata-and-file-journeys.md)** —
  current-state reference for how metadata and files flow (submission, accessions, upload,
  file mapping, serving). Read before touching those paths.
- **[migration/runbook.md](migration/runbook.md)** — phased, executable migration with a cutover
  checklist.
- **[../scripts/migration/](../scripts/migration/)** — the import + one-way-sync tooling and the
  [`repos.tsv`](../scripts/migration/repos.tsv) source-of-truth mapping.

## Features
- **[features/early-data-lifecycle.md](features/early-data-lifecycle.md)** — early rollout of the
  GHGA data lifecycle (study lifecycle PIDs + revisions, reuse-friendly file mapping) on the
  existing LinkML/offline stack. Design + per-component change list.

## Decisions (ADRs)
| # | Decision |
|---|---|
| [0001](adr/0001-consolidate-into-monorepo.md) | Consolidate into one polyglot monorepo; retire the template + `.template/` sync |
| [0002](adr/0002-uv-workspace-source-coupled-libs.md) | `uv` workspace; internal libs source-coupled; one `uv.lock` |
| [0003](adr/0003-repository-scope.md) | Scope: everything except `datahub-test-bed` |
| [0004](adr/0004-versioning-and-release-by-tag.md) | Per-component versions; release via `name/version` tags |
| [0005](adr/0005-helm-app-chart-services-and-config-only.md) | ~~App chart = "services + config only"~~ — **superseded by 0011** |
| [0006](adr/0006-self-contained-demo-lightweight-infra.md) | Self-contained demo umbrella; lightweight infra (revised: Envoy Gateway edge, demo == testbed) |
| [0007](adr/0007-local-aai-generic-oidc.md) | Local AAI via a generic OIDC provider (mock-oauth2-server default) |
| [0008](adr/0008-state-management-service-testbed-only.md) | `state-management-service` is test-bed-only, values-gated |
| [0009](adr/0009-testbed-kind-minikube.md) | Integration test bed on kind (CI) / minikube (local); same artifact as the install |
| [0010](adr/0010-history-preserving-migration.md) | History-preserving import + one-way sync; sandbox under `lkuchenb` |
| [0011](adr/0011-helm-chart-boundary-hybrid.md) | Helm chart boundary = **hybrid** (app charts own app-coupled CRDs) |
| [0012](adr/0012-self-contained-edge-envoy-gateway.md) | Self-contained edge & ext-authz via **Envoy Gateway** (Istio → staging) |
| [0013](adr/0013-adopt-ghga-common-chart-system.md) | Adopt & evolve the existing `ghga-common` chart library + generator |
| [0014](adr/0014-capability-markers-and-placement.md) | `[tool.ghga]` capability markers; place by primary identity |
| [0015](adr/0015-task-runner.md) | Task runner: `just` now, `moon` later |
| [0016](adr/0016-secrets-and-tls.md) | Secrets: K8s Secrets (demo) / Vault Agent + cert-manager (prod) |

## Phased roadmap (high level)

| Phase | Outcome | Key refs |
|---|---|---|
| **1. Skeleton** | `git init`; root `uv` workspace + shared toolchain; gitignore legacy/scratch | runbook §1 |
| **2. Import** | All repos imported, history-preserving, into `libs/`/`services/`/`tools/`/`frontend/`/`testbed/` | runbook §2, `import-all.sh` |
| **3. Harmonise** | `[tool.uv.sources]` wiring, single `uv.lock` (skew reconciled), one toolchain, shared Dockerfile, lib matrix | runbook §3, ADR-0002 |
| **4. Charts & test bed** | Adopt `ghga-common` + generator; `ghga-demo` umbrella (Envoy Gateway edge + lightweight infra + AAI); testbed = the same install on kind | runbook §4, ADR-0011/12/13/06/07/09 |
| **5. CI/CD (sandbox)** | Affected-target gate + kind integration gate; image/chart publish to `lkuchenb`; PyPI off | runbook §5, ADR-0004 |
| **6. Sync** | Periodic one-way sync from mainline keeps the gap small | runbook §6, `sync-from-mainline.sh` |
| **7. Cutover** | Flip CD to prod orgs, enable PyPI, archive old repos | runbook §7 |

## Open items (tracked, non-blocking)
See [architecture/overview.md §6](architecture/overview.md). Notably: detailed `ghga-common`
evolution (prune Emissary, DRY the generator against `[tool.ghga]` markers); confirming the
Envoy Gateway `SecurityPolicy.extAuth` ↔ prod `envoyExtAuthzHttp` header mapping; whether to
maintain an optional full-Istio umbrella profile; demo observability target.

> The earlier edge/boundary/secrets/placement/task-runner open items are now resolved
> (ADR-0011–0016).
