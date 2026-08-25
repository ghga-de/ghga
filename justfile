# GHGA monorepo task runner — a thin facade over uv / pnpm / helm + the affected script.
# See docs/adr/0015-task-runner.md. Run `just` to list recipes.
set shell := ["bash", "-uc"]

# Registry root the `image`/`image-mono`/`demo-load` recipes tag/load under. Defaults to
# the real platform registry (matches the charts' generated image.registry/repository) so
# the local kind demo loop needs no override. dev-images.yaml/security-scan.yaml set
# IMAGE_REGISTRY to their own GHCR scratch space, which is deliberately independent of the
# release target (see those workflows' headers).
image_registry := env_var_or_default("IMAGE_REGISTRY", "docker.io/ghga")

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

# A single `mypy .` collides on duplicate module names across members, and the result
# depends on the path set it is given -- so the unit, not the file, is what gets checked.
# scripts/typecheck.py is the same runner the pre-commit hook and CI use.
# Type-check every member (src + tests) and the non-member Python.
typecheck:
    uv run python scripts/typecheck.py --all

# --- Git hooks (pre-commit; ADR-0018) ---------------------------------------------------
# Once per clone -- the dev container does it for you.
# Install the git hooks into .git/hooks.
hooks:
    uv run pre-commit install

# The branch guard is skipped: it exists to stop commits landing on main, not to fail a
# full-tree sweep.
# Run every hook over the whole tree, as CI's `hygiene` job does.
hooks-all:
    SKIP=no-commit-to-branch uv run pre-commit run --all-files

# Only the generic pre-commit-hooks repo carries a `rev`; the ruff / mypy / prettier /
# eslint hooks take their version from uv.lock and pnpm-lock.yaml, so those are bumped by
# updating the lockfiles instead.
# Bump the pinned hook revisions.
hooks-update:
    uv run pre-commit autoupdate

# Run tests; optionally scope to a member, e.g. `just test libs/hexkit`.
test target=".":
    uv run pytest {{target}}

# Print the workspace targets affected by the working tree vs a base ref.
affected base="origin/main":
    uv run python scripts/affected_targets.py --base {{base}}

