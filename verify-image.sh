#!/usr/bin/env bash
# Verify the keyless cosign signature and SBOM/provenance attestations on a published
# ghga/ghga-de image, per ADR-0019 (docs/adr/0019-image-signing-sbom-provenance.md).
#
# Usage:
#   ./verify-image.sh [image-tag-ref] [workflow-file] [ref]
#
# image-tag-ref must be a TAG (repo:tag), not a digest. Release-lane images are
# multi-platform (linux/amd64 + linux/arm64) OCI indexes; buildx's --metadata-file
# reports the INDEX digest, and that's what scripts/attest-image.sh attests against — so
# the SBOM/provenance attestations live on the index digest only, never on a per-platform
# child manifest (ADR-0019 "Consequences": signatures are recursive over the whole index,
# attestations are not). Passing a digest copied from Docker Hub's "layers" UI almost
# always gives you a per-platform child digest instead, which has the signature (cosign
# sign --recursive covers children too) but none of the attestations — confirmed
# empirically 2026-08-27 against auth-service@sha256:97af0c7a90c... (the linux/amd64
# child of ghga/15.3.1-rc.3): signature verified, `cosign verify-attestation --type
# spdxjson` found nothing. This script resolves the tag to its index digest via
# `docker buildx imagetools inspect` so you don't have to hunt for it by hand.
#
# Defaults to the auth-service release candidate: docker.io/ghga/auth-service:15.3.1-rc.3
#
# workflow-file selects which CI workflow's identity to verify against:
#   release.yaml     (default) — Docker Hub release-lane images (docker.io/ghga/<member>)
#   dev-images.yaml  — GHCR :dev-tag images (ghcr.io/ghga-de/ghga/<image>)
#
# ref is the job_workflow_ref suffix baked into the signing cert — NOT necessarily
# refs/heads/main. A release.yaml dispatch run's ref reflects whatever the "Use workflow
# from" picker was pointed at: refs/heads/main for a normal main dispatch, but
# refs/tags/<tag> when (as ADR-0004 instructs) the picker is pointed at the release tag
# itself — confirmed empirically 2026-08-27 against ghga/15.3.1-rc.3, which carries
# refs/tags/ghga/15.3.1-rc.3, not refs/heads/main (hence that's the default below).
# dev-images.yaml only ever runs from main, so refs/heads/main is correct there. When
# unsure, run with INSPECT=1 first.
#
# Requires: cosign (https://docs.sigstore.dev/system_config/installation/), docker buildx, jq.

set -euo pipefail

TAG_REF="${1:-docker.io/ghga/auth-service:15.3.1-rc.3}"
WORKFLOW="${2:-release.yaml}"
REF="${3:-refs/tags/ghga/15.3.1-rc.3}"

ISSUER="https://token.actions.githubusercontent.com"
IDENTITY="https://github.com/ghga-de/ghga/.github/workflows/${WORKFLOW}@${REF}"

command -v cosign >/dev/null || {
  echo "::error::cosign not found — install it: https://docs.sigstore.dev/system_config/installation/" >&2
  exit 1
}

if [[ "$TAG_REF" == *"@sha256:"* ]]; then
  echo "::warning::given a digest ref directly — if it's a per-platform child manifest" >&2
  echo "::warning::(not the index), attestation lookups below will find nothing. Prefer" >&2
  echo "::warning::passing a tag (repo:tag) so this script resolves the index digest." >&2
  IMAGE="$TAG_REF"
else
  echo "== resolving index digest for ${TAG_REF} =="
  digest=$(docker buildx imagetools inspect "$TAG_REF" | awk '/^Digest:/{print $2; exit}')
  [ -n "$digest" ] || {
    echo "::error::could not resolve an index digest for ${TAG_REF}" >&2
    exit 1
  }
  repo="${TAG_REF%:*}"
  IMAGE="${repo}@${digest}"
  echo "   index digest: ${digest}"
  echo
fi

echo "== verifying ${IMAGE} =="
echo "   issuer:   ${ISSUER}"
echo "   identity: ${IDENTITY}"
echo

if [ "${INSPECT:-0}" = "1" ]; then
  echo "== [inspect] actual certificate identity (loose match) =="
  cosign verify \
    --certificate-identity-regexp='.*' \
    --certificate-oidc-issuer="${ISSUER}" \
    --output json \
    "${IMAGE}" | jq '.[0].optional'
  exit 0
fi

echo "== [1/3] signature =="
cosign verify \
  --certificate-identity="${IDENTITY}" \
  --certificate-oidc-issuer="${ISSUER}" \
  "${IMAGE}" | jq .

echo
echo "== [2/3] SBOM attestation (spdxjson) =="
cosign verify-attestation --type spdxjson \
  --certificate-identity="${IDENTITY}" \
  --certificate-oidc-issuer="${ISSUER}" \
  "${IMAGE}" | jq -r '.payload' | base64 -d | jq '{predicateType, packages: (.predicate.packages | length)}'

echo
echo "== [3/3] provenance attestation (slsaprovenance1) =="
cosign verify-attestation --type slsaprovenance1 \
  --certificate-identity="${IDENTITY}" \
  --certificate-oidc-issuer="${ISSUER}" \
  "${IMAGE}" | jq -r '.payload' | base64 -d | jq '{predicateType, builder: .predicate.runDetails.builder}'

echo
echo "done: ${IMAGE} is signed, and both attestations verify."
