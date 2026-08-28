# ADR-0020 — Git Flow: `main` is the latest release, `dev` is the integration branch

- **Status:** Proposed
- **Date:** 2026-08-28
- **Deciders:** Byron Himes

## Context
The monorepo has released off a single `main` branch, with releases cut as tags ([ADR-0004](0004-versioning-and-release-by-tag.md)). That means the state of `main` is always in flux. Since changes are constantly being merged, `main` is more often broken than not, except for the narrow window around a release. This approach was fine with our polyrepo setup because the churn for a given repo was comparatively low and thus manageable. With this new monorepo setup, however, the entire team's work is concentrated on the same repo, so `main` gets updated multiple times per day. The question of  "what is in production?" is only answerable by finding the newest tag and comparing commit ranges or PRs included in the release. That's *doable* for a single microservice repo (not ideal), but becomes an actual headache in a monorepo. A favorable branching strategy would involve creating a `dev` branch to contain all unreleased work. When the time comes to release the latest version of the monorepo, `dev` gets merged into `main`. Subsequent changes continue to be merged into `dev` from feature branches. Hotfix branches can be made against `main` directly, then merged into `dev`. Feature branches are created from `dev`, but the exact structure for feature branches is deliberately left less defined in order to allow developers the freedom to use the strategy most compatible with the work and/or their preferences, especially since it is important to experiment while we are still getting accustomed to the monorepo as a team.

## Decision
We will adopt a Git Flow variant with two long-lived branches:

- **`main` reflects the latest release.** Its HEAD is always a released state, and every release tag sits on it.
- **`dev` runs alongside `main`** and is the integration branch. It is branched from `main` and is where completed work accumulates between releases.
- **Feature branches are cut from `dev` and merged back into `dev`** via pull request.
- **A release merges `dev` into `main`**, and the release tag is applied on `main`.
- **Hotfixes are made on `main`** (branched from it, merged back into it, released) and are then **merged back into `dev`** so the fix is never lost on the next release.
- **Long-lived feature branches are permitted but not mandatory.** How feature branches are structured should be decided on a case-by-case basis, and devs should feel encouraged to communicate and experiment in order to find the best approach.

## Consequences
- We gain a clear division between deployed state (`main`) and work-in-progress (`dev`).
- Releasing is a merge plus a tag, and can be prepared and reviewed as a pull request.
- Two branches must be kept in sync. Every hotfix must be merged back into `dev`, lest the next release be cursed.
- Work merged to `dev` is not released until the next release merge.
- We gain the ability to continuously deploy to staging from `dev` while leaving production deployments compartmentalized. With just a `main` branch this is a more involved process.
- CI and tooling assume a single branch today and must be updated:
  - workflow triggers on `branches: [main]` (`ci.yaml`, `dev-images.yaml`, `integration.yaml`) need to cover `dev`.
  - `no-commit-to-branch` in `.pre-commit-config.yaml` guards `main` only and should also guard `dev`. The comment "this repo has only `main`" and the corresponding note in [ADR-0018](0018-pre-commit-hooks.md) need to be updated.
  - branch protection is needed on `dev` as well as `main`.

## Alternatives considered
- **Trunk-based on `main` alone** (what we do now). Rejected: no branch represents the released state and `main` is always in flux.
- **Trunk-based on `main` with merge queues** (remix of status quo). Rejected: merge queues would allow PRs to pile up against `main` until certain criteria green-lit the merge. This would, in essence, give the same end result as the proposed strategy, except all the changes that would be merged into `dev` would be in a limbo state against `main`. It would automate the role of `dev` but in exchange we would lose the concrete state tracking and conceptual simplicity offered by an actual branch. This approach might be revisited in the future as part of a production CD strategy when the GHGA platform has gelled more and changes are less disruptive/conflicting.
- **Release branches per version** (full Git Flow). Rejected: with controlled platform releases and hotfixes applied to the latest release only, `main` already serves that role; per-version maintenance branches are not something we want or have the user base to justify. We tried doing this with `hexkit` early on, up through about v3 or v4, but it got tedious quickly.
- **`dev` only, with releases tagged there.** Rejected: it is the status quo renamed — the point is a branch whose HEAD is a release.

## Final Note
The strategy adopted through this ADR is not binding, it's merely a commitment to *try it out* long enough to be able to judge its suitability for our needs.
