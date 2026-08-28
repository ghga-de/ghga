# GHGA Monorepo — Architecture Overview

> Status: **Proposal / planning**. This document describes the target architecture for
> consolidating GHGA's ~28 actively-maintained repositories into one polyglot monorepo.
> The load-bearing decisions are captured as ADRs under [docs/adr/](../adr/) and the
> step-by-step migration is in [docs/migration/runbook.md](../migration/runbook.md).

## 1. Goals & non-goals

### Goals
- **One repo for all GHGA applications** — Python services, libraries, CLIs, and the
  Angular front end — with a single, harmonised toolchain built around **`uv`**.
- **Retire the `microservice-repository-template`** and its cross-repo `.template/` file-sync
  mechanism. One toolchain, defined once at the repo root, replaces N synchronised copies.
- **HEAD of `main` is always fully integrated.** A single `uv.lock` and source-level coupling
  of internal libraries make this true by construction (see §3.2).
- **Helm charts are a product of this repo.** `helm install ghga` yields a working GHGA,
  including a local AAI (Life Science Login replacement).
- **Integration testing on Kubernetes** (kind in CI; a host-level cluster locally — no
  DinD/DooD in the devcontainer, ADR-0017) using the same charts, replacing the
  docker-compose test bed.
- **CI/CD keeps `main` green** by running the integration tests on proposed changes.
- **Independent component lifecycle** preserved: tagging `name/version` releases just that
  component.

### Non-goals
- Replacing the application architecture itself (hexagonal services, Kafka event bus,
  MongoDB/S3/Vault) — that stays.
- Re-platforming production. Production keeps its "bells and whistles" (Istio mesh + ingress,
  Strimzi-managed Kafka, Loki/Prometheus/Grafana). This repo produces the **app layer** (incl.
  app-coupled CRDs); the platform/GitOps layer owns the cluster edge + auth + per-env config
  (the *hybrid* boundary, see [ADR-0011](../adr/0011-helm-chart-boundary-hybrid.md)).
- Importing `datahub-test-bed` (different audience) or the retired template.

## 2. Current state (summary)

- ~30 repos under `github.com/ghga-de`, ~25 generated from `microservice-repository-template`
  and kept in sync via `.template/` + per-repo CI checks.
- `file-services-backend` is already a working Python monorepo (6 services) and is the closest
  blueprint: it already uses `uv pip compile`, a **single global lock**, near-empty per-service
  `pyproject.toml`s, per-service versions, one shared `Dockerfile` (ENTRYPOINT swapped per
  service), and a `get_affected_services` CI matrix.
- Dependency layering: `hexkit` → `ghga-service-commons` / `ghga-event-schemas` → `metldata`
  → `ghga-datasteward-kit`; `schemapack` → `ghga-transpiler`.
- **Live version skew** today (the problem this repo fixes): services pin `ghga-event-schemas`
  at `~=12` *and* `~=13` simultaneously; `ghga-datasteward-kit` pins `ghga-transpiler >=2.1.2,<3`
  while transpiler is already `3.0.0` (unsatisfiable against HEAD).
- Integration today: docker-compose stands up ~20 services (most as a **rest** + **consumer**
  pair), Kafka+ZooKeeper, MongoDB, 2× LocalStack (S3), Vault, MailHog, an Envoy gateway,
  OTel collector, a **test OIDC provider**, and a **state-management-service** that resets
  Kafka/Mongo/S3/Vault between BDD scenarios.

## 3. Target architecture

### 3.1 Repository layout

