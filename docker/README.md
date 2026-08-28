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
- `platform:dev` + `data-portal:dev` — mutable dev tags tracking `main`
  (`.github/workflows/dev-images.yaml`): the mono Python image (VARIANT=mono, all members
  in one venv) and the front-end image. Not release artifacts — they feed the daily
  vulnerability watch (`.github/workflows/security-scan.yaml`), which rescans them,
  trials a lockfile update, and opens a PR when the update fixes known CVEs.

Every published tag also carries a keyless cosign signature (over the resolved digest)
plus SBOM and SLSA-provenance attestations (buildx-native, `provenance=mode=max`). See
[ADR-0019](../docs/adr/0019-image-signing-sbom-provenance.md) for the decision record.

Because buildx's own attestations live inside the OCI index where `cosign` does not look,
both predicates are additionally re-published as signed cosign attestations
(`cosign attest --type spdxjson` / `--type slsaprovenance1`) against the same digest — so
`cosign verify-attestation`, and any policy engine built on it, can actually query them.
`scripts/attest-image.sh` does that re-publishing and is shared by both publish workflows.

That is the **producer** side only. Verifying it back means matching the keyless
certificate identity, which is **confirmed** for the release lane (`docker.io/ghga/<member>`,
`.github/workflows/release.yaml`) against a real published image — see ADR-0019
"Verification identity" for the exact subject shape, or just run `verify-image.sh` from the
repo root. The `dev-images.yaml` / GHCR lane's identity is still the predicted shape, not
yet independently confirmed against a real dev image. Admission-control verification lives
in the platform/GitOps layer ([ADR-0011](../docs/adr/0011-helm-chart-boundary-hybrid.md));
treat the dev-image lane as signed-but-identity-unproven until that side confirms it.

> **Verify against a tag, not a digest copied off a UI.** Release images are multi-platform
> OCI indexes: `cosign sign --recursive` signs the index **and** every per-platform child
> manifest, but the SBOM/provenance attestations are published only against the **index**
> digest. A digest copied from Docker Hub's "layers" UI (or similar) is usually a
> per-platform child — the signature will verify, but `cosign verify-attestation` will find
> nothing. Resolve the index digest first (`docker buildx imagetools inspect <repo>:<tag>`),
> or just pass a tag to `verify-image.sh`, which resolves it for you.
