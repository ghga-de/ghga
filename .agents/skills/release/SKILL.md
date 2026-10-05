---
name: release
description: Cut a GHGA release by tag, a platform release or candidate or a PyPI release of one member or the whole lane, with the checks before each step that cannot be undone. Run as /release with a name and a version, such as /release ghga 15.4.0 or /release hexkit.
disable-model-invocation: true
---

# Releases

The lanes, tags, branches and workflows are in [releases.md](../../../docs/releases.md); read it first.
This skill gives only the order of the work, the commands, and the checks before each step that cannot be undone.

## Work out the release

1. Map the arguments to a tag with the table in releases.md's "Tags and branches".
   `ghga X.Y.Z` is a platform release, `ghga X.Y.Z-rc.N` a candidate, a PyPI-lane member's name a targeted `name/x.y.z`, and `packages` a sweep.
   Any other member has no tag of its own: a service ships with `ghga/`, `ghga-datasteward-kit` is tagged by the platform run, and `ghga-event-schemas` is never published.
2. Without a version, propose one: the next after `git -c versionsort.suffix=-rc tag -l 'ghga/*' --sort=-v:refname | head -3` for the platform, where the suffix setting sorts a candidate below its final release, the declared version in the member's `pyproject.toml` for a targeted tag, the platform version as the label of a sweep.
3. Ask when the release does not follow: a version not above the last tag, a skipped candidate number, a declared version that differs from the tag.
4. Name the tag, the branch, the commit and what the tag push will do, and wait for the dev to agree.

## Checks before the tag

Run them in this order and stop at the first that fails.

1. `git fetch origin --tags`; the commit to tag is the tip of `origin/<branch>`, never a local branch.
2. The tag is free: `git ls-remote --tags origin <tag>` prints nothing, and `gh release view <tag>` finds no release.
3. CI on that commit is green: `gh run list --workflow ci.yaml --commit <sha>`.
   `resolve` waits for a run still in flight, but fails on a red one.
4. For a final platform release, the commit is a merge on `main`: of the release PR (`Release ghga/X.Y.Z`, `dev` into `main`), or of a hotfix.
   Both take a merge commit, never a squash, and the dev merges; you cannot.
5. For a PyPI tag, run the plan on a clean checkout of that commit.
   A targeted tag takes `uv run --script scripts/pypi_members.py --plan --target <name>`, which refuses when a dependency in the member's closure waits too: tag that one first, or sweep.
   A sweep takes `--plan` alone, and its list is what goes out; an empty plan means nothing to release.
6. For a final `ghga/` or targeted tag, tag locally and show the dev the notes the workflow will draft, as in releases.md's "Release notes".
   Run `git tag <tag> <sha>`, then `uv run --script scripts/release_notes.py <tag>`.
   The script needs the tag in the clone; if the dev does not go on, delete it with `git tag -d <tag>`, so no later push takes it along.
   A sweep has no notes of its own: the script refuses a `packages/` tag, and each member's draft follows its upload.

## The steps that cannot be undone

Print each one as a command, run it only after the dev's go in this session, and one at a time.

1. Push the tag: `git tag <tag> <sha>` if it is not there yet, then `git push origin <tag>`.
   The push runs `release.yaml`: a build without publishing for `ghga/`, the upload for a PyPI tag.
2. For `ghga/`, final or candidate, publish the images and charts with `gh workflow run release.yaml --ref <tag> -f ref=<tag> -f push=true`.
   `--ref` and `ref` name the same tag, or `resolve` fails.
   The dispatch builds again and queues behind the tag push's run, so waiting for that run first is optional.
3. For a PyPI tag, the `publish` job waits for a reviewer of the `ghga-pypi` environment; the dev approves it in the run.
4. Publishing the release notes is the dev's, in the GitHub UI (below).

Never create a release with `gh release create` or in the GitHub UI: GitHub then creates the tag itself, and the notes are never generated.

## After

1. Watch the run: `gh run list --workflow release.yaml --limit 3`, then `gh run view <id>` for the failing job.
2. For a final release, the workflow leaves a draft: `gh release view <tag>`.
   Check it with the dev against releases.md's three steps: summaries under New features, Changes and Bug fixes written for users, no PR numbers, empty headings and the hint comments deleted.
   The platform draft names the libraries and tools that changed; `ghga-datasteward-kit` gets a draft of its own when it changed.
3. The dev publishes each draft; `gh release edit` is denied to agents.
4. After a hotfix release on `main`, `main` is merged back into `dev` ([branching](../../../docs/conventions.md#branching)).

## Traps

- Push one tag per command: GitHub starts no workflow when more than three tags are pushed at once.
- A pushed tag is never moved or deleted without the dev: its run may have built or published already.
- A PyPI version bump merged on `dev` reaches `main`, and so PyPI, only with the next platform release.
- A version stranded on TestPyPI by a failed run collides on the rehearsal; only a new version bump clears it.
- A targeted tag for a member with nothing to publish fails, by design.
- A candidate gets no release notes; `release_notes.py` still prints its changes since the previous tag.
