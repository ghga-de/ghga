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
#
# The clone is repacked to hold its own objects (about 60 MB, a second): the sandbox of a
# run cannot read the main clone's, so `git diff` would fail, and so would pushing to the
# bare repo some cases set up as their origin.
# Given a patch and a branch name, it also commits the patch on that branch, off an
# `origin/dev` at the pin, so that a case can review or describe a change of its own.
# `--pin <commit>` first replaces the pin, for a suite about code newer than it.
set -euo pipefail

PIN=9f5df2dd4
if [[ ${1:-} == --pin ]]; then
    PIN=$2
    shift 2
fi

repo=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)
user_home=$(getent passwd "$(id -un)" | cut -d: -f6)

git clone --quiet --shared --no-checkout "$repo" .
git checkout --quiet --detach "$PIN"
# The clone has a branch for whatever the main clone has checked out; no case wants it.
git for-each-ref --format='%(refname:short)' refs/heads | xargs -r git branch --quiet -D
git remote remove origin
git rm -r --quiet .agents/skills .claude/skills
# A skill shipped in a package is a root skill too; its files stay behind otherwise.
git ls-files -z -- ':(glob)libs/*/src/*/.agents/skills/**' | xargs -0r git rm --quiet
# The runner gives the scaffold a home of its own, so uv is pointed at the real one for its
# managed Pythons, as for its cache: the system has none newer than 3.13.
export UV_PYTHON_INSTALL_DIR="$user_home/.local/share/uv/python"
UV_CACHE_DIR="$user_home/.cache/uv" UV_OFFLINE=1 UV_LINK_MODE=copy \
    uv sync --quiet --frozen --all-packages --all-extras
# The skill catalogue lists the removed skills; regenerate it so the tree starts clean.
uv run --offline --quiet python scripts/docs_check.py >/dev/null || true
uv run --offline --quiet python scripts/docs_check.py >/dev/null
git add -A
git -c user.name=eval -c user.email=eval@localhost commit --quiet -m "eval: remove the root skills"
git repack -a -d -q
rm .git/objects/info/alternates
if [[ $# -eq 2 ]]; then
    git update-ref refs/remotes/origin/dev HEAD
    git checkout --quiet -b "$2"
    git apply --index "$1"
    git -c user.name=eval -c user.email=eval@localhost commit --quiet -m "wip"
fi
