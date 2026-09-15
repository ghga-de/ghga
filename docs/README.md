# GHGA Monorepo — Design & Migration Docs

Design and migration records for the consolidation of GHGA's ~28 maintained repositories
into one polyglot monorepo (Python `uv` workspace + Angular front end) that builds Helm
charts and runs its integration tests on Kubernetes.

> Status: **executed; cutover in progress.** The import is done — 20 services, 7 libraries,
> 5 tools and the Angular front end are in the tree — CI and both release lanes run from
> here, and the platform lane has cut `ghga/15.3.1-rc.*`. What remains is the mainline-side
> wind-down in the [runbook §7](migration/runbook.md) checklist. The ADRs record the decisions
> as they stand; git keeps how they got there.

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
- **[releases.md](releases.md)** — how a release is cut, built and published: the two lanes,
  their tags, version stamping, the PyPI upload plan and the publish targets.
- **[dependencies.md](dependencies.md)** — how dependencies are updated, and which are
  deliberately kept behind their latest version, why, and the signal to update.

## Epics
- **[epics/](epics/README.md)** — technical specifications for GHGA development epics, written
  before each epic starts. Imported history-preserving from `ghga-de/epic-docs`
  ([ADR-0025](adrs/0025-consolidate-into-monorepo.md)); authoring conventions and the two
  templates (exploratory / implementation) live alongside them.

