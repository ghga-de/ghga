# ADR-0004 — Hybrid releases: platform lockstep + per-component PyPI lanes

- **Status:** Accepted — **revised 2026-07-23** (supersedes the original per-component-only
  scheme, which predated the consequences of an always-integrated HEAD)
- **Date:** 2026-06-30 / 2026-07-23
- **Deciders:** Leon Kuchenbecker

## Context

The original decision gave every component an independent `name/x.y.z` release tag. Working
with the integrated monorepo exposed the flaw: **the only combination CI ever tests is
HEAD-with-HEAD** ([ADR-0002](0002-uv-workspace-source-coupled-libs.md)). Releasing and
deploying a single service against older siblings produces a combination *no CI run has seen* —
recreating in production exactly the version skew the monorepo eliminates in development.
Meanwhile, published libraries and end-user CLI tools genuinely need per-component semver:
external consumers pin ranges, and series continuity on PyPI is load-bearing.

## Decision

Two release lanes, routed by each member's `[tool.ghga]` markers
([ADR-0014](0014-capability-markers-and-placement.md)):

### Platform lane — one version for everything deployable

- Members: all services (incl. `auth-km-jobs`, a K8s-deployed job), the front end, the charts
  and the `ghga-demo` umbrella, and `ghga-datasteward-kit` (internal-only, transitional).
- One pushed tag **`ghga/X.Y.Z`** releases the whole set: build **all** images from the tagged
  commit, package all charts, stamp everything with the platform version. There is no
  affected-only shortcut for releases — lockstep is the point; layer caching keeps unchanged
  members cheap.
- **Images embed internal libraries from source at the release commit — never from PyPI.**
  A lib's "independent lifecycle" means an independent *publishing cadence for external
  consumers*, not an independent integration state (the Kubernetes staging-repos model).
- **Versioning: operator-oriented semver.** Major = operators must act (breaking external API,
  migration, required config change); minor = features; patch = fixes. The **initial version is
  computed at cutover**, not fixed in advance:
  `N.0.0` where `N = 1 + max(all platform-lane member versions, file-services-backend's
  repo-level release series, any absorbed image-tag series)` — self-buffering against ongoing
  mainline development (currently evaluates to 17).
- **Version stamping happens at image build, after dependency resolution** (keeps `uv.lock`
  stable and member pyprojects untouched — no sync-window conflicts):
  - the member's installed `dist-info` `Version:` is rewritten to the platform version (this is
    what services report via `importlib.metadata`, e.g. in OpenAPI);
  - workspace-internal libraries inside the image get a **PEP 440 local suffix**
    (`8.6.0+ghga.17.0.0`) — constraints stay satisfied, SBOM/scanner metadata stays coherent,
    and local versions are unpublishable to PyPI by design;
  - OCI labels `org.opencontainers.image.version` / `.revision` and the
    `GHGA_PLATFORM_VERSION` env var carry the version and commit.
- The release workflow **verifies rather than re-tests**: it asserts the tagged commit is on
  `main` with a green CI run (ADR-0009's gates are the evidence; the tag snapshots it).
- `ghga-datasteward-kit` is distributed **run-from-repo**: stewards `git clone -b ghga/X.Y.Z`
  and `uv run ghga-datasteward-kit` — `uv.lock` at the tag reproduces the exact tested
  combination. No PyPI publishing from the monorepo; requires only `git` + `uv`.
- At cutover (not before — the fields are mainline-synced until then): platform-lane member
  versions are fixed at `0.0.0` (build-time stamping supplies the real one), datasteward-kit
  drops its PyPI lane and pins `requires-python` to the workspace baseline, and `auth-km-jobs`
  moves to `services/`.

### PyPI lane — per-component semver for out-of-tree consumers

- Members: the libraries (`hexkit`, `ghga-service-commons`, `ghga-event-schemas`, `schemapack`,
  `metldata`) and the public CLI tools (`ghga-connector`, `ghga-validator`).
- A pushed tag **`name/x.y.z`** publishes that component's wheel; CI asserts the tag matches
  the member's version at HEAD. Libraries release **on demand** — when an external consumer
  needs something or a tool release requires it.
- **Closure-train rule:** a published tool must not induce untested combinations on user
  machines. `ghga-connector`'s internal closure (`ghga-service-commons`, `hexkit`) is released
  from the same commit when changed, and the tool pins those versions **exactly** (app-style;
  documented install method: `pipx`/`uvx`). `ghga-validator` has no internal dependencies —
  its train is trivially itself.
- The **published-combo matrix** ([ADR-0002](0002-uv-workspace-source-coupled-libs.md)) — the
  component against PyPI-resolved dependencies across its supported Python range — is a
  **prerequisite for the first PyPI-lane release from this repo**, since the workspace only
  tests the 3.13 source combination.

### Both lanes

- **Final** publish targets (registries, PyPI enablement) remain undecided. Interim
  (2026-07-23): the platform lane can push images to **GHCR under the repo's namespace**
  (`ghcr.io/ghga-de/ghga/<member>`, private) — manual `workflow_dispatch` only, no tag
  triggers, authenticated via the ephemeral `GITHUB_TOKEN` so **no stored credentials
  exist**. The PyPI lane stays a stub.
- Local development builds use the same Dockerfile/stamping path with a dev placeholder
  version (`0.0.0+dev.g<sha>`) — release/local parity is the guarantee that "worked locally"
  transfers.

## Consequences

- "What version is auth-service?" stops having its own answer: it's the auth-service *of
  platform X.Y.Z*. Per-service version-bump rituals end at cutover.
- One number describes a deployment; upgrades, rollbacks, and support conversations are
  one-dimensional. Adjacent-release compatibility (rolling upgrades) replaces arbitrary-skew
  compatibility.
- Unchanged services get rebuilt/retagged each release (cheap: cached layers, deduped storage)
  and their pods roll on upgrade — accepted, standard for lockstep products.
- Lib publishing cannot lapse entirely while `ghga-connector` publishes (its closure needs
  wheels) — the lane is small but load-bearing.

## Alternatives considered

- **Per-component releases for everything** (the original decision). Rejected: deploys
  untested combinations; ~30 versions and tag rituals whose distinctions nothing consumes.
- **Full lockstep including libs/tools on PyPI.** Rejected: destroys semver meaning and series
  continuity for external consumers.
- **CalVer for the platform.** Workable (and dodges all numeric-ordering concerns), but
  operator semver was chosen: the major digit carries the "operators must act" signal, which
  a regulated deployment values; ordering is guaranteed instead by the cutover-day
  initial-version rule.
