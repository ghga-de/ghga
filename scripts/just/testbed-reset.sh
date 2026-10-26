#!/usr/bin/env bash
# `just testbed-reset`: reset the identity state to a coherent cold start.
#
# The suite's clean slate restores the data steward from its own snapshot, so leftovers
# from earlier runs (or an out-of-band edit) can leave the claim, user, IVA and
# notification projection disagreeing. Dropping both databases and restarting lets the
# services re-seed and rebuild their projections from events.
set -euo pipefail

K="kubectl --context kind-ghga"
MPOD=$($K get pods -o name | grep mongodb | head -1)
apps=$($K get deploy -o name | grep -vE "envoy|mongodb|kafka|minio|vault|mailhog|lox24|test-oidc|aai")
# Stop the services before dropping their databases, and wait until their pods are
# gone: a pod still running writes new documents into the emptied database, and the
# restarted service then finds data but no migration record, re-runs its migrations
# over it and crash-loops.
# shellcheck disable=SC2086  # $apps is a list of deployment names
replicas=$($K get $apps -o json | jq -r '.items[] | "\(.metadata.name) \(.spec.replicas)"')
echo "$apps" | xargs kubectl --context kind-ghga scale --replicas=0 > /dev/null
for d in $apps; do
    sel=$($K get "$d" -o json | jq -r '.spec.selector.matchLabels | to_entries | map("\(.key)=\(.value)") | join(",")')
    $K wait --for=delete pod -l "$sel" --timeout=120s > /dev/null
done
# Drop every service database, migration records included, so each service
# migrates and re-seeds from empty.
$K exec "$MPOD" -- mongosh --quiet --eval \
  'db.adminCommand({listDatabases:1}).databases
     .map(d => d.name)
     .filter(n => !["admin","config","local"].includes(n))
     .forEach(n => db.getSiblingDB(n).dropDatabase())' > /dev/null
echo "$replicas" | while read -r name n; do $K scale deploy "$name" --replicas="$n" > /dev/null; done
# Name what is being waited on, and what failed. Every app deployment starts at once
# above while each service re-migrates and rejoins its Kafka consumer group — 240s
# was not enough on a loaded machine, and a bare `rollout status > /dev/null` under
# `set -e` then aborted with kubectl's "timed out waiting for the condition" and no
# clue which of the ~19 deployments it meant.
total=$(echo "$apps" | wc -l | tr -d ' ')
i=0
for d in $apps; do
    i=$((i + 1))
    name="${d#deployment.apps/}"
    printf '  [%2d/%s] waiting for %s\n' "$i" "$total" "$name" >&2
    $K rollout status "$d" --timeout=600s > /dev/null \
      || { echo "error: $name did not become ready within 600s — \`just logs $name\` shows why" >&2; exit 1; }
done
echo "state reset (databases empty, services re-migrated and re-seeded)"
