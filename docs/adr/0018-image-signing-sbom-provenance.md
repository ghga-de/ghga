# ADR-0018 — Sign, SBOM, and attest published images; verification foundation for Kyverno

- **Status:** Accepted
- **Date:** 2026-08-14
- **Deciders:** MKoesters

## Context

Every deployable workload is built `FROM` GHGA's private Docker Hardened Images mirror
(`dhi.io`) and published to `ghcr.io/ghga-de/ghga` by `.github/workflows/dev-images.yaml`
(every merge to `main`, mutable `:dev` tags) and `.github/workflows/release.yaml` (manual,
versioned platform-lane artifacts, per [ADR-0004](0004-versioning-and-release-by-tag.md)).
Neither workflow currently produces an SBOM, provenance, or a signature — there is no way
for anything downstream to verify that a given image actually came from this repo's CI, or
what went into it.

GHGA's Helm charts (per-workload resources) live in this repo; the cluster-wide,
GitOps/platform layer — including the Istio `AuthorizationPolicy` that already enforces
cluster-wide authorization — lives in a separate repo, `devops-kubernetes-hub`
([ADR-0011](0011-helm-chart-boundary-hybrid.md)). Admission-control image verification
(Kyverno `ClusterPolicy`) is the same class of cluster-wide, policy-enforcement concern as
that `AuthorizationPolicy`, so it belongs there too, not in this repo. What this repo *can*
and should do is the producer side: sign what it publishes and attach SBOM + provenance —
the verification foundation the enforcement layer builds on. Authoring the policy itself is
`devops-kubernetes-hub`'s concern; this ADR records what that policy will have to verify
against, not the policy.

## Decision

