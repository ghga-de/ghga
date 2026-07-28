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

# --- Helm charts --------------------------------------------------------------------------
# Regenerate the per-service charts from workspace metadata + member chart-values.yaml.
charts version="0.0.0-dev":
    uv run python deploy/src/create_charts.py --version {{version}}

# Run the chart library tests (renders the dummy chart via helm).
charts-test:
    uv run pytest -q deploy/tests/

# Build chart dependencies bottom-up (app charts BEFORE the umbrella — the umbrella
# packages the app charts as they sit on disk), then render ghga-demo as a smoke check.
demo-template:
    #!/usr/bin/env bash
    set -euo pipefail
    for c in deploy/charts/*/; do
        name=$(basename "$c")
        { [ "$name" = "ghga-common" ] || [ "$name" = "ghga-demo" ]; } && continue
        helm dep up "$c" --skip-refresh > /dev/null
    done
    helm dep up deploy/charts/ghga-demo --skip-refresh > /dev/null
    helm template ghga deploy/charts/ghga-demo > /dev/null
    echo "ghga-demo renders OK"

# --- Docker -----------------------------------------------------------------------------
# Build a member image locally, e.g. `just image services/auth-service`.
# Python members use the shared Dockerfile (entrypoint = package name, ADR-0014);
# members shipping their own Dockerfile.dhi (frontend) build with it in-place.
# Tags use the release registry scheme with tag 'local' so the charts' generated
# image references resolve with only a tag override (values-local.yaml).
image target:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f "{{target}}/Dockerfile.dhi" ]; then
        name=$(python3 -c "import json; print(json.load(open('{{target}}/package.json'))['name'])")
        docker build -f "{{target}}/Dockerfile.dhi" -t "ghcr.io/ghga-de/ghga/$name:local" "{{target}}"
    else
        name=$(python3 -c "import tomllib; print(tomllib.load(open('{{target}}/pyproject.toml','rb'))['project']['name'])")
        docker build -f docker/Dockerfile --build-arg PACKAGE="$name" -t "ghcr.io/ghga-de/ghga/$name:local" .
    fi

# Build every image member and load them into the kind cluster.
demo-images:
    #!/usr/bin/env bash
    set -euo pipefail
    python3 scripts/image_members.py | python3 -c "
    import json, sys
    for m in json.load(sys.stdin):
        print(m['path'])
    " | while read -r path; do
        echo "== building $path =="
        just image "$path"
        name=$(basename "$path")
        if [ -f "$path/pyproject.toml" ]; then
            name=$(python3 -c "import tomllib; print(tomllib.load(open('$path/pyproject.toml','rb'))['project']['name'])")
        elif [ -f "$path/package.json" ]; then
            name=$(python3 -c "import json; print(json.load(open('$path/package.json'))['name'])")
        fi
        kind load docker-image --name ghga "ghcr.io/ghga-de/ghga/$name:local"
    done

# Reclaim BuildKit cache and dangling layers. Run occasionally: local image builds grew
# the cache to ~17 GB within days, and a full disk breaks builds AND testcontainers.
docker-prune:
    docker builder prune -f --keep-storage 5GB
    docker image prune -f

# --- Local cluster (kind in the devcontainer's docker; ADR-0009/0017 as amended) --------
# On hosts whose outer dockerd enforces an nftables FORWARD drop policy (e.g. a Lima
# docker VM), the nested bridges lose egress after every VM restart — exempt them in
# the sanctioned DOCKER-USER chain. Idempotent; skipped where iptables-nft is absent.
net-fix:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v iptables-nft > /dev/null || { echo "no iptables-nft; skipping"; exit 0; }
    sudo iptables-nft -S FORWARD 2>/dev/null | grep -q '^-P FORWARD DROP' || { echo "FORWARD policy not DROP; skipping"; exit 0; }
    for subnet in 172.17.0.0/16 172.18.0.0/16; do
        for dir in -s -d; do
            sudo iptables-nft -C DOCKER-USER $dir "$subnet" -j ACCEPT 2>/dev/null \
              || sudo iptables-nft -I DOCKER-USER $dir "$subnet" -j ACCEPT
        done
    done
    echo "nested-bridge egress exemptions in place"

# Bring up (or update) the self-contained demo: cluster + charts. Build/load images
# first with `just demo-images` (slow the first time; app pods crashloop until loaded).
up:
    #!/usr/bin/env bash
    set -euo pipefail
    just net-fix
    kind get clusters 2>/dev/null | grep -qx ghga || kind create cluster --config deploy/kind-config.yaml --wait 120s
    just demo-template
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      --kube-context kind-ghga --timeout 10m
    echo "gateway: http://localhost/  (portal at /, issuer at /ghga)"

down:
    kind delete cluster --name ghga

# --- Integration testbed (BDD suite in testbed/; ADR-0009) -------------------------------
# Generate the metldata artifact model from the testbed's example metadata model
# (DSKit, ADR-aligned: derived artifact, not committed) as a values overlay.
testbed-artifacts:
    #!/usr/bin/env bash
    set -euo pipefail
    cd testbed/example_data/metadata
    rm -rf artifact_models && mkdir artifact_models
    uv run ghga-datasteward-kit metadata generate-artifact-models --config-path=metadata_config.yaml
    uv run --with pyyaml python ../../../scripts/artifact_values.py
    rm -rf artifact_models

# Deploy/refresh the demo with the testbed profile (sms, test OP, artifact model).
testbed-up:
    #!/usr/bin/env bash
    set -euo pipefail
    just net-fix
    kind get clusters 2>/dev/null | grep -qx ghga || kind create cluster --config deploy/kind-config.yaml --wait 120s
    [ -f deploy/charts/ghga-demo/values-artifacts.yaml ] || just testbed-artifacts
    just demo-template
    docker manifest inspect ghga/test-oidc-provider:2.2.0 > /dev/null 2>&1 || true
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      -f deploy/charts/ghga-demo/values-artifacts.yaml \
      -f deploy/charts/ghga-demo/values-testbed.yaml \
      --kube-context kind-ghga --timeout 10m

# One-time: virtualenv for the testbed suite (own requirements; not a workspace member).
testbed-install:
    uv venv .venv-testbed --allow-existing --python 3.12  # 3.13 breaks the pinned linkml (typing.re)
    VIRTUAL_ENV=$PWD/.venv-testbed uv pip install -r testbed/requirements.txt

# Run the testbed suite (optionally scoped, e.g. `just testbed steps/test_001_health_check.py`).
# Harvests tokens/keys from the cluster secrets, port-forwards mailhog + lox24, runs pytest.
testbed *args:
    #!/usr/bin/env bash
    set -euo pipefail
    K="kubectl --context kind-ghga"
    secret() { $K get secret "$1" -o jsonpath="{.data.$2}" | base64 -d; }
    export TB_CONFIG_YAML="$PWD/testbed/tb.kind.yaml"
    export TB_STATE_MANAGEMENT_TOKEN=$(secret ghga-harness-tokens SMS_TOKEN)
    export TB_PURGE_CONTROLLER_TOKEN=$(secret ghga-harness-tokens PCS_TOKEN)
    export TB_DLQ_TOKEN=$(secret ghga-harness-tokens DLQS_TOKEN)
    export TB_UPLOAD_TOKEN=$(secret ghga-harness-tokens METLDATA_TOKEN)
    printf '%s' "$TB_UPLOAD_TOKEN" > "$HOME/.ghga_data_steward_token.txt"
    export TB_FIS_PUBKEY=$(secret ghga-c4gh-files crypt4gh\\.pub | sed -n 2p)
    # per-run test-user crypt4gh keypair (any fresh pair works)
    eval "$(uv run --quiet --package auth-km-jobs python -c "from auth_km_jobs.c4gh import generate_crypt4gh_key_pair; k = generate_crypt4gh_key_pair(); print(f'export TB_USER_PRIVATE_CRYPT4GH_KEY={k.export_private()}'); print(f'export TB_USER_PUBLIC_CRYPT4GH_KEY={k.export_public()}')")"
    $K port-forward svc/ghga-mailhog 8025:8025 > /dev/null 2>&1 &
    PF1=$!
    $K port-forward svc/ghga-lox24-mock 8080:8080 > /dev/null 2>&1 &
    PF2=$!
    trap "kill $PF1 $PF2 2>/dev/null || true" EXIT
    sleep 2
    cd testbed && ../.venv-testbed/bin/pytest -v {{args}}
