#!/usr/bin/env bash
# `just pypi-drift [base]`: fail when a PyPI-lane member changed since the merge base with
# `base` without declaring a version the index does not already serve.
# scripts/pypi_drift.py carries the reasoning; CI's check-pypi-drift job runs this.
set -euo pipefail

base=${1:-origin/dev}

# On GitHub Actions `::error::` lifts the message onto the Checks tab.
error() {
    if [ -n "${GITHUB_ACTIONS:-}" ]; then
        echo "::error::$1"
    else
        echo "error: $1" >&2
    fi
}

# Failing, not skipping: an undeterminable change set is not evidence of no drift.
if ! merge_base=$(git merge-base "$base" HEAD 2> /dev/null); then
    error "drift check failed: no base commit to compare against ($base) — the base branch was force-pushed or newly created"
    exit 1
fi

errors=$(mktemp)
trap 'rm -f "$errors"' EXIT
if git diff --name-only "$base...HEAD" \
    | uv run -q --script scripts/pypi_drift.py --base "$merge_base" 2> "$errors"; then
    exit 0
fi
# The gate is fail-closed: `pipefail` fails it whatever failed. But only the script's
# stderr is captured, so a failure on the `git diff` side would report nothing — hence a
# message that at least says the failure was not drift.
if [ -s "$errors" ]; then
    while IFS= read -r line; do
        error "$line"
    done < "$errors"
else
    error "drift check failed without reporting drift — see the log above"
fi
exit 1