# --- PyPI lane --------------------------------------------------------------------------
# Run ONE cell of the published-combo matrix (.github/workflows/pypi-matrix.yaml) locally.
#
# Use it when a cell goes red: `uv sync` cannot reproduce those failures, because in the
# shared workspace venv a member can import whatever a sibling installed. Here it gets only
# its own wheel and its declared dependencies, so the gaps surface.
#
#   just published-combo tools/ghga-connector        # on the default version
#   just published-combo libs/hexkit 3.11
#
# Test one member the way an external consumer gets it: wheel + PyPI-resolved deps.
published-combo member python="3.12":
    #!/usr/bin/env bash
    set -euo pipefail
    # The same script CI reads, so a local run cannot drift from the cell.
    cell=$(MEMBER="{{member}}" PYTHON="{{python}}" \
      MEMBERS="$(python3 scripts/pypi_members.py --members --check-pypi --paths "{{member}}")" \
      python3 -c "
    import json, os, sys
    member, python = os.environ['MEMBER'], os.environ['PYTHON']
    members = json.loads(os.environ['MEMBERS'])
    if not members:
        sys.exit(f'error: {member} is not a PyPI-lane member — check its [tool.ghga]'
                 ' release marker (ADR-0014)')
    cell = members[0]
    package, declared = cell['package'], cell['testable_requires_python']
    if python not in cell['pythons']:
        runs_on = ', '.join(cell['pythons']) or 'no version in the matrix range'
        sys.exit(f'error: the matrix does not run {package} on {python} — it declares'
                 f' {declared}, so it runs on: {runs_on}')
    print(package)
    print(','.join(cell['extras']))
    print(' '.join(cell['train_deps']))
    ")
    # One field per line, not tab-separated: tab is IFS *whitespace*, so bash collapses a
    # run of them and an empty `extras` (every tool has one) shifts train_deps into it.
    { read -r package; read -r extras; read -r train_deps; } <<< "$cell"

    # Fixed path, not mktemp: the venv outlives the recipe, so a failure can be poked at
    # (`$work/venv/bin/python -m pytest -k ...`), and a re-run wipes it rather than
    # leaving a trail of temp trees.
    work="${TMPDIR:-/tmp}/ghga-published-combo/$package-{{python}}"
    rm -rf "$work" && mkdir -p "$work/wheels"

    # Member + whatever is being released alongside it (--check-pypi decides that: the
    # libraries whose declared version is not on the index yet). Everything else is left
    # out so it resolves from PyPI, exactly as in CI and as on a user's machine.
    for path in "{{member}}" $train_deps; do
        uv build --wheel --out-dir "$work/wheels" "$path"
    done

    # From outside the repo: inside it, uv picks up the workspace's requires-python (3.13)
    # and warns about every member that cannot have it.
    cd "$work"
    uv venv --python "{{python}}" "$work/venv"

    # The closure is in the wheelhouse to be resolved against, not installed directly —
    # so pick this member's own wheel by name.
    wheel=$(ls "$work"/wheels/"${package//-/_}"-*.whl)
    spec="$wheel"
    [ -n "$extras" ] && spec="${wheel}[${extras}]"
    echo "== installing $spec"
    uv pip install --python "$work/venv/bin/python" --find-links "$work/wheels" "$spec"

    # Test dependencies live in the root dependency-group, not in the member — minus the
    # lint tools, plus whatever this member imports without declaring.
    cd "{{justfile_directory()}}"
    python3 scripts/pypi_members.py --dev-requirements --package "$package" \
      > "$work/test-requirements.txt"
    uv pip install --python "$work/venv/bin/python" --find-links "$work/wheels" \
      -r "$work/test-requirements.txt"

    # cwd = the member directory, as in CI: each member is its own pytest rootdir, and the
    # src/ layout means the tests import the installed package, not the working tree.
    echo "== running {{member}} tests on {{python}} (env: $work/venv)"
    cd "{{member}}"
    "$work/venv/bin/python" -m pytest -q --durations=10

# --- Front end (data-portal, pnpm) ------------------------------------------------------
fe-install:
    cd frontend/data-portal && pnpm install --frozen-lockfile

fe-build:
    cd frontend/data-portal && pnpm build

fe-test:
    cd frontend/data-portal && pnpm test

fe-lint:
    cd frontend/data-portal && pnpm lint

# Prettier owns formatting for the front end (ESLint does not check it).
fe-format:
    cd frontend/data-portal && pnpm format

fe-format-check:
    cd frontend/data-portal && pnpm format:check

# The four dev-server modes are the two independent switches --with-backend (real API
# instead of the MSW mocks) and --with-oidc (real login instead of the faked session);
# frontend/data-portal/README.md documents what each one needs. Per-developer settings
# and secrets go in frontend/data-portal/local.env (see local.env.example).

# Generates public/config.js (mock_api=true) and serves on http://localhost:8080.
# (Bare `pnpm start` won't work on its own: it skips the config.js generation this
# launcher does — that's why the server needs run.js, not plain `ng serve`.)
# Run the data-portal dev server with MOCKED api + oidc (MSW) — no backend needed.
fe-dev:
    cd frontend/data-portal && node run.js --dev

# Run the data-portal against a real backend (default: staging) instead of mocks.
fe-dev-backend:
    cd frontend/data-portal && node run.js --dev --with-backend

# Run the data-portal against the real OIDC provider (mock API), on https://<backend host>/.
fe-dev-oidc: fe-dev-ssl
    cd frontend/data-portal && node run.js --dev --with-oidc

# Run the data-portal against both the real backend and the real OIDC provider.
fe-dev-backend-oidc: fe-dev-ssl
    cd frontend/data-portal && node run.js --dev --with-backend --with-oidc

# Create the dev server's self-signed certificate (idempotent, reissued per hostname).
fe-cert:
    frontend/data-portal/create-cert.sh

# What the --with-oidc modes need before they can serve: a certificate, and a node that
# may bind port 443. The port is not negotiable — the OIDC provider redirects back to a
# registered URI that carries no port — but this container shares the host's network
# namespace (see .devcontainer/devcontainer.json), so it also inherits the host's
# net.ipv4.ip_unprivileged_port_start=1024 instead of the 0 a private namespace gets.
# Rather than lower that on the host, grant the capability to this container's node,
# which a rebuild or a node upgrade then discards along with everything else in the
# image. Idempotent; only the setcap needs sudo.
[private]
fe-dev-ssl: fe-cert
    #!/usr/bin/env bash
    set -euo pipefail
    command -v getcap > /dev/null && command -v setcap > /dev/null \
      || { echo "getcap/setcap not found; install libcap2-bin" >&2; exit 1; }
    node=$(readlink -f "$(command -v node)")
    # plain grep, not -q — see the SIGPIPE note in `images-present`
    if getcap "$node" | grep cap_net_bind_service > /dev/null; then exit 0; fi
    sudo setcap cap_net_bind_service=+ep "$node"
    echo "granted cap_net_bind_service to $node"

# --- Migration (see docs/migration/runbook.md) ------------------------------------------
# Dry-run the history-preserving import from the local .legacy_repos snapshot.
import-from-snapshot:
    LEGACY_DIR="$PWD/.legacy_repos" scripts/migration/import-all.sh

# One-way incremental sync from mainline (optionally limit to dests).
sync-mainline *args:
    scripts/migration/sync-from-mainline.sh {{args}}

# --- Helm charts --------------------------------------------------------------------------
# Regenerate the per-service charts from workspace metadata + member chart-values.yaml.
# Passing no version reuses the committed one: release-charts.yaml publishes whatever is
# committed, so regenerating must not change it (ADR-0004).
charts version="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{version}}" ]; then
        uv run python deploy/src/create_charts.py --version "{{version}}"
    else
        uv run python deploy/src/create_charts.py
    fi

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
# `tag` and trailing docker-build flags are overridable so CI reuses these recipes
# instead of duplicating the build commands — e.g. dev-images.yaml / security-scan.yaml
# run `just image-mono dev --pull --label org.opencontainers.image.revision=<sha>`.
image target tag='local' *flags: check-members
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f "{{target}}/Dockerfile.dhi" ]; then
        name=$(python3 -c "import json; print(json.load(open('{{target}}/package.json'))['name'])")
        docker build -f "{{target}}/Dockerfile.dhi" {{flags}} -t "{{image_registry}}/$name:{{tag}}" "{{target}}"
    else
        name=$(python3 -c "import tomllib; print(tomllib.load(open('{{target}}/pyproject.toml','rb'))['project']['name'])")
        docker build -f docker/Dockerfile --build-arg PACKAGE="$name" {{flags}} -t "{{image_registry}}/$name:{{tag}}" .
    fi

