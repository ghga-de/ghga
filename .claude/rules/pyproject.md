---
paths:
  - "**/pyproject.toml"
---

# Rules for `pyproject.toml`

Each workspace member has its own `pyproject.toml`; the root one also configures the checks for all of them.

- **No check config in a member.** ruff, mypy, pytest and rumdl are configured once, in the root `pyproject.toml`, and a member's file holds only its package metadata, dependencies and `[tool.ghga]` marker.
  A change to the root check tables changes every member's checks, so the hook asks before it.
- **Internal libraries come from source:** a dependency on a workspace member is also listed under `[tool.uv.sources]` with `{ workspace = true }` ([internal dependencies](../../docs/conventions.md#internal-dependencies)).
- **After a dependency change, run `just lock`** and commit `uv.lock` with the change.
- **`[tool.ghga]` says what the member ships**: release lane, image, wheel, CLI, deployment roles ([capability markers](../../docs/conventions.md#toolghga-capability-markers)).
  Write a marker only where the member deviates from its directory's default.
  The chart generator reads it, so run `just charts` after changing `image`, `executable` or `roles`.
