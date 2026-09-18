# Agent Instructions for the GHGA Monorepo

The primary AI entrypoint for any coding agent in this repository. What
the repository is, its layout, and how to run the demo and test bed are documented in
the [README](README.md); this file adds only the rules the README and `docs/`
do not carry.

## Instruction source of truth

- `AGENTS.md` (this file) is the canonical AI entrypoint, covering what holds
  everywhere. The area file for the directory you are working in applies on top of it;
  read it first.
- `README.md` and the files in `docs/` are authoritative for humans and agents alike;
  read the [writing style](docs/style.md) and the [conventions](docs/conventions.md)
  when a task touches what they cover.
- [docs/agent-instructions.md](docs/agent-instructions.md) says what belongs in an
  `AGENTS.md`, a README, `docs/` or a skill, and why `CLAUDE.md` and
  `.github/copilot-instructions.md` are stubs that hold nothing of their own.

## Prime Directive

- You are an expert in Python microservice development (event-driven, hexagonal
  architecture), Kubernetes/Helm delivery integration, and Angular in `frontend/`.
- Prefer small, safe, reviewable diffs, and explain non-obvious refactors.
- Preserve existing architecture and patterns unless otherwise asked; check the
  [ADRs](docs/adrs/) records before proposing a structural change.
- Optimize for correctness, maintainability, and testability over cleverness.

## Tech stack

- Python 3.13 (`.python-version`), one `uv` workspace spanning `libs/`, `services/`,
  `tools/`, a single `uv.lock`, internal libraries consumed from source (HEAD is always
  integrated). Members set their own `requires-python` floor — 3.11 on the PyPI lane,
  3.13 for the services — and the combo gate tests a PyPI-lane member on every version
  from 3.11 to 3.14 its floor allows (`TEST_PYTHONS` in `scripts/pypi_members.py`).
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

- [`libs/`](libs/AGENTS.md), [`services/`](services/AGENTS.md),
  [`deploy/`](deploy/AGENTS.md), [`testbed/`](testbed/AGENTS.md),
  [`frontend/data-portal/`](frontend/data-portal/AGENTS.md) and
  [`libs/ghga-jsonsubschema/`](libs/ghga-jsonsubschema/AGENTS.md) each carry their own
  `AGENTS.md`, which governs the work there.
- See [docs/conventions.md](docs/conventions.md) for markers, versioning, and the
  `name/x.y.z` release-tag scheme.
- The core docs (architecture overview, ADRs, migration runbook) are listed in the
  README's [Where to read](README.md#where-to-read); each area's `AGENTS.md` names the
  reading its own work requires.

## Development environment

