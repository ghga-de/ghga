#!/usr/bin/env bash
# Publish buildx's SBOM + SLSA provenance as signed cosign attestations.
#
# buildx attaches both as unsigned in-toto statements inside the OCI index, where cosign
# does not look — so without this step nothing downstream can verify them. See ADR-0019.
#
# Usage:
#   scripts/attest-image.sh <registry>/<name>@sha256:<digest>
#
# Env:
#   COSIGN_BIN         cosign executable (default: cosign)
#   COSIGN_EXTRA_ARGS  extra `cosign attest` args (CI: none, keyless via OIDC)
#   OUT_DIR            scratch dir for extracted predicates (default: $RUNNER_TEMP)
#
# ---------------------------------------------------------------------------------------
# Where the constants below come from. Each finding is version-dependent, so this is the
# file to re-check them in when cosign or buildx moves; ADR-0019 records the decision, not
# this. All of it was established against a throwaway image pushed to a local registry:
#
#   docker run -d -p 5000:5000 registry:2
#   docker buildx create --use --driver docker-container --driver-opt network=host
#   docker buildx build --push --provenance=mode=max --sbom=true \
#     -t localhost:5000/test/demo:test .
#
# (host networking, so the builder container can reach localhost:5000.)
#
# The predicate types buildx emits (2026-08-14): `https://spdx.dev/Document` for the
# SBOM and `https://slsa.dev/provenance/v1` for provenance. Read the
# `in-toto.io/predicate-type` annotation off the pushed attestation manifest — `docker
# buildx imagetools inspect --raw`, or the registry's raw manifest API. It lives on that
# manifest's layer annotations, not inside the `.SBOM`/`.Provenance` content.
# Buildx-version-dependent, not Dockerfile-dependent, so it holds for the real images too.
#
# Why this script has to exist (2026-08-17, cosign v3.1.3, buildx v0.36.1): on an image
# built as above, `docker buildx imagetools inspect` found both predicates as
# `application/vnd.in-toto+json` layers, while `cosign download attestation` returned
# nothing and `cosign tree` reported "No Supply Chain Security Related Artifacts found".
# Running `cosign attest` on the same image made both cosign commands find it.
#
# The `--type` pairings (2026-08-17): `spdxjson` -> `https://spdx.dev/Document` and
# `slsaprovenance1` -> `https://slsa.dev/provenance/v1`, reproducing exactly what buildx
# emits. `slsaprovenance` without the suffix is SLSA v0.2 and would publish the wrong type,
# since buildx emits the v1 shape (`buildDefinition`/`runDetails`).
#
# Both extraction shapes handled by `extract` below were verified against real builds.
# ---------------------------------------------------------------------------------------

set -euo pipefail

REF="${1:?usage: attest-image.sh <registry>/<name>@sha256:<digest>}"
# By digest, and the same digest that was signed, so signature and attestations share a subject.
case "$REF" in
*@sha256:*) ;;
*) echo "::error::reference must be by digest, got: ${REF}" >&2 && exit 1 ;;
esac

COSIGN_BIN="${COSIGN_BIN:-cosign}"
OUT_DIR="${OUT_DIR:-${RUNNER_TEMP:-$(mktemp -d)}}"
read -r -a cosign_extra <<<"${COSIGN_EXTRA_ARGS:-}"

# buildx returns {SPDX: …} for one platform but {"linux/amd64": {SPDX: …}, …} for several.
# Normalise both to a platform -> predicate map so one code path covers either.
extract() { # $1 = SBOM|Provenance, $2 = SPDX|SLSA
  docker buildx imagetools inspect --format "{{json .$1}}" "$REF" |
    jq -c --arg k "$2" 'if has($k) then {"-": .[$k]} else map_values(.[$k]) end'
}

# --type sets the predicateType a policy matches on, so it is load-bearing. Note
# `slsaprovenance` is SLSA v0.2; buildx emits the v1 shape, hence slsaprovenance1.
attest_all() { # $1 = map, $2 = cosign --type, $3 = label
  local map="$1" type="$2" label="$3" plat file
  for plat in $(echo "$map" | jq -r 'keys[]'); do
    file="${OUT_DIR}/${label}-${plat//\//-}.json"
    echo "$map" | jq -c --arg p "$plat" '.[$p]' >"$file"
    "$COSIGN_BIN" attest --yes ${cosign_extra[@]+"${cosign_extra[@]}"} \
      --type "$type" --predicate "$file" "$REF"
    echo "  attested ${label} [${plat}] ($(wc -c <"$file" | tr -d ' ') bytes)"
  done
}

sboms="$(extract SBOM SPDX)"
provs="$(extract Provenance SLSA)"

# An empty attestation looks like coverage that isn't there, so fail instead.
for pair in "SBOM:${sboms}" "Provenance:${provs}"; do
  name="${pair%%:*}"
  body="${pair#*:}"
  echo "$body" | jq -e 'length > 0 and (to_entries | all(.value | type == "object" and length > 0))' \
    >/dev/null 2>&1 || {
    echo "::error::no usable ${name} predicate found in ${REF} — did the build run with --sbom/--provenance?" >&2
    exit 1
  }
done

attest_all "$sboms" spdxjson "sbom"
attest_all "$provs" slsaprovenance1 "provenance"
