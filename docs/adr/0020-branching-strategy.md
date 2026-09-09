# ADR-0020 — Git Flow: `main` is the latest release, `dev` is the integration branch

- **Status:** Accepted — **amended 2026-09-08**: implemented. `dev` exists and the
  repo-side changes below have landed; the GitHub-side settings are tracked in
  "Remaining setup"
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
- **Platform version strings are always up-to-date in `dev`**.
- **Release candidates are created from `dev`**, where the pre-release git tag is cut. Only
  from `dev` — see the hotfix bullet.
- **`dev` is merged back into `main` with a merge commit** for production releases, and the platform release git tag is cut on `main`.
- **Production images are rebuilt** after release candidates are verified in staging.
  - The rebuilt images then get a final, confirmatory deployment to staging, so the images production runs have themselves been deployed there, not just their release candidates.
  - See "Open questions" for more on this.
- **All hotfixes are made on `main`** (branched from it, merged back into it, released) and are then **merged back into `dev`**, if applicable, so the fix isn't lost on the next release. **Hotfixes get no release candidate** (decided 2026-09-08): they are cut, reviewed and released on `main` in one step. A candidate exists to stage integrated-but-unreleased work, which is what `dev` holds and what a hotfix by definition is not — and a hotfix is the case where the extra round trip costs the most. So `ghga/X.Y.Z-rc.N` is a `dev`-only tag, and the release gate rejects one on `main` rather than accepting it.
- **Long-lived feature branches are permitted but not mandatory.** How feature branches are structured should be decided on a case-by-case basis, and devs should feel encouraged to communicate and experiment in order to find the best approach.

## Consequences
- We gain a clear division between deployed state (`main`) and work-in-progress (`dev`).
- Releasing is a merge commit plus a tag, and can be prepared and reviewed as a pull request.
- Two branches must be kept in sync. Every hotfix must be merged back into `dev`, unless `dev` already carries an equivalent fix.
- Work merged to `dev` is not released until the next release merge.
- We gain the ability to continuously deploy from `dev` while leaving production deployments compartmentalized. With just a `main` branch this would be/is a more difficult process.
- PR checks are fine as-is, since `ci.yaml` and `integration.yaml` run on every PR no matter the base branch. What needs updating is the stuff tied to a push: post-merge runs, `:dev` images, the release gate, and a couple of local defaults (see below).

### Necessary changes

> **Amended 2026-09-08 — the repo-side changes have landed.** `dev` is branched from `main`
> and pushed; `ci.yaml` and `integration.yaml` trigger on pushes to both branches;
> `dev-images.yaml` follows `dev`; `release.yaml` asserts the branch per lane, after routing;
> `security-scan.yaml` scans and targets `dev`; `no-commit-to-branch` guards both branches; and
> `scripts/affected_targets.py` and the justfile's `affected` recipe default to `origin/dev`.
> Prose that described `main` as the integrated branch was swept with it:
> [ADR-0019](0019-image-signing-sbom-provenance.md) (its predicted provenance subject is now
> `@refs/heads/dev`), [ADR-0009](0009-testbed-kind-minikube.md), the architecture overview, and
> the ADR index. The ADR set and the repo now agree —
> [ADR-0004](0004-versioning-and-release-by-tag.md)'s 2026-09-01 amendment (pre-release cuts on
> `dev`, per-lane branch gate) is backed by the workflow, and was itself amended on 2026-09-08
> where implementing it showed the per-lane branches had to be sets rather than single names.
> What is left is GitHub-side and cannot be done from the tree; see "Remaining setup".

**Branch**
- Create `dev` from `main`.
- Rebase all unmerged work which previously targeted `main` onto `dev`, and retarget open PRs.
- Forbid squash-merging and rebasing on `main`. "Require linear history" must stay *off* for `main`, since it would forbid the release merge commit.

