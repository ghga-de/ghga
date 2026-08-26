# ADR-0004 — Hybrid releases: platform lockstep + per-component PyPI lanes

- **Status:** Accepted — **revised 2026-07-23** (supersedes the original per-component-only
  scheme, which predated the consequences of an always-integrated HEAD) — **amended
  2026-08-18**: PyPI-lane membership corrected to what the markers declare (see below) —
  **amended 2026-08-19**: the release set is decided against the index rather than a git
  diff, and the closure-train rule is narrowed to bumped dependencies (see below) —
  **amended 2026-08-25**: `ghga-arcticfreeze` and `ghga-jsonsubschema` named in the member
  list, which had omitted them (see below)
- **Date:** 2026-06-30 / 2026-07-23 / 2026-08-18 / 2026-08-19 / 2026-08-25
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

- Members (amended 2026-08-25): the libraries (`hexkit`, `ghga-service-commons`,
  `schemapack`, `ghga-arcticfreeze`, `ghga-jsonsubschema`) and the public CLI tools
  (`ghga-connector`, `ghga-validator`, `ghga-transpiler`). Changes against the 2026-07-23
  list:
  - `ghga-event-schemas` — **out.** Embedded in the images and consumed from workspace
    source; nothing outside the deployment installs it, so an external series would have
    no consumer.
  - `metldata` — **out.** A library *and* a deployable service, released in the platform
    lane with the rest of the deployment.
  - `ghga-transpiler` — **in.** A public CLI stewards install standalone, like
    `ghga-validator`.
  - `ghga-arcticfreeze`, `ghga-jsonsubschema` — **in** (2026-08-25). Both were already in
    the lane through the `libs/*` default and already have PyPI series; this only names
    them, so the list matches what `scripts/pypi_members.py` enumerates. Neither is
    optional: `schemapack` depends on both, and a member whose internal dependency sits
    outside the lane fails the release plan — nobody could install it.

  The `[tool.ghga]` markers are the operative source
  ([ADR-0014](0014-capability-markers-and-placement.md)) and `scripts/pypi_members.py`
  reads the lane from them; this list records the decision behind them.
- A pushed tag **`name/x.y.z`** publishes that component's wheel; CI asserts the tag matches
  the member's version at HEAD. Libraries release **on demand** — when an external consumer
  needs something or a tool release requires it.
- The tag names the component; **what uploads is decided against the index** — every lane
  member declaring a version above the latest one PyPI serves, ordered dependencies-first.
  `release.yaml` asserts the tag, then delegates to `pypi-publish.yaml`, which owns that
  plan. Nothing is diffed against a git ref: "did this commit bump it?" is a different
  question, and one that misses a bump made weeks ago and never published. So the lane has
  one implementation, a bump arriving through the mainline sync is picked up like any
  other, a missed release repairs itself on the next run, a tag for a member already on the
  index is a no-op, and re-running is idempotent because the second run sees the version
  there. A member *trailing* the index (`ghga-validator` declares 1.1.1 while PyPI serves
  1.2.0) is skipped, not an error — being behind is a sync question, not a release one.
- **Closure-train rule** (amended 2026-08-19): a published tool must not induce untested
  combinations on user machines. `ghga-connector`'s internal closure
  (`ghga-service-commons`, `hexkit`) is released **in the same train** when those libraries
  are themselves candidates, dependencies first, so the tool never reaches the index before
  a version it needs. `ghga-validator` and `ghga-transpiler` have no internal dependencies —
  their trains are trivially themselves.

  Two things the original rule asked for are deliberately **not** done:

  - **Exact pinning** is dropped. It would mean editing synced `pyproject.toml`s
    ([ADR-0010](0010-history-preserving-migration.md)) and would stop users taking
    dependency fixes. Whatever a member already declares stays the contract, untouched in
    either direction: `ghga-connector` came from upstream pinning
    `ghga-service-commons==8.1.0` and `hexkit[s3]==9.0.1` and keeps those exacts, while
    `schemapack` declares a range (`ghga-arcticfreeze >=1.0, <2`). The lane adds no pins
    and relaxes none.
  - **A library that changed without a bump does not block a dependant's release.** For the
    outside world that library did not change, so the dependant resolves it from the index
    like any consumer would. Holding an unrelated release hostage to someone's unreleased
    work — a fix merged to main that is not ready to ship — would be wrong, and "the
    directory changed" cannot distinguish a docstring edit from a new API.

  What keeps that honest is the published-combo matrix, which resolves the *same* way: an
  internal dependency is built from this repo only when it is a release candidate, and
  otherwise comes from PyPI. So the combination under test is the combination that ships.
  If a tool genuinely needs unreleased library code, its own floor says so and the install
  fails there — the accurate signal, at the layer that owns it.
