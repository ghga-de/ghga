#!/usr/bin/env bash
# Shared config + helpers for the GHGA monorepo migration.
# Sourced by import-all.sh and sync-from-mainline.sh.
#
# REVIEW BEFORE RUNNING. This rewrites git history with `git filter-repo`.
# Requires: git, git-filter-repo (https://github.com/newren/git-filter-repo).

set -euo pipefail

# --- Configuration (override via environment) --------------------------------
GHGA_ORG="${GHGA_ORG:-ghga-de}"                       # upstream org (source of truth)
GH_BASE="${GH_BASE:-https://github.com/${GHGA_ORG}}"  # base URL for cloning sources
BRANCH="${BRANCH:-main}"                              # upstream branch to track
LEGACY_DIR="${LEGACY_DIR:-}"                          # if set, clone from local mirrors here
                                                      #   (e.g. /workspaces/ghga-monorepo/.legacy_repos)
MONOREPO="${MONOREPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)}"
WORK="${WORK:-${MONOREPO}/.migration-work}"           # scratch (gitignored)
MANIFEST="${MANIFEST:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/repos.tsv}"

SRC_CACHE="${WORK}/_src"   # pristine clones, fetched once per source repo
RW_DIR="${WORK}/_rw"       # per-destination rewritten clones

# --- Boilerplate to drop on import, by kind ----------------------------------
# These paths are centralised at the monorepo root, so they must not enter the
# repo (and must not appear in incremental sync deltas -> no conflicts).
# Whole-repo imports (subpath == ".") use these; partial imports (file-services-backend)
# select a single subtree instead and need no drops.
drop_paths_for_kind() {
  case "$1" in
    lib|service|tool)
      printf '%s\n' \
        lock .github .template .pyproject_generation .readme_generation scripts \
        .pre-commit-config.yaml Dockerfile Dockerfile.dhi .devcontainer .dockerignore ;;
    frontend)
      # Keep the bespoke frontend Dockerfile/build; only drop per-repo CI + devcontainer.
      printf '%s\n' .github .devcontainer ;;
    testbed)
      # Keep features/steps/fixtures + pytest config; drop compose/CI/lock/devcontainer.
      printf '%s\n' .github .devcontainer lock Dockerfile Dockerfile.dhi ;;
    *) : ;;
  esac
}

log()  { printf '\033[1;34m[migrate]\033[0m %s\n' "$*" >&2; }
warn() { printf '\033[1;33m[migrate]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[migrate]\033[0m %s\n' "$*" >&2; exit 1; }

require_tools() {
  command -v git >/dev/null || die "git not found"
  git filter-repo --version >/dev/null 2>&1 || die "git-filter-repo not found (pip install git-filter-repo)"
}

# Iterate manifest rows: calls `handle_row kind source subpath dest` for each.
each_row() {
  local handler="$1" kind source subpath dest
  [[ -f "$MANIFEST" ]] || die "manifest not found: $MANIFEST"
  while IFS=$'\t' read -r kind source subpath dest; do
    [[ -z "${kind:-}" || "${kind:0:1}" == "#" ]] && continue
    "$handler" "$kind" "$source" "$subpath" "$dest"
  done < "$MANIFEST"
}

# Fetch (or refresh) a pristine mirror of a source repo into SRC_CACHE.
ensure_src() {
  local source="$1" dst="${SRC_CACHE}/$1"
  if [[ -d "$dst/.git" ]]; then
    log "refreshing source: $source"
    git -C "$dst" fetch --tags --prune origin "$BRANCH"
    git -C "$dst" checkout -q "$BRANCH"
    git -C "$dst" reset -q --hard "origin/${BRANCH}"
  else
    mkdir -p "$SRC_CACHE"
    if [[ -n "$LEGACY_DIR" && -d "${LEGACY_DIR}/${source}/.git" ]]; then
      log "cloning source from local mirror: $source"
      git clone -q --branch "$BRANCH" "file://${LEGACY_DIR}/${source}" "$dst"
    else
      log "cloning source from ${GH_BASE}/${source}.git"
      git clone -q --branch "$BRANCH" "${GH_BASE}/${source}.git" "$dst"
    fi
  fi
}

# Produce a rewritten clone for one destination at RW_DIR/<dest-slug> whose
# history has the files at `dest` and the boilerplate removed. Echoes the path.
rewrite_for_row() {
  local kind="$1" source="$2" subpath="$3" dest="$4"
  local slug rw; slug="${dest//\//__}"; rw="${RW_DIR}/${slug}"
  ensure_src "$source"
  rm -rf "$rw"; mkdir -p "$RW_DIR"
  git clone -q "${SRC_CACHE}/${source}" "$rw"

  # NB: git-filter-repo prints a "NOTICE: Removing 'origin' remote" line to STDOUT; this
  # function returns $rw via stdout, so all filter-repo output must go to stderr (>&2),
  # otherwise the NOTICE pollutes the captured return value.
  if [[ "$subpath" == "." ]]; then
    # Pass 1: drop centralised boilerplate (if any for this kind).
    local -a drops=(); mapfile -t drops < <(drop_paths_for_kind "$kind")
    if (( ${#drops[@]} )); then
      local -a args=(); local p; for p in "${drops[@]}"; do args+=(--path "$p"); done
      git -C "$rw" filter-repo --invert-paths "${args[@]}" --force 1>&2
    fi
    # Pass 2: move everything into the destination subdir.
    git -C "$rw" filter-repo --to-subdirectory-filter "$dest" --force 1>&2
  else
    # Partial import (file-services-backend): keep only the subtree, place at dest.
    git -C "$rw" filter-repo --path "${subpath}/" --path-rename "${subpath}/:${dest}/" --force 1>&2
  fi
  printf '%s\n' "$rw"
}