**GitHub configuration**
- Protect `dev` like we protect `main`, and keep `main` protected too.
- Make `dev` the default branch so new branches and PRs target it automatically.
- `security-scan.yaml` opens its lockfile PR against `main`. That needs to become `dev`.
  - **Corrected while implementing (2026-09-08):** changing the PR base alone was a live bug. The workflow runs on `schedule`/`workflow_dispatch`, where a bare `actions/checkout` follows the event's ref: the *default* branch on a schedule — still `main` until the flip below — and whatever the "Use workflow from" picker resolved on a dispatch. Neither is tied to the branch the scan is about, so the daily run would have scanned `main`'s tree while diffing against `:dev` images now built from `dev`. Two effects, both silent: the lockfiles were resolved from `main`'s manifests, so any dependency change made on `dev` since the branch point would be overwritten by a lockfile that never saw it; and the vulnerability delta was measured on `main`'s tree, so the whole `main..dev` gap was attributed to the lockfile update. (The blast radius was the lockfiles, not the tree — `create-pull-request` commits the working-tree diff, which `add-paths` limits to `uv.lock` and `pnpm-lock.yaml`, onto the base branch. An earlier draft of this bullet said the PR would revert everything merged since the branch point; it would not, and the mechanism does not support that claim.) Every checkout now takes its commit from a `base` job that resolves `BASE_BRANCH` once, which the PR base and the close-step lookup also read — so the workflow is correct regardless of the default-branch setting, and all three jobs see one commit even when a merge lands mid-run. That pin covers the *scan*, not the PR: `create-pull-request` cherry-picks onto the base branch's live tip with `--strategy-option=theirs`, so a lockfile landing on `dev` mid-scan would lose to the older one the run resolved. A guard before the PR step drops the run instead, and the next day's scan starts from the new tip.

**pre-commit**
- `no-commit-to-branch` in `.pre-commit-config.yaml` only guards `main`, it should guard `dev` too. Its comment ("this repo has only `main`") and the matching note in [ADR-0018](0018-pre-commit-hooks.md) are then stale.

**Workflows**
- Add `dev` to the `push: branches: [main]` trigger in `ci.yaml` and `integration.yaml`, since that trigger is the post-merge run and merges now land on `dev`. We still need it despite the PR runs, because merging makes a new commit that no PR run has seen, and `release.yaml` looks up CI results by commit SHA. Without it, a git tag cut on `dev` would fail the CI check even though everything passed.
  - **Added while implementing (2026-09-08):** `ci.yaml`'s concurrency block also had to learn about `dev`. It grouped `main` by commit and never cancelled it, precisely so a tag would find its own green run, and cancelled everything else. Adding the trigger alone would have put `dev` on the cancelling side, where the next merge kills the run a release candidate is about to be cut against — losing the evidence this bullet exists to preserve. Both long-lived branches now group by commit and are never cancelled.
- `dev-images.yaml` publishes the `:dev` image tags on pushes to `main`. It should follow `dev` instead, since those tags are meant to track integration and `main` only moves at release time.
- `release.yaml` checks that the tagged commit is on `main` before it routes the lanes, so right now that check hits every git tag, rc and PyPI ones included. Since release candidates are cut from `dev`, that check has to move after the routing and go per-lane: platform release tags on `main`, rc tags on `dev`, and PyPI tags left on `main`.
  - **Revised while implementing (2026-09-08):** the bullet's per-lane split is right, and each lane ended up pinned to exactly one branch — but not the ones first written down. Two cases surfaced while implementing it, both settled by decision rather than by loosening the gate:
    - **Hotfix candidates.** Implementing the gate surfaced that a `dev`-only rc rule makes `ghga/17.0.1-rc.1` unbuildable, since hotfixes never touch `dev`. That was first handled by accepting rc tags on `main` as well, which deferred the question rather than answering it. **Settled 2026-09-08 by the decider: hotfixes get no candidate** (recorded in the Decision above), so the rc lane is `dev`-only after all and rejecting a `-rc.N` tag on `main` is now the intended behaviour, not an accident.
    - **Component releases serialize behind platform releases.** A PyPI version bump lands in `dev` and only reaches `main` at the release merge, so `hexkit/8.7.0` cannot be tagged until the next platform release — a coupling this ADR introduced without weighing it against [ADR-0004](0004-versioning-and-release-by-tag.md)'s independent component lifecycle. Accepting PyPI tags on `dev` too was considered and rejected. **Settled 2026-09-08: keep the lockstep**, because one release cadence is simpler than two. So "PyPI tags left on `main`" stands as written, now deliberately.
  - **Also while implementing:** the tree-reading half of the routing step (`python3 scripts/image_members.py`) moved *behind* the gate. Routing needs only the ref string, so the gate now runs before anything from the tagged tree executes — previously the on-`main` check ran first and gave that ordering for free.
- `integration.yaml`'s concurrency block is **deliberately left cancellable** (decided 2026-09-08), unlike `ci.yaml`'s. It groups by ref with `cancel-in-progress: true`, so a post-merge integration run on `dev` is killed by the next merge. That is the same behaviour `main` had before the merge traffic moved; it is acceptable here and not in `ci.yaml` because `release.yaml` reads CI results by commit SHA and never reads integration results, so a cancelled integration run cannot cost anyone a release. Superseding a ~1h job is worth more than the redundant verdict.