```
ghga-monorepo/
  pyproject.toml              # [tool.uv.workspace] members = libs/*, services/*, tools/*
  uv.lock                     # ONE lockfile — the integration contract
  ruff.toml / mypy config     # one toolchain config, repo-wide
  libs/                       # source-coupled internal libraries
    hexkit/  ghga-service-commons/  ghga-event-schemas/  schemapack/  metldata/
    ghga-arcticfreeze/        # deep-freeze helpers, used by schemapack
    ghga-jsonsubschema/       # GHGA fork of IBM/jsonsubschema, used by schemapack
  services/                   # deployable services (FSB's 6 flattened in)
    auth-service/  access-request-service/  dataset-information-service/  mass/
    notification-service/  notification-orchestration-service/  work-package-service/
    well-known-value-service/  dlq-service/  state-management-service/  ghga-registry-service/
    reverse-transpiler-service/  datahub-file-service/
    dcs/ ekss/ fis/ ifrs/ pcs/ ucs/
  tools/                      # CLIs / jobs
    ghga-connector/  ghga-datasteward-kit/  ghga-transpiler/  ghga-validator/  auth-km-jobs/
  frontend/
    data-portal/              # pnpm workspace, its own lockfile (JS toolchain)
  deploy/
    charts/
      ghga-common/            # adopted library chart (Bitnami-common based) + generator
      <per-service charts>/   # generated from ghga-common + workspace metadata
      ghga-demo/              # self-contained umbrella: app + Envoy Gateway + lightweight infra + AAI
  testbed/                    # ex-archive-test-bed: BDD + Playwright, runs vs kind+helm
  docker/                     # shared Dockerfile(s) (+ DHI hardened variant)
  scripts/                    # codegen, lock, affected-targets, migration tooling
  .github/workflows/          # one CI definition for everything
```

Repo→destination mapping for the import is the source of truth in
[scripts/migration/repos.tsv](../../scripts/migration/repos.tsv).

### 3.2 Python: uv workspace & dependency model — [ADR-0002](../adr/0002-uv-workspace-source-coupled-libs.md)

- The repo is **one `uv` workspace**. Each lib/service/tool is a workspace **member** with its
  own `pyproject.toml` and **its own version**.
- Internal libraries are consumed **from source**: a consuming member declares
  `[tool.uv.sources]` with `hexkit = { workspace = true }` (etc.). There is **one `uv.lock`**,
  so exactly one resolved version of every package exists across the whole repo. That is what
  makes "HEAD always integrated" literally true.
- **Consequence (accepted):** a breaking change to a shared lib must be fixed for *all*
  consumers in the same PR. "Independent lifecycle" of a lib means "we can cut a `hexkit`
  release whenever", **not** "service X may lag on an old `hexkit`".
- **Workspace Python baseline = 3.13** (the services' target). The workspace lock resolves for
  one interpreter.
- **Published libraries keep broad support** (3.9–3.12 today). Their declared dependency
  *ranges* stay broad in their own `pyproject.toml`; a **per-package standalone matrix** job
  (`uv run --python 3.10…3.13`) validates the *published* combination. So: the workspace lock
  tests "the integrated combo"; the matrix tests "the published combo". Both are required.

### 3.3 Versioning & release — [ADR-0004](../adr/0004-versioning-and-release-by-tag.md)

- Every component keeps a semver in its `pyproject.toml` (or `Chart.yaml` / `package.json`).
- A push of a git tag **`name/x.y.z`** (e.g. `hexkit/8.4.0`, `dcs/10.2.0`, `ghga/2.1.0`)
  triggers release of *only* that component. The version in the tag must match the version in
  HEAD for that component (CI validates, as `file-services-backend` already does).
- Because HEAD is integrated, tagging releases **the integrated HEAD's** version of the
  component — not an isolated branch.
- Artifact per component kind: libs/CLIs → wheel to PyPI; services → image to the registry;
  charts → OCI package. The umbrella `ghga/<version>` pins a tested set of component versions.

### 3.4 Build & containerisation

- Keep `file-services-backend`'s proven pattern: **one shared multi-stage `Dockerfile`** (plus
  the DHI hardened variant) under `docker/`, building any service from the workspace; ENTRYPOINT
  selected per service. Images are multi-arch (amd64/arm64) and Trivy-scanned, as today.
- `get_affected_services` generalises to **affected targets** (libs, services, frontend, charts)
  so CI only builds/tests what a change touches.

