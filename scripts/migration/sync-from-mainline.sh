#!/usr/bin/env bash
# One-way incremental sync: pull new mainline commits into the monorepo,
# history-preserving, for one or more destinations (default: all).
#
# Relies on `git filter-repo` being deterministic: re-running it on append-only
# mainline yields identical SHAs for already-imported commits and new SHAs only
# for new ones, so `git merge` brings in just the delta.
#
# Usage:
#   scripts/migration/sync-from-mainline.sh                 # sync everything
#   scripts/migration/sync-from-mainline.sh libs/hexkit     # sync one destination
#   LEGACY_DIR=...  scripts/migration/sync-from-mainline.sh # source from local mirrors
#
# On conflict (expected only in per-service pyproject.toml [tool.uv.sources]),
# the merge stops for manual resolution; resolve, `git commit`, then re-run for the rest.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_tools
[[ -z "$(git -C "$MONOREPO" status --porcelain)" ]] \
  || die "monorepo working tree is dirty — commit or stash first"

ONLY=("$@")   # optional list of destinations to limit the sync to

want_dest() {
  (( ${#ONLY[@]} == 0 )) && return 0
  local d; for d in "${ONLY[@]}"; do [[ "$d" == "$1" ]] && return 0; done
  return 1
}

sync_row() {
  local kind="$1" source="$2" subpath="$3" dest="$4"
  want_dest "$dest" || return 0
  log "syncing ${source} (${subpath}) -> ${dest}"
  local rw remote; rw="$(rewrite_for_row "$kind" "$source" "$subpath" "$dest")"
  remote="sync_${dest//\//__}"
  git -C "$MONOREPO" remote remove "$remote" 2>/dev/null || true
  git -C "$MONOREPO" remote add "$remote" "$rw"
  git -C "$MONOREPO" fetch -q "$remote" "$BRANCH"
  if git -C "$MONOREPO" merge-base --is-ancestor "${remote}/${BRANCH}" HEAD 2>/dev/null; then
    log "  up to date."
  else
    git -C "$MONOREPO" merge --no-edit \
        -m "Sync ${source} (${subpath}) -> ${dest} from ${GHGA_ORG}/${BRANCH}" \
        "${remote}/${BRANCH}" \
      || die "merge conflict in ${dest} — resolve, commit, then re-run for the remaining dests"
  fi
  git -C "$MONOREPO" remote remove "$remote"
}

each_row sync_row
log "sync complete."
