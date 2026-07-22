# ADR-0010 — History-preserving migration with one-way incremental sync

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
The monorepo is developed **separately from mainline (`ghga-de`) for a while** before any
commitment. Mainline keeps committing daily during this window. The code migration must be
**history-preserving**, and the monorepo must be able to catch up to mainline at cutover.

## Decision
- **Host the monorepo at `github.com/ghga-de/ghga`** — a new repo, developed separately from the
  existing per-component repos until cutover.
- **Publish targets (images, charts, PyPI) are not yet decided.** Until they are, the release
  workflow stays dormant: no triggers, no publish steps, no write permissions. Nothing is
  published from this repo. PyPI is not needed meanwhile because internal deps are consumed as
  source ([ADR-0002](0002-uv-workspace-source-coupled-libs.md)); note that PyPI's global
  namespace also constrains reusing prod lib names, so that choice needs care at cutover.
- **Import with `git filter-repo`**, per the manifest
  [scripts/migration/repos.tsv](../../scripts/migration/repos.tsv): move each repo into its
  destination subdir **and drop centralised boilerplate** (`lock/`, `.github/`, `.template/`,
  `.pyproject_generation/`, `.readme_generation/`, `scripts/`, `Dockerfile*`,
  `.pre-commit-config.yaml`, per-service `.devcontainer/`). Keep `src/`, `tests/`, service
  config, and `pyproject.toml`. Drop historical release tags (originals remain on `ghga-de`).
  `file-services-backend` is imported by flattening its `services/*` to top-level.
- **One-way incremental sync** until cutover: `git filter-repo` is deterministic, so re-running
  it on append-only mainline yields the same SHAs for old commits and new SHAs only for new
  ones; a `fetch` + `merge` brings in just the delta. Dropped paths cannot conflict; the
  conflict surface is reduced to each service's `pyproject.toml` (`[tool.uv.sources]` block).

**Rules during the window:** harmonise only at the **root** (workspace, lock, CI, Dockerfile,
charts); never restructure a service's `src/`; keep libs' own `pyproject.toml` aligned with
mainline (workspace wiring lives in the root pyproject + consumers' `[tool.uv.sources]`).

## Consequences
- Full history, authorship, and dates preserved; `git blame`/`log` follow files into subdirs.
- Commit SHAs change; old PR cross-references (`#NNN`) become dangling. Originals stay on
  `ghga-de`.
- Sandbox is fully isolated from production releases.
- A `scripts/migration/sync-from-mainline.sh` run periodically keeps the gap small; cutover is
  a final sync + freeze + flip of CD targets ([runbook](../migration/runbook.md)).

## Alternatives considered
- **One-time snapshot then diverge.** Rejected: catch-up cost grows with time.
- **Continuous bidirectional mirror (josh).** Rejected: overkill for a temporary evaluation.
- **`git subtree`.** Viable and has built-in incremental pulls, but produces messier history
  and worse blame across the import boundary than `filter-repo`.
