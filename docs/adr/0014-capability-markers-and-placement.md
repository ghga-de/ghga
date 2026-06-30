# ADR-0014 — Capability markers decouple build/release from folder placement

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
Several members are hybrids: `metldata` is a framework library **and** a deployable service
**and** a CLI; `ghga-transpiler`/`ghga-validator` are CLI **and** service. A single top-level
folder (`libs`/`services`/`tools`) cannot express "imported by others *and* shipped as an image
*and* published to PyPI", and we don't want the folder to silently dictate what gets built.

## Decision
Capability is declared per member in a `[tool.ghga]` table in its `pyproject.toml`, and **drives
the build/release matrix**:

```toml
[tool.ghga]
image = true    # build & push a container image (and a chart) on its release tag
pypi  = true    # publish a wheel to PyPI on its release tag
cli   = true    # exposes a console entry point
```

Members are **placed by primary identity** — `metldata` → `libs/`, `ghga-transpiler` /
`ghga-validator` → `tools/` — and the folder is purely human grouping. The shared Dockerfile,
the chart generator ([ADR-0013](0013-adopt-ghga-common-chart-system.md)), and the
affected-target CI all key off the markers, not the path.

## Consequences
- Hybrids stop being awkward; a `libs/` member can still produce an image; a `tools/` member can
  still be a workspace-source dependency.
- One declarative source of truth for "what artifacts does this member produce".
- Requires a small validation step (markers vs. presence of an entry point / Dockerfile needs).

## Alternatives considered
- **Place strictly by deployability** (anything with an image → `services/`). Rejected: inverts
  layering (a lib depending on a `services/` member) and still can't express PyPI+image+CLI.
- **Split every hybrid** into separate lib/service packages. Rejected as migration-time
  refactoring; can be revisited per package later.
