# ADR-0033 — Capability markers decide what a member builds and releases

- **Status:** accepted
- **Date:** 2026-06-30

## Summary

In the context of **workspace members that are libraries, services and CLIs at once**

facing **top-level folders that cannot express a member that is imported, shipped as an
image and published to PyPI**

we decided for **a `[tool.ghga]` table per member declaring its release lane and
artifacts, with defaults per directory, and placing members by primary identity**

and neglected **placing members by deployability, and splitting every hybrid into
separate packages**

to achieve **one declared source for what each member produces, independent of its
folder**

accepting that **markers must be kept consistent with entry points and images, and a
folder alone no longer says what a member ships**.

## Details

### Context

Several members are hybrids. `metldata` is a library, a deployable service and a CLI;
`ghga-transpiler` and `ghga-validator` are CLIs and services. A single folder, `libs/`,
`services/` or `tools/`, cannot say "imported by others, shipped as an image and
published to PyPI", and the folder should not silently decide what gets built.

### Decision

Each member declares its capabilities in a `[tool.ghga]` table in its `pyproject.toml`:
its release lane (`platform`, `pypi` or `none`, see
[ADR-0027](0027-versioning-and-release-by-tag.md)), and whether it builds an image,
publishes a wheel or exposes a CLI. The shared Dockerfile, the chart generator, the
release lanes and affected-target CI read the markers, not the path.

Directories supply defaults, so a marker is written only where a member deviates:
`services/` and `frontend/` default to the platform lane with an image, `libs/` to the
PyPI lane, and `tools/` to no lane at all.

Members are placed by primary identity: `metldata` is in `libs/`, `ghga-transpiler` and
`ghga-validator` in `tools/`. The folder is for people.

An image member's console script has the same name as its distribution, so the package
name is the image entry point.

The markers, defaults and examples are in
[docs/conventions.md](../conventions.md#toolghga-capability-markers).

### Consequences

- A `libs/` member can produce an image, and a `tools/` member can be a workspace
  dependency.
- One declared place says what artifacts a member produces.
- Markers must stay consistent with what the member contains; the Dockerfile checks at
  build time that the entry point exists.
- Adding a member outside the defaults needs a marker, or it is not built or released.

### Alternatives

- **Place members by deployability**, so anything with an image is in `services/`.
  Inverts the layering, with libraries depending on `services/` members, and still
  cannot express a member that is a PyPI package, an image and a CLI.
- **Split every hybrid into separate library and service packages.** Refactoring during
  the migration; still possible per package later.
