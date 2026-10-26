#!/usr/bin/env bash
# `just skill-eval <name> [args...]`: run a root skill's eval suite,
# .agents/skills/<name>/evals.yaml, each case with and without the skill in a pinned clone
# that scripts/skill-eval-scaffold.sh prepares (docs/agent-instructions.md).
#
# Each run's trace is kept in the results, so a fixed grader can be checked against a pass
# without rerunning it; the workspaces themselves, a clone and a .venv each, go.
set -euo pipefail

# A pass is due for every suite when this moves to a new default model.
SKILL_EVAL_MODEL="claude-opus-5-5"

name=$1
shift

# One run per plugin: the skill itself, or each entry of the suite's `plugins`.
mapfile -t targets < <(uv run python scripts/skill_eval.py expand "$name")
stamp=$(date -u +%Y-%m-%dT%H-%M-%SZ)
# Each kept workspace holds a clone and a copied .venv, about 2.5 GB, until `collect`
# removes it: a pass outgrows the container's /tmp, so the runner works on the disk.
export TMPDIR="${XDG_CACHE_HOME:-$HOME/.cache}/ghga-skill-eval"
mkdir -p "$TMPDIR"
for target in "${targets[@]}"; do
    pass=""
    [[ "$target" == */evals/* ]] && pass="-${target##*/}"
    out=".agents/skills/$name/evals/results/$stamp$pass"
    # The threshold is 0 so that only a run that breaks, not a low score, fails the
    # recipe.
    claude plugin eval "$target" --model "$SKILL_EVAL_MODEL" \
        --scaffold --trust-plugin --no-publish --allow-tools Bash Write Edit \
        --concurrency 4 --max-cost-usd 20 --threshold 0 --keep-temp \
        --output-dir "$out" "$@" || status=$?
    echo "== $name$pass on $SKILL_EVAL_MODEL"
    uv run python scripts/skill_eval.py collect "$out"
done
exit "${status:-0}"