### 3.5 Helm — adopt `ghga-common`; app charts + demo umbrella

We **adopt and evolve the existing `ghga-common` chart system** rather than build from scratch
([ADR-0013](../adr/0013-adopt-ghga-common-chart-system.md)): the Bitnami-`common`-based library
chart + the per-service generator move into `deploy/`, the generator is DRYed against workspace
metadata ([ADR-0014](../adr/0014-capability-markers-and-placement.md)), and the dead Emissary
paths + the `istio-ext-authz-sync` Job are dropped. `devops-kubernetes-hub` stays as the
GitOps/platform layer.

- **App charts (`ghga-common`)** — emit Deployments / Services / ConfigMaps + a **rest/consumer
  role abstraction** (N Deployments sharing config with distinct `service_instance_id`s) **and
  the app-coupled CRDs** they already own: `HTTPRoute` (Gateway API), `DestinationRule` (toggle),
  `NetworkPolicy`, `KafkaUser`/`KafkaTopic` (toggle), plus the secret-consumption shape. The
  GitOps/platform layer owns the **edge** (`Gateway`), the **edge-auth** object, and **per-env**
  config — the *hybrid* boundary ([ADR-0011](../adr/0011-helm-chart-boundary-hybrid.md)).
- **`deploy/charts/ghga-demo`** — a self-contained **single-command** umbrella
  ([ADR-0006](../adr/0006-self-contained-demo-lightweight-infra.md)) that bundles the **edge**
  (**Envoy Gateway**, Gateway-API-native, real Envoy ext_authz against the auth-adapter —
  [ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md); gateway Service → NodePort on
  bare clusters) plus **lightweight infra**: Bitnami Kafka (KRaft; `KafkaUser`/`KafkaTopic`
  toggled off), standalone MongoDB, **MinIO**, Vault dev-mode, **mock-oauth2-server** as the
  local AAI ([ADR-0007](../adr/0007-local-aai-generic-oidc.md)), MailHog, a pre-install
  **secret-gen Job** (plain K8s Secrets — [ADR-0016](../adr/0016-secrets-and-tls.md)) and a
  **seed Job**. This same umbrella **is** the test bed.

**App-chart binding contract** (already met by `ghga-common`; kept as hard requirements):
- pod/service **label + annotation passthrough**;
- **named ports with `http-`/`grpc-` prefixes** and stable Service names;
- **per-workload ServiceAccounts** (Strimzi `KafkaUser` principals / mesh identity bind to the SA);
- injectable OTLP / Kafka / Mongo / S3 / Vault / OIDC config; customisable probes;
- secret consumption toggle: Vault Agent (prod) vs env-from-Secret (demo);
- seed/secret-gen **Jobs default to `sidecar.istio.io/inject: "false"`**.

### 3.6 Integration test bed — [ADR-0009](../adr/0009-testbed-kind-minikube.md)

