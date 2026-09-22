# `libs/` — source-coupled internal libraries

Workspace members that other members import **from source** (one `uv.lock`, one resolved
version repo-wide — see [ADR-0026](../docs/adrs/adr-0026-uv-workspace-source-coupled-libs.md)).

- Consumers depend on these via `[tool.uv.sources] <lib> = { workspace = true }`.
- Libraries keep **broad** Python/version ranges in their own `pyproject.toml` for external
  PyPI users; a standalone per-Python **matrix** validates the published combination.
- A library may also be deployable or a CLI — that is declared via `[tool.ghga]` capability
  markers, not by which folder it lives in
  ([ADR-0033](../docs/adrs/adr-0033-capability-markers-and-placement.md)). e.g. `metldata` lives
  here but is also built as an image.
