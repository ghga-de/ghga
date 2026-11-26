#!/usr/bin/env bash
# `just up` and `just testbed-up`: install (or update) the ghga-demo umbrella on kind and
# wait until it actually serves.
#
# Usage: install-demo.sh <profile> [helm args...]
# `mono` adds the mono-image overlay after any values files passed in; empty adds nothing.
set -euo pipefail

profile=$1
shift
chart=deploy/charts/ghga-demo
extra=()
case "$profile" in
    "") ;;
    mono)
        [ -f "$chart/values-mono.yaml" ] \
          || { echo "error: values-mono.yaml is missing — run \`just charts\`" >&2; exit 1; }
        extra=(-f "$chart/values-mono.yaml")
        ;;
    *) echo "error: unknown profile '$profile' (expected 'mono', or nothing)" >&2; exit 1 ;;
esac

just demo-template
echo "installing — this waits for every workload to become ready, a few minutes"
# The API server warns about every int32/int64 format in the Envoy Gateway CRDs,
# dozens of lines that say nothing about this install; the filter drops only those.
helm upgrade --install ghga "$chart" \
  -f "$chart/values-local.yaml" \
  "$@" \
  ${extra[@]+"${extra[@]}"} \
  --set-json "global.localImageIds=$(just _local-image-ids)" \
  --kube-context kind-ghga --wait --timeout 15m \
  2>&1 | { grep -vE --line-buffered 'warnings\.go:[0-9]+\] "Warning: unrecognized format \\"int(32|64)\\""$' || true; }
just wait-ready
