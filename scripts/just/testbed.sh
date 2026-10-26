#!/usr/bin/env bash
# `just testbed [pytest args...]`: run the test-bed suite against the demo on kind.
#
# Harvests tokens and keys from the cluster secrets, port-forwards the services the suite
# reaches directly (mailhog, lox24 — MinIO is published by kind), then runs pytest.
set -euo pipefail

# The suite shells out to ghga-datasteward-kit and ghga-connector and expects them
# on PATH. The testbed venv holds them as editable workspace installs (see
# testbed-install), so the CLIs are the very install the suite also imports.
export PATH="$PWD/.venv-testbed/bin:$PATH"
K="kubectl --context kind-ghga"
# Fail in seconds, not in 300 s timeouts per scenario, when the platform is broken:
# e.g. a crash-looping service, or Vault not letting ekss log in (its readiness
# probe does that login).
if ! $K wait --for=condition=Available deploy --all --timeout=60s > /dev/null 2>&1; then
    echo "error: not every deployment is available — \`just logs\` lists them:" >&2
    $K get deploy --no-headers | awk '{split($2, r, "/")} r[1] != r[2] {print "  " $1 " " $2}' >&2
    exit 1
fi
secret() { $K get secret "$1" -o jsonpath="{.data.$2}" | base64 -d; }
export TB_CONFIG_YAML="$PWD/testbed/tb.kind.yaml"
# shellcheck disable=SC2155  # export masks a failed lookup, as the recipe always has
{
export TB_STATE_MANAGEMENT_TOKEN=$(secret ghga-harness-tokens SMS_TOKEN)
export TB_PURGE_CONTROLLER_TOKEN=$(secret ghga-harness-tokens PCS_TOKEN)
export TB_DLQ_TOKEN=$(secret ghga-harness-tokens DLQS_TOKEN)
export TB_UPLOAD_TOKEN=$(secret ghga-harness-tokens METLDATA_TOKEN)
export TB_FIS_PUBKEY=$(secret ghga-c4gh-files 'crypt4gh\.pub' | sed -n 2p)
}
printf '%s' "$TB_UPLOAD_TOKEN" > "$HOME/.ghga_data_steward_token.txt"
# per-run test-user crypt4gh keypair (any fresh pair works)
# the connector needs the RAW 32-byte secret (export_private is PEM-ish and
# fails with "PrivateKey must be created from a 32 bytes long raw secret key")
eval "$(uv run --quiet --package auth-km-jobs python -c "from auth_km_jobs.c4gh import generate_crypt4gh_key_pair; k = generate_crypt4gh_key_pair(); print(f'export TB_USER_PRIVATE_CRYPT4GH_KEY={k.export_private_raw()}'); print(f'export TB_USER_PUBLIC_CRYPT4GH_KEY={k.export_public()}')")"
mkdir -p /tmp/submission /tmp/connector
$K port-forward svc/ghga-mailhog 8025:8025 > /dev/null 2>&1 &
PF1=$!
# 18080, not the mock's own 8080, which `just fe-dev` serves the portal on
$K port-forward svc/ghga-lox24-mock 18080:8080 > /dev/null 2>&1 &
PF2=$!
# MinIO needs no forward: kind publishes its S3 node port on the host's 9000
# (deploy/kind-config.yaml), which is the authority the pre-signed URLs carry —
# forwarding here would collide with that published port and fail to bind.
just testbed-hosts
trap 'kill $PF1 $PF2 2> /dev/null || true' EXIT
sleep 2
cd testbed && ../.venv-testbed/bin/pytest -v "$@"
