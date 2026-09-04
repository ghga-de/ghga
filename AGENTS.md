# Agent Instructions for the GHGA Monorepo

The primary AI entrypoint for any coding agent in this repository. What
the repository is, its layout, and how to run the demo and test bed are documented in
the [README](README.md); this file adds only the rules the README and `docs/`
do not carry.

## Instruction source of truth

- `AGENTS.md` (this file) is the canonical AI entrypoint, covering project-wide concerns.
- For any work under `frontend/data-portal/`, read
  [frontend/data-portal/AGENTS.md](frontend/data-portal/AGENTS.md) first.
- `README.md` and the files in `docs/` are authoritative for humans and agents alike.
- Keep tool-specific entry files (`CLAUDE.md`, `.github/copilot-instructions.md`) short
  and linking back here; do not duplicate AI guidance across files.

## Prime Directive

- You are an expert in Python microservice development (event-driven, hexagonal
  architecture), Kubernetes/Helm delivery integration, and Angular in `frontend/`.
- Prefer small, safe, reviewable diffs.
- Preserve existing architecture and patterns unless otherwise asked; check the
  [ADRs](docs/adr/) records before proposing a structural change.
- Optimize for correctness, maintainability, and testability over cleverness.

## Tech stack

- Python 3.12+, one `uv` workspace spanning `libs/`, `services/`, `tools/`, a single
  `uv.lock`, internal libraries consumed from source (HEAD is always integrated)
- Services: FastAPI + Pydantic on `hexkit` (ports-and-adapters; Kafka, MongoDB, S3
  providers); most run as a rest + consumer pair
- Lint/format: `ruff` · typecheck: `mypy` · unit tests: `pytest`, each configured
  **once**, in the root `pyproject.toml`
- Front end: Angular 22 with its own `pnpm` workspace and lockfile (not a uv member)
- Delivery: Helm charts generated from workspace metadata; demo and integration test
  bed run the same umbrella chart on a local kind cluster
- Integration tests: pytest-bdd feature files + Playwright (`testbed/`)
- Task runner: `just` (see [Repo commands](#repo-commands-just))

## Repo layout

The layout table lives in the [README](README.md#layout). Beyond it:

- `frontend/data-portal/` carries its own `AGENTS.md`, which governs all work there.
-  See [docs/conventions.md](docs/conventions.md) for markers, versioning, and the
  `name/x.y.z` release-tag scheme.

## Where to read

The core docs (architecture overview, ADRs, migration runbook) are listed in the README's
[Where to read](README.md#where-to-read). Branch-specific required reading:

- [docs/architecture/metadata-and-file-journeys.md](docs/architecture/metadata-and-file-journeys.md:
how metadata and files flow.
- [deploy/README.md](deploy/README.md): how the chart system works.

## Development environment

The devcontainer (`.devcontainer/`) is the intended environment: it provisions uv, pnpm,
`just`, kind, kubectl/helm, and docker-in-docker, and the demo/test-bed cluster lives in
its docker daemon. Run repo tooling inside the devcontainer; when the environment doesn't match,
ask rather than installing host tooling or patching scripts around the mismatch.

## Repo commands (just)

Everything runs through `just`, documented by `just` itself and by the README's
[Recipe reference](README.md#recipe-reference) plus its[demo](README.md#run-the-demo-locally)
and [test bed](README.md#run-the-test-bed-locally) walkthroughs (Playwright traces for
failing browser tests, `just logs`). Read commands from there, and prefer the recipes over
raw uv/pnpm/helm/kubectl — they encode ordering and environment details the raw commands miss.

Further rules:

- Always scope test runs to the member you touched (e.g. `just test services/auth-service`);
a bare `just test` runs every suite in the workspace..
- Use `just affected [base]` to decide what to test when a change may cross members.
- Use `just fe-dev` for the front-end dev server, bare `pnpm start` skips the
  `config.js` generation the launcher does. For anything beyond the `just fe-*`
  recipes, work in `frontend/data-portal` under its own `AGENTS.md`.

## Test levels

- **Member unit tests** (pytest, in each member's `tests/`): the default.
hexkit's testcontainers-based testutils make real Kafka/MongoDB/S3 available here,
persistence and event handling are unit-testable per service.
- **Chart tests** (`just charts-test`, `just demo-template`): render-level checks that
  the chart library and the umbrella produce valid manifests.
- **Test bed** (`testbed/`, `just testbed`): pytest-bdd + Playwright against the full
  platform on kind. It is the only level that can verify a cross-service flow end to end
  (events consumed, projections updated, files actually served). Setup, scoping, and resets
  are in the README's [test-bed walkthrough](README.md#run-the-test-bed-locally).
- **Front-end levels** (Vitest unit tests, Playwright smoke tests against MSW mocks) are
  defined in [frontend/data-portal/AGENTS.md](frontend/data-portal/AGENTS.md). For the flows
  whose outcome depends on backend state changing belong here in the test bed.

The test bed is **not** a uv workspace member: it runs from its own `.venv-testbed`
(`just testbed-install`) while shelling out to the workspace-built `ghga-connector` and
`ghga-datasteward-kit`.

## Execution policy

- For code changes, run the smallest relevant validation first (the touched member's
tests, `just lint`), then widen via `just affected` when the change crosses members
editing a `libs/` member affects every consumer.
- For documentation-only changes, test runs are optional unless requested.
- Do not create commits or branches unless explicitly requested.

## Definition of done

1. Unit tests cover the change and the touched member's suite passes
   (`just test <member>`), with `just lint` clean.
2. `just affected` is green when the change crosses members; editing a `libs/` member
   means every consumer.
3. Generated artifacts are regenerated, never hand-edited (`just charts`, `just lock`).
4. The feature branch is peer reviewed and meets every requirement of the story.

## Generated artifacts

- `deploy/charts/<service>/` charts are **generated**, never edit them by hand; change
  the generator (`deploy/src/`) or the member's `chart-values.yaml` and run
  `just charts`. `ghga-common`, `ghga-demo`, and `aai` are hand-maintained.
- `uv.lock` is updated only via `just lock` (or `uv` itself), never by hand.
- The test-bed artifact model overlay (`values-artifacts.yaml`) is derived by
  `just testbed-artifacts`, not committed.
- Front-end generated directories are listed in its own `AGENTS.md`.

## Python best practices

- The root `pyproject.toml` is the single source of truth for ruff/mypy/pytest
  configuration, never add per-member tool config.
- Match the member's existing patterns: hexkit ports/adapters, Pydantic
  settings-from-env config, dependency injection.

### Docstrings

Explain a function's purpose shortly; add detail only where the code doesn't
already make it obvious.

- **Document**: public functions and classes; non-obvious behaviour or side effects;
  business logic that needs context.
- **Skip**: anything already clear from naming and type hints; parameter names/types,
  return types, obvious behaviour. Document those only when the signature isn't clear.
- **Cover**: the *what* in natural language; constraints, side effects, and edge cases;
  the *why*/*how* when non-obvious.
- Follow the established (simplified Google style) Docstring format already in this repo.


## AI agent integration

- `AGENTS.md` files are the shared instruction source for all coding agents: this one for
  the monorepo, the nested one for the data portal.
- Project skills live in `.claude/skills/` directories (the data portal ships an
  `angular-developer` skill); prefer them for reusable task procedures, and keep
  always-on rules in the `AGENTS.md` files.
- The data portal's `CLAUDE.md` documents its MCP setup (`angular-cli`, `context7`);
  there is no monorepo-level MCP configuration.
