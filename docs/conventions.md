# Monorepo conventions

Quick reference for how the repo is organised and what is automated from metadata. See the
[ADRs](adr/) for the rationale.

## Layout & placement

- `libs/` · `services/` · `tools/` are `uv` workspace members; `frontend/` is the JS toolchain;
  `deploy/` (charts), `testbed/`, `docker/`, `scripts/`, `docs/` are support.
- Members are placed by **primary identity**, not by capability — a `libs/` member can still
  produce an image; a `tools/` member can still be a workspace dependency
  ([ADR-0014](adr/0014-capability-markers-and-placement.md)).

## `[tool.ghga]` capability markers

Each member declares what artifacts it produces in its own `pyproject.toml`. The build,
chart-generation, and release pipelines key off these — **not** off the folder.

```toml
[tool.ghga]
release = "platform"  # release lane: "platform" (lockstep) | "pypi" | "none"
image = true    # build & push a container image (and generate a Helm chart) on the release tag
pypi  = true    # publish a wheel to PyPI on the release tag
cli   = true    # exposes a console entry point

# optional, when image = true:
executable = "auth-service"   # console script used as the image ENTRYPOINT
roles = ["rest", "consumer"]  # deployment roles (distinct service_instance_id per role)
```

Directories supply the defaults, so a marker is only written where a member deviates:
`services/*` and `frontend/*` default to the platform lane with an image, `libs/*` to the
PyPI lane, `tools/*` to no lane at all
([ADR-0014](adr/0014-capability-markers-and-placement.md)).

Examples: `libs/hexkit` → `{pypi}` and `services/auth-service` → `{platform, image}`, both by
default; `libs/metldata` → `{platform, image}` (a library that is also deployed);
`libs/ghga-event-schemas` → `{none}` (embedded in the images, never published on its own);
`tools/ghga-connector` and `tools/ghga-transpiler` → `{pypi, cli}` (public CLIs opting in).

## Internal dependencies

Consume internal libraries **from source**:

```toml
[tool.uv.sources]
hexkit = { workspace = true }
ghga-event-schemas = { workspace = true }
```

One `uv.lock` governs the whole repo → HEAD is always integrated
([ADR-0002](adr/0002-uv-workspace-source-coupled-libs.md)).

## Branching

Two long-lived branches ([ADR-0020](adr/0020-branching-strategy.md)): **`dev`** is the
integration branch and the repo default, **`main`** is the latest platform release — its HEAD
is always a released state.

- **Cut feature branches from `dev` and merge them back into `dev`** via pull request. That is
  the default for everything; `just affected` compares against `origin/dev` for the same reason.
- **Pull requests are squashed** — one pull request, one commit on `dev`. Rebase merges are off.
- **Hotfixes are the exception:** branch from `main`, merge back into `main`, release, then
  merge `main` back into `dev` so the fix survives the next release.
- **Release:** `dev` is merged into `main` with a merge commit (never squashed or rebased —
  that is why "Require linear history" is off for `main`).
- Committing directly to either branch is blocked by `no-commit-to-branch`
  ([ADR-0018](adr/0018-pre-commit-hooks.md)).

Which branch a tag is cut on is **enforced** by `release.yaml`, per lane — it tests membership
of the branch's first-parent chain, so a back-merge does not launder a tag onto the wrong lane:

| tag | cut on | lane |
|---|---|---|
| `ghga/X.Y.Z` | `main` | platform release |
| `ghga/X.Y.Z-rc.N` | `dev` | release candidate — hotfixes get none, so this is `dev`-only |
| `name/x.y.z`, `packages/x.y.z` | `main` | PyPI, deliberately in lockstep with the platform release |

### Names: branches, PRs, commits

A change carries three names, all derived from one grammar
([ADR-0022](adr/0022-naming-branches-prs-commits.md)):

