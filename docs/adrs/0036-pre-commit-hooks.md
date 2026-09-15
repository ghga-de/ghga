# ADR-0036 — One pre-commit configuration for both stacks

- **Status:** accepted
- **Date:** 2026-08-21

## Summary

In the context of **a polyglot monorepo that lost the git hooks of both its predecessors
in the import**

facing **one hook manager that must serve `uv` and `pnpm`, and checks that were simple
in one repository but not in a monorepo**

we decided for **one root `pre-commit` configuration whose tools come from the
lockfiles, with mypy run per member including its tests, and front-end checks that never
rewrite files**

and neglected **husky at the root, pinned hook mirrors, one configuration per stack, and
shfmt**

to achieve **commits gated by the same tools, at the same versions, as CI, before
anything is pushed**

accepting that **hooks need both workspaces installed, and hook versions move only with
the lockfiles**.

## Details

### Context

Each Python repository carried a `.pre-commit-config.yaml` synced from the template,
which the import stripped. The data portal used husky, whose hook never ran in the
monorepo because husky does not install unless `.git` sits directly above it.
`pre-commit` was already a development dependency; the configuration was missing.

A monorepo adds its own problems: whitespace hooks meet generated chart output,
`check-yaml` meets Go-templated Helm manifests, and mypy meets many members that each
carry a `tests` package.

### Decision

- **One `.pre-commit-config.yaml` at the root** covers both stacks.
- **Hook tools come from the lockfiles.** ruff, mypy, prettier and eslint are local
  hooks that run through `uv run` and `pnpm exec`, so a commit is gated by the version
  that `just` and CI use. Only the generic `pre-commit-hooks` repository is pinned.
- **mypy runs per member, never per file**, since its result depends on the set of paths
  it is given. `scripts/typecheck.py` checks a member's `src` and tests in one
  invocation and serves the hook, `just typecheck` and CI alike. The hook checks the
  members a commit touches; their dependents are CI's job.
- **Tests are type-checked like `src/`**, except for `method-assign`, because
  monkeypatching a method is routine in tests.
- **Front-end hooks check and do not fix**, as the data portal's hook did; ruff keeps
  its autofix.
- **Generated output is fixed at its source.** The chart generator emits files the
  whitespace hooks accept, and CI checks that regenerating the charts changes nothing.
- **`no-commit-to-branch`** guards `main` and `dev`.

Each exclusion carries its reason in the configuration.

### Consequences

- Commits get the checks CI runs before the push. CI's `hygiene` job runs the remaining
  hooks over the whole tree.
- Hooks need both workspaces installed (`just sync`, `just fe-install`); the
  devcontainer does that.
- Hook versions change only with `uv.lock` and `pnpm-lock.yaml`; `pre-commit autoupdate`
  covers only the pinned repository.
- Type-checking the tests found no runtime bugs, mostly stale ignore comments and wrong
  annotations. Its value is that tests keep compiling against the API they exercise.
- `docs/epics/` is exempt from the whitespace hooks, since it is imported history.

### Alternatives

- **husky at the root.** Puts an npm toolchain in charge of hooks for some twenty Python
  members, while `pre-commit` is already the GHGA convention.
- **Pinned ruff and mypy mirrors.** They drift from `uv.lock`, and `mirrors-mypy` cannot
  load the `pydantic.mypy` plugin the configuration needs.
- **One configuration per stack.** Only one can own `core.hooksPath`.
- **Excluding generated charts from the whitespace hooks.** Leaves hundreds of files
  unchecked to avoid a one-time fix.
- **mypy in CI only.** Type errors are expensive to find late, and a per-member run
  takes under a second.
- **shfmt as a hook.** Would rewrite a third of the shell lines for no correctness gain,
  and cannot reach the justfile's recipe bodies; shellcheck covers correctness.
