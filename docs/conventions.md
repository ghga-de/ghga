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
release = "platform"  # release lane: "platform" (lockstep) | "pypi" | "none"
image = true    # build & push a container image (and generate a Helm chart) on the release tag
pypi  = true    # publish a wheel to PyPI on the release tag (disabled during the sandbox)
cli   = true    # exposes a console entry point

# optional, when image = true:
executable = "auth-service"   # console script used as the image ENTRYPOINT
roles = ["rest", "consumer"]  # deployment roles (distinct service_instance_id per role)
```

Directories supply the defaults, so a marker is only written where a member deviates:
`services/*` and `frontend/*` default to the platform lane with an image, `libs/*` to the
PyPI lane, `tools/*` to no lane at all
([ADR-0014](adr/0014-capability-markers-and-placement.md)).

Examples: `libs/hexkit` → `{pypi}` and `services/auth-service` → `{platform, image}`, both by
default; `libs/metldata` → `{platform, image}` (a library that is also deployed);
`libs/ghga-event-schemas` → `{none}` (embedded in the images, never published on its own);
`tools/ghga-connector` and `tools/ghga-transpiler` → `{pypi, cli}` (public CLIs opting in).

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
- One `.pre-commit-config.yaml` at the root covers **both** stacks
  ([ADR-0018](adr/0018-pre-commit-hooks.md)). `just hooks` installs it, `just hooks-all` runs
  everything. The ruff / mypy / prettier / eslint hooks take their version from `uv.lock` and
  `pnpm-lock.yaml`, not from a `rev:` pin, so a hook can never disagree with CI.
- mypy runs per member (`src` + tests) via `scripts/typecheck.py` — the same runner behind
  `just typecheck`, the hook, and CI. Never `mypy .`: the members' `tests` packages collide.

## Testing outbound HTTP calls

- The API a member calls is mocked with `ghga_service_commons.api.mock_api`, never with
  `pytest-httpx` or a hand-rolled transport: one `ApiMock` subclass per external API, declaring
  its endpoints with `endpoint(...)` and their default responses. Tests swap a handler onto the
  `on_...` attribute of the endpoint they exercise (`respond`, `fail_to_connect`, `fail_with`,
  `in_sequence`, or one of their own) and assert against the mock's recorded `requests`.
- The mock lives in the member's `tests/fixtures/`, named after the API it stands in for, and
  takes the same config the service builds its URLs from — so the mock and the client under test
  can never disagree about where the API is.
- Mount `as_transport()` as the innermost transport of the client under test, so the retry and
  rate limiting layers stay in the loop. A client talking to several APIs, or also carrying real
  traffic, gets a `RoutingTransport` over the mocks instead. Code that takes no transport at all —
  building its own client, or calling `httpx2.get` — is reached with `patch_httpx_module(monkeypatch)`.
- An endpoint only one test cares about does not need a subclass: `ApiMock` used directly, with
  the endpoint registered by `add(...)`, is the form for those — the datasteward kit's tests are
  the example.
