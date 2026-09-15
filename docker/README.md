# `docker/` — shared container images

One Dockerfile builds **any** deployable workspace member from the repo root, parameterised by
`PACKAGE` (the member to install) and `EXECUTABLE` (its console-script ENTRYPOINT). This mirrors
the proven `file-services-backend` "one Dockerfile, ENTRYPOINT per service" approach, adapted to
the `uv` workspace (resolve from the single `uv.lock`, install only the target package + its
source-coupled deps).

- [`Dockerfile`](Dockerfile) — the canonical image, based on **Docker Hardened Images**.
  Build stages run on the DHI dev variant so the runtime libc matches; the runtime stage is
  the plain hardened base (non-root, shell-less).

```bash
# build from the REPO ROOT:
docker build -f docker/Dockerfile \
  --build-arg PACKAGE=auth-service --build-arg EXECUTABLE=auth-service .
```

> Scaffold: exercisable only after the workspace members + `uv.lock` exist (post-import). The
> per-member `PACKAGE`/`EXECUTABLE` values come from `[tool.ghga]`
> ([conventions](../docs/conventions.md)). The front end keeps its own bespoke Dockerfile under
> `frontend/`.

## Published tags

- `<member>:<platform-version>` — release artifacts, one image per member
  (`.github/workflows/release.yaml`, manual for now).
- `platform:dev` + `data-portal:dev` — mutable dev tags tracking `dev`
  (`.github/workflows/dev-images.yaml`): the mono Python image (VARIANT=mono, all members
  in one venv) and the front-end image. Not release artifacts — they feed the daily
  vulnerability watch (`.github/workflows/security-scan.yaml`), which rescans them,
  trials a lockfile update, and opens a PR when the update fixes known CVEs.

Every published tag also carries a keyless cosign signature (over the resolved digest)
plus SBOM and SLSA-provenance attestations (buildx-native, `provenance=mode=max`). See
[ADR-0037](../docs/adrs/0037-image-signing-sbom-provenance.md) for the decision.

Because buildx's own attestations live inside the OCI index where `cosign` does not look,
both predicates are additionally re-published as signed cosign attestations
(`cosign attest --type spdxjson` / `--type slsaprovenance1`) against the same digest — so
`cosign verify-attestation`, and any policy engine built on it, can actually query them.
`scripts/attest-image.sh` does that re-publishing and is shared by both publish workflows.

## Verifying images

This repo is the **producer** side only; admission-control verification lives in the
platform/GitOps layer ([ADR-0031](../docs/adrs/0031-helm-chart-boundary-hybrid.md)).
Fulcio issues a short-lived certificate per run, bound to the workflow's OIDC claims, so
a verifier matches those claims rather than a tag or key:

| Workflow | Certificate subject | Status |
|---|---|---|
| `release.yaml` | `https://github.com/ghga-de/ghga/.github/workflows/release.yaml@refs/tags/<tag>` | confirmed against a published release candidate |
| `dev-images.yaml` | `https://github.com/ghga-de/ghga/.github/workflows/dev-images.yaml@refs/heads/dev` | predicted, not yet confirmed on a real dev image |

The issuer is `https://token.actions.githubusercontent.com` for both. The subject is the
run's `job_workflow_ref`: release dispatches run with "Use workflow from" set to the
release tag, so the tag appears in it, not a branch. Read the exact subject off a real
run (`cosign verify … --output json`) before pinning a policy to the dev-image shape.

Predicate types to match: `https://spdx.dev/Document` (SBOM) and
`https://slsa.dev/provenance/v1` (provenance). Both workflows pin `cosign-release:
v3.1.3`: cosign v3 publishes attachments as OCI referrers where v2 used
`sha256-<digest>.att` tags, so the pin fixes the layout a verifier reads. Keyless
signing writes every signature to the public Rekor log.

> **Verify against a tag, not a digest copied off a UI.** Release images are multi-platform
> OCI indexes: `cosign sign --recursive` signs the index **and** every per-platform child
> manifest, but the SBOM/provenance attestations are published only against the **index**
> digest. A digest copied from Docker Hub's "layers" UI (or similar) is usually a
> per-platform child — the signature will verify, but `cosign verify-attestation` will find
> nothing. Resolve the index digest first (`docker buildx imagetools inspect <repo>:<tag>`)
> before verifying attestations against it.