- The **published-combo matrix** ([ADR-0002](0002-uv-workspace-source-coupled-libs.md)) — the
  component against PyPI-resolved dependencies across its supported Python range — is a
  **prerequisite for the first PyPI-lane release from this repo**, since the workspace only
  tests the 3.13 source combination.

### Both lanes

- **Platform image target decided** (2026-08-21): **Docker Hub**, under the `ghga`
  namespace (`docker.io/ghga/<member>`) — matches what production already pulls from. The
  platform lane pushes there, manual `workflow_dispatch` only, no tag triggers yet,
  authenticated with the org's stored `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` secrets (the
  same credentials used to pull the hardened dhi.io base images). GHCR
  (`ghcr.io/ghga-de/ghga`) remains in use as a separate, deliberately independent scratch
  registry for `dev-images.yaml`/`security-scan.yaml`'s `:dev`/`:updated` tags — never the
  release target.
- **PyPI publish targets decided** (2026-08-26): the lane publishes to **PyPI**, rehearsed
  on **TestPyPI** first, both by **trusted publishing** (OIDC; no stored tokens). One
  `pypi-publish.yaml` run builds and checks the whole train before uploading anything, then
  uploads to TestPyPI, then the *same files* to PyPI; `--check-url` on both makes a re-run
  idempotent. The `publish` job runs under `environment: ghga-pypi`, whose required
  reviewers gate the whole job. The two indexes hold **separate** trusted-publisher
  entries, matched on owner, repository, workflow filename and environment — a mismatch
  reports only `invalid-publisher`, so both sides change together. The lane has **one
  entrance**: `release.yaml` routes `name/x.y.z` tags to it via `workflow_call`, so every
  publish has passed `resolve` (commit on `main`, CI green, tag matching the declared
  version). `pypi-publish.yaml` declares no `workflow_dispatch` of its own — a second
  entrance would bypass all three.
- Local development builds use the same Dockerfile/stamping path with a dev placeholder
  version (`0.0.0+dev.g<sha>`) — release/local parity is the guarantee that "worked locally"
  transfers.
- **Chart publish target decided** (2026-08-24): charts publish as **OCI artifacts**,
  alongside the images — package + push happen in the same `release.yaml` run that builds
  the images, from the same tagged commit, stamped with the same platform version. This
  supersedes the interim `release-charts.yaml` gh-pages index, which published charts
  independently on every `main` push touching `deploy/` and so let a chart version denote
  no defined state relative to the images it shipped alongside.
- **Chart publish target corrected** (2026-08-25): the initial `oci://docker.io/ghga/charts/<chart>`
  target is invalid — Docker Hub repository paths are exactly two segments
  (`namespace/repo`), and a chart's name always equals its image's package name
  (ADR-0014), so publishing under the bare name would collide tag-for-tag with the
  container image of the same name and version in the same `ghga` namespace. Charts
  instead publish to `oci://registry-1.docker.io/ghga/<chart>-chart` — same namespace,
  each chart's own repo, distinguished by a `-chart` suffix (the packaged copy is renamed
  for this push only; the umbrella's local dependency graph keeps the real chart names).
  `registry-1.docker.io` is the actual backend host OCI push/pull operations need to
  hit, distinct from `docker.io`.
- **Chart push auth fixed** (2026-08-25): a real dispatch 401'd pushing charts —
  `docker login` only writes Docker Hub credentials under the canonical
  `https://index.docker.io/v1/` key when given `docker.io` (its recognized alias);
  logging into `registry-1.docker.io` directly writes credentials under a key ORAS's
  lookup never finds, so the push goes out unauthenticated. Fix: login targets
  `docker.io` (same as the image-build login), while the push target stays
  `registry-1.docker.io` — ORAS does translate a `registry-1.docker.io` lookup back to
  the canonical key, it's only the write side that needed the alias.
- **Pre-release cuts**: `ghga/X.Y.Z-rc.N` is a normal platform-lane ref for staging — same
  mechanism, same lockstep guarantee (images and charts from one commit), just a SemVer
  pre-release identifier on the version. Not a separate process or workflow.

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