**Local tooling**
- `scripts/affected_targets.py` defaults `--base` to `origin/main`, as does the `affected` recipe in the justfile. That needs to be switched to `origin/dev`.

### Remaining setup

The tree is done; these are repo settings and in-flight work, and have to be done through
GitHub rather than a commit. Until they are, `dev` works but nothing steers people onto it.

**The default-branch flip is the one with a deadline.** GitHub runs a `schedule` trigger from
the *default branch's* copy of the workflow file, whatever branch the work merged into. So
between merging this and flipping the default, the nightly `security-scan.yaml` is still
`main`'s version: scanning `main`, diffing against `:dev` images now built from `dev`, and
opening its PR with `base: main` — the exact bug this change set fixes, still running once a
day at 04:17 UTC. Nothing breaks, but the fix is not in force until the flip, so do the two
together rather than leaving a gap over a weekend. (`renovate.yaml` is untouched here, so
which copy of it runs makes no difference — what retargets Renovate is the flip itself.)

- Make `dev` the default branch, and protect it the way `main` is protected. Renovate has no
  `baseBranches` in `renovate.json5`, so the flip is what retargets it — no config change
  needed. It does leave Renovate's existing `main`-based PRs stranded, though, exactly as it
  strands the lockfile PR below: `renovate/dhi.io-node-base-image` and
  `renovate/dhi.io-python-base-image` are superseded by whatever the next Monday run opens
  against `dev`, so close them alongside that one. `renovate.yaml` itself needs no change; it
  has no checkout at all and drives the Renovate action over the API.
- Keep "Require linear history" *off* for `main` — it would forbid the release merge commit —
  and forbid squash-merging and rebasing there for the same reason.
- Retarget the open pull requests that still name `main` as their base. `dev` was branched
  from `main` at the same commit, so nothing needs rebasing yet; that stops being true as soon
  as the first PR merges into `dev`.
- Close the existing `automated/lockfile-security-update` PR by hand, **after** the flip, not
  before. It is open against `main`, and the new close step looks up its PR with `--base dev`,
  so it can never match that one — but that is only true once the flip makes the nightly run
  use this version of the workflow. Until then `main`'s copy is what runs, it still looks up
  `--base main`, and it will keep that PR refreshed (or close and reopen it) every morning, so
  closing it early just means closing it again. Delete the branch with it: the `dev`-based run
  reuses the same `automated/lockfile-security-update` name, and leaving the old PR pointed at
  that branch means the first post-flip run rewrites the branch under it.

## Open questions

These are being settled separately. None of them change the branch layout.

- How a tested candidate becomes the production release: promoting the same image digests, or rebuilding at the release tag. The main point here is that by rebuilding images for production we would deploy something that is technically not tested, even if there should be no material differences. For now we are rebuilding images, but it is a temporary solution until this question is answered.
- Likewise, how a promoted image would be tagged.
- Whether `release.yaml` needs to tell promoting apart from building, since a hotfix on `main` has no candidate to promote. **Amended 2026-09-08:** that premise is now a decision rather than an assumption — hotfixes get no candidate (see the Decision), so "hotfix" is a reliable synonym for "nothing to promote" and this question only has to cover the normal `dev` → rc → `main` path.
- [ADR-0004](0004-versioning-and-release-by-tag.md) was amended on 2026-09-01 for the pre-release cut moving to `dev` and the per-lane branch gate. It will need a further amendment if the questions above resolve toward promoting digests, since that's where release tagging/image publishing/promotion belong.

## Alternatives considered
- **Trunk-based on `main` alone** (what we do now). Rejected: no branch represents the released state and `main` is always in flux.
- **Trunk-based on `main` with merge queues** (remix of status quo).
Rejected: merge queues would allow PRs to pile up against `main` until certain criteria green-lit the merge.
This would, in essence, give the same end result as the proposed strategy, except all the changes that would be merged into `dev` would be in a limbo state against `main`.
It would automate the role of `dev` but in exchange we would lose the concrete state tracking and conceptual simplicity offered by an actual branch.
This approach might be revisited in the future as part of a production CD strategy when the GHGA platform has gelled more and changes are less disruptive/conflicting.
- **Release branches per version** (full Git Flow). Rejected: with controlled platform releases and hotfixes applied to the latest release only, `main` already serves that role; per-version maintenance branches are not something we want or have the user base to justify. We tried doing this with `hexkit` early on, up through about v3 or v4, but it got tedious quickly.

## Final Note
The strategy adopted through this ADR is not binding, it's merely a commitment to *try it out* long enough to be able to judge its suitability for our needs.
