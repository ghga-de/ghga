#!/usr/bin/env bash
set -euo pipefail

# Named volumes mount root-owned; chown the mount points back to vscode
# so uv, Playwright, and Claude Code can write to them.
sudo chown vscode:vscode ~/.local ~/.local/share ~/.cache
sudo chown -R vscode:vscode ~/.claude ~/.local/share/uv ~/.cache/uv ~/.cache/ms-playwright

# Migration tooling
uv tool install --reinstall git-filter-repo

# Provision both stacks
uv sync --all-packages --all-extras
(cd frontend/data-portal && pnpm install --frozen-lockfile && pnpm exec playwright install --with-deps chromium)
