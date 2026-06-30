# GHGA Monorepo

One polyglot monorepo for GHGA: Python services, libraries, and CLIs (a single `uv` workspace)
alongside the Angular `data-portal`, with Helm charts and a Kubernetes integration test bed as
build products.

> **Status: scaffolding.** The source repos have **not** been imported yet. This is the
> Phase-1 skeleton (workspace + toolchain + structure) plus the planning docs. The
> history-preserving import, dependency lock, charts, and CI are deliberate next steps —
> see the runbook.

## Layout

| Path | Contents |
|---|---|
| [`libs/`](libs/) | Source-coupled internal libraries (hexkit, ghga-service-commons, …) |
| [`services/`](services/) | Deployable services |
| [`tools/`](tools/) | CLIs & jobs (ghga-connector, ghga-datasteward-kit, auth-km-jobs, …) |
| [`frontend/`](frontend/) | The Angular `data-portal` (own `pnpm` workspace) |
| [`deploy/`](deploy/) | Helm charts (adopted `ghga-common` library + generator, demo umbrella) |
| [`testbed/`](testbed/) | BDD + Playwright integration suite (runs on kind/minikube) |
| [`docker/`](docker/) | Shared Dockerfile(s) |
| [`scripts/`](scripts/) | Codegen, affected-targets, and migration tooling |
| [`docs/`](docs/) | Architecture, ADRs, migration runbook |

## Getting started (once members are imported)

```bash
uv sync                 # or: just sync
just lint && just test
```

## Where to read

- **[docs/architecture/overview.md](docs/architecture/overview.md)** — the target architecture.
- **[docs/adr/](docs/adr/)** — the decisions (and why), ADR-0001…0016.
- **[docs/migration/runbook.md](docs/migration/runbook.md)** — the phased migration plan.

## Conventions

See [docs/conventions.md](docs/conventions.md) — workspace layout, the `[tool.ghga]` capability
markers, naming, and the per-component release-tag scheme (`name/x.y.z`).
