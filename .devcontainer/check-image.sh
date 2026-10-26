#!/usr/bin/env bash
# Assert the dev container image provides what the repo assumes. ci.yaml's
# check-devcontainer job feeds this to a login shell in the built image:
#
#   docker run --rm -i ghga-devcontainer:ci bash -l -s < .devcontainer/check-image.sh
set -eux

# The bootstrap interpreter must carry the stdlib, not just python3-minimal:
# the justfile image recipes and scripts/*.py import tomllib.
python3 -c "import tomllib, json"
node --version && pnpm --version && uv --version && just --version
# Working tools the whole monorepo leans on: fd/rg/bat/jq for navigating and
# inspecting a tree this size, shellcheck/shfmt for the shell the repo runs on
# (scripts/just, .devcontainer/post-create.sh, scripts/migration, testbed),
# dig for the container's several competing sources of name resolution. dig
# arrives via docker-in-docker too, so this also catches that feature dropping
# it. static-web-server serves the data portal's production build (`just fe-prod`).
# One at a time: `command -v a b c` exits 0 even when some are missing.
for t in fd bat rg jq shellcheck shfmt dig static-web-server; do command -v "$t"; done
# docker/Dockerfile uses `RUN --mount=type=cache`, so the image builds the repo
# publishes depend on BuildKit being available, not just a docker CLI.
docker buildx version
docker compose version
