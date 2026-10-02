# Getting started

A first read for developers new to this repo: how the parts fit together, how you work, test and ship here, and what to read next.
It is about the repo itself, not about coding agents: [using-agents.md](using-agents.md) covers working with them, and the agents themselves start from the `AGENTS.md` files.
The commands and rules live in the pages it links.

## What the repo is

The repo holds GHGA's backend services, the libraries they share, the command-line tools for data stewards and submitters, and the Angular data portal.
From it, CI builds the platform's container images and Helm charts, and the wheels of the libraries and tools published on PyPI.
The same charts run the whole platform on a local kind cluster, as a demo and as the integration test bed.

The services have a hexagonal architecture (ports and adapters), built on our hexkit library: the core logic depends only on interfaces, the ports, and adapters implement them for Kafka, MongoDB and S3.
They exchange events over Kafka, each keeps its own MongoDB database, and files live in S3 buckets.
The data portal and the CLIs call the services' REST APIs through one gateway: Istio in staging and production, Envoy Gateway in the demo and the test bed ([ADR-0032](../adrs/adr-0032-self-contained-edge-envoy-gateway.md)).
The [architecture overview](../architecture/overview.md) and the [journeys](../architecture/metadata-and-file-journeys.md) have the details.

## How it is organised

- **`services/`** holds the deployable services; you change an API, an event consumer or a database model here.
  Most services run as a REST process and a consumer process from one codebase.
- **`libs/`** holds the shared libraries, chief among them hexkit, the ports-and-adapters framework the services are built on, and ghga-service-commons, the functionality our services share: FastAPI server setup, authentication and authorization, HTTP utilities.
  A change here reaches every member that uses the library.
- **`tools/`** holds the CLIs and jobs, such as `ghga-connector` for uploads and downloads and `ghga-datasteward-kit`.
- **`frontend/data-portal/`** is the data portal.
- **`deploy/`** holds the Helm charts.
  Most are generated from the members' metadata, so you change the generator or a member's `chart-values.yaml`, not the chart.
- **`testbed/`** is the BDD and Playwright suite that runs against the platform on kind.
- **`docker/`** and **`scripts/`** hold the shared Dockerfile and the repo's own tooling: code generation, affected targets, checks.
- **`docs/`** holds the architecture documents, the ADRs, the conventions and the epics.

Every directory under `libs/`, `services/` and `tools/` is a member of one `uv` workspace.
A member is a Python package with its own `pyproject.toml`, `src/`, `tests/` and version.
Members use the internal libraries from source, and one `uv.lock` pins the whole workspace, so `dev` is always integrated ([ADR-0026](../adrs/adr-0026-uv-workspace-source-coupled-libs.md)).
The `[tool.ghga]` table in a member's `pyproject.toml` says what it builds and on which lane it is released ([conventions](../conventions.md#toolghga-capability-markers)).
The ruff, mypy and pytest configuration lives once, in the root `pyproject.toml`.

The front end is not a workspace member.
It has its own `pnpm` workspace and lockfile, and the `just fe-*` recipes drive it.

## How you work

