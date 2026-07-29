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
# `reclaim=true` (CI) drops each image from the docker store once it is loaded and
# trims the build cache as it goes: `kind load` copies into the node's containerd,
# so holding the docker copy doubles the footprint for no gain on a one-shot runner.
# Locally the default keeps both — rebuilds are far faster off the warm cache.
demo-images reclaim="false": cluster
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
        if [ "{{reclaim}}" = "true" ]; then
            docker image rm "ghcr.io/ghga-de/ghga/$name:local" > /dev/null
            docker builder prune -f --keep-storage 4GB > /dev/null
        fi
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
# Create the kind cluster if it isn't there yet (idempotent). Everything that loads
# images into the node or installs into it depends on this: `kind load` fails with
# "no nodes found for cluster" when the cluster is missing — easy to miss locally,
# where a cluster is nearly always already up, and fatal in CI, where it never is.
cluster:
    #!/usr/bin/env bash
    set -euo pipefail
    just net-fix
    kind get clusters 2>/dev/null | grep -qx ghga || kind create cluster --config deploy/kind-config.yaml --wait 120s

up: cluster
    #!/usr/bin/env bash
    set -euo pipefail
    just demo-template
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      --kube-context kind-ghga --wait --timeout 15m
    just wait-ready
    echo "gateway: http://localhost/  (portal at /, issuer at /ghga)"

# Block until the platform is actually serving. `helm --wait` covers the release's own
# workloads, but the gateway's pod is created by the Envoy operator from the Gateway
# resource — outside the release — so it needs its own condition. Without both gates a
# fresh cluster answers the first request before anything is listening: the services
# fail fast when Kafka is not yet up (KafkaConnectionError), and though Kubernetes
# restarts them, a suite that starts immediately runs against the crash-loop window.
wait-ready:
    kubectl --context kind-ghga wait --for=condition=Programmed gateway/ghga --timeout=5m

down:
    kind delete cluster --name ghga

# --- Integration testbed (BDD suite in testbed/; ADR-0009) -------------------------------
# Generate the metldata artifact model from the testbed's example metadata model
# (DSKit, ADR-aligned: derived artifact, not committed) as a values overlay.
testbed-artifacts:
    #!/usr/bin/env bash
    set -euo pipefail
    root=$PWD
    cd testbed/example_data/metadata
    rm -rf artifact_models && mkdir artifact_models
    # testbed/ carries its own pyproject.toml, so from here uv discovers *it* as the
    # project and builds a venv holding none of the workspace tools. Point uv at the
    # workspace root instead. --no-sync then leaves that root environment exactly as
    # `just sync` built it (--all-packages --all-extras); a plain `uv run` would
    # re-resolve it to the root defaults and drop members later recipes rely on.
    uv run --no-sync --project "$root" \
      ghga-datasteward-kit metadata generate-artifact-models --config-path=metadata_config.yaml
    uv run --no-sync --project "$root" --with pyyaml python "$root/scripts/artifact_values.py"
    rm -rf artifact_models

# Deploy/refresh the demo with the testbed profile (sms, test OP, artifact model).
testbed-up: cluster
    #!/usr/bin/env bash
    set -euo pipefail
    [ -f deploy/charts/ghga-demo/values-artifacts.yaml ] || just testbed-artifacts
    just demo-template
    docker manifest inspect ghga/test-oidc-provider:2.2.0 > /dev/null 2>&1 || true
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      -f deploy/charts/ghga-demo/values-artifacts.yaml \
      -f deploy/charts/ghga-demo/values-testbed.yaml \
      --kube-context kind-ghga --wait --timeout 15m
    just wait-ready

# One-time: virtualenv for the testbed suite (own requirements; not a workspace member).
# The UI phase drives a real browser, so the matching chromium build comes with it
# (playwright pins the build to the library version; a system chromium won't do).
testbed-install:
    uv venv .venv-testbed --allow-existing --python 3.12  # 3.13 breaks the pinned linkml (typing.re)
    VIRTUAL_ENV=$PWD/.venv-testbed uv pip install -r testbed/requirements.txt
    .venv-testbed/bin/playwright install chromium

# Make the in-cluster MinIO name resolve locally: services hand the connector
# pre-signed S3 URLs built from s3_endpoint_url, and those signatures are bound to
# that exact host — so the name must resolve both in-cluster and here.
testbed-hosts:
    #!/usr/bin/env bash
    set -euo pipefail
    grep -q "ghga-minio" /etc/hosts || echo "127.0.0.1 ghga-minio" | sudo tee -a /etc/hosts > /dev/null
    echo "ghga-minio resolves locally"

# Reset the identity state to a coherent cold start: the suite's clean slate
# restores the data steward from its own snapshot, so leftovers from earlier runs
# (or an out-of-band edit) can leave the claim, user, IVA and notification
# projection disagreeing. Dropping both databases and restarting lets the
# services re-seed and rebuild their projections from events.
testbed-reset:
    #!/usr/bin/env bash
    set -euo pipefail
    K="kubectl --context kind-ghga"
    MPOD=$($K get pods -o name | grep mongodb | head -1)
    # Drop every service database: the suite's clean slate removes the migration
    # bookkeeping, so a service restarting afterwards would re-run migrations over
    # already-migrated data and crash-loop. Starting from empty avoids that.
    $K exec "$MPOD" -- mongosh --quiet --eval \
      'db.adminCommand({listDatabases:1}).databases
         .map(d => d.name)
         .filter(n => !["admin","config","local"].includes(n))
         .forEach(n => db.getSiblingDB(n).dropDatabase())' > /dev/null
    apps=$($K get deploy -o name | grep -vE "envoy|mongodb|kafka|minio|vault|mailhog|lox24|test-oidc|aai")
    echo "$apps" | xargs -r -n1 $K rollout restart > /dev/null
    for d in $apps; do $K rollout status "$d" --timeout=240s > /dev/null; done
    sleep 20
    echo "state reset (databases empty, services re-migrated and re-seeded)"

# Run the testbed suite (optionally scoped, e.g. `just testbed steps/test_001_health_check.py`).
# Harvests tokens/keys from the cluster secrets, port-forwards the services the suite
# and the connector reach directly (mailhog, lox24, minio), runs pytest.
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
    # the connector needs the RAW 32-byte secret (export_private is PEM-ish and
    # fails with "PrivateKey must be created from a 32 bytes long raw secret key")
    eval "$(uv run --quiet --package auth-km-jobs python -c "from auth_km_jobs.c4gh import generate_crypt4gh_key_pair; k = generate_crypt4gh_key_pair(); print(f'export TB_USER_PRIVATE_CRYPT4GH_KEY={k.export_private_raw()}'); print(f'export TB_USER_PUBLIC_CRYPT4GH_KEY={k.export_public()}')")"
    mkdir -p /tmp/submission /tmp/connector
    $K port-forward svc/ghga-mailhog 8025:8025 > /dev/null 2>&1 &
    PF1=$!
    $K port-forward svc/ghga-lox24-mock 8080:8080 > /dev/null 2>&1 &
    PF2=$!
    just testbed-hosts
    $K port-forward svc/ghga-minio 9000:9000 > /dev/null 2>&1 &
    PF3=$!
    trap "kill $PF1 $PF2 $PF3 2>/dev/null || true" EXIT
    sleep 2
    cd testbed && ../.venv-testbed/bin/pytest -v {{args}}
