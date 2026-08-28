# ADR-0018 — One `pre-commit` config for both stacks

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** Christoph Zwerschke

## Context
The monorepo had no git hooks at all. Both predecessor setups were lost in the import:

- Each of the ~28 Python repos carried a byte-identical `.pre-commit-config.yaml` synced from the
  retired `microservice-repository-template`. `scripts/migration/lib.sh` strips it on import by
  design — one root config was always the intended end state
  ([ADR-0003](0003-repository-scope.md), [runbook §3.3](../migration/runbook.md)).
- The data-portal used husky. Its hook came across but never ran once: husky v9 refuses to install
  when `.git` is not the parent of the husky directory, so `core.hooksPath` stayed unset. It ran a
  `main`-branch guard, `pnpm format:check` and `ng lint`.

Meanwhile `pre-commit` was already a dev dependency and `scripts/affected_targets.py` already
treated `.pre-commit-config.yaml` as a repo-wide trigger. The gap was the config itself.

Two properties make this more than a copy of the template's file. The repo is polyglot, so one hook
manager has to serve `uv` and `pnpm` at once. And it is a *mono*repo, so several checks that were
trivially correct per-repo are not: whitespace hooks meet generated output, `check-yaml` meets 379
Go-templated Helm manifests, and mypy meets 24 members that each carry a `tests` package.

## Decision
We will keep a single `.pre-commit-config.yaml` at the repo root, covering both stacks.

**Hook tools come from the lockfiles, not from `rev:` pins.** ruff, mypy, prettier and eslint are
`repo: local` hooks invoking `uv run` / `pnpm exec`, so the version that gates a commit is by
construction the version `just lint`, `just typecheck`, `just fe-lint` and CI use. The template kept
its pins honest with `scripts/update_hook_revs.py`, which reads a `lock/requirements-dev.txt` that
the single root `uv.lock` replaced; without that script, pinned mirrors would silently drift from
the workspace. Only the generic `pre-commit-hooks` repo, which has no local equivalent, stays
pinned — `just hooks-update` bumps it.

**mypy runs per unit, never per file.** Its answer depends on the set of paths it is handed:
`mypy services/dcs/src` is clean, but adding `libs/ghga-event-schemas/src` to the same invocation
reports an error in dcs that dcs does not have. `mypy .` cannot run at all, because the members'
`tests` packages collide. So `scripts/typecheck.py` maps changed files back to the member that owns
them and checks `<member>/src` plus its test package(s) in one invocation. `just typecheck` and
CI's `check-python` go through the same runner, so the three cannot drift. The hook checks only the
units you touched; the reverse-dependency closure stays CI's job.

**Type-checking covers tests, not just `src/`, with one relaxation.** This is a widening: it
surfaced 183 errors, since fixed. Worth being honest about what they were — **none was a runtime
bug**. The bulk were stale `# type: ignore` comments that `warn_unused_ignores` only flags once a
file is actually checked, and the rest were annotations that lied about the object in hand (a test
double annotated as the port it stands in for, hiding the mock API the tests then use). That is
hygiene, not defect detection. The forward-looking case is the stronger one: tests are code that
has to keep compiling against the API it exercises, so renames and signature changes surface in the
suite instead of at runtime.

Against that, test code legitimately does things the type system dislikes. Monkeypatching a method
onto an instance is a bug in production and routine in a test, and left unchecked it cost a
suppression comment at every patch site — 47 of them across 14 files. So `method-assign` is
disabled for the test packages via `[[tool.mypy.overrides]]`, and those 47 comments are gone.
`attr-defined` deliberately stays on: reaching through a port-typed handle into a private member
needs a suppression, but the same check catches a typo'd or renamed attribute, which is a real
class of bug in test code. (Note that mypy accepts `*` only as a whole module component, so
`tests_*` is rejected and the members whose test package carries their name are listed by hand.)

**The front end is checked, not fixed.** prettier and eslint run with `--check` and without
`--fix`, preserving the data-portal's rule that the hook never rewrites what you are about to
commit. ruff keeps the template's autofix. The asymmetry is deliberate: each stack keeps the
behaviour its contributors already know.