- **Work in the dev container** (`.devcontainer/`), which has the whole toolchain.
  The Python recipes refuse to run on the host, because the host and the container share `.venv`; the [README](../../README.md#work-inside-the-dev-container) explains why that breaks.
- **Run everything through `just`**; `just` alone lists the recipes, and the [recipe reference](../../README.md#recipe-reference) groups them.
  On the first day you need these:
  - `just sync` installs the workspace into `.venv`.
  - `just lint` checks lint and formatting, and `just fmt` fixes what it can.
  - `just test services/auth-service` runs one member's tests.
  - `just affected` lists the members your branch reaches, compared with `origin/dev`.
  - `just fe-dev` starts the data portal against mocked APIs, with no backend.

  To run the whole platform, `just demo-images-mono` and `just up mono` build it and start it on kind ([demo walkthrough](../../README.md#run-the-demo-locally)).
- **Branch from `dev` and open the pull request against `dev`**, where it is squash-merged; `main` carries the latest release and takes hotfixes only.
  Branch names, pull request titles and commit messages follow one [grammar](../conventions.md#names-branches-prs-commits).
- **Let the pre-commit hooks run.**
  One configuration covers both stacks ([ADR-0036](../adrs/adr-0036-pre-commit-hooks.md)): ruff, mypy, rumdl, Prettier, ESLint, the docs checks and the generated service docs.
  The dev container installs the hooks; if a commit runs none, run `just hooks`.

## Ports and networking

The dev container shares the host's network (`--net=host`), and kind runs inside the container's own Docker.
So a port the demo or a dev server opens in the container is the same port on your computer, and `.devcontainer/devcontainer.json` sets no `forwardPorts`.
Forwarding a port as well creates a loop that hangs the connection; leave VS Code's port forwarding off for these ports.

| Port | What listens | Why it matters |
|---|---|---|
| 80 | the demo gateway (`just up`) | The OIDC issuer must have the same address in the browser and in the cluster, and that address cannot carry a port, so the demo needs a bare `http://localhost`. |
| 9000 | MinIO, the demo's S3 | Pre-signed URLs name the host `ghga-minio`, so that name must resolve to `127.0.0.1`; the dev container maps it, and `just testbed-hosts` does it elsewhere. |
| 8080 | `just fe-dev` | The data portal with mocked APIs. |
| 443 | `just fe-dev-oidc` and `just fe-dev-backend-oidc` | The OIDC provider redirects to a URL without a port; the recipe allows `node` to bind it. |
| 9323 | `just testbed-trace` | The Playwright trace viewer. |

Because of these fixed ports, only one checkout or worktree at a time can run the demo or the test bed.

Three problems come up most often:

- **Docker Desktop** forwards host-network ports only with *Settings → Resources → Network → Enable host networking* turned on; OrbStack and Docker Engine on Linux need nothing ([devcontainer.json](../../.devcontainer/devcontainer.json)).
- **No network from inside kind** after a VM restart, on hosts whose firewall drops forwarded traffic: run `just net-fix`.
- **`context "kind-ghga" does not exist`** after a container rebuild: run `just cluster`, or see the [README](../../README.md#run-the-demo-locally).

## How a change is tested

Each level is defined in the root [AGENTS.md](../../AGENTS.md#test-levels) and the area files it links.

- **Member unit tests** (pytest, `just test <member>`) are the default.
  A service's suite gets real Kafka, MongoDB and S3 from testcontainers, so persistence and event handling are tested there.
- **Consumers of a library:** after a change under `libs/`, run `just affected` and test what it lists.
- **Chart tests** (`just charts-test`, `just demo-template`) render the charts; run them for any change under `deploy/`.
- **Front-end tests** are Vitest unit tests (`just fe-test`) and Playwright smoke tests against mocked APIs ([data portal README](../../frontend/data-portal/README.md#test-levels)).
- **The test bed** (`just testbed`) runs the whole platform on kind, and is the only level that checks a flow across services.
  It is slow to set up; run it locally when your change crosses services, following the [walkthrough](../../README.md#run-the-test-bed-locally).

CI runs the same levels: `ci.yaml` lints the whole repo and tests the affected members, and `integration.yaml` runs the test bed on every pull request with relevant changes.

## How it ships

There are two release lanes, and a member's `[tool.ghga]` markers put it on one.
The platform lane releases the services, the front end and a few other members together: a `ghga/X.Y.Z` tag on `main` builds every image and chart with one version, and `ghga/X.Y.Z-rc.N` on `dev` builds a release candidate.
The PyPI lane publishes libraries and public CLIs, each with its own version, by a `name/x.y.z` tag on `main`.
A tag push builds and verifies; publishing is a separate, deliberate step ([releases.md](../releases.md), [conventions](../conventions.md#versioning--releases)).

## What to read next

In this order:

1. **[Architecture overview](../architecture/overview.md)**, sections 3.1 to 3.7, for how the repo is built and why.
2. **[Metadata and file journeys](../architecture/metadata-and-file-journeys.md)**, for how metadata and files flow across the services.
   Read it before you change submission, upload, file mapping or serving.
3. **[The ADR index](../README.md#decisions-adrs)**, for the decisions and their reasons; skim the titles and read those in your area.
4. **[Conventions](../conventions.md)** and the **[writing style](../style.md)**, for names, branches, versions and how docs, comments and pull requests are written.
5. **The README and `AGENTS.md` of your area**: [`services/`](../../services/AGENTS.md), [`libs/`](../../libs/AGENTS.md), [`deploy/`](../../deploy/AGENTS.md), [`testbed/`](../../testbed/AGENTS.md) or [`frontend/data-portal/`](../../frontend/data-portal/AGENTS.md).
   The `AGENTS.md` files are written for coding agents, but their rules hold for people too.

If you work with a coding agent, read [using-agents.md](using-agents.md) next.