# One build instead of ~22 — the demo/CI image step drops from ~15-20 min to ~1 min.
# The charts start services with `command: [<executable>]`, so one image serves them all;
# see the mono stage in docker/Dockerfile for why this is demo/CI only.
# Build the mono image: EVERY Python member in one venv (docker/Dockerfile VARIANT=mono).
image-mono tag='local' *flags: check-members
    docker build -f docker/Dockerfile --build-arg VARIANT=mono {{flags}} \
      -t {{image_registry}}/platform:{{tag}} .

# uv finds workspace members by glob (`libs/*`, `services/*`, `tools/*`) and refuses any
# match without a pyproject.toml. In a working tree it consults git first and skips matches
# whose contents are all ignored, so a directory left behind by a removed member -- tracked
# files gone, an ignored build artifact such as *.egg-info keeping the directory alive --
# resolves fine here. The build context has no .git (see .dockerignore), so uv there sees a
# real member with no manifest and fails several minutes into the build, far from the cause.
# .dockerignore cannot prevent it: excluding the residue still leaves the empty directory in
# the context. So check up front, where the message can name the directory and the fix.
check-members:
    #!/usr/bin/env bash
    set -euo pipefail
    orphans=()
    for d in libs/*/ services/*/ tools/*/; do
        [ -f "$d/pyproject.toml" ] || orphans+=("${d%/}")
    done
    if [ ${#orphans[@]} -gt 0 ]; then
        printf 'error: workspace member directory without a pyproject.toml:\n' >&2
        printf '  %s\n' "${orphans[@]}" >&2
        printf 'Left over from a removed member? Its tracked files are gone, but ignored\n' >&2
        printf 'build residue keeps the directory alive. Remove it: git clean -fdx <dir>\n' >&2
        exit 1
    fi

# Building and loading are deliberately SEPARATE (`just demo-load` does the loading): the
# build survives `just down`, the load does not, and coupling them made a cluster teardown
# cost a full rebuild of everything.
# Build every image member into the local docker store (one image per member, as released).
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
    done

# Members shipping their own Dockerfile (the frontend) cannot be folded into the shared
# venv, so they are still built one by one.
# Build the mono profile: the single Python image plus the non-Python members.
demo-images-mono: image-mono
    #!/usr/bin/env bash
    set -euo pipefail
    python3 scripts/image_members.py | python3 -c "
    import json, sys
    for m in json.load(sys.stdin):
        if m['kind'] != 'python':
            print(m['path'])
    " | while read -r path; do
        echo "== building $path =="
        just image "$path"
    done

# Copy the built images from the docker store into the kind node. Safe to re-run, which is
# why `up` can depend on it unconditionally — but not free: kind's "already present" check
# compares the docker image ID against the node's, and with docker's containerd image store
# those never match, so every image is re-copied on every run (~40 s for the full per-member
# set, a couple of seconds for the mono profile). Measured, not assumed — do not "optimise"
# this by skipping the load.
# Loads the set the requested profile actually deploys, NOT everything in the docker store:
# a store holding both profiles would otherwise load 24 images to run the 2 the mono profile
# needs, throwing away most of what mono buys. `up`/`testbed-up` pass their profile through.
# `reclaim=true` (CI) drops each docker copy once it is loaded: `kind load` copies into the
# node's containerd, so keeping both doubles the footprint for no gain on a one-shot runner.
# Locally the default keeps both — a later reload then costs no rebuild at all.
# Copy the profile's built images from the docker store into the kind node.
demo-load profile="" reclaim="false": cluster
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{profile}}" ] && [ "{{profile}}" != "mono" ]; then
        echo "error: unknown profile '{{profile}}' (expected 'mono', or nothing)" >&2
        exit 1
    fi
    # what the node already has, so a reclaimed docker store is not mistaken for
    # "never built": reclaim=true deletes each docker copy after loading it, and
    # `up`/`testbed-up` re-enter this recipe as a dependency afterwards
    node_images=$(docker exec ghga-control-plane crictl images 2>/dev/null | awk 'NR>1 {print $1":"$2}' || true)
    loaded=0
    already=0
    while read -r name; do
        ref="{{image_registry}}/$name:local"
        if ! docker image inspect "$ref" > /dev/null 2>&1; then
            if printf '%s\n' "$node_images" | grep -Fx "$ref" > /dev/null; then
                already=$((already + 1))
            fi
            continue
        fi
        kind load docker-image --name ghga "$ref"
        loaded=$((loaded + 1))
        if [ "{{reclaim}}" = "true" ]; then
            docker image rm "$ref" > /dev/null
            docker builder prune -f --keep-storage 4GB > /dev/null
        fi
    done < <(python3 scripts/image_members.py | PROFILE="{{profile}}" python3 -c "
    import json, os, sys
    mono = os.environ['PROFILE'] == 'mono'
    for m in json.load(sys.stdin):
        # in the mono profile the Python members are all inside the one image; the
        # members shipping their own Dockerfile still need theirs
        if not (mono and m['kind'] == 'python'):
            print(m['package'])
    if mono:
        print('platform')
    ")
    if [ $((loaded + already)) -eq 0 ]; then
        echo "error: no ghga images in the docker store or on the node — run \`just demo-images\` (or \`just demo-images-mono\`) first" >&2
        exit 1
    fi
    echo "loaded $loaded image(s) into the kind node ($already already there)"

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
    # plain grep, not -q — see the SIGPIPE note in `images-present`
    sudo iptables-nft -S FORWARD 2>/dev/null | grep '^-P FORWARD DROP' > /dev/null || { echo "FORWARD policy not DROP; skipping"; exit 0; }
    for subnet in 172.17.0.0/16 172.18.0.0/16; do
        for dir in -s -d; do
            sudo iptables-nft -C DOCKER-USER $dir "$subnet" -j ACCEPT 2>/dev/null \
              || sudo iptables-nft -I DOCKER-USER $dir "$subnet" -j ACCEPT
        done
    done
    echo "nested-bridge egress exemptions in place"

# Everything that loads images into the node or installs into it depends on this:
# `kind load` fails with "no nodes found for cluster" when the cluster is missing —
# easy to miss locally, where a cluster is nearly always already up, and fatal in CI,
# where it never is.
# Create the kind cluster if it isn't there yet (idempotent).
cluster:
    #!/usr/bin/env bash
    set -euo pipefail
    just net-fix
    # plain grep, not -q — see the SIGPIPE note in `images-present`
    kind get clusters 2>/dev/null | grep -x ghga > /dev/null || kind create cluster --config deploy/kind-config.yaml --wait 120s

# Build the images first — `just demo-images` (one per member, as released) or
# `just demo-images-mono` (a single Python image; far faster, demo/CI only). Loading them
# into the node is handled here via `demo-load`, so re-running after a `just down` costs
# a reload, not a rebuild.
# `just up mono` installs against the mono image instead of the per-member ones.
# Bring up (or update) the whole demo on kind and wait until it actually serves.
up profile="": (demo-load profile)
    #!/usr/bin/env bash
    set -euo pipefail
    extra=()
    if [ "{{profile}}" = "mono" ]; then
        [ -f deploy/charts/ghga-demo/values-mono.yaml ] \
          || { echo "error: values-mono.yaml is missing — run \`just charts\`" >&2; exit 1; }
        extra=(-f deploy/charts/ghga-demo/values-mono.yaml)
    elif [ -n "{{profile}}" ]; then
        echo "error: unknown profile '{{profile}}' (expected 'mono', or nothing)" >&2
        exit 1
    fi
    just demo-template
    echo "installing — this waits for every workload to become ready, a few minutes"
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      ${extra[@]+"${extra[@]}"} \
      --kube-context kind-ghga --wait --timeout 15m
    just wait-ready
    echo "gateway: http://localhost/  (portal at /, issuer at /ghga)"

# `helm --wait` covers the release's own workloads, but the gateway's pod is created by
# the Envoy operator from the Gateway resource — outside the release — so it needs its
# own condition. Without both gates a fresh cluster answers the first request before
# anything is listening: the services fail fast when Kafka is not yet up
# (KafkaConnectionError), and though Kubernetes restarts them, a suite that starts
# immediately runs against the crash-loop window.
# Block until the gateway is programmed, i.e. the platform actually serves.
wait-ready:
    kubectl --context kind-ghga wait --for=condition=Programmed gateway/ghga --timeout=5m

# Delete the kind cluster (the images on its node go with it; the docker store keeps them).
down:
    #!/usr/bin/env bash
    set -euo pipefail
    kind delete cluster --name ghga
    # the node's containerd went with it; say so, because the docker store still holds
    # the images and the next `just up` reloads them without rebuilding
    echo "cluster deleted — the node's images went with it; \`just up\` reloads them (no rebuild)"

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

# `just testbed-up mono` adds the mono-image overlay, as `just up mono` does.
# Deploy/refresh the demo with the testbed profile (sms, test OP, artifact model).
testbed-up profile="": (demo-load profile)
    #!/usr/bin/env bash
    set -euo pipefail
    extra=()
    if [ "{{profile}}" = "mono" ]; then
        [ -f deploy/charts/ghga-demo/values-mono.yaml ] \
          || { echo "error: values-mono.yaml is missing — run \`just charts\`" >&2; exit 1; }
        extra=(-f deploy/charts/ghga-demo/values-mono.yaml)
    elif [ -n "{{profile}}" ]; then
        echo "error: unknown profile '{{profile}}' (expected 'mono', or nothing)" >&2
        exit 1
    fi
    [ -f deploy/charts/ghga-demo/values-artifacts.yaml ] || just testbed-artifacts
    just demo-template
    docker manifest inspect ghga/test-oidc-provider:2.2.0 > /dev/null 2>&1 || true
    helm upgrade --install ghga deploy/charts/ghga-demo \
      -f deploy/charts/ghga-demo/values-local.yaml \
      -f deploy/charts/ghga-demo/values-artifacts.yaml \
      -f deploy/charts/ghga-demo/values-testbed.yaml \
      ${extra[@]+"${extra[@]}"} \
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
# reaches directly (mailhog, lox24 — MinIO is published by kind), runs pytest.
# Run the testbed suite (optionally scoped, e.g. `just testbed steps/test_001_health_check.py`).
testbed *args:
    #!/usr/bin/env bash
    set -euo pipefail
    # The suite shells out to ghga-datasteward-kit and ghga-connector and expects them
    # on PATH. Both are workspace members (tools/), so the gate has to exercise our
    # build of them — testbed/requirements.txt also pins released versions from PyPI
    # into .venv-testbed, and those would silently be tested instead. Locally this was
    # only ever right by accident: the devcontainer happens to put .venv/bin on PATH.
    export PATH="$PWD/.venv/bin:$PATH"
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
    # MinIO needs no forward: kind publishes its S3 node port on the host's 9000
    # (deploy/kind-config.yaml), which is the authority the pre-signed URLs carry —
    # forwarding here would collide with that published port and fail to bind.
    just testbed-hosts
    trap "kill $PF1 $PF2 2>/dev/null || true" EXIT
    sleep 2
    cd testbed && ../.venv-testbed/bin/pytest -v {{args}}
