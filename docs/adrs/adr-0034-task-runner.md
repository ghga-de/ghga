---
status: accepted
date: 2026-06-30
tags: [build]
---

# ADR-0034 — Task runner: `just`, with `moon` as a later option

## Summary

In the context of **a repository spanning `uv`, `pnpm`, Helm and shell tooling**

facing **the need for one set of commands across languages, while CI's slowest steps are image builds and cluster start-up**

we decided for **`just` as a thin facade over the native tools and the affected-target script, deferring `moon`**

and neglected **`moon` now, `pants`, `mise`, `turbo`, `make` and no runner at all**

to achieve **discoverable commands with no build-graph concepts to learn**

accepting that **there is no task caching across languages**.

## Details

### Context

We want the same few commands, such as test, lint, build, image and up, across languages.
`uv` and `pnpm` already cache their own work, and an affected-target script already existed.
What a heavier runner such as `moon` or Bazel adds is caching and an affected graph across languages, but CI's slowest steps are image builds and cluster start-up, which task caching does not speed up.

The raw commands alone are not enough, because most of them only work correctly with steps run before them.
A test run must first check that the environment matches `uv.lock`, the demo needs charts generated and images loaded into the cluster, and nearly every recipe checks that it is running inside the dev container.
Written in a README, those steps get skipped; written into a recipe, they always run.

`just` meets that need with little to learn.
It is a single binary with no runtime of its own, recipes take named arguments with defaults, and recipes depend on each other.
A recipe can be a multi-line bash script, private recipes hide helpers such as the environment guards, and `just` with no arguments lists every recipe with its comment.
It tracks no files and caches nothing, so there is no hidden state that can make a recipe skip its work.

### Decision

`just` recipes wrap `uv`, `pnpm`, `helm` and the repo's scripts, and the docs point to them.
Affected-target detection stays in `scripts/affected_targets.py`, called from CI and from `just affected`.
We adopt `moon` only if caching or affected detection becomes a measured bottleneck.

### Consequences

- Commands are simple and discoverable: `just` lists them.
- Recipes carry ordering and environment details, so people and agents should use them rather than the raw commands.
- There is no task caching across languages.
- The recipes map onto `moon` tasks if we switch.

### Alternatives

- **`moon` now.**
  Real caching and affected detection, but configuration and learning cost for a benefit we cannot yet measure.
- **`pants`.**
  A build system built around Python, with dependency inference, local and remote caching, affected detection, and Docker and Helm backends.
  It manages Python dependencies in its own resolves and lockfiles and runs pytest in its own sandboxes, so it would replace the `uv` workspace and its single `uv.lock` ([ADR-0026](adr-0026-uv-workspace-source-coupled-libs.md)) instead of wrapping them.
  Its JavaScript backend is experimental, so the Angular build would still run through `pnpm` underneath.
  Rejected for the same reason as `moon`, and ranked behind it, because `moon` runs the native tools as tasks and leaves their configuration alone.
- **`mise`.**
  Pins tool versions, sets environment variables and runs tasks.
  The dev container already provides the tools and `uv` the Python interpreter, so its version management would be a second source that can drift from the first.
  As a task runner alone it offers what `just` does, with tasks in TOML or script files, and brings a tool whose main job we do not need.
  Worth revisiting if we give up the dev container, or if different tool versions in CI and in the container start causing failures.
- **`turbo`.**
  Centred on JavaScript, a poor fit for a mostly Python repo.
- **`make`.**
  Available everywhere, but awkward for recipes with arguments across languages.
- **No runner.**
  Scripts in `scripts/` and commands in the README cost nothing to adopt, but they leave the order of the steps to whoever reads the README, and give no single list of commands.
