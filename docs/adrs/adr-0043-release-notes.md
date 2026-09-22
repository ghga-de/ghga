---
status: proposed
date: 2026-09-22
tags: [release, process]
related: [ADR-0027, ADR-0038]
---

# ADR-0043 — Release notes as drafted GitHub releases

## Summary

In the context of **releasing the platform, the libraries and the tools from one
repository**

facing **GitHub's generated release notes, which list every pull request in the
repository and cannot tell one member's changes from another's**

we decided for **a draft GitHub release for the platform and for each library and
tool, with hand-written summaries above a list of the pull requests that touched its
files, which the release workflow generates**

and neglected **GitHub's generated notes, path labels, changelog files and releases per
service**

to achieve **notes a user can read at a glance, with the full list for whoever needs
it, and no bookkeeping in pull requests**

accepting that **someone fills in the summaries of each generated draft and then
publishes it, and that the list is only as good as the commit messages**.

## Details

### Context

The repositories this one replaced each published GitHub's generated release notes: a
list of the pull requests merged since the previous release. In one repository that
list covers every member, while a library user wants only the changes to that library.
GitHub can filter the list by label, not by path.

Releases come in two lanes ([ADR-0027](adr-0027-versioning-and-release-by-tag.md)). A
`ghga/X.Y.Z` tag releases the platform: the services, the front end and their charts.
The libraries and tools are dependencies and add-ons of the platform. A `name/x.y.z`
tag publishes one PyPI-lane member, and a `packages/x.y.z` tag every member the index is
behind on. Two members with a release of their own to users are on the platform lane
all the same: `metldata`, a library that also runs as a service, and
`ghga-datasteward-kit`, which stewards run from a clone of the platform tag.

Squash commits carry the commit grammar `type(scope): description (#PR)`
([ADR-0038](adr-0038-branching-strategy.md)), so their type and pull request number can
be read from the history.

A plain list of pull requests does not tell a user what a release means for them. That
takes a short summary, which only a person can write.

### Decision

We keep release notes as GitHub releases, one for each platform release and one for
each release of a library or tool. There are no changelog files in the repository. A
release lists the pull requests since the previous release of the same name that
touched its files. A final release compares with the previous final release, so it
covers the whole cycle; a candidate compares with the previous tag, candidate or not.

- **Platform:** a `ghga/` tag lists the pull requests that touched the services, the
  front end, the charts in `deploy/` or `uv.lock`. The lock file counts because a
  dependency update changes the images. The libraries and tools are part of the
  platform too, but their pull requests are listed in their own notes. The platform's
  notes name each library and tool whose shipped files changed, with its version before
  and now and a link to its release.
- **Libraries and tools:** a `name/x.y.z` tag lists the pull requests that changed what
  the member ships. That is the set the drift gate uses: the packaged roots,
  `pyproject.toml`, the README and the licence.
- **Companions:** `metldata` and `ghga-datasteward-kit` have no tag of their own. A
  platform release tags each of them as `name/X.Y.Z` with the platform version, the
  version stamping gives them in the images, and drafts their release like a library's.
  A companion with no change since its previous release gets neither. Of `metldata`, the
  library is the companion, and its chart belongs to the platform.
- **Sweeps:** a `packages/` release tags every member it uploaded as `name/x.y.z`, so
  that the next release of each member has a tag to compare with.
- **No release page:** `ghga-event-schemas` is embedded in the images only, and
  `auth-km-jobs` is a service, counted with the platform.

`scripts/release_notes.py` generates the notes, and the release workflows create them
as a **draft** release. A tag that already has a release is left alone. The notes have
two parts:

1. **Summaries:** New features, Changes and Bug fixes, each a few short sentences in
   plain language, with no pull request numbers and without minor changes or
   refactorings. A feature that spans several services or pull requests is one item,
   and a library change platform users notice is described in the platform's terms.
   The script supplies the headings, and only those that apply to the release. Whoever
   cuts the release writes the text or asks an agent to draft it. They delete a heading
   with nothing worth saying.
2. **Pull requests:** grouped under Features, Fixes, Documentation, Refactoring, Tests
   and Chores by the commit type. Breaking changes are marked and come first in their
   group. A commit outside the grammar is listed under Chores, and empty groups are
   left out.

Only the platform's final releases are marked as the repository's latest release.

### Consequences

- A release is not finished until someone writes its summaries and publishes the
  draft. Publishing images and charts is a manual step too, so this adds to that step
  rather than creating a new one.
- The commit grammar now affects what users read: a wrong type puts a pull request in
  the wrong group, and a vague description stays vague in the notes.
- A pull request merged with a merge commit, such as a hotfix or a Renovate update, is
  listed once under its title, with its type taken from the branch name.
- The first monorepo release of a member has no earlier tag to compare with, so its
  notes list no pull requests. `--previous` gives the script a starting point by hand.
- The releases page mixes platform and member releases; GitHub's search filters it by
  name.

### Alternatives

- **GitHub's generated notes:** each library's notes would list every pull request in
  the repository.
- **Labels by path:** an action labels each pull request by the members it touches, and
  a configuration per member picks the labels. That is a configuration file per member,
  and labels only for pull requests made after the labeller was set up. The paths
  answer the same question from the history.
- **Changelog files:** they would need an entry in every pull request, cause conflicts
  in parallel work, and say what the pull request titles already say.
- **Releases per service:** services are deployed together and released in lockstep, so
  one set of platform notes covers them.
- **Library pull requests in the platform notes:** every library change would be listed
  twice, and users of the platform would read about changes they see only through the
  services. The versions and links say what changed, and a change platform users notice
  belongs in the platform's summary.
- **Generated summaries:** a summary rewritten from the commit list adds little to the
  list. The value is in choosing what matters, which is left to the person releasing.
