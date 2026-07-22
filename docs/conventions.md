# Monorepo conventions

Quick reference for how the repo is organised and what is automated from metadata. See the
[ADRs](adr/) for the rationale.

## Layout & placement

- `libs/` · `services/` · `tools/` are `uv` workspace members; `frontend/` is the JS toolchain;
  `deploy/` (charts), `testbed/`, `docker/`, `scripts/`, `docs/` are support.
- Members are placed by **primary identity**, not by capability — a `libs/` member can still
  produce an image; a `tools/` member can still be a workspace dependency
  ([ADR-0014](adr/0014-capability-markers-and-placement.md)).

## `[tool.ghga]` capability markers

Each member declares what artifacts it produces in its own `pyproject.toml`. The build,
chart-generation, and release pipelines key off these — **not** off the folder.

```toml
[tool.ghga]
image = true    # build & push a container image (and generate a Helm chart) on the release tag
pypi  = true    # publish a wheel to PyPI on the release tag (disabled during the sandbox)
cli   = true    # exposes a console entry point

# optional, when image = true:
executable = "auth-service"   # console script used as the image ENTRYPOINT
roles = ["rest", "consumer"]  # deployment roles (distinct service_instance_id per role)
```

Examples: `libs/metldata` → `{image, pypi, cli}`; `libs/hexkit` → `{pypi}`;
`services/auth-service` → `{image}`; `tools/ghga-connector` → `{pypi, cli}`;
`tools/ghga-transpiler` → `{image, pypi, cli}`.

## Internal dependencies

Consume internal libraries **from source**:

```toml
[tool.uv.sources]
hexkit = { workspace = true }
ghga-event-schemas = { workspace = true }
```

One `uv.lock` governs the whole repo → HEAD is always integrated
([ADR-0002](adr/0002-uv-workspace-source-coupled-libs.md)).

## Versioning & releases

- Every member keeps its own semver (in `pyproject.toml` / `Chart.yaml` / `package.json`).
- A pushed git tag **`name/x.y.z`** releases only that component; CI asserts the tag matches the
  member's version at HEAD ([ADR-0004](adr/0004-versioning-and-release-by-tag.md)).
- Publish targets (images / charts / PyPI) are **not yet decided**; until they are, the release
  workflow stays dormant with no publish steps
  ([ADR-0010](adr/0010-history-preserving-migration.md)).

## Toolchain

- One `ruff` / `mypy` / `pytest` config at the repo root (in `pyproject.toml`); no per-member
  copies (the old `.template/` sync is retired).
- `just` is the task facade ([ADR-0015](adr/0015-task-runner.md)); `uv` manages Python 3.13.