| | in a stack | solo |
|---|---|---|
| branch | `<stack>/<kind>/<description>` | `<kind>/<description>` |
| PR title | `[<stack>] <Description> (<ISSUE>)` | `<Description> (<ISSUE>)` |
| commit | `<type>(<stack>): <description> (#<PR>)` | `<type>: <description> (#<PR>)` |

A **stack** is a chain of PRs, each based on the previous one and rooted at `dev`. GitHub does
not model that, so the stack name — one or two words, naming the stack and not the member —
is what holds it together in the PR list. Branch names are lowercase kebab-case, PR titles are
prose. The YouTrack key goes in front of the description, or in front of the stack name when
the issue covers the whole stack: `upload/feat/GSI-1234-add-ucs-endpoints` versus
`GSI-1234-upload/feat/add-ucs-endpoints`. Both are titled `[upload] Add UCS endpoints
(GSI-1234)`.

| kind | for | cut from | commit type |
|---|---|---|---|
| `feat` | new functionality | `dev` | `feat` |
| `fix` | bug fix on unreleased work | `dev` | `fix` |
| `hotfix` | fix against the latest release | `main` | `fix` |
| `docs` | documentation, ADRs, READMEs | `dev` | `docs` |
| `refactor` | behaviour-preserving restructuring | `dev` | `refactor` |
| `test` | test bed, test tooling, test-only changes | `dev` | `test` |
| `chore` | tooling, CI, dependencies, charts — and anything not clearly one of the above | `dev` | `chore` |

`hotfix` is the only kind that names its base branch; the rest are labels. There is deliberately
no `release` kind — a release is a merge plus a tag.

**At merge time** the commit message is written by hand, because neither prefill is right:
subject imperative and lower case, 52 characters where it fits and 72 at the outside, counting
the ` (#<PR>)` GitHub appends; body is the PR description cut to three to five bullets, wrapped
at 72. Mark a breaking change `feat(upload)!:` with a `BREAKING CHANGE:` footer. Do not repeat
the YouTrack key — `(#<PR>)` leads to it.

`renovate/*` and `automated/*` are owned by Renovate and the nightly security scan. Nothing
enforces the convention, and branches already in flight are not renamed.

## Versioning & releases

- Every member keeps its own semver (in `pyproject.toml` / `Chart.yaml` / `package.json`).
- A pushed git tag **`name/x.y.z`** releases only that component; CI asserts the tag matches the
  member's version at HEAD ([ADR-0004](adr/0004-versioning-and-release-by-tag.md)).
- A pushed git tag **`packages/x.y.z`** releases every PyPI-lane member the index is behind
  on, dependencies first; the version is a label naming no member
  ([ADR-0004](adr/0004-versioning-and-release-by-tag.md)).
- Wheels publish to **PyPI**, rehearsed on **TestPyPI** first, both by trusted publishing.
  Images publish to `docker.io/ghga/<member>` and charts as OCI artifacts under
  `ghga/<chart>-chart` — a tag push builds both; publishing them is a deliberate dispatch
  ([ADR-0004](adr/0004-versioning-and-release-by-tag.md)).

## Toolchain

- One `ruff` / `mypy` / `pytest` config at the repo root (in `pyproject.toml`); no per-member
  copies (the old `.template/` sync is retired).
- `just` is the task facade ([ADR-0015](adr/0015-task-runner.md)); `uv` manages Python 3.13.
- One `.pre-commit-config.yaml` at the root covers **both** stacks
  ([ADR-0018](adr/0018-pre-commit-hooks.md)). `just hooks` installs it, `just hooks-all` runs
  everything. The ruff / mypy / prettier / eslint hooks take their version from `uv.lock` and
  `pnpm-lock.yaml`, not from a `rev:` pin, so a hook can never disagree with CI.
- mypy runs per member (`src` + tests) via `scripts/typecheck.py` — the same runner behind
  `just typecheck`, the hook, and CI. Never `mypy .`: the members' `tests` packages collide.
