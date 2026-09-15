---
status: accepted
date: 2026-08-14
tags: [security, release]
related: [ADR-0027, ADR-0031]
---

# ADR-0037 — Sign published images and attach SBOM and provenance

## Summary

In the context of **images published from this repo, to Docker Hub for production and to
GHCR for development**

facing **nothing downstream being able to verify that an image came from this
repository's CI, or what went into it**

we decided for **keyless cosign signatures on the image digest, SBOM and provenance
published as signed attestations, and admission control left to the platform layer**

and neglected **managed signing keys, the SLSA GitHub generator, and a Kyverno policy in
this repo**

to achieve **a verification foundation that a platform policy can pin, with no private
keys to manage**

accepting that **every signature is recorded in the public Rekor log, and the provenance
is attested by our own workflow**.

## Details

### Context

Every deployable image is built on Docker Hardened Images and published by one of two
workflows: `dev-images.yaml` pushes `:dev` tags to GHCR on every merge to `dev`, and
`release.yaml` pushes release images to Docker Hub
([ADR-0027](0027-versioning-and-release-by-tag.md)). Neither produced an SBOM,
provenance or a signature.

Admission control, such as a Kyverno policy that verifies images, is an environment-wide
concern and belongs to the platform repository, like the cluster auth policy
([ADR-0031](0031-helm-chart-boundary-hybrid.md)). This repo's part is the producer side:
sign what it publishes, and attach what a policy verifies against.

### Decision

- **SBOM and provenance** come from buildx attestations (`--sbom=true`,
  `--provenance=mode=max`) on every push of both workflows.
- **Signing** is keyless cosign through GitHub Actions OIDC, on the resolved digest
  rather than the tag, and recursive over the image index and its platform manifests.
- **Attesting:** SBOM and provenance are also published with `cosign attest` against the
  same digest. cosign, and any policy built on it, cannot find the attestations buildx
  stores inside the index.
- **Verification identity** is the certificate's OIDC issuer and the publishing workflow
  at the ref it ran on. Consumers pin that; the [image
  docs](../../docker/README.md#verifying-images) list it.
- **No Kyverno policy in this repo**, not even an example: a copy here could not be run
  or tested, and would drift from the one that enforces.

### Consequences

- The public, permanent Rekor log records which workflow built which digest and when,
  production images included.
- There are no private keys to store or rotate.
- Every push becomes an OCI index, even for one platform.
- Signatures cover the index and each platform manifest, attestations only the index. A
  verifier has to resolve the index digest first, which needs settling with whoever
  writes the policy.
- CI signs and attests but never verifies, so a change that breaks verification surfaces
  only at a consuming cluster.
- Local builds stay unattested, since attested images cannot be loaded into the local
  Docker store.
- Provenance comes from our own workflow rather than an isolated builder. A deliberate,
  revisitable limit.

### Alternatives

- **Signing keys in a KMS.** Custody, rotation and an owner, for what keyless signing
  already gives.
- **`slsa-framework/slsa-github-generator`.** Stronger provenance from an isolated
  builder, but heavier, and it does not fit the per-member matrix build. A later upgrade
  path.
- **A Kyverno policy in this repo.** Cluster-wide enforcement belongs to the platform
  layer.
