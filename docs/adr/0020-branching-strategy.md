# ADR-0020 — Git Flow: `main` is the latest release, `dev` is the integration branch

- **Status:** Proposed
- **Date:** 2026-08-28
- **Deciders:** Byron Himes

## Context
In our previous polyrepo setup, branching was simple: single feature branches were created and merged directly into main.
This worked because, usually, there was only one dev touching a given repo at any given moment and the maximum scope of the work was limited by the repository.
There was no possibility of cross-cutting updates or sweeping changes from giant features (except in the File Services Monorepo, but that was a unique case).
When we weren't sure about which changes had been released or not, we had to look at when the last release had occurred vs when the changes in question had been merged.
That was doable, if not ideal, because of the small repository size and relatively low rate of change.
Now that we've moved to a singular monorepo, the dynamic has shifted and none of that holds anymore.
We're trying to settle on a branching strategy that balances concerns of procedural facility (shouldn't require a complicated SOP), situational clarity (what's deployed, and what changes have been merged since then?), and good change management.
Since we made the switch to the monorepo a few weeks ago, we've continued to use the old strategy where all the feature branches stemmed from and merged directly back into a single `main` branch.
The result is that the state of `main` is always in flux, because developers are no longer split among isolated repositories but rather touching the same repo.
Churn is especially high right now because we're A) making adjustments to the repository tooling and B) multiple big features are in progress with more to come.
The question of "what is in production?" is never clear because the latest release state gets quickly obscured by new updates in preparation for the _next_ release.

## Decision

> We decided for a Git Flow variant with two long-lived branches and neglected trunk-based-only and merge queues, to achieve a monorepo with transparent state and separation of concerns (releases vs work), as well as the ability to CD to staging, accepting that we have to keep `dev` and `main` in sync.

Creating a `dev` branch to contain all unreleased work addresses the concerns listed in the Context section by clearly delineating work-in-progress and the latest release state.

- **`main` reflects the latest platform release.** Its HEAD is always a released state.
- **`dev` runs alongside `main`** and is the integration branch. It is branched from `main` and is where completed work accumulates between releases.
- **Feature branches are cut from `dev` and merged back into `dev`** via pull request.
- **A platform release merges `dev` into `main`**, and the release tag is applied on `main`.
- **Hotfixes are made on `main`** (branched from it, merged back into it, released) and are then **merged back into `dev`** so the fix is never lost on the next release.
- **Long-lived feature branches are permitted but not mandatory.** How feature branches are structured should be decided on a case-by-case basis, and devs should feel encouraged to communicate and experiment in order to find the best approach.
- **Release tags are cut on `main`, pre-release and PyPI-lane tags may be cut on `dev`.** `ghga/X.Y.Z` on `main` is what makes `main` the released state. A `ghga/X.Y.Z-rc.N` staging cut is just a *candidate*, so it is tagged on `dev` and staging deploys from there. PyPI-lane tags for libraries/tools are also cut on `dev`, so that we can adhere to [ADR-0004](0004-versioning-and-release-by-tag.md) and publish them on demand.

## Consequences
- We gain a clear division between deployed state (`main`) and work-in-progress (`dev`).
- Releasing is a merge plus a tag, and can be prepared and reviewed as a pull request.
- Two branches must be kept in sync. Every hotfix must be merged back into `dev`, lest the next release be cursed.
- Work merged to `dev` is not released until the next release merge.
- We gain the ability to continuously deploy to staging from `dev`, including the platform release candidates, which now come from `dev` — while leaving production deployments compartmentalized. With just a `main` branch this would be/is a more difficult process.
- CI and tooling assume a single branch today and have to be updated (see below).

### Necessary changes

**Branch**
- Create `dev` from `main`.
- Rebase all unmerged work which previously targeted `main` onto `dev`, and retarget open PRs.

**GitHub configuration**
- Protect `dev` the same way we protect `main`, and keep `main` protected: with releases landing there by merge, nothing should reach it any other way.
- Make `dev` the default branch, so new branches and PRs are cut against it without anyone having to remember.
- `security-scan.yaml` opens its automated lockfile PR with `base: main`; that becomes `dev`.

**pre-commit**
- `no-commit-to-branch` (`.pre-commit-config.yaml`) guards `main` only and must also guard `dev`; its comment ("this repo has only `main`") and the corresponding note in [ADR-0018](0018-pre-commit-hooks.md) are then stale.

**Workflows**
- `ci.yaml` and `integration.yaml` trigger on `push: branches: [main]`; both need to cover `dev`, which is where merges will land. Their `pull_request` triggers are branch-agnostic and need no change.
- `dev-images.yaml` publishes the `:dev` image tags on every push to `main`. That should follow `dev` instead — under this strategy `main` moves only at a release, and the `:dev` tags are meant to track integration.
- `release.yaml`'s `resolve` job currently asserts the tagged commit is on `main` *before* it routes the lanes, meaning both platform release candidates and lib/tool PyPI tags are releasable only once `dev` has merged to `main`. To get the desired behavior, it has to move behind the routing step and become per-lane: final platform tags (e.g. `ghga/X.Y.Z`) on `main` only, pre-release platform tags and PyPI-lane tags on `main` or `dev`. The CI half of the check is branch-independent and runs for every tag.
- [ADR-0004](0004-versioning-and-release-by-tag.md) needs an amendment for the above: it says the release workflow "asserts the tagged commit is on `main`" and describes `ghga/X.Y.Z-rc.N` as a normal platform-lane ref, but that was written back when we only had `main`. It should be updated to reflect that release candidates are cut from `dev`. `release.yaml`'s header comment needs the same treatment.

**Local tooling**
- `scripts/affected_targets.py` defaults `--base` to `origin/main`, as does the `affected` recipe in the justfile. That needs to be switched to `origin/dev`.

## Alternatives considered
- **Trunk-based on `main` alone** (what we do now). Rejected: no branch represents the released state and `main` is always in flux.
- **Trunk-based on `main` with merge queues** (remix of status quo).
Rejected: merge queues would allow PRs to pile up against `main` until certain criteria green-lit the merge.
This would, in essence, give the same end result as the proposed strategy, except all the changes that would be merged into `dev` would be in a limbo state against `main`.
It would automate the role of `dev` but in exchange we would lose the concrete state tracking and conceptual simplicity offered by an actual branch.
This approach might be revisited in the future as part of a production CD strategy when the GHGA platform has gelled more and changes are less disruptive/conflicting.
- **Release branches per version** (full Git Flow). Rejected: with controlled platform releases and hotfixes applied to the latest release only, `main` already serves that role; per-version maintenance branches are not something we want or have the user base to justify. We tried doing this with `hexkit` early on, up through about v3 or v4, but it got tedious quickly.
- **`dev` only, with releases tagged there.** Rejected: it is the status quo renamed — the point is a branch whose HEAD is a release.

## Final Note
The strategy adopted through this ADR is not binding, it's merely a commitment to *try it out* long enough to be able to judge its suitability for our needs.
