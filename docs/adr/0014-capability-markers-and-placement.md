# ADR-0014 — Capability markers decouple build/release from folder placement

- **Status:** Accepted — **amended 2026-07-23**: added the `release` lane key and
  directory defaults (see the revised [ADR-0004](0004-versioning-and-release-by-tag.md))
- **Date:** 2026-06-30 / 2026-07-23
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
release = "platform"  # release lane: "platform" (lockstep, ADR-0004) | "pypi" | "none"
image   = true        # built as a container image (platform lane)
pypi    = true        # publish a wheel to PyPI on its name/x.y.z tag (pypi lane)
cli     = true        # exposes a console entry point
```

To keep the marker (and sync-conflict) surface minimal, **directories provide defaults** and
markers are only written where a member deviates:

| Directory | Default |
|---|---|
| `services/*`, `frontend/*` | `release = "platform"`, `image = true` |
| `libs/*` | `release = "pypi"`, `pypi = true` |
| `tools/*`, `testbed`, `deploy/*` | `release = "none"` — tools must opt in explicitly |

Explicit markers (the deviations): `auth-km-jobs` (`platform` + image — a K8s job, relocated
to `services/` at cutover), `ghga-datasteward-kit` (`platform`, **no** image — run-from-repo),
`ghga-connector` and `ghga-validator` (`pypi`).

Members are **placed by primary identity** — `metldata` → `libs/`, `ghga-transpiler` /
`ghga-validator` → `tools/` — and the folder is purely human grouping. The shared Dockerfile,
the chart generator ([ADR-0013](0013-adopt-ghga-common-chart-system.md)), the release lanes
(ADR-0004), and the affected-target CI all key off the markers, not the path.

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