- The ex-`archive-test-bed` BDD + Playwright suite moves to `testbed/` and runs **the same
  self-reliant `ghga-demo` umbrella** a user installs (test-bed profile) against a **kind**
  cluster (CI) / a **host-level cluster** locally (minikube on Linux/WSL2, or a container
  runtime's built-in Kubernetes — [ADR-0017](../adr/0017-local-integration-host-cluster.md)).
  The devcontainer stays unprivileged: no DinD/DooD, it only talks to the cluster via a
  namespace-scoped kubeconfig; images are built next to the cluster (the runtime's shared
  image store / `minikube image build`) — no local registry needed. "What you install ==
  what CI tests."
- Because the demo edge is **Envoy Gateway**, the gate exercises the **real** Gateway-API
  routing + Envoy ext_authz path against the real auth-adapter — not a stand-in.
- **`state-management-service` is testbed-only** ([ADR-0008](../adr/0008-state-management-service-testbed-only.md)):
  a security-sensitive backdoor that resets Kafka/Mongo/S3/Vault between scenarios. Values-gated
  (`testbed.enabled`), **never** in demo or production.
- Still **not** per-PR: the prod Istio edge-auth CRs, mesh mTLS, and Strimzi specifics — covered
  by a periodic **staging** check against the real platform
  ([ADR-0006](../adr/0006-self-contained-demo-lightweight-infra.md)).

### 3.7 CI/CD

- **PR gate**: affected-target lint/type/unit, then a **kind-based integration gate**
  (`helm install ghga-demo` + the BDD suite). This is what keeps HEAD integrated.
- **The long pole** is building ~20 images per relevant change; mitigated by building only
  *affected* images and pulling last-released tags for the rest, then `kind load`.
- **Release**: tag `name/x.y.z` → publish only that component (§3.3).

## 4. Sandbox phase & migration

The monorepo is developed **separately from mainline (`ghga-de`) for a while**
([ADR-0010](../adr/0010-history-preserving-migration.md)):

- Hosted at **`github.com/ghga-de/ghga`** (a new repo, separate from the per-component repos).
  **Publish targets (images, charts, PyPI) are not yet decided** — until they are, the release
  workflow is dormant and nothing is published from this repo.
- **History-preserving import** via `git filter-repo` (subdir move + boilerplate drop), then a
  **one-way incremental sync** from mainline until cutover. See the
  [runbook](../migration/runbook.md).

## 5. Key tensions & resolutions

| Tension | Resolution |
|---|---|
| "HEAD always integrated" vs "independent lifecycle" | Source-coupled libs (one `uv.lock`) → integration is structural; *independent lifecycle* applies to **release cadence** (per-component tags), not to consumers lagging on lib versions. |
| Services need 3.13, libs need 3.9–3.12 | Workspace baseline 3.13; libs keep broad ranges + a standalone per-Python **matrix** job. |
| Self-reliant `helm install ghga` vs prod-faithful tests | One self-contained umbrella with an **Envoy Gateway** edge ([ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md)) is **both** the install and the test bed: real Gateway-API routing + real Envoy ext_authz against the real auth-adapter, no external ops. Residual prod-only bits (Istio edge-auth CRs, mesh mTLS, Strimzi) → periodic staging check. |
| App chart portability (Istio prod vs Envoy Gateway demo) | *Hybrid* boundary ([ADR-0011](../adr/0011-helm-chart-boundary-hybrid.md)): app charts own app-coupled CRDs (HTTPRoute, etc.) with toggles; the edge + edge-auth object live in the GitOps/demo layer and differ per environment. |
| `state-management-service` power | Test-only, values-gated, never in demo/prod. |
| Migrate without disrupting live repos | One-way incremental, history-preserving sync; harmonise only at the root; keep service `src/` aligned with mainline. |

## 6. Open items (tracked, not blocking)
- Detailed `ghga-common` evolution: pruning Emissary, DRYing the generator against
  `[tool.ghga]` markers, and co-locating per-service chart values with each service.
- Envoy Gateway `SecurityPolicy.extAuth` field mapping vs the prod `envoyExtAuthzHttp` header
  contract (confirm 1:1 on `includeRequestHeadersInCheck`/`headersToBackend`).
- Whether the optional **full-Istio** umbrella profile is worth maintaining for an opt-in
  higher-fidelity gate, or staging-only is sufficient.
- Observability in the demo (OTLP endpoint target) vs prod Loki/Prometheus/Grafana.

> Resolved since first draft: edge ([ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md)),
> chart boundary ([ADR-0011](../adr/0011-helm-chart-boundary-hybrid.md)), adopting `ghga-common`
> ([ADR-0013](../adr/0013-adopt-ghga-common-chart-system.md)), member placement
> ([ADR-0014](../adr/0014-capability-markers-and-placement.md)), task runner
> ([ADR-0015](../adr/0015-task-runner.md)), secrets ([ADR-0016](../adr/0016-secrets-and-tls.md)).