## Decisions (ADRs)
Status mirrors each ADR's own `Status:` line. Write new ADRs from the
[template](adrs/0000-template.md), following the
[writing style](style.md#architecture-decision-records).

| # | Decision | Status |
|---|---|---|
| [0001](adrs/0001-drop-di-framework.md) | Drop DI framework | Accepted |
| [0002](adrs/0002-angular-as-frontend-framework.md) | Angular as frontend framework | Accepted |
| [0003](adrs/0003-custom-2fa-service.md) | Custom 2FA micro service | Accepted |
| [0004](adrs/0004-user-session-management.md) | User session management in the GHGA data portal | Accepted |
| [0005](adrs/0005-db-event-consistency.md) | Consistency between events and databases of services | Accepted |
| [0006](adrs/0006-custom-schema-framework.md) | A custom framework for defining linked metadata models | Proposed |
| [0007](adrs/0007-sourcing-notifications.md) | Sourcing notifications | Accepted |
| [0008](adrs/0008-usage-of-enums.md) | Naming and usage of enums | Accepted |
| [0009](adrs/0009-kafka-dead-letter-queues.md) | Kafka dead letter queues (DLQ) | Accepted |
| [0010](adrs/0010-naming-mongo-and-kafka.md) | Naming conventions for databases and event streams | Accepted |
| [0011](adrs/0011-uuids-datetimes-mongodb.md) | UUID and datetime representation in MongoDB | Accepted |
| [0012](adrs/0012-use-of-ngmodules.md) | Angular with standalone components instead of NgModules | Accepted |
| [0013](adrs/0013-angular-code-style.md) | Angular code style | Accepted |
| [0014](adrs/0014-angular-project-documentation.md) | Angular project documentation | Accepted |
| [0015](adrs/0015-node-runtime-selection.md) | Node runtime for the Angular project | Accepted |
| [0016](adrs/0016-semantic-web-technologies.md) | Use of semantic web technologies | Accepted |
| [0017](adrs/0017-server-side-rendering-in-angular.md) | Using Angular server-side rendering | Accepted |
| [0018](adrs/0018-frontend-architecture.md) | Frontend architecture and modularization | Accepted |
| [0019](adrs/0019-responsive-design-systems.md) | Responsive design systems | Accepted |
| [0020](adrs/0020-angular-component-library.md) | Angular UI component library selection | Accepted |
| [0021](adrs/0021-tailwind.md) | Tailwind | Accepted |
| [0022](adrs/0022-db-migrations.md) | MongoDB migration code storage | Accepted |
| [0023](adrs/0023-schema-versioning.md) | Schema versioning | Accepted |
| [0024](adrs/0024-chart-versioning.md) | Helm charts versioning | Superseded by [0027](adrs/0027-versioning-and-release-by-tag.md) |
| [0025](adrs/0025-consolidate-into-monorepo.md) | One monorepo for everything except `datahub-test-bed`, imported history-preserving and synced one way | Accepted |
| [0026](adrs/0026-uv-workspace-source-coupled-libs.md) | `uv` workspace; internal libs source-coupled; one `uv.lock` | Accepted |
| [0027](adrs/0027-versioning-and-release-by-tag.md) | Releases: platform lockstep (`ghga/X.Y.Z`) and a per-component PyPI lane | Accepted |
| [0028](adrs/0028-self-contained-demo-lightweight-infra.md) | Demo and test bed are one self-contained umbrella, on kind in CI and in the devcontainer | Accepted |
| [0029](adrs/0029-local-aai-generic-oidc.md) | Local AAI: mock-oauth2-server in the demo, the test OIDC provider in the test bed | Accepted |
| [0030](adrs/0030-state-management-service-testbed-only.md) | `state-management-service` is test-bed-only, values-gated | Accepted |
| [0031](adrs/0031-helm-chart-boundary-hybrid.md) | Helm charts from `ghga-common` with a **hybrid** boundary (app charts own app-coupled CRDs) | Accepted |
| [0032](adrs/0032-self-contained-edge-envoy-gateway.md) | Self-contained edge & ext-authz via **Envoy Gateway** (Istio → staging) | Accepted |
| [0033](adrs/0033-capability-markers-and-placement.md) | `[tool.ghga]` markers + directory defaults decide what a member builds and releases | Accepted |
| [0034](adrs/0034-task-runner.md) | Task runner: `just` now, `moon` later | Accepted |
| [0035](adrs/0035-secrets-and-tls.md) | Secrets: K8s Secrets (demo) / Vault Agent + cert-manager (prod) | Accepted |
| [0036](adrs/0036-pre-commit-hooks.md) | One root `pre-commit` config for both stacks; hook versions from the lockfiles | Accepted |
| [0037](adrs/0037-image-signing-sbom-provenance.md) | Sign published images; attach SBOM + provenance; enforcement stays in the platform layer | Accepted |
| [0038](adrs/0038-branching-strategy.md) | Branching, merging and naming: `dev` and `main`, squashed pull requests, one naming grammar | Accepted |
| [0039](adrs/0039-docs-lane-github-pages.md) | One Pages site for the repo; one subpath per documented member, tracking `main` | Accepted |
| [0040](adrs/0040-adr-frontmatter.md) | YAML frontmatter replaces the ADR header list; the index is generated from it | Accepted |
| [0041](adrs/0041-adr-linting.md) | A pre-commit hook checks the ADR set and every ADR reference, and regenerates the index | Proposed |

## Phased roadmap (high level)

| Phase | Outcome | Key refs |
|---|---|---|
| **1. Skeleton** | `git init`; root `uv` workspace + shared toolchain; gitignore legacy/scratch | runbook §1 |
| **2. Import** | All repos imported, history-preserving, into `libs/`/`services/`/`tools/`/`frontend/`/`testbed/` | runbook §2, `import-all.sh` |
| **3. Harmonise** | `[tool.uv.sources]` wiring, single `uv.lock` (skew reconciled), one toolchain, shared Dockerfile, lib matrix | runbook §3, ADR-0026 |
| **4. Charts & test bed** | Adopt `ghga-common` + generator; `ghga-demo` umbrella (Envoy Gateway edge + lightweight infra + AAI); testbed = the same install on kind | runbook §4, ADR-0031/12/06/07 |
| **5. CI/CD** | **Done.** Both stages live: the affected-target component gate (`ci.yaml`, incl. reverse-dep closure + front end) and the kind integration gate (`integration.yaml`). Publish targets decided — Docker Hub for images and charts, PyPI for the library lane; a tag push builds, publishing a platform release is a deliberate dispatch | runbook §5, ADR-0027/0028/0037 |
| **6. Sync** | Periodic one-way sync from mainline keeps the gap small. Quiet since 2026-07-22; the tooling is now mostly used to import further repos | runbook §6, `sync-from-mainline.sh` |
| **7. Cutover** | **In progress.** Repo lives at `ghga-de/ghga`, the PyPI lane publishes, and the platform lane has cut `ghga/15.3.1-rc.*`. Still open: freezing and archiving the mainline repos, and the version-reconciliation and external-consumer checks in the checklist | runbook §7 |

## Open items (tracked, non-blocking)
See [architecture/overview.md §6](architecture/overview.md). Notably: confirming the Envoy
Gateway `SecurityPolicy.extAuth` ↔ prod `envoyExtAuthzHttp` header mapping; whether to
maintain an optional full-Istio umbrella profile; demo observability target.

> The earlier edge/boundary/secrets/placement/task-runner open items are now resolved
> (ADR-0031–0035).
