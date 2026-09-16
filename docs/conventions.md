# Monorepo conventions

Quick reference for how the repo is organised and what is automated from metadata. See the
[ADRs](adrs/) for the rationale.

## Layout & placement

- `libs/` · `services/` · `tools/` are `uv` workspace members; `frontend/` is the JS toolchain;
  `deploy/` (charts), `testbed/`, `docker/`, `scripts/`, `docs/` are support.
- Members are placed by **primary identity**, not by capability — a `libs/` member can still
  produce an image; a `tools/` member can still be a workspace dependency
  ([ADR-0033](adrs/adr-0033-capability-markers-and-placement.md)).

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
([ADR-0033](adrs/adr-0033-capability-markers-and-placement.md)).

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
([ADR-0026](adrs/adr-0026-uv-workspace-source-coupled-libs.md)).

## Branching

Two long-lived branches ([ADR-0038](adrs/adr-0038-branching-strategy.md)): **`dev`** is
the integration branch and the repo default, **`main`** is the latest platform release —
its HEAD is always a released state.

- **Cut feature branches from `dev` and merge them back into `dev`** via pull request. That is
  the default for everything; `just affected` compares against `origin/dev` for the same reason.
- **Pull requests into `dev` are squashed** — one pull request, one commit. Rebase merges are off.
- **Hotfixes are the exception:** branch from `main`, merge back into `main` with a merge commit
  (`main` takes no squash), release, then merge `main` back into `dev` so the fix survives the
  next release.
- **Release:** `dev` is merged into `main` with a merge commit (never squashed or rebased —
  that is why "Require linear history" is off for `main`).
- **Long-lived feature branches** are allowed, and decided case by case.
- Committing directly to either branch is blocked by `no-commit-to-branch`
  ([ADR-0036](adrs/adr-0036-pre-commit-hooks.md)).

Which branch a tag is cut on is **enforced** by `release.yaml`, per lane — it tests membership
of the branch's first-parent chain, so a back-merge does not launder a tag onto the wrong lane:

| tag | cut on | lane |
|---|---|---|
| `ghga/X.Y.Z` | `main` | platform release |
| `ghga/X.Y.Z-rc.N` | `dev` | release candidate — hotfixes get none, so this is `dev`-only |
| `name/x.y.z`, `packages/x.y.z` | `main` | PyPI, deliberately in lockstep with the platform release |

### Names: branches, PRs, commits

A change carries three names, all derived from one grammar
([ADR-0038](adrs/adr-0038-branching-strategy.md)):

| | in a stack | solo |
|---|---|---|
| branch | `<stack>/<kind>/<description>` | `<kind>/<description>` |
| PR title | `[<stack>] <Description> (<ISSUE>)` | `<Description> (<ISSUE>)` |
| commit | `<type>(<stack>): <description> (#<PR>)` | `<type>[(<member>)]: <description> (#<PR>)` |

A **stack** is a chain of PRs, each based on the previous one and rooted at `dev`. GitHub
supports the stacking but does not yet name a stack, and the PR list cannot yet be grouped or
sorted by one — so the stack name, one or two words and naming the stack rather than the
member, is a workaround that holds it together in the list. The position in the chain is
already shown there, and merging the bottom of a stack renumbers the rest, so it does not
belong in the title. Branch names are lowercase kebab-case, PR titles are
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
no `release` kind — a release is a merge plus a tag. Conventional Commits' `perf`, `ci`, `build`
and `style` are not used; they are `chore`.

**At merge time** the commit message is rewritten, because neither prefill is right — by
whoever merges, or by an agent asked to draft it from the PR:
subject imperative and lower case, ending in ` (#<PR>)` — the prefill supplies it and the
rewrite must keep it — and 52 characters where it fits, 72 at the outside, counting that
suffix; body is the PR description cut to three to five bullets, wrapped at 72. A solo commit
names the member as its scope where one owns the change, and leaves it off where none does. A
hotfix's merge commit is written the same way. Mark a breaking change `feat(upload)!:` with a
`BREAKING CHANGE:` footer, and do not repeat the YouTrack key —
`(#<PR>)` leads to it. **No `Co-authored-by:` line for an agent in a commit**, whatever the
tool says; human co-authors keep their trailers. For branch
`upload/feat/GSI-1234-add-ucs-endpoints`, merged as #207:

```text
feat(upload): add UCS endpoints (#207)

- Add POST /uploads and GET /uploads/{id}
- Resolve the storage alias from the box configuration
- Cover both routes in the UCS API tests
```

**PR descriptions** are written for the reviewer: a few short paragraphs on what changed, why,
and what to look at — not a summary of the diff, and not a report on how the work went. Plain
language, no model register, no walls of text — a description that will not shorten is usually
a PR that should be split into a stack. Emoji are fine here, sparingly, as visual cues
that help a reader scan, and nowhere else — not in branch names, titles or commit messages,
where they are permanent, noisy, and awkward for search and for screen readers.
A coding agent is credited by how much it drafted: "Generated by <agent>" when it drafted most
of the change, "Co-authored by <agent>" when it drafted a substantial part alongside people,
and no line for anything less — suggestions, explanations, reviews, proofreading. `<agent>` is
the tool (Claude Code, Codex, Copilot, …); name the model only where that matters.

`renovate/*` and `automated/*` are owned by Renovate and the nightly security scan. Nothing
enforces the convention, and branches already in flight are not renamed.

## Versioning & releases

How a release runs end to end is in [releases.md](releases.md).

- Every member keeps its own semver (in `pyproject.toml` / `Chart.yaml` / `package.json`).
- A pushed git tag **`name/x.y.z`** releases only that component; CI asserts the tag matches the
  member's version at HEAD ([ADR-0027](adrs/adr-0027-versioning-and-release-by-tag.md)).
- A pushed git tag **`packages/x.y.z`** releases every PyPI-lane member the index is behind
  on, dependencies first; the version is a label naming no member
  ([ADR-0027](adrs/adr-0027-versioning-and-release-by-tag.md)).
- Wheels publish to **PyPI**, rehearsed on **TestPyPI** first, both by trusted publishing.
  Images publish to `docker.io/ghga/<member>` and charts as OCI artifacts under
  `ghga/<chart>-chart` — a tag push builds both; publishing them is a deliberate dispatch
  ([ADR-0027](adrs/adr-0027-versioning-and-release-by-tag.md)).

## Toolchain

- One `ruff` / `mypy` / `pytest` config at the repo root (in `pyproject.toml`); no per-member
  copies (the old `.template/` sync is retired).
- `just` is the task facade ([ADR-0034](adrs/adr-0034-task-runner.md)); `uv` manages Python 3.13.
- One `.pre-commit-config.yaml` at the root covers **both** stacks
  ([ADR-0036](adrs/adr-0036-pre-commit-hooks.md)). `just hooks` installs it, `just hooks-all` runs
  everything. The ruff / mypy / prettier / eslint hooks take their version from `uv.lock` and
  `pnpm-lock.yaml`, not from a `rev:` pin, so a hook can never disagree with CI.
- mypy runs per member (`src` + tests) via `scripts/typecheck.py` — the same runner behind
  `just typecheck`, the hook, and CI. Never `mypy .`: the members' `tests` packages collide.
