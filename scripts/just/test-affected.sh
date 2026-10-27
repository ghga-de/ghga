#!/usr/bin/env bash
# `just test-affected [base]`: run `just test` over the members `just affected` reports.
#
# One `just test` takes every affected member, so a red member does not stop the others
# and the failed ones are listed at the end. A change to a repo-wide file affects
# everything, scripts/ included, so it runs the full sweep, which adds the non-member
# suites a target list would miss.
#
# affected_targets.py also reports targets that have no member suite, because it feeds
# CI's other jobs as well: the front end (check-frontend), and the charts and the test
# bed (the integration gate). Those are named with the recipe that checks them, not run.
set -euo pipefail

json=$(just affected "$1")
mapfile -t targets < <(jq -r '.targets[]' <<< "$json")

members=()
frontend=()
charts=0
testbed=0
for target in "${targets[@]}"; do
    case "$target" in
        libs/* | services/* | tools/*) members+=("$target") ;;
        frontend/*) frontend+=("$target") ;;
        deploy/charts/*) charts=$((charts + 1)) ;;
        testbed) testbed=1 ;;
        *)
            echo "error: affected target '$target' is of no kind this recipe knows" >&2
            exit 2
            ;;
    esac
done

for target in "${frontend[@]}"; do
    echo "not run: $target -- \`just fe_dir=$target fe-check\` checks it"
done
if [ "$charts" -gt 0 ] || [ "$testbed" = 1 ]; then
    echo "not run: $charts chart(s)$([ "$testbed" = 1 ] && echo " and the test bed")" \
        "-- \`just testbed\` exercises them"
fi

if [ "$(jq -r .all <<< "$json")" = true ]; then
    echo "a repo-wide file changed, so every member is affected: running the full sweep"
    exec just test
fi
if [ ${#members[@]} -eq 0 ]; then
    echo "no workspace member affected"
    exit 0
fi
exec just test "${members[@]}"
