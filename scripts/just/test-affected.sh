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
# bed (the integration gate). Those are named with the recipe that checks them, not run,
# after the sweep, where its output does not scroll them away.
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

status=0
if [ "$(jq -r .all <<< "$json")" = true ]; then
    echo "a repo-wide file changed, so every member is affected: running the full sweep"
    just test || status=$?
elif [ ${#members[@]} -gt 0 ]; then
    just test "${members[@]}" || status=$?
else
    echo "no workspace member affected"
fi

for target in "${frontend[@]}"; do
    echo "not run: $target -- \`just fe_dir=$target fe-check\` checks it"
done
deployed=()
[ "$charts" -eq 0 ] || deployed+=("$charts chart(s)")
[ "$testbed" = 0 ] || deployed+=("the test bed")
if [ ${#deployed[@]} -gt 0 ]; then
    names="${deployed[0]}${deployed[1]:+ and ${deployed[1]}}"
    echo "not run: $names -- \`just testbed\` exercises them"
fi
exit "$status"
