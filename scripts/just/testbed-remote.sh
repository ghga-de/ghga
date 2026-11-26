#!/usr/bin/env bash
# `just testbed-remote <config> [pytest args...]`: run the test-bed suite against the
# deployment a tb.*.yaml names, reached through its gateway alone.
#
# Never calls kubectl, forwards a port or edits /etc/hosts. Every secret comes from the
# environment, and a missing one fails here by name instead of as a scenario timeout.
set -euo pipefail

# The suite shells out to ghga-datasteward-kit and ghga-connector and expects them
# on PATH. The testbed venv holds them as editable workspace installs (see
# testbed-install), so the CLIs are the very install the suite also imports.
export PATH="$PWD/.venv-testbed/bin:$PATH"
arg=$1
shift
# a path as given, relative to where `just` was called, or a file name in testbed/
config=$arg
[ -f "$config" ] || config=${INVOCATION_DIR:-.}/$arg
[ -f "$config" ] || config=testbed/$arg
[ -f "$config" ] || { echo "error: no such configuration: $arg (a tb.*.yaml path)" >&2; exit 1; }
missing=()
for var in TB_STATE_MANAGEMENT_TOKEN TB_PURGE_CONTROLLER_TOKEN TB_DLQ_TOKEN TB_UPLOAD_TOKEN \
           TB_FIS_PUBKEY TB_USER_PRIVATE_CRYPT4GH_KEY TB_USER_PUBLIC_CRYPT4GH_KEY; do
    [ -n "${!var:-}" ] || missing+=("$var")
done
[ ${#missing[@]} -eq 0 ] || { echo "error: not set in the environment: ${missing[*]}" >&2; exit 1; }
TB_CONFIG_YAML="$(realpath "$config")"
export TB_CONFIG_YAML
# ghga-datasteward-kit reads the steward token from a file (the default dsk_token_path), not the environment
token_file="$HOME/.ghga_data_steward_token.txt"
printf '%s' "$TB_UPLOAD_TOKEN" > "$token_file"
trap 'rm -f "$token_file"' EXIT
cd testbed && ../.venv-testbed/bin/pytest -v "$@"
