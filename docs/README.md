# GHGA Monorepo — Design & Migration Docs

Design and migration records for the consolidation of GHGA's ~28 maintained repositories
into one polyglot monorepo (Python `uv` workspace + Angular front end) that builds Helm
charts and runs its integration tests on Kubernetes.

> Status: **executed; cutover essentially done.** The import is done — 20 services, 7
> libraries, 5 tools and the Angular front end are in the tree — CI and both release
> lanes run from here, and the platform lane has cut `ghga/15.3.1-rc.*`. The leftovers
> are listed in the [runbook §7](migration/runbook.md#7-cutover-checklist). The ADRs
> record the decisions as they stand; git keeps how they got there.

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
- **[agent-instructions.md](agent-instructions.md)** — where guidance for coding agents
  lives: the `AGENTS.md` files, their stubs, the READMEs and the skills, and what belongs
  in each ([ADR-0042](adrs/adr-0042-agent-instruction-files.md)).
- **[dependencies.md](dependencies.md)** — how dependencies are updated, and which are
  deliberately kept behind their latest version, why, and the signal to update.

## Epics
- **[epics/](epics/README.md)** — technical specifications for GHGA development epics, written
  before each epic starts. Imported history-preserving from `ghga-de/epic-docs`
  ([ADR-0025](adrs/adr-0025-consolidate-into-monorepo.md)); authoring conventions and the two
  templates (exploratory / implementation) live alongside them.

## Decisions (ADRs)
Write new ADRs from the [template](adrs/adr-template.md), following the
[writing style](style.md#architecture-decision-records). The table is generated from each
ADR's frontmatter by `just docs-check`; do not edit it by hand.

<!-- adr-index:start -->
| # | Title | Status | Tags |
|---|---|---|---|
| [0001](adrs/adr-0001-drop-di-framework.md) | Drop DI framework | accepted | backend |
| [0002](adrs/adr-0002-angular-as-frontend-framework.md) | Angular as frontend framework | accepted | frontend |
| [0003](adrs/adr-0003-custom-2fa-service.md) | Custom 2FA micro service | accepted | backend, security |
| [0004](adrs/adr-0004-user-session-management.md) | User session management in the GHGA data portal | accepted | backend, frontend, security |
| [0005](adrs/adr-0005-db-event-consistency.md) | Consistency between events and databases of services | accepted | backend, data, events |
| [0006](adrs/adr-0006-custom-schema-framework.md) | A custom framework for defining linked metadata models | proposed | data |
| [0007](adrs/adr-0007-sourcing-notifications.md) | Sourcing notifications | accepted | backend, events |
| [0008](adrs/adr-0008-usage-of-enums.md) | Naming and usage of enums | accepted | backend |
| [0009](adrs/adr-0009-kafka-dead-letter-queues.md) | Kafka dead letter queues (DLQ) | accepted | backend, events |
| [0010](adrs/adr-0010-naming-mongo-and-kafka.md) | Naming conventions for databases and event streams | accepted | data, events |
| [0011](adrs/adr-0011-uuids-datetimes-mongodb.md) | UUID and datetime representation in MongoDB | accepted | backend, data |
| [0012](adrs/adr-0012-use-of-ngmodules.md) | Angular with standalone components instead of NgModules | accepted | frontend |
| [0013](adrs/adr-0013-angular-code-style.md) | Angular code style | accepted | frontend |
| [0014](adrs/adr-0014-angular-project-documentation.md) | Angular project documentation | accepted | frontend, docs |
| [0015](adrs/adr-0015-node-runtime-selection.md) | Node runtime for the Angular project | accepted | frontend, build |
| [0016](adrs/adr-0016-semantic-web-technologies.md) | Use of semantic web technologies | accepted | data |
| [0017](adrs/adr-0017-server-side-rendering-in-angular.md) | Using Angular server-side rendering | accepted | frontend |
| [0018](adrs/adr-0018-frontend-architecture.md) | Frontend architecture and modularization | accepted | frontend |
| [0019](adrs/adr-0019-responsive-design-systems.md) | Responsive design systems | accepted | frontend |
| [0020](adrs/adr-0020-angular-component-library.md) | Angular UI component library selection | accepted | frontend |
| [0021](adrs/adr-0021-tailwind.md) | Tailwind | accepted | frontend |
| [0022](adrs/adr-0022-db-migrations.md) | MongoDB migration code storage | accepted | backend, data |
| [0023](adrs/adr-0023-schema-versioning.md) | Schema versioning | accepted | backend, data |
| [0024](adrs/adr-0024-chart-versioning.md) | Helm charts versioning | superseded by [0027](adrs/adr-0027-versioning-and-release-by-tag.md) | release, deploy |
| [0025](adrs/adr-0025-consolidate-into-monorepo.md) | Consolidate into one monorepo by history-preserving import | accepted | process, build |
| [0026](adrs/adr-0026-uv-workspace-source-coupled-libs.md) | `uv` workspace with source-coupled internal libraries | accepted | build |
| [0027](adrs/adr-0027-versioning-and-release-by-tag.md) | Releases: platform lockstep and a PyPI lane | accepted; supersedes [0024](adrs/adr-0024-chart-versioning.md) | release, deploy |
| [0028](adrs/adr-0028-self-contained-demo-lightweight-infra.md) | Demo and test bed: one self-contained umbrella on kind | accepted | deploy, testing |
| [0029](adrs/adr-0029-local-aai-generic-oidc.md) | Local AAI via generic OIDC providers | accepted | security, deploy, testing |
| [0030](adrs/adr-0030-state-management-service-testbed-only.md) | `state-management-service` is test-bed-only | accepted | deploy, testing |
| [0031](adrs/adr-0031-helm-chart-boundary-hybrid.md) | Helm charts from `ghga-common` with a hybrid boundary | accepted | deploy |
| [0032](adrs/adr-0032-self-contained-edge-envoy-gateway.md) | Self-contained edge: Envoy Gateway | accepted | deploy, security |
| [0033](adrs/adr-0033-capability-markers-and-placement.md) | Capability markers decide what a member builds and releases | accepted | build, release |
| [0034](adrs/adr-0034-task-runner.md) | Task runner: `just`, with `moon` as a later option | accepted | build |
| [0035](adrs/adr-0035-secrets-and-tls.md) | Secrets and TLS: Kubernetes Secrets in the demo, Vault and cert-manager in production | accepted | security, deploy |
| [0036](adrs/adr-0036-pre-commit-hooks.md) | One pre-commit configuration for both stacks | accepted | build, process |
| [0037](adrs/adr-0037-image-signing-sbom-provenance.md) | Sign published images and attach SBOM and provenance | accepted | security, release |
| [0038](adrs/adr-0038-branching-strategy.md) | Branching, merging and naming | accepted | process, release |
| [0039](adrs/adr-0039-docs-lane-github-pages.md) | One documentation site for the monorepo | accepted | docs, release |
| [0040](adrs/adr-0040-adr-frontmatter.md) | YAML frontmatter for ADRs | accepted | docs, process |
| [0041](adrs/adr-0041-docs-linting.md) | A pre-commit check for ADRs and epics | accepted | docs, process |
| [0042](adrs/adr-0042-agent-instruction-files.md) | Layered AGENTS.md for coding agents | accepted | docs, process |
| [0043](adrs/adr-0043-release-notes.md) | Release notes as drafted GitHub releases | accepted | release, process |
<!-- adr-index:end -->

## Phased roadmap (high level)

| Phase | Outcome | Key refs |
|---|---|---|
| **1. Skeleton** | `git init`; root `uv` workspace + shared toolchain; gitignore legacy/scratch | runbook §1 |
| **2. Import** | All repos imported, history-preserving, into `libs/`/`services/`/`tools/`/`frontend/`/`testbed/` | runbook §2, `import-all.sh` |
| **3. Harmonise** | `[tool.uv.sources]` wiring, single `uv.lock` (skew reconciled), one toolchain, shared Dockerfile, lib matrix | runbook §3, ADR-0026 |
| **4. Charts & test bed** | Adopt `ghga-common` + generator; `ghga-demo` umbrella (Envoy Gateway edge + lightweight infra + AAI); testbed = the same install on kind | runbook §4, ADR-0031/0032/0028/0029 |
| **5. CI/CD** | **Done.** Both stages live: the affected-target component gate (`ci.yaml`, incl. reverse-dep closure + front end) and the kind integration gate (`integration.yaml`). Publish targets decided — Docker Hub for images and charts, PyPI for the library lane; a tag push builds, publishing a platform release is a deliberate dispatch | runbook §5, ADR-0027/0028/0037 |
| **6. Sync** | Periodic one-way sync from mainline kept the gap small until each repo was archived. Now used only to import the schemapack line | runbook §6, `sync-from-mainline.sh` |
| **7. Cutover** | **Essentially done.** Repo lives at `ghga-de/ghga`, the PyPI lane publishes, the platform lane has cut `ghga/15.3.1-rc.*`, and the source repos are archived. The leftovers are listed in runbook §7 | runbook §7 |

## Open items (tracked, non-blocking)
See [architecture/overview.md §6](architecture/overview.md). Notably: confirming the Envoy
Gateway `SecurityPolicy.extAuth` ↔ prod `envoyExtAuthzHttp` header mapping; whether to
maintain an optional full-Istio umbrella profile; demo observability target.

> The earlier edge/boundary/secrets/placement/task-runner open items are now resolved
> (ADR-0031–0035).
