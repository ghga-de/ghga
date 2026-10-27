#!/usr/bin/env bash
# `just test [target...] [pytest option...]`: run pytest per workspace member, as CI's
# check-python matrix does.
#
# Each member runs as its own pytest: 24 of them carry a `tests` package, so ONE pytest
# over the whole tree dies on the duplicate module names before running anything (the same
# collision scripts/typecheck.py works around for mypy). That collision is why a bare tier
# ("libs", "services", "tools") is swept member-by-member too, not handed to pytest as one
# target. Every run still finds the one pytest config in the root pyproject.toml, so the
# rootdir is the repo root.
#
# A member runs from its own directory; scripts/ and deploy/ belong to no member and run
# from the root. Nothing fails fast: a red target should not hide the state of the others.
#
# Targets: nothing (every member, then the non-member suites), a tier, a member, a path
# inside a member, or a non-member path such as scripts/tests. The first argument that
# starts with `-` ends the targets: it and everything after it go to every pytest run, so
# an option's value (`-k "a and b"`) is never mistaken for a target.
set -uo pipefail

failed=()

# pytest one member, or a scope inside it given relative to the member
run_member() {
    local member=$1 scope=${2:-}
    [ -f "$member/pyproject.toml" ] || { echo "no such member: $member" >&2; return 1; }
    echo "== pytest $member${scope:+/$scope} =="
    (cd "$member" && uv run pytest -q --durations=10 ${scope:+"$scope"} "${opts[@]}")
}

run_target() {
    local target=$1 tier member
    # repeated trailing slashes must not defeat the bare-tier and member checks below
    while [[ "$target" == */ && "$target" != / ]]; do
        target="${target%/}"
    done
    tier="${target%%/*}"
    case "$tier" in
        libs | services | tools)
            if [ "$target" = "$tier" ]; then
                for member in "$tier"/*/; do
                    member="${member%/}"
                    [ -f "$member/pyproject.toml" ] || continue
                    run_member "$member" || failed+=("$member")
                done
                return
            fi
            member=$(cut -d/ -f1-2 <<< "$target")
            # anything deeper than the member is a scope *within* its suite
            scope="${target#"$member"}"
            run_member "$member" "${scope#/}" || failed+=("$target")
            ;;
        *)
            echo "== pytest $target =="
            uv run pytest -q --durations=10 "$target" "${opts[@]}" || failed+=("$target")
            ;;
    esac
}

targets=()
while [ $# -gt 0 ] && [[ "$1" != -* ]]; do
    targets+=("$1")
    shift
done
opts=("$@")
everything=$(( ${#targets[@]} == 0 ))
for target in "${targets[@]}"; do
    # `.` means everything too, wherever it stands: one pytest over the root would die
    # on the duplicate module names
    case "$target" in "" | . | ./) everything=1 ;; esac
done
if [ "$everything" = 1 ]; then
    targets=(libs services tools scripts/tests deploy/tests)
fi
for target in "${targets[@]}"; do
    run_target "$target"
done

if [ ${#failed[@]} -gt 0 ]; then
    echo "pytest failed in: ${failed[*]}" >&2
    exit 1
fi