**Generated output is fixed at its source.** The chart generator emitted trailing whitespace and
files without a final newline, which a whitespace hook would strip and the next `just charts` would
restore — forever. `deploy/src/create_charts.py` and the chart templates were changed so
regeneration is idempotent, and CI asserts it stays that way.

**`no-commit-to-branch` guards `main` only.** `dev` and `int` do not exist here; releases are tags
([ADR-0004](0004-versioning-and-release-by-tag.md)).

The exclusions are deliberate and each has a reason recorded in the config: imported epic docs
(hard line breaks), Go-templated Helm manifests, the transpiler's `!!python/object/apply` configs,
one schemapack fixture that is a duplicate-key document on purpose, generated `config_schema.json`,
and JSONC files.

## Consequences
- Commits are gated on the same checks CI runs, per changed file, so the feedback arrives before
  the push rather than after it.
- CI's new `hygiene` job runs the hooks over the whole tree, skipping ruff/mypy/eslint/prettier
  because `lint`, `check-python` and `check-frontend` already run them — the checks are enforced
  once, not twice. It also asserts the charts are reproducible.
- `pnpm format:check` now runs in CI. Prettier was enforced nowhere, which is how the data-portal's
  `chart-values.yaml` drifted out of format.
- Hooks need both workspaces provisioned (`just sync`, `just fe-install`). The dev container does
  this; the front-end hooks fail with a pointer to `just fe-install` rather than a stack trace.
- `pretty-format-json` from the template is dropped: it rewrites 39 tracked files, including ones
  Prettier owns and formats differently. `check-json` still guarantees validity.
- A one-off normalisation commit was unavoidable, and `docs/epics/` is exempt from the whitespace
  hooks rather than rewritten — it is imported history.
- Test code is now type-checked under the same settings as `src/` apart from `method-assign`. If a
  further category turns out to cost suppressions without catching anything, the override is the
  place to record that — one entry per error code, with the reason.
- Hook tool versions can now only be bumped by updating `uv.lock` / `pnpm-lock.yaml`. That is the
  point, but it does mean `pre-commit autoupdate` no longer tells the whole story.

## Alternatives considered
- **Hoist husky to the repo root.** Rejected: it would put an npm toolchain in charge of the hooks
  for ~22 Python members, and `pre-commit` is already the GHGA convention and already a dependency.
- **Keep the template's pinned `ruff-pre-commit` / `mirrors-mypy` mirrors.** Rejected: without
  `update_hook_revs.py` the pins drift from `uv.lock`, giving green-locally/red-in-CI. `mirrors-mypy`
  additionally cannot work here at all — the isolated hook environment cannot import the
  `pydantic.mypy` plugin the root config declares, which is a hard error before any checking.
- **Two configs, one per stack.** Rejected: only one can own `core.hooksPath`.
- **Exclude the generated charts from the whitespace hooks** instead of fixing the generator.
  Rejected: it leaves ~450 tracked files unchecked forever to avoid a one-time fix.
- **Skip mypy in the hook** (leave it to CI). Rejected: type errors are the expensive class to find
  late, and the per-unit runner makes the cost ~0.8 s per touched member.
- **shfmt for the shell scripts.** Rejected, measured rather than assumed. At its friendliest flag
  set (`-i 2 -ci -sr -bn`) it rewrites 5 of the 7 tracked `.sh` files, 134 of their 383 lines — for
  no correctness gain, since shellcheck (which *is* included, and needed three real fixes) covers
  that. Some of its output is worse: in `scripts/migration/lib.sh` it dedents aligned continuation
  comments to column 0, detaching them from the variable they document. And it misses most of the
  target — roughly 302 further lines of shell live in the justfile's recipe bodies, which neither
  it nor shellcheck can parse. The seven scripts are already uniformly 2-space and
  `.devcontainer/post-create.sh` already conforms exactly, so there is no style dispute to settle.
  Revisit only if one appears, or if the justfile recipe bodies ever move into `.sh` files — which
  would flip the coverage argument.
