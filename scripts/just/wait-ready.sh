#!/usr/bin/env bash
# `just wait-ready`: wait until the demo on kind actually serves.
#
# `helm --wait` covers the release's own workloads, but the gateway's pod is created by
# the Envoy operator from the Gateway resource — outside the release — so it needs its
# own condition. And a Ready pod can still crash: the services fail fast when Kafka is
# not yet up (KafkaConnectionError), and a suite that starts immediately runs against
# the crash-loop window. So after the gateway is programmed, this polls the DRS health
# check, the suite's first request, until it answers 200; it passes ext-authz, so that
# proves routing and the auth adapter work end to end.
set -euo pipefail

K="kubectl --context kind-ghga"
$K wait --for=condition=Programmed gateway/ghga --timeout=5m
url=http://localhost/api/ga4gh/drs/v1/health
deadline=$((SECONDS + 120))
until code=$(curl -s -o /dev/null -w '%{http_code}' "$url"); [ "$code" = 200 ]; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        echo "error: $url still answers $code after 2 min; the gateway logged:" >&2
        $K logs -l gateway.envoyproxy.io/owning-gateway-name=ghga -c envoy --tail=500 \
          | jq -rR 'fromjson? | select(.["x-envoy-origin-path"] == "/api/ga4gh/drs/v1/health")
              | "\(.start_time) \(.response_code) \(.response_code_details) \(.response_flags)"' \
          | tail -3 >&2
        echo "ext_authz_error means the auth adapter failed: see 'just logs auth-adapter'" >&2
        exit 1
    fi
    sleep 2
done
