#!/usr/bin/env bash
# Prepare the workspace of one skill eval run (`just skill-eval`): a clone of this repo
# at a pinned commit, without the root skills, with its own synced .venv.
#
# The commit is pinned so that scores stay comparable across passes and the cases' expected
# values (the next ADR number, the facts in the docs) stay true. Move the pin on purpose,
# check every case against the new commit, and rerun both suites.
#
# The root skills are removed and the removal committed, or the arm without the skill would
# find it in the repo, and `git status` would point at it. The sandbox of a run blocks the
# network, so the .venv is synced here from the warm uv cache; linking the main clone's
# .venv instead would let `uv run` rewrite it for the clone's paths.
set -euo pipefail

PIN=9f5df2dd4

repo=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)
user_home=$(getent passwd "$(id -un)" | cut -d: -f6)

git clone --quiet --shared --no-checkout "$repo" .
git checkout --quiet --detach "$PIN"
git remote remove origin
git rm -r --quiet .agents/skills .claude/skills
UV_CACHE_DIR="$user_home/.cache/uv" UV_OFFLINE=1 UV_LINK_MODE=copy \
    uv sync --quiet --frozen --all-packages --all-extras
# The skill catalogue lists the removed skills; regenerate it so the tree starts clean.
uv run --offline --quiet python scripts/docs_check.py >/dev/null || true
uv run --offline --quiet python scripts/docs_check.py >/dev/null
git add -A
git -c user.name=eval -c user.email=eval@localhost commit --quiet -m "eval: remove the root skills"
