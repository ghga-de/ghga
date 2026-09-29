---
status: accepted
date: 2026-06-30
supersedes: [ADR-0024]
tags: [release, deploy]
related: [ADR-0026, ADR-0033, ADR-0038]
---

# ADR-0027 — Releases: platform lockstep and a PyPI lane

## Summary

In the context of **an integrated monorepo whose CI only tests HEAD with HEAD, and
libraries and CLIs that people outside the platform install from PyPI**

facing **per-component releases that would deploy combinations no CI run has seen, and
external consumers who need semver series they can pin**

we decided for **two release lanes: one platform version for everything deployable,
built from a single commit, and per-component semver on PyPI for the libraries and
public CLIs**

and neglected **per-component releases for everything, lockstep for PyPI too, and
CalVer**

to achieve **one tested combination per deployment, and PyPI series that external
consumers can rely on**

accepting that **every release rebuilds and rolls unchanged services, and a PyPI release
waits for the next platform release**.

## Details

### Context

The first version of this decision gave every component its own `name/x.y.z` release.
The monorepo showed the flaw: the only combination CI ever tests is HEAD with HEAD
([ADR-0026](adr-0026-uv-workspace-source-coupled-libs.md)). Releasing one service
against older siblings would deploy a combination no CI run has seen, which is the
version skew the monorepo removes. Published libraries and CLIs still need their own
semver: external consumers pin ranges, and their PyPI series must continue.

### Decision

Each member's markers put it in one of two lanes
([ADR-0033](adr-0033-capability-markers-and-placement.md)).

**Platform lane.** Services, the front end, the charts, `metldata` and
`ghga-datasteward-kit` share one version. A `ghga/X.Y.Z` tag builds every image and
chart from the tagged commit and stamps them with that version. Images embed internal
libraries from source at that commit, never from PyPI. The version is operator-oriented
semver: a major release means operators must act, a minor one adds features, a patch
fixes, and the series continues from 15.3, the version the charts carried at cutover.
`ghga-datasteward-kit` is not published; data stewards run it from a clone of the tag.

**PyPI lane.** The libraries and public CLIs that outside users install keep their own
semver.

- `name/x.y.z` releases that member alone; `packages/x.y.z` releases every member whose
  declared version is ahead of PyPI.
- What is uploaded is decided against the index, not against a git diff.
- A tool never reaches PyPI before an internal library version it needs. A release that
  would break that is refused rather than widened.
- A member whose shipped content changed must declare a version PyPI does not serve yet,
  before its pull request merges. One version never names two contents.
- The lane adds no pins to members' dependency constraints, and relaxes none.
- Published members are tested against their dependencies as resolved from PyPI.

**Both lanes.** The release workflow verifies rather than re-tests: the tagged commit
must be on the lane's branch and have a green CI run. Platform and PyPI tags are cut on
`main`, release candidates on `dev` ([ADR-0038](adr-0038-branching-strategy.md)). A tag
push builds; publishing is a deliberate, approved step. Images and charts go to Docker
Hub, wheels to PyPI after a TestPyPI rehearsal.

[Releases](../releases.md) describes the tags, version stamping, upload planning and
publish targets in detail.

### Consequences

- One number describes a deployment: auth-service is the auth-service of platform X.Y.Z.
  Compatibility is needed between adjacent releases, not arbitrary combinations.
- Every release rebuilds unchanged services and rolls their pods; cached layers keep the
  build cheap.
- Version bumps land on `dev`, so a PyPI release waits for the next platform release.
  One cadence is simpler than two; revisit if a component needs its own schedule.
- Every content change to a PyPI member needs a version bump before merge. If a tag
  publishes the same version between the check and the merge, `dev` fails afterwards and
  needs a second bump.
- Library releases cannot lapse while `ghga-connector` publishes, since its wheels need
  them.

### Alternatives

- **Per-component releases for everything.** Deploys untested combinations, and adds
  some 30 versions whose differences nothing consumes.
- **Lockstep for PyPI too.** Breaks semver and series continuity for external consumers.
- **CalVer for the platform.** Workable, but the semver major digit carries the
  "operators must act" signal.
- **Choosing the PyPI release set from a git diff.** Misses bumps that were never
  published; the index is what consumers see.
- **Every PyPI tag releasing the whole gap.** Leaves no way to release one library
  alone.
- **PyPI tags on `dev` as well.** Two release cadences to reason about.
- **Exact pins on internal dependencies of published tools.** Would stop users from
  taking dependency fixes.
