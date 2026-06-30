# ADR-0001 — Consolidate GHGA repositories into one polyglot monorepo

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
GHGA maintains ~30 repositories. ~25 are generated from `microservice-repository-template`
and kept consistent by a `.template/` file-sync mechanism: lists of static / mandatory /
deprecated files, a `update_template_files.py` script that pulls files from the template's
`main` via raw GitHub URLs, and a per-repo CI check that fails when a repo drifts.

This "virtual monorepo via continuous templation" works but has real costs:
- every toolchain change (ruff/mypy/CI/Dockerfile) must propagate to ~25 repos;
- cross-cutting changes (e.g. a new `ghga-event-schemas` major) span many PRs across many
  repos and are never atomic;
- integration is implicit — there is no single place where "all of GHGA builds and tests
  together", which is why live version skew exists (see [ADR-0002](0002-uv-workspace-source-coupled-libs.md)).

`file-services-backend` already demonstrates that a GHGA Python monorepo is viable and pleasant.

## Decision
We will consolidate the GHGA applications (services, libraries, CLIs, and the Angular front
end) into **one polyglot monorepo** and **retire** `microservice-repository-template` and the
`.template/` sync. The shared toolchain is defined **once at the repo root**.

## Consequences
- One place to make and verify cross-cutting changes; the `.template/` machinery and its
  per-repo CI checks disappear.
- A single CI/CD definition replaces ~25 copies.
- Larger repo, more contributors in one place → mitigated by affected-target CI and CODEOWNERS.
- Commit history of the imported repos is preserved (see [ADR-0010](0010-history-preserving-migration.md)),
  but commit SHAs change and old PR cross-references become dangling.
- The template repo's history stays on `ghga-de` for provenance.

## Alternatives considered
- **Keep the template + sync.** Rejected: it is precisely the maintenance burden we want gone,
  and it cannot make integration atomic.
- **Polyrepo with a meta-build tool (e.g. Bazel across repos).** Rejected: heavier, and does
  not give a single integrated `HEAD`.
