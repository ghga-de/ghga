#!/usr/bin/env bash
# Audit uv.lock as it is and list what the images install from it, for the security scan.
#
# One script for both audits of .github/workflows/security-scan.yaml, before and after the
# lockfile update, so the two cannot drift apart in their flags: a runtime list exported
# with other flags than the other would class the same package differently.
#
# Usage:
#   scripts/audit-uv-lock.sh <prefix>
#
# Writes <prefix>.json, the uv audit report of every group and extra, and
# <prefix>-runtime.txt, the export of what the mono image installs (docker/Dockerfile).
set -euo pipefail

prefix=$1

# Exit 1 only means findings; anything else, an OSV outage say, fails the script.
just audit --output-format json --preview-features json-output >"$prefix.json" ||
  [ $? -eq 1 ]
uv export --frozen --no-dev --all-packages --no-emit-workspace \
  --no-header --no-hashes --no-annotate >"$prefix-runtime.txt"