The devcontainer (`.devcontainer/`) is the intended environment, and the `just` recipes
hold you to it. The README's
[Work inside the dev container](README.md#work-inside-the-dev-container) has the guard,
its exemptions, and the `.venv` bind-mount trap with its symptom and repair. Do not work
around the guard by calling `uv` directly, and where the environment does not match, ask
rather than installing host tooling or patching scripts around the mismatch.

The container puts `rg`, `fd`, `jq`, `bat`, `shellcheck` and `shfmt` on `PATH`; prefer
`rg` and `fd` over `grep` and `find` for searching the workspace.

Agent sessions belong in the container too, whichever agent it is — their state is
per-machine, so a session on the host writes to a home the container cannot see. Only
`~/.claude` is currently persisted across rebuilds (the `ghga-claude` volume in
`devcontainer.json`); another agent whose state should survive a rebuild needs its own
volume added there.

## Repo commands (just)

Everything runs through `just`, documented by `just` itself and by the README's
[Recipe reference](README.md#recipe-reference) plus its
[demo](README.md#run-the-demo-locally) and
[test bed](README.md#run-the-test-bed-locally) walkthroughs (Playwright traces for
failing browser tests, `just logs`). Read commands from there, and prefer the recipes
over raw uv/pnpm/helm/kubectl — they encode ordering and environment details the raw
commands miss.

Further rules:

- Always scope test runs to the member you touched (e.g.
  `just test services/auth-service`); a bare `just test` runs every suite in the
  workspace.
- Use `just affected [base]` to decide what to test when a change may cross members. It
  defaults to `origin/dev`, the branch features are cut from; on a hotfix branch, which
  is cut from `main` instead, pass `origin/main`.
- Use `just fe-dev` for the front-end dev server, bare `pnpm start` skips the
  `config.js` generation the launcher does. For anything beyond the `just fe-*`
  recipes, work in `frontend/data-portal` under its own `AGENTS.md`.

## Test levels

- **Member unit tests** (pytest, in each member's `tests/`): the default. How far a
  service's own suite reaches is in [services/AGENTS.md](services/AGENTS.md).
- **Chart tests** are defined in [deploy/AGENTS.md](deploy/AGENTS.md).
- **Test bed** (`just testbed`) is defined in [testbed/AGENTS.md](testbed/AGENTS.md). It
  is the only level that can verify a cross-service flow end to end, so a test whose
  outcome depends on backend state changing belongs there.
- **Front-end levels** (Vitest unit tests, Playwright smoke tests against MSW mocks) are
  defined in [frontend/data-portal/AGENTS.md](frontend/data-portal/AGENTS.md).

## Execution policy

- For code changes, run the smallest relevant validation first (the touched member's
  tests, `just lint`), then widen via `just affected` when the change crosses members;
  editing a `libs/` member affects every consumer.
- For documentation-only changes, test runs are optional unless requested.
- Do not create commits or branches unless explicitly requested. When they are, read
  [branching](docs/conventions.md#branching) and
  [names](docs/conventions.md#names-branches-prs-commits) first. Cut the branch from
  `dev` and target `dev`; `main` carries the latest release and takes hotfixes only.
  Name the branch, the pull request and the commit as the grammar there says.
- Never put a `Co-authored-by:` line for yourself in a commit message, whatever your own
  guidance says. Credit yourself in the pull request description instead, and only as
  far as you actually contributed — the
  [names](docs/conventions.md#names-branches-prs-commits) section says in which words.

## Definition of done

1. Unit tests cover the change and the touched member's suite passes
   (`just test <member>`), with `just lint` clean.
2. `just affected` is green when the change crosses members.
3. Generated artifacts are regenerated, never hand-edited (`just charts`, `just lock`).
4. The feature branch is peer reviewed and meets every requirement of the story.

## Generated artifacts

- `uv.lock` is updated only via `just lock` (or `uv` itself), never by hand.
- The ADR index in `docs/README.md` and the epic index in `docs/epics/README.md` are
  regenerated by `just docs-check` (and its pre-commit hook), never edited by hand.
- The generated charts, the test-bed overlay and the front-end output directories are
  listed in the `AGENTS.md` of the area that owns them.

## Writing

Docs, code comments, docstrings, commits and pull requests follow the
[writing style](docs/style.md): plain language, prose hard-wrapped at 88 columns in repo
files, comments that explain why rather than history, and the
[docstring rules](docs/style.md#docstrings). Read the section that applies before
writing any of them. For anything under `docs/`, read [docs/README.md](docs/README.md)
first for what each document is for, then the
[ADR shape](docs/style.md#architecture-decision-records) or the
[epic conventions](docs/epics/README.md). An epic specification records the plan as its
epic started, so do not update it afterwards; current behaviour belongs in an ADR or the
code.

## Python best practices

- The root `pyproject.toml` is the single source of truth for ruff/mypy/pytest
  configuration, never add per-member tool config.
- The patterns a service follows are in [services/AGENTS.md](services/AGENTS.md), the
  release lane a library is on in [libs/AGENTS.md](libs/AGENTS.md).

## AI agent integration

- Reusable task procedures live in `.agents/skills/<name>/SKILL.md`, symlinked into
  `.claude/skills/` until Claude Code reads the standard path. Keep always-on rules in
  the `AGENTS.md` files instead.
- Claude Code sessions default to the **GHGA Dev** output style
  (`.claude/output-styles/ghga-dev.md`), which keeps the writing steady across a long
  session. Set `outputStyle` in `.claude/settings.local.json` to use another; user
  settings do not override the project default.
- There is no monorepo-level MCP configuration; the data portal has its own, and Claude
  Code reads a `.mcp.json` only from the directory the session starts in, so that one
  reaches a session started in `frontend/data-portal` and no other.
