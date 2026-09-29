# Releases

How a release is cut, built and published: the two lanes, their tags, how versions are
stamped, how the PyPI lane decides what to upload, where artifacts go, and how release
notes are made. The decisions behind it are
[ADR-0027](adrs/adr-0027-versioning-and-release-by-tag.md) (lanes and tags),
[ADR-0033](adrs/adr-0033-capability-markers-and-placement.md) (markers),
[ADR-0038](adrs/adr-0038-branching-strategy.md) (branches),
[ADR-0037](adrs/adr-0037-image-signing-sbom-provenance.md) (signing) and
[ADR-0043](adrs/adr-0043-release-notes.md) (release notes). The workflows are
`.github/workflows/release.yaml` and `pypi-publish.yaml`.

In short: `ghga/X.Y.Z` builds every deployable image and chart from one commit;
`name/x.y.z` and `packages/x.y.z` publish PyPI-lane members. A tag push verifies and
builds; publishing is a deliberate step, and so is publishing the release notes.
Everything is tagged on `main`, except release candidates on `dev`.

## Lanes and members

Each member's `[tool.ghga]` markers put it in a lane
([conventions](conventions.md#toolghga-capability-markers)). `scripts/image_members.py`
and `scripts/pypi_members.py` enumerate the lanes from them.

| Lane | Members | Artifacts |
|---|---|---|
| platform | all services, `auth-km-jobs`, `metldata`, the front end, `ghga-datasteward-kit` | images and charts to Docker Hub; datasteward-kit is run from a clone of the tag |
| pypi | `hexkit`, `ghga-service-commons`, `schemapack`, `ghga-arcticfreeze`, `ghga-jsonsubschema`, `ghga-connector`, `ghga-validator`, `ghga-transpiler` | wheels to PyPI |
| none | `ghga-event-schemas` | embedded in the images from source, never published on its own |

## Tags and branches

| Tag | Lane | Cut on |
|---|---|---|
| `ghga/X.Y.Z` | platform release | `main` |
| `ghga/X.Y.Z-rc.N` | release candidate | `dev` |
| `name/x.y.z` | PyPI, that member only (targeted) | `main` |
| `packages/x.y.z` | PyPI, every member behind the index (sweep) | `main` |

`release.yaml` verifies rather than re-tests. Its `resolve` job routes the tag to a lane
from the tag name alone, then checks that the tagged commit is on that lane's branch and
has a green CI run. The branch check tests the branch's **first-parent chain**, not
reachability: the release merge and hotfix back-merges make every commit reachable from
both branches. It runs before any code from the tagged tree executes. For a targeted tag
it also checks that the tag matches the member's declared version.

A PyPI version bump lands on `dev` and reaches `main` at the release merge, so component
releases wait for the platform release.

## Platform lane

The platform version continues the 15.3 series the charts already carry; the first
candidates are `ghga/15.3.1-rc.N`.

A `ghga/X.Y.Z` tag builds **all** images from the tagged commit, with no affected-only
shortcut; layer caching keeps unchanged members cheap. Charts are packaged in the same
run and stamped with the same version.

Images embed internal libraries from workspace source at that commit, never from PyPI.
`scripts/stamp_platform_version.py` stamps the version after dependencies are installed,
so `uv.lock` and member `pyproject.toml` files stay untouched:

- The member's dist-info `Version:` becomes the platform version, which services report
  through `importlib.metadata`.
- Other workspace libraries in the image get a PEP 440 local suffix,
  `8.6.0+ghga.17.0.0`: constraints still match, SBOM metadata stays coherent, and PyPI
  rejects local versions.
- OCI labels `org.opencontainers.image.version` and `.revision`, and the
  `GHGA_PLATFORM_VERSION` environment variable, carry the version and commit.

Local builds take the same path with `0.0.0+dev.g<sha>`, so a local build matches a
release build.

`ghga-datasteward-kit` is not published: stewards run `git clone -b ghga/X.Y.Z` and `uv
run ghga-datasteward-kit`, and `uv.lock` at the tag gives the tested combination.

### Candidates and production

`ghga/X.Y.Z-rc.N` runs through the same workflow on `dev` and is deployed to staging.
The production release merges `dev` into `main`, tags `ghga/X.Y.Z` and rebuilds the
images; the rebuilt images go to staging once more before production. Promoting the
candidate's digests instead is an open question in ADR-0038.

## PyPI lane

### What gets uploaded

`pypi-publish.yaml` plans the upload against the index, not a git diff: every member
whose declared version is above the latest one PyPI serves, dependencies first. So a
bump made weeks ago still goes out, a missed release repairs itself on the next run, and
a re-run uploads nothing twice. A member *behind* the index is skipped, not an error.

The tag sets the scope, passed from `release.yaml` as a mode:

- **targeted** (`name/x.y.z`): that member alone. A tag naming a member with nothing to
  publish fails rather than succeeding as a no-op.
- **sweep** (`packages/x.y.z`): the whole gap. The version in the tag is only a label.

### Closure trains

A published tool must not reach the index before a version it needs. When a member of a
tool's internal closure (for `ghga-connector`: `ghga-service-commons`, `hexkit`) is
itself a candidate, a sweep uploads it in the same run, dependencies first. A targeted
tag refuses instead and names both ways out: a `packages/` tag, or tagging the
dependencies first. The refusal does not look at pins: an exact pin would give an
uninstallable wheel, a range an untested one, and the remedy is the same.

The lane adds no pins and relaxes none; a member's declared constraints are the
contract. A library that changed without a bump does not block a dependant, which
resolves it from the index like any consumer.

### Drift gate

CI's `check-pypi-drift` (`scripts/pypi_drift.py`) fails when a member's shipped content
changed while its declared version is already on PyPI, so one version never means two
contents. Shipped content is the member's packaged roots plus `pyproject.toml`, `README`
and `LICENSE`; tests and internal docs do not count. It does not reuse
`affected_targets.py`, which expands to dependents and repo-wide paths — right for
tests, wrong for spending versions.

The check reads the index when it runs. If a tag publishes the same version between a
pull request's run and its merge, the result is stale, and the post-merge run on `dev`
fails; the fix is a second bump.

### Published-combo matrix

`check-published-combo` tests each member against PyPI-resolved dependencies across its
supported Python range (`TEST_PYTHONS` in `scripts/pypi_members.py`). An internal
dependency is built from the repo only when it is a release candidate, so the tested
combination is the one that ships. It runs after the drift gate, which it depends on.

## Publish targets

- **Images:** `docker.io/ghga/<member>`, pushed with the org's `DOCKERHUB_USERNAME` and
  `DOCKERHUB_TOKEN`. A tag push builds only; publishing is a `workflow_dispatch` against
  the tag with `push` set. GHCR (`ghcr.io/ghga-de/ghga`) holds only the `:dev` and
  `:updated` scratch tags of `dev-images.yaml` and `security-scan.yaml`.
- **Charts:** OCI artifacts at `oci://registry-1.docker.io/ghga/<chart>-chart`, from the
  same run and commit as the images. The `-chart` suffix avoids colliding with the image
  of the same name, since Docker Hub paths have two segments. Login targets `docker.io`,
  because only that alias stores credentials where ORAS looks them up.
- **Wheels:** PyPI, rehearsed on TestPyPI in the same run with the same files, both by
  trusted publishing. The `publish` job runs in the `ghga-pypi` environment, whose
  required reviewers gate it. Each index has its own trusted-publisher entry, matched on
  owner, repository, workflow file and environment. Neither upload uses `--check-url`: a
  rebuilt wheel never matches the index byte for byte. `pypi-publish.yaml` has no
  dispatch trigger of its own, so every publish passes `resolve`.

## Release notes

The platform and each library and tool get a draft GitHub release
([ADR-0043](adrs/adr-0043-release-notes.md)), generated by `scripts/release_notes.py`.
A tag that already has a release is left alone.

A release therefore starts with pushing its tag, from the command line or any other git
client. Do not create the release in the GitHub UI: GitHub creates the tag only when
that release is published, and the workflow then finds a release it leaves untouched,
so the notes are never generated. Once the tag is pushed, edit the draft the workflow
created.

- `release.yaml` drafts one for a `ghga/` tag once its images and charts are built. It
  also tags the companions, the platform-lane members with `notes = true`, now
  `metldata` and `ghga-datasteward-kit`, as `name/X.Y.Z` with the platform version and
  drafts theirs, unless nothing they ship has changed.
- `pypi-publish.yaml` drafts one for each member it uploaded. A sweep first tags each of
  them as `name/x.y.z`.

The draft lists the pull requests since the previous release of the same name, grouped
by commit type; a first release lists those since the first `ghga/` tag. For the
platform, those are the ones that touched `services/`, `frontend/`, `deploy/` or
`uv.lock`; for a library or tool, those that changed its shipped files. The platform's
draft also names each library and tool that changed, with its version and a link to its
release; a release tagged after the draft is not linked yet. The summary headings above
the lists are left for you to fill in:

1. Open the draft under the repository's releases.
2. Under New features, Changes and Bug fixes, write a few short sentences each for
   users: no pull request numbers, no minor changes or refactorings, and one item for a
   feature that spans several services. Delete a heading with nothing worth saying, and
   the hint comments.
3. Publish the draft.

To see the notes before tagging, or to compare with a ref other than the previous tag:

```sh
uv run --script scripts/release_notes.py ghga/15.4.0 --previous ghga/15.3.1
```

## Open at cutover

Listed with the other cutover leftovers in the
[runbook §7](migration/runbook.md#7-cutover-checklist): platform-lane member
versions are to be fixed at `0.0.0`, with stamping supplying the real one;
`ghga-datasteward-kit` pins `requires-python` to the workspace baseline; and
`auth-km-jobs` moves to `services/`.
