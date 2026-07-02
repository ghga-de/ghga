#!/usr/bin/env bash
# Initial, history-preserving import of all source repos into the monorepo.
# Each source is rewritten (subdir move + boilerplate drop) and merged with
# --allow-unrelated-histories. Destinations are disjoint, so merges do not conflict.
#
# Usage:
#   cd <monorepo>            # must already be a git repo with at least one commit
#   LEGACY_DIR=$PWD/.legacy_repos scripts/migration/import-all.sh        # use local mirrors (all)
#   scripts/migration/import-all.sh                                       # clone from ghga-de (all)
#   scripts/migration/import-all.sh tools/ghga-transpiler                 # re-import only this dest
#
# Idempotency: re-running re-merges; for a clean re-run start from a fresh monorepo branch.
# To re-import a single dest onto a different branch, first `git rm -r <dest>` and commit, then
# pass the dest here (its branch comes from repos.tsv).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_tools
git -C "$MONOREPO" rev-parse HEAD >/dev/null 2>&1 \
  || die "monorepo has no commits yet — create the root scaffolding commit first (see runbook)"
[[ -z "$(git -C "$MONOREPO" status --porcelain)" ]] \
  || die "monorepo working tree is dirty — commit or stash first"

ONLY=("$@")   # optional list of destinations to limit the import to (default: all)
want_dest() {
  (( ${#ONLY[@]} == 0 )) && return 0
  local d; for d in "${ONLY[@]}"; do [[ "$d" == "$1" ]] && return 0; done
  return 1
}

import_row() {
  local kind="$1" source="$2" subpath="$3" dest="$4" branch="$5"
  want_dest "$dest" || return 0
  log "importing ${source} (${subpath})@${branch} -> ${dest}"
  local rw remote; rw="$(rewrite_for_row "$kind" "$source" "$subpath" "$dest" "$branch")"
  remote="import_${dest//\//__}"
  git -C "$MONOREPO" remote remove "$remote" 2>/dev/null || true
  git -C "$MONOREPO" remote add "$remote" "$rw"
  git -C "$MONOREPO" fetch -q "$remote" "$branch"
  git -C "$MONOREPO" merge --allow-unrelated-histories --no-edit \
      -m "Import ${source} (${subpath})@${branch} into ${dest} (history-preserving)" \
      "${remote}/${branch}"
  git -C "$MONOREPO" remote remove "$remote"
}

each_row import_row
log "import complete. Review 'git log --oneline --graph' and run the harmonisation steps (runbook §3)."
