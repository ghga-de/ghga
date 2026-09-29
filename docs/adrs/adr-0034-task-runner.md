---
status: accepted
date: 2026-06-30
tags: [build]
---

# ADR-0034 — Task runner: `just`, with `moon` as a later option

## Summary

In the context of **a repository spanning `uv`, `pnpm`, Helm and shell tooling**

facing **the need for one set of commands across languages, while CI's slowest steps are
image builds and cluster start-up**

we decided for **`just` as a thin facade over the native tools and the affected-target
script, deferring `moon`**

and neglected **`moon` now, `turbo` and `make`**

to achieve **discoverable commands with no build-graph concepts to learn**

accepting that **there is no task caching across languages**.

## Details

### Context

We want the same few commands, such as test, lint, build, image and up, across
languages. `uv` and `pnpm` already cache their own work, and an affected-target script
already existed. What a heavier runner such as `moon` or Bazel adds is caching and an
affected graph across languages, but CI's slowest steps are image builds and cluster
start-up, which task caching does not speed up.

### Decision

`just` recipes wrap `uv`, `pnpm`, `helm` and the repo's scripts, and the docs point to
them. Affected-target detection stays in `scripts/affected_targets.py`, called from CI
and from `just affected`. We adopt `moon` only if caching or affected detection becomes
a measured bottleneck.

### Consequences

- Commands are simple and discoverable: `just` lists them.
- Recipes carry ordering and environment details, so people and agents should use them
  rather than the raw commands.
- There is no task caching across languages.
- The recipes map onto `moon` tasks if we switch.

### Alternatives

- **`moon` now.** Real caching and affected detection, but configuration and learning
  cost for a benefit we cannot yet measure.
- **`turbo`.** Centred on JavaScript, a poor fit for a mostly Python repo.
- **`make`.** Available everywhere, but awkward for recipes with arguments across
  languages.
