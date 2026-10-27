#!/usr/bin/env bash
# `just published-combo <member> [python]`: run ONE cell of the published-combo matrix
# (.github/workflows/pypi-matrix.yaml) locally.
#
# `uv sync` cannot reproduce those failures, because in the shared workspace venv a member
# can import whatever a sibling installed. Here it gets only its own wheel and its declared
# dependencies, so the gaps surface.
set -euo pipefail

member=$1
python=${2:-3.12}
root=$PWD

# The same script CI reads, so a local run cannot drift from the cell.
cell=$(uv run --script scripts/pypi_members.py --check-pypi --paths "$member" --cell "$python")
# `$(...)` strips trailing newlines, so a member with no extras and/or no train_deps
# yields fewer lines than there are reads, and the read that hits EOF returns 1 — which
# under `set -e` kills the script before it prints anything. `|| var=""` both neutralizes
# that and states the intended empty value.
{ read -r package
  read -r extras || extras=""
  read -r train_deps || train_deps=""; } <<< "$cell"

# Fixed path, not mktemp: the venv outlives the run, so a failure can be poked at
# (`$work/venv/bin/python -m pytest -k ...`), and a re-run wipes it rather than
# leaving a trail of temp trees.
work="${TMPDIR:-/tmp}/ghga-published-combo/$package-$python"
rm -rf "$work" && mkdir -p "$work/wheels"

# Member + whatever is being released alongside it (--check-pypi decides that: the
# libraries whose declared version is not on the index yet). Everything else is left
# out so it resolves from PyPI, exactly as in CI and as on a user's machine.
# shellcheck disable=SC2086  # train_deps is a space-separated list of paths
for path in "$member" $train_deps; do
    uv build --wheel --out-dir "$work/wheels" "$path"
done

# From outside the repo: inside it, uv picks up the workspace's requires-python (3.14)
# and warns about every member that cannot have it.
cd "$work"
uv venv --python "$python" "$work/venv"

# The closure is in the wheelhouse to be resolved against, not installed directly —
# so pick this member's own wheel by name.
wheel=$(ls "$work"/wheels/"${package//-/_}"-*.whl)
spec="$wheel"
[ -n "$extras" ] && spec="${wheel}[${extras}]"
echo "== installing $spec"
uv pip install --python "$work/venv/bin/python" --find-links "$work/wheels" "$spec"

# Test dependencies live in the root dependency-group, not in the member — minus the
# lint tools. The same shared list for every member: anything else a member's suite
# needs is declared by the member itself.
cd "$root"
uv run --script scripts/pypi_members.py --dev-requirements \
  > "$work/test-requirements.txt"
uv pip install --python "$work/venv/bin/python" --find-links "$work/wheels" \
  -r "$work/test-requirements.txt"

# cwd = the member directory, as in CI: each member runs as its own pytest, and the
# src/ layout means the tests import the installed package, not the working tree.
echo "== running $member tests on $python (env: $work/venv)"
cd "$member"
"$work/venv/bin/python" -m pytest -q --durations=10
