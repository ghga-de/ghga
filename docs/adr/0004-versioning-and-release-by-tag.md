# ADR-0004 — Versioning & release via `name/version` tags

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
Components must keep an **independent lifecycle** even though `HEAD` is integrated
([ADR-0002](0002-uv-workspace-source-coupled-libs.md)). Today releases are driven by GitHub
Release events per repo; in a monorepo we need a per-component trigger. `file-services-backend`
already derives image tags from each service's `pyproject.toml` version and validates semver.

## Decision
Each component carries its own version (`pyproject.toml` / `Chart.yaml` / `package.json`). A
pushed git tag **`name/x.y.z`** releases *only* that component:
- `libs/*`, `tools/*` → build wheel, publish to PyPI (sandbox: disabled — see
  [ADR-0010](0010-history-preserving-migration.md));
- `services/*`, `frontend/data-portal` → build & push the image;
- `deploy/charts/*` → package & push the OCI chart.

CI **asserts the tag version matches the component's version at HEAD**. Because HEAD is
integrated, a tag releases the integrated HEAD's version of that component, not an isolated
branch. An umbrella tag **`ghga/<version>`** pins a tested set of component versions.

## Consequences
- Releasing is a small, auditable act (bump version in a PR → merge → tag).
- Per-component release notes/changelogs; no global version churn.
- The release matrix must map tag prefix → component path → artifact kind (driven by the same
  manifest as the build).
- "Release of a lib" no longer implies any consumer migration — consumers already track HEAD.

## Alternatives considered
- **Single repo-wide version.** Rejected: kills independent lifecycle.
- **GitHub Releases per component (UI-driven).** Rejected: tags are scriptable, reviewable in
  git, and compose with the affected-target build.
- **Tag format `name-vX.Y.Z`.** Cosmetic; `name/x.y.z` groups cleanly and is unambiguous with
  slashes.
