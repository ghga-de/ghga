---
status: proposed
date: 2026-10-07
tags: [release]
related: [ADR-0027, ADR-0038, ADR-0043, ADR-0045]
---

# ADR-0046 — The platform version comes from tags alone

## Summary

In the context of **platform-lane members whose artifacts a `ghga/X.Y.Z` tag stamps with the platform version**

facing **member versions that name no release, are still bumped by hand and leak into `openapi.yaml`, the mono image and local front-end builds**

we decided for **the tag as the only source of the platform version: members declare `0.0.0`, release builds stamp the tag's version, and everything else derives one from `git describe`**

and neglected **per-member versions, a version file, writing the version into every member, VCS-derived versions in the build backends, versions computed from commit types and a release bot**

to achieve **no version bumps in pull requests and a version that says where a build stands**

accepting that **the next version is unknown until its tag, and three small copies of the derivation**.

## Details

### Context

Since [ADR-0027](adr-0027-versioning-and-release-by-tag.md), a `ghga/X.Y.Z` tag stamps every platform-lane image and chart with the platform version.
The versions the members still declare (`package.json` 2.5.16, `auth-service` 10.0.2, `ucs` 16.0.0) belong to no release.
They are bumped by hand in some pull requests, and they surface wherever nothing stamps: `openapi.yaml`, the mono image and a local front-end build.

### Decision

- **Declared version.**
  Every platform-lane member declares `0.0.0` in its `pyproject.toml` or `package.json`, with a comment pointing here where the format allows one.
  A declared version never names a release, and CI rejects any other.
  The PyPI lane keeps its own semver.
- **Release builds** stamp the version of the tag they build from, as before.
- **Any other build** derives the version from `git describe --tags --match 'ghga/*'` and turns it into semver.
  At a tag it is that tag's version (`15.3.1-rc.8`); after one, the commits since it and the abbreviated SHA follow as build metadata (`15.3.1-rc.8+dev.64.e50c714`); local changes add `.dirty`.
  Without git or a matching tag it is `0.0.0+dev`.
- **CD builds** keep the `0.0.0-dev.<run>.<attempt>` of [ADR-0045](adr-0045-dev-charts-for-continuous-deployment.md): a cluster's CD tool needs a version that rises with every merge, which build metadata does not give.

[Releases](../releases.md#platform-lane) defines the format and where it is applied.

### Consequences

- No pull request bumps a platform-lane member, and there is no version file to keep in step.
- A checkout, a local image and `just fe-dev` report where they stand; stewards running `ghga-datasteward-kit` from a tag send that tag's version.
- The next version is not known before its tag is cut.
- `dev` is not merged back after a release ([ADR-0038](adr-0038-branching-strategy.md)), so until the next candidate it describes itself from the last candidate; `+dev` says it is not the release.
- The derivation lives in three places that cannot import each other: the Python tools, the front end's `run.js` and the image recipes.

### Alternatives

- **Per-member versions (the status quo).**
  Numbers no artifact reports, bumped by hand.
- **A version file holding the next release, checked against the tag.**
  Shows the next version early, but needs a bump per release, is retargeted when a minor turns major at release time, and conflicts when a hotfix bumps `main` while `dev` targets the next minor.
  A checkout still needs the git suffix.
- **Writing the version into every member.**
  The costs of the version file times some 24 files plus `uv.lock`, and untagged builds still need stamping.
- **VCS-derived versions in the build backends** (`hatch-vcs`, `setuptools-scm`).
  Right everywhere without stamping, but editable installs go stale until the next sync, uv needs cache keys on tags, image builds need `.git`, and every member's build configuration carries the tag pattern.
- **The next version computed from commit types since the tag.**
  Only as good as the merge subjects, and a breaking change does not mean operators must act.
- **A release bot pull request bumping a version file.**
  Automates the bump, but adds bot churn, does not fit candidates on `dev`, and overlaps the release notes of [ADR-0043](adr-0043-release-notes.md).
