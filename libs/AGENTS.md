# Agent Instructions for `libs/`

How we work on the source-coupled internal libraries. The repo-wide rules are in the root
[AGENTS.md](../AGENTS.md), what the directory is in its [README](README.md), and
[docs/agent-instructions.md](../docs/agent-instructions.md) says what belongs in which
file. `ghga-jsonsubschema` carries its own `AGENTS.md` besides this one.

## Release lane

- `libs/*` defaults to the **PyPI lane**: a pushed `name/x.y.z` tag publishes the wheel,
  rehearsed on TestPyPI first. A member deviates only by writing its own `[tool.ghga]`
  marker — `metldata` is on the platform lane with an image, `ghga-event-schemas` on no
  lane at all ([conventions](../docs/conventions.md#toolghga-capability-markers)).
- Every member keeps its own semver in its `pyproject.toml`, and CI asserts the tag
  matches the version at HEAD
  ([ADR-0027](../docs/adrs/adr-0027-versioning-and-release-by-tag.md)).
- Keep `requires-python` **broad**, for external PyPI users rather than for this
  workspace. The published-combo gate tests the member the way an external consumer gets
  it, on every version the floor allows: `just published-combo <member> <python>`.

## What a change costs

Consumers import these from source, so one `uv.lock` resolves them and a change lands in
every consumer at once
([ADR-0026](../docs/adrs/adr-0026-uv-workspace-source-coupled-libs.md)). Editing a `libs/`
member therefore means running `just affected` and testing every consumer, not only the
member's own suite.
