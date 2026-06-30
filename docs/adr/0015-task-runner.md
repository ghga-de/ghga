# ADR-0015 — Cross-language task runner: `just` now, `moon` later if needed

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
The monorepo spans `uv` (Python), `pnpm` (the Angular front end), Helm, and shell tooling. We
want one-command DX (`test`, `lint`, `build`, `image <svc>`, `up`) across languages. uv and pnpm
already cache their own work, and an affected-target script already exists; the main value a
heavy runner (moon/bazel) would add is cross-language caching + affected-graph — but the actual
CI long pole is image builds + cluster spin-up, which task caching does not address.

## Decision
Start with **`just`** as a thin, discoverable facade over `uv`/`pnpm`/`helm` + the affected
script. Defer adopting **`moon`** until/unless caching + first-class affected detection becomes a
measured bottleneck. Keep affected-target detection in the existing (generalised) script,
invoked from both CI and `just`.

## Consequences
- Immediate, low-magic DX; no new build-graph concepts to learn now.
- No cross-language remote caching yet (acceptable given the image/cluster long pole).
- `moon` remains a clean upgrade path; the `justfile` recipes map onto moon tasks later.

## Alternatives considered
- **`moon` now.** Real polyglot caching/affected, but config + learning cost up front for
  benefit we can't yet measure.
- **`turbo`.** JS-centric; poor fit for a Python-majority repo.
- **`make`.** Ubiquitous but weaker ergonomics for polyglot orchestration.
