# GHGA Monorepo — Design & Migration Docs

Design and migration records for the consolidation of GHGA's ~28 maintained repositories
into one polyglot monorepo (Python `uv` workspace + Angular front end) that builds Helm
charts and runs its integration tests on Kubernetes.

> Status: **executed; cutover in progress.** The import is done — 20 services, 7 libraries,
> 5 tools and the Angular front end are in the tree — CI and both release lanes run from
> here, and the platform lane has cut `ghga/15.3.1-rc.*`. What remains is the mainline-side
> wind-down in the [runbook §7](migration/runbook.md) checklist. These documents stay the
> record of the agreed design; where one has drifted from the repo, the drift is marked
> with a dated amendment rather than silently rewritten.

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

## Epics
- **[epics/](epics/README.md)** — technical specifications for GHGA development epics, written
  before each epic starts. Imported history-preserving from `ghga-de/epic-docs`
  ([ADR-0010](adr/0010-history-preserving-migration.md)); authoring conventions and the two
  templates (exploratory / implementation) live alongside them.

## Decisions (ADRs)
Status mirrors each ADR's own `Status:` line; the last column records supersession and
cross-ADR amendment, which is how several of these are meant to be read together.

| # | Decision | Status | Supersedes / superseded by |
|---|---|---|---|
| [0001](adr/0001-consolidate-into-monorepo.md) | Consolidate into one polyglot monorepo; retire the template + `.template/` sync | Accepted |  |
| [0002](adr/0002-uv-workspace-source-coupled-libs.md) | `uv` workspace; internal libs source-coupled; one `uv.lock` | Accepted · last amended 2026-08-24 |  |
| [0003](adr/0003-repository-scope.md) | Scope: everything except `datahub-test-bed` | Accepted |  |
| [0004](adr/0004-versioning-and-release-by-tag.md) | Hybrid releases: platform lockstep (`ghga/X.Y.Z`) + per-component PyPI lanes | Accepted · revised 2026-07-23 · last amended 2026-09-01 | follows [0020](adr/0020-branching-strategy.md) for the `dev` cut |
| [0005](adr/0005-helm-app-chart-services-and-config-only.md) | ~~App chart = "services + config only"~~ | **Superseded** | superseded by [0011](adr/0011-helm-chart-boundary-hybrid.md) |
| [0006](adr/0006-self-contained-demo-lightweight-infra.md) | Self-contained demo umbrella; lightweight infra (revised: Envoy Gateway edge, demo == testbed) | Accepted · revised 2026-06-30 · last amended 2026-09-04 |  |
| [0007](adr/0007-local-aai-generic-oidc.md) | Local AAI via a generic OIDC provider (mock-oauth2-server default) | Accepted · last amended 2026-09-04 |  |
| [0008](adr/0008-state-management-service-testbed-only.md) | `state-management-service` is test-bed-only, values-gated | Accepted |  |
| [0009](adr/0009-testbed-kind-minikube.md) | Integration test bed on kind (CI) / minikube (local); same artifact as the install | Accepted · last amended 2026-09-04 | amended by [0017](adr/0017-local-integration-host-cluster.md) |
| [0010](adr/0010-history-preserving-migration.md) | History-preserving import + one-way sync; hosted at `ghga-de/ghga` | Accepted · last amended 2026-09-04 |  |
| [0011](adr/0011-helm-chart-boundary-hybrid.md) | Helm chart boundary = **hybrid** (app charts own app-coupled CRDs) | Accepted | supersedes [0005](adr/0005-helm-app-chart-services-and-config-only.md) |
| [0012](adr/0012-self-contained-edge-envoy-gateway.md) | Self-contained edge & ext-authz via **Envoy Gateway** (Istio → staging) | Accepted |  |
| [0013](adr/0013-adopt-ghga-common-chart-system.md) | Adopt & evolve the existing `ghga-common` chart library + generator | Accepted |  |
| [0014](adr/0014-capability-markers-and-placement.md) | `[tool.ghga]` markers + directory defaults route the release lanes | Accepted · last amended 2026-08-18 |  |
| [0015](adr/0015-task-runner.md) | Task runner: `just` now, `moon` later | Accepted |  |
| [0016](adr/0016-secrets-and-tls.md) | Secrets: K8s Secrets (demo) / Vault Agent + cert-manager (prod) | Accepted |  |
| [0017](adr/0017-local-integration-host-cluster.md) | Local integration on a host-level cluster; no DinD/DooD in the devcontainer | Accepted · last amended 2026-08-11 | amends [0009](adr/0009-testbed-kind-minikube.md) |
| [0018](adr/0018-pre-commit-hooks.md) | One root `pre-commit` config for both stacks; hook versions from the lockfiles | Accepted |  |
| [0019](adr/0019-image-signing-sbom-provenance.md) | Sign published images; attach SBOM + provenance; enforcement stays in the platform layer | Accepted |  |
| [0020](adr/0020-branching-strategy.md) | Git Flow: `main` is the latest release, `dev` is the integration branch | **Proposed** — unimplemented | [0004](adr/0004-versioning-and-release-by-tag.md) already amended for it |

## Phased roadmap (high level)

| Phase | Outcome | Key refs |
|---|---|---|
| **1. Skeleton** | `git init`; root `uv` workspace + shared toolchain; gitignore legacy/scratch | runbook §1 |
| **2. Import** | All repos imported, history-preserving, into `libs/`/`services/`/`tools/`/`frontend/`/`testbed/` | runbook §2, `import-all.sh` |
| **3. Harmonise** | `[tool.uv.sources]` wiring, single `uv.lock` (skew reconciled), one toolchain, shared Dockerfile, lib matrix | runbook §3, ADR-0002 |
| **4. Charts & test bed** | Adopt `ghga-common` + generator; `ghga-demo` umbrella (Envoy Gateway edge + lightweight infra + AAI); testbed = the same install on kind | runbook §4, ADR-0011/12/13/06/07/09 |
| **5. CI/CD** | **Done.** Both stages live: the affected-target component gate (`ci.yaml`, incl. reverse-dep closure + front end) and the kind integration gate (`integration.yaml`). Publish targets decided — Docker Hub for images and charts, PyPI for the library lane; a tag push builds, publishing a platform release is a deliberate dispatch | runbook §5, ADR-0004/0009/0017/0019 |
| **6. Sync** | Periodic one-way sync from mainline keeps the gap small. Quiet since 2026-07-22; the tooling is now mostly used to import further repos | runbook §6, `sync-from-mainline.sh` |
| **7. Cutover** | **In progress.** Repo lives at `ghga-de/ghga`, the PyPI lane publishes, and the platform lane has cut `ghga/15.3.1-rc.*`. Still open: freezing and archiving the mainline repos, and the version-reconciliation and external-consumer checks in the checklist | runbook §7 |

## Open items (tracked, non-blocking)
See [architecture/overview.md §6](architecture/overview.md). Notably: detailed `ghga-common`
evolution (prune Emissary, DRY the generator against `[tool.ghga]` markers); confirming the
Envoy Gateway `SecurityPolicy.extAuth` ↔ prod `envoyExtAuthzHttp` header mapping; whether to
maintain an optional full-Istio umbrella profile; demo observability target.

> The earlier edge/boundary/secrets/placement/task-runner open items are now resolved
> (ADR-0011–0016).
