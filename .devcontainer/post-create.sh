#!/usr/bin/env bash
set -euo pipefail

# Named volumes mount root-owned; chown the mount points back to vscode
# so uv, Playwright, Claude Code, and gh can write to them.
sudo chown vscode:vscode ~/.local ~/.local/share ~/.cache ~/.config
sudo chown -R vscode:vscode ~/.claude ~/.config/gh ~/.local/share/uv ~/.cache/uv ~/.cache/ms-playwright

# just and kind come from no feature, and ~/.local/bin is not one of the persisted
# volumes — so a rebuild loses them and every justfile recipe stops working, including
# the whole local cluster and test-bed flow. Pinned to the versions the demo and the
# integration gate are verified against. The arch split is not hypothetical: this runs
# on arm64 workstations as readily as on an x86 runner.
JUST_VERSION=1.57.0
KIND_VERSION=0.30.0
case "$(uname -m)" in
  aarch64 | arm64) JUST_ARCH=aarch64 KIND_ARCH=arm64 ;;
  x86_64 | amd64) JUST_ARCH=x86_64 KIND_ARCH=amd64 ;;
  *)
    echo "unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac
mkdir -p ~/.local/bin
if [ "$(just --version 2> /dev/null || true)" != "just ${JUST_VERSION}" ]; then
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${JUST_ARCH}-unknown-linux-musl.tar.gz" \
    | tar -xz -C ~/.local/bin just
fi
if [ "$(kind --version 2> /dev/null || true)" != "kind version ${KIND_VERSION}" ]; then
  curl -fsSL -o ~/.local/bin/kind "https://kind.sigs.k8s.io/dl/v${KIND_VERSION}/kind-linux-${KIND_ARCH}"
  chmod +x ~/.local/bin/kind
fi

# Migration tooling
uv tool install --reinstall git-filter-repo

# Provision both stacks
uv sync --all-packages --all-extras
(cd frontend/data-portal && pnpm install --frozen-lockfile && pnpm exec playwright install --with-deps chromium)

# Git hooks (ADR-0018). Idempotent, and after the sync above because the hooks run ruff,
# mypy, prettier and eslint out of the two workspaces rather than their own environments.
uv run pre-commit install
