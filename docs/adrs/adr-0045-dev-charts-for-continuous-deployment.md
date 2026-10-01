---
status: proposed
date: 2026-10-01
tags: [deploy, release]
related: [ADR-0027, ADR-0037, ADR-0038]
---

# ADR-0045 — Publish dev charts on the mono image for continuous deployment

## Summary

In the context of **running the `dev` branch continuously on a cluster of our own**

facing **charts that are published only at a platform release, and dev images that exist only as the mono image under a mutable `:dev` tag**

we decided for **publishing every member chart to GHCR on each merge to `dev`, versioned `0.0.0-dev.<run number>.<attempt>`, generated with `--mono` and pinned to the image digests built in the same run**

and neglected **per-member dev images, setting the images in the cluster's own values, and a version taken from the commit SHA**

to achieve **a cluster that rolls out each merge in order, from charts whose image is fixed when they are built, at no extra build cost**

accepting that **the dev cluster runs an image production never runs, and that dev charts and image tags pile up on GHCR**.

## Details

### Context

Charts are stamped and pushed only by a `ghga/X.Y.Z` release ([ADR-0027](adr-0027-versioning-and-release-by-tag.md)), so a cluster tracking `dev` has nothing to pull between releases.
`dev-images.yaml` publishes one image for all Python members, the mono image, plus the front-end image, under the mutable `:dev` tag on GHCR ([ADR-0037](adr-0037-image-signing-sbom-provenance.md)).
A mutable tag never triggers a rollout, and the generated charts point each member at its own image, which dev CI does not build.

The mono image carries every member's console script on its `PATH`.
Every member chart already starts its service by that script (`command: [<package>]`), not by the image's entrypoint, which is how the demo runs on the mono image today.

### Decision

- **Mono image.**
  `create_charts.py --mono` points every Python member chart at the `platform` image and leaves its command as it is.
  The front end keeps its own image.
- **Version.**
  Each run of `dev-images.yaml` is `0.0.0-dev.<run number>.<attempt>`, as chart version, `appVersion` and an extra image tag beside `:dev`.
  SemVer compares numeric prerelease fields as numbers, so the newest merge is always the highest version and a CD tool following `>=0.0.0-0` picks it.
  The attempt makes a re-run a new version: the mono build is not reproducible, so a re-run under the same version would change its digest without the cluster rolling out.
- **Digests.**
  The chart job takes the digests the image job just pushed and pins them in the charts, as the release lane does.
  It fails if a chart is left without one, which is what a member whose image the job does not build would get.
- **Scope.**
  Only the generated member charts are published, to `oci://ghcr.io/ghga-de/ghga/charts`.
  `aai`, `ghga-common` and `ghga-demo` are not; `ghga-common` is bundled into each chart.
- **No promise.**
  Like `:dev`, dev charts are integration state, not releases.
  They are not signed, and they are published regardless of `ci.yaml` on the merge commit.

### Consequences

- A cluster can follow `dev` with a semver range and no manual step.
- The dev cluster tests the mono image, not the per-member release images: a fault in one member's image alone reaches production first.
- Dev and release charts live in different registries, so a range on one never picks up the other.
  Switching a cluster to releases means changing the chart source, not only the version.
- A run cancelled by a newer merge partway through the push leaves some charts at the older version until the newer run finishes.
  Each chart still pins a valid digest.
- The run number restarts at 1 if `dev-images.yaml` is renamed or recreated, and versions would then go backwards; raising the `0.0.0` base in `DEV_VERSION` restores the order.
- Every merge adds one version per member chart and one image tag, and nothing prunes them yet.

### Alternatives

- **Per-member dev images.**
  Matches production, but adds the release lane's per-member build to every merge to `dev`.
- **Images set in the cluster's values.**
  No change in this repo, but the chart version and the image it runs stay in step only by convention.
- **The commit SHA as version.**
  SemVer sorts alphanumeric prerelease fields as text, so the newest commit would not be the highest version.
