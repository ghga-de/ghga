---
status: accepted
date: 2026-08-28
tags: [process, release]
related: [ADR-0027]
---

# ADR-0038 — Branching, merging and naming

## Summary

In the context of **one repository in which many developers and several large features
change the same code between platform releases**

facing **a `main` branch always in flux, which hid what was in production, and names for
branches, pull requests and commits that drifted apart**

we decided for **two long-lived branches, `dev` for integration and `main` for the
latest release, with pull requests squashed into `dev` and all three names derived from
one grammar of kind, stack and description**

and neglected **trunk-based development with or without merge queues, release branches
per version, merge commits or rebase merges per pull request, and member-based branch
names**

to achieve **a branch that always shows the released state, a history of one readable
commit per change, and stacks that hold together in the pull request list**

accepting that **hotfixes must be merged back into `dev`, merged work and component
releases wait for the platform release, and every squash merge needs its commit message
rewritten**.

## Details

### Context

In the old repositories, one developer at a time worked on a small scope, and feature
branches merged straight into `main`. What was released could be read off the date of
the last release. In the monorepo, many people and several large features change the
same repository, and with the same flow the released state was buried under work for the
next release within days.

A change carries three names: its branch, its pull request and the commit it lands as.
Left to taste, they drifted apart, in the three lists where work is found. Stacks of
pull requests cannot be grouped in the pull request list, and once pull requests are
squashed, their titles become the permanent history.

### Decision

**Branches.**

- `main` is the latest platform release; its HEAD is always a released state.
- `dev` is the integration branch and the repository default. Work is cut from `dev` and
  merged back into it by pull request.
- Release candidates are tagged on `dev`. A release merges `dev` into `main`, and the
  release tag is cut on `main`.
- Hotfixes are cut from `main`, merged back into it and released without a candidate,
  then merged into `dev`.
- Component releases are tagged on `main` as well, in lockstep with the platform
  ([ADR-0027](0027-versioning-and-release-by-tag.md)).
- Long-lived feature branches are allowed, decided case by case.

**Merging.** Pull requests into `dev` are squashed, so one pull request becomes one
commit. `main` takes merge commits only: the release merge and hotfixes. Rebase merges
are off.

**Names.** Branch, pull request title and commit message follow one grammar:

- A **kind** from a short list shared with Conventional Commits: `feat`, `fix`, `docs`,
  `refactor`, `test` and `chore`, plus `hotfix`. `hotfix` is the one kind that names its
  base branch, and it becomes `fix` in the commit.
- A **stack name** for work in a stack: in the branch, in brackets in the title, and as
  the commit scope.
- A short **description**, with the YouTrack key where there is one.

The commit message is rewritten at merge time as a Conventional Commit ending in the
pull request number. A coding agent is credited in the pull request description by how
much it drafted, never in a commit trailer.

The formats, examples and tag rules per lane are in
[docs/conventions.md](../conventions.md#branching).

### Consequences

- `main` shows what is deployed and `dev` what is not; a release is a reviewable pull
  request plus a tag.
- Every hotfix must be merged back into `dev`, unless `dev` already carries an
  equivalent fix.
- Merged work waits for the next release, and so do component releases.
- `dev` has one commit per pull request, even for a long stack. Intermediate commits
  stay readable in the pull request that the commit's `(#N)` links to.
- "Require linear history" cannot enforce squashing on `dev`, because the hotfix
  back-merge is a merge commit, and must stay off for `main`. Squashing and naming are
  conventions that nothing enforces.
- Production images are rebuilt at the release tag and deployed to staging once more.
  Whether to promote the candidates' tested digests instead is still open.
- The stack name makes up for stacks having no name in the pull request list, and should
  be retired once they do.
- The team adopted this model as a trial, to be judged once it has been used long
  enough.

### Alternatives

- **Trunk-based on `main` alone.** No branch shows the released state.
- **Merge queues on `main`.** They automate what `dev` does but leave pending work in
  limbo instead of on a branch. Worth revisiting for continuous delivery to production.
- **Release branches per version.** We hotfix only the latest release; maintenance
  branches in `hexkit` proved tedious.
- **A merge commit per pull request.** A long stack lands as many merge commits plus
  every intermediate commit.
- **Rebase merges.** Keep every intermediate commit and lose the merge record.
- **Branch names prefixed by member.** Much work crosses members or belongs to none, and
  the diff shows which members a change touches; only the name records its kind and
  base.
- **Conventional-Commit pull request titles.** They would make the prefill right, but
  titles are read as a list by people who do not write the code, and the body needs
  cutting at merge time anyway.
