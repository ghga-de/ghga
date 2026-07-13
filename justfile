# GHGA monorepo task runner — a thin facade over uv / pnpm / helm + the affected script.
# See docs/adr/0015-task-runner.md. Run `just` to list recipes.
set shell := ["bash", "-uc"]

default:
    @just --list

# --- Python workspace -------------------------------------------------------------------
# Resolve + install all workspace members, their extras, and the shared dev toolchain.
# --all-extras is needed so member test suites (which use optional deps) can run.
sync:
    uv sync --all-packages --all-extras

# Update the single workspace lockfile.
lock:
    uv lock

# Lint + format check across the workspace.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint + format.
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# mypy per member (a single `mypy .` collides on duplicate module names across members)
typecheck:
    for m in libs/*/src services/*/src tools/*/src; do echo "== $m =="; uv run mypy "$m" || exit 1; done

# Run tests; optionally scope to a member, e.g. `just test libs/hexkit`.
test target=".":
    uv run pytest {{target}}

# Print the workspace targets affected by the working tree vs a base ref.
affected base="origin/main":
    uv run python scripts/affected_targets.py --base {{base}}

# --- Front end (data-portal, pnpm) ------------------------------------------------------
fe-install:
    cd frontend/data-portal && pnpm install --frozen-lockfile

fe-build:
    cd frontend/data-portal && pnpm build

fe-test:
    cd frontend/data-portal && pnpm test

fe-lint:
    cd frontend/data-portal && pnpm lint

# Run the data-portal dev server with MOCKED api + oidc (MSW) — no backend needed.
# Generates public/config.js (mock_api=true) and serves on http://localhost:8080.
# (Bare `pnpm start` won't work on its own: it skips the config.js generation this
# launcher does — that's why the server needs run.js, not plain `ng serve`.)
fe-dev:
    cd frontend/data-portal && node run.js --dev

# Run the data-portal against a real backend (default: staging) instead of mocks.
fe-dev-backend:
    cd frontend/data-portal && node run.js --dev --with-backend

# --- Migration (see docs/migration/runbook.md) ------------------------------------------
# Dry-run the history-preserving import from the local .legacy_repos snapshot.
import-from-snapshot:
    LEGACY_DIR="$PWD/.legacy_repos" scripts/migration/import-all.sh

# One-way incremental sync from mainline (optionally limit to dests).
sync-mainline *args:
    scripts/migration/sync-from-mainline.sh {{args}}

# --- Local cluster (TODO: implemented once charts land — ADR-0012) ----------------------
# up:    kind create cluster && build/load affected images && helm install ghga ./deploy/charts/ghga-demo
# down:  kind delete cluster