- **SBOM + provenance:** generate via buildx-native attestations (`docker buildx build
  --provenance=mode=max --sbom=true`, run directly rather than through the
  `docker/build-push-action` wrapper — matches this repo's existing raw-CLI CI style and
  avoids an extra third-party action; a `docker-container` buildx builder is created first,
  since the default docker-driver builder can't export attestations), attached to the
  image at push time as OCI-index attestation manifests. Applied to **both**
  `dev-images.yaml` and `release.yaml` (the latter only when `push=true` — its existing
  build-only dry-run mode is unaffected, since attestations require an actual registry
  push).

  The resulting `predicateType`s — `https://spdx.dev/Document` (SBOM) and
  `https://slsa.dev/provenance/v1` (provenance) — are **confirmed**, verified locally
  (2026-08-14) by pushing a throwaway build to a local registry
  (`docker run -d -p 5000:5000 registry:2`, then `docker buildx create --use --driver
  docker-container --driver-opt network=host` — host networking so the builder container
  can reach `localhost:5000` — then `docker buildx build --push --provenance=mode=max
  --sbom=true -t localhost:5000/test/demo:test .`) and reading the `in-toto.io/predicate-type`
  annotation directly off the pushed attestation manifest (`docker buildx imagetools
  inspect --raw`, or the registry's raw manifest API — the predicateType lives on the
  attestation manifest's layer annotations, not inside `.SBOM`/`.Provenance` content
  itself). This result is buildx-version-dependent, not Dockerfile-dependent, so it holds
  for the real images too.
- **Signing:** keyless cosign (Sigstore Fulcio + Rekor via GitHub Actions OIDC,
  `permissions: id-token: write`), signing the resolved image **digest**, not the mutable
  tag. No private key to manage or rotate.
- **Attesting:** the same two predicates are additionally re-published as signed cosign
  attestations (`cosign attest --type spdxjson` / `--type slsaprovenance1`) against that
  same digest. Buildx's in-index attestations are not where cosign looks, so without this
  step nothing downstream could actually verify an SBOM or provenance claim — see
  Consequences for the evidence and the exact failure mode.
- **Verification identity** — Fulcio issues a short-lived cert per run, bound to the
  workflow's OIDC claims:
  - Issuer (both workflows): `https://token.actions.githubusercontent.com`
  - `dev-images.yaml` subject: `https://github.com/ghga-de/ghga/.github/workflows/dev-images.yaml@refs/heads/main`
  - `release.yaml` subject: `https://github.com/ghga-de/ghga/.github/workflows/release.yaml@refs/heads/main`
    (a manual `workflow_dispatch` run's `job_workflow_ref` claim reflects the branch the
    dispatch UI ran against, not the `ref` **input** string used for lane routing —
    revisit this subject once [ADR-0004](0004-versioning-and-release-by-tag.md)'s tag
    trigger is restored, since a tag-triggered run's ref claim becomes
    `refs/tags/<tag>`, widening the regex needed)

  **These two subject strings are the expected shape based on GitHub's documented OIDC
  token claims, not yet empirically confirmed against a real signed image** — confirm with
  `cosign verify` against a real pushed `:dev` image and a real `push=true` dispatch before
  any consumer treats them as final.
- **SLSA rigor:** buildx-native provenance only, for now — not the
  `slsa-framework/slsa-github-generator` reusable workflow. See Alternatives.
- **Kyverno enforcement stays out of this repo** — no policy, not even an example one.
  Admission control is `devops-kubernetes-hub`'s to author and own, against the identities
  and predicate types recorded above. A reference policy carried here would be a second,
  unversioned copy that nothing in this repo can execute or test, drifting from the one
  that actually runs.
- **Base image staleness** (the other half of this repo's supply-chain hardening pass) is
  handled separately by Renovate, tracking each base image as a single full-tag dep
  (`dhi.io/python`, `dhi.io/node`) rather than tracking the language and alpine versions
  separately — see `docker/README.md`'s "Base image updates" section for why, and for the
  consequence that alpine minor bumps are a deliberate hand edit. Not this ADR's concern.

## Consequences

- Keyless signing writes to the **public** Rekor transparency log. Even though
  `ghcr.io/ghga-de/ghga` is currently private and explicitly interim/disposable
  ([ADR-0004](0004-versioning-and-release-by-tag.md)), the fact that a given digest was
  built by a given workflow run at a given time becomes public and permanent. Acceptable
  given the registry's already-documented interim status, but a real, honest trade-off —
  revisit if/when a non-disposable production registry is chosen.
- No private-key custody burden — nothing to rotate, no HSM/KMS to provision, no owner to
  assign for key material.
- Enabling attestations turns even a single-platform push into an OCI image index (image +
  attestation manifests) rather than a plain single manifest. Kubernetes/containerd/Trivy
  resolve this transparently; it is expected buildx behavior, not a regression, but worth
  knowing if a downstream tool ever chokes on it.
- **buildx's own attestations are not discoverable by cosign — so they are additionally
  re-published via `cosign attest`.** buildx attaches them as unsigned in-toto
  statements on an attestation manifest inside the index; `cosign attest` instead publishes
  a signed DSSE envelope as a separate cosign attachment. These are different locations, and
  cosign only reads the latter. Verified locally (2026-08-17, cosign v3.1.3, buildx v0.36.1)
  against a throwaway image pushed to a local registry: `docker buildx imagetools inspect`
  found both predicates (`https://spdx.dev/Document`, `https://slsa.dev/provenance/v1`) as
  `application/vnd.in-toto+json` layers, while `cosign download attestation` returned
  nothing and `cosign tree` reported "No Supply Chain Security Related Artifacts found".
  Running `cosign attest` on the same image made both cosign commands find it.

  Strictly speaking this was a discoverability gap, not an integrity one: `cosign sign`
  covers the index digest, and the index references the attestation manifests by digest, so
  tampering with an SBOM already broke the signature. That implicit, transitive coverage is
  deliberately **not** what this repo relies on — an attestation a verifier cannot query is
  not a usable one, and "the signature transitively covers it somewhere inside the index" is
  not something an enforcement layer can express as a policy rule. Both publish workflows
  therefore extract the two predicates back out of the index (`docker buildx imagetools
  inspect --format '{{json .SBOM.SPDX}}'` / `.Provenance.SLSA`) and re-publish them with
  `cosign attest`, against the same digest `cosign sign` signed.

  The `--type` values are load-bearing, since they set the `predicateType` a verifier
  matches on. Confirmed empirically (2026-08-17) that they reproduce exactly what buildx
  emits: `--type spdxjson` → `https://spdx.dev/Document`, `--type slsaprovenance1` →
  `https://slsa.dev/provenance/v1`. `--type slsaprovenance` (no suffix) is SLSA **v0.2** and
  would publish the wrong type — buildx emits the v1 predicate shape
  (`buildDefinition`/`runDetails`), so v1 is the correct pairing.

  The extraction is platform-agnostic: buildx returns `{SPDX: …}` for a single-platform
  build and `{"linux/amd64": {SPDX: …}, …}` for a multi-platform one, so
  `scripts/attest-image.sh` normalises both to a platform → predicate map and emits one
  attestation per platform, each attached to the index digest. Verified against both shapes.

  One caveat for whoever writes the consuming policy: cosign v3 publishes attachments via
  OCI referrers where v2 used the `sha256-<digest>.att` tag. Both workflows therefore pin
  `cosign-release: v3.1.3` rather than tracking the latest major, so the attachment layout
  the verifying side has to read is fixed and explicit.
- **CI runs the producer half only.** It signs and attests, and the job ends without
  reading anything back — nothing here verifies its own output, so a change that silently
  breaks verifiability would surface only at a consuming cluster's admission controller.
  Both publish workflows call the same `scripts/attest-image.sh` rather than each carrying
  its own copy, which at least keeps that path single-sourced. Closing the gap properly
  means a consumer-side check; see "Verification identity" for the piece that cannot be
  confirmed outside a real CI run at all.
- SLSA rigor is intentionally capped below what `slsa-framework/slsa-github-generator`
  would provide (an isolated, non-forgeable builder identity vs. this repo's own workflow
  self-attesting its own build). A deliberate, revisitable choice, not an oversight.
- The justfile's `image`/`image-mono` recipes are deliberately left building plain
  (unattested) local images for
  `just demo-images`/`security-scan.yaml`'s local rebuild-and-diff step — attestations are
  incompatible with `--load`ing into the local docker store. Only the two publish
  workflows build via `docker buildx build` directly.

## Alternatives considered

- **Static/KMS-managed cosign keys.** Rejected for now: real custody overhead (rotation,
  access control, an owning team) with no clear owner yet, for a benefit keyless signing
  already gets us (a verifiable identity bound to this repo's CI).
- **`slsa-framework/slsa-github-generator`.** Produces provenance from an isolated,
  non-forgeable builder identity — stronger than buildx-native provenance's
  self-attestation. Rejected for now: heavier (an extra reusable workflow, more moving
  parts), and its isolated-builder model doesn't map cleanly onto the current per-member
  matrix build shape. Noted as a future upgrade path once the signing/SBOM baseline here
  has proven itself.
- **Kyverno `ClusterPolicy` living in this repo.** Rejected: contradicts the
  [ADR-0011](0011-helm-chart-boundary-hybrid.md) boundary — cluster-wide policy
  enforcement belongs in `devops-kubernetes-hub`, alongside the cluster-wide
  `AuthorizationPolicy` that already lives there.
