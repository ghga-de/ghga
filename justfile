# GHGA monorepo task runner — a thin facade over uv / pnpm / helm + the affected script.
# See docs/adrs/adr-0034-task-runner.md. Run `just` to list recipes.
set shell := ["bash", "-uc"]
# Recipes hand their arguments on as "$@", so an argument with spaces stays one argument.
set positional-arguments

# Registry root the `image`/`image-mono`/`demo-load` recipes tag/load under. Defaults to
# the real platform registry (matches the charts' generated image.registry/repository) so
# the local kind demo loop needs no override. dev-images.yaml/security-scan.yaml set
# IMAGE_REGISTRY to their own GHCR scratch space, which is deliberately independent of the
# release target (see those workflows' headers).
image_registry := env_var_or_default("IMAGE_REGISTRY", "docker.io/ghga")

default:
    @just --list

# --- Environment guard ------------------------------------------------------------------
# `.venv` lives in the workspace, and the dev container bind-mounts the workspace from the
# host -- so whichever side ran uv last owns it, and the loser gets an interpreter symlink
# pointing into a home directory that does not exist on its side.
#
# Neither half of that reports itself. The generated .git/hooks/pre-commit hardcodes
# .venv/bin/python3, so when the symlink dangles the hook falls through to a PATH lookup
# git has not got and says `pre-commit not found. Did you forget to activate your
# virtualenv?` -- which is not what went wrong, and sends you looking at activation.
#
# Order matters: the host check comes first, because `just sync` is the right repair only
# on the side you actually work on. Telling a host shell to sync would just flip the
# ownership back and break the container instead.
#
# Exempt: CI ($CI), which runs these recipes on a bare runner by design, and anyone who
# sets GHGA_ALLOW_HOST=1 -- the deliberate bare-host escape hatch (cf. `just docs`).
[private]
_guard-host:
    #!/usr/bin/env bash
    set -uo pipefail
    if [ -z "${CI:-}" ] && [ -z "${GHGA_ALLOW_HOST:-}" ] && [ ! -f /.dockerenv ]; then
        echo "error: repo tooling is meant to run inside the dev container (.devcontainer/)." >&2
        echo "Running it on the host leaves a .venv only the host can use, and the container" >&2
        echo "(or its git hooks) then fails in ways that do not name this as the cause." >&2
        echo "Reopen the folder in the container, or set GHGA_ALLOW_HOST=1 to override." >&2
        exit 1
    fi

# The dangling-venv half is separate because `just sync` is the repair it prescribes, and a
# guard that blocked the repair would be a dead end. `uv sync` rebuilds a venv whose
# interpreter has gone missing, so sync takes the host check alone.
[private]
_guard: _guard-host
    #!/usr/bin/env bash
    set -uo pipefail
    if [ -e .venv ] && [ ! -x .venv/bin/python3 ]; then
        echo "error: .venv/bin/python3 does not resolve to an interpreter that exists here." >&2
        echo "That is what a uv run from the other side of the bind mount leaves behind." >&2
        echo "Rebuild the environment where you are working now:" >&2
        echo "  just sync" >&2
        exit 1
    fi

# --- Python workspace -------------------------------------------------------------------
# --all-extras is needed so member test suites (which use optional deps) can run.
# CI passes --locked, which also asserts uv.lock is in sync with the pyprojects.
# Resolve + install all workspace members, their extras, and the shared dev toolchain.
sync *flags: _guard-host
    uv sync --all-packages --all-extras "$@"

# Update the single workspace lockfile.
lock: _guard-host
    uv lock

# `uv run` syncs the environment but does not prune it, so a distribution that is no longer
# in uv.lock stays installed and can shadow a workspace member's source -- the suite then
# tests code that is not in the repo. CI cannot drift that way: it builds the environment
# from the lock (`uv sync --locked`). This is that same assertion, read-only and in ~0.1s,
# so `just test` cannot report on an environment CI would not recognise.
#
# Two assertions, because CI's one `uv sync --locked` covers two failures that need
# different fixes here: `--check` reports a stale ENVIRONMENT but passes a stale LOCK
# straight through, so the lock is checked on its own first.
# In CI it does nothing: every job builds its environment with `just sync --locked`,
# which already asserts both.
# Assert uv.lock and the environment are current, as CI's `uv sync --locked` does.
sync-check: _guard
    #!/usr/bin/env bash
    set -uo pipefail
    [ -n "${CI:-}" ] && exit 0
    if ! out=$(uv lock --check 2>&1); then
        echo "$out" >&2
        printf '\nerror: uv.lock is out of date with the pyproject.toml files.\n' >&2
        printf 'Refresh the lock and the environment, then re-run:\n' >&2
        printf '  just lock && just sync\n' >&2
        exit 1
    fi
    out=$(uv sync --locked --all-packages --all-extras --check 2>&1) && exit 0
    echo "$out" >&2
    printf '\nerror: the environment does not match uv.lock, so a test run here would not\n' >&2
    printf 'be the run CI does. Update the environment, then re-run:\n' >&2
    printf '  just sync\n' >&2
    exit 1

# Lint + format check across the workspace.
lint: _guard
    uv run ruff check .
    uv run ruff format --check .
    uv run rumdl check .

# Auto-fix lint + format.
fmt: _guard
    uv run ruff format .
    uv run ruff check --fix .
    uv run rumdl fmt .

# A single `mypy .` collides on duplicate module names across members, and the result
# depends on the path set it is given -- so the unit, not the file, is what gets checked.
# scripts/typecheck.py is the same runner the pre-commit hook and CI use.
# Type-check members (src + tests) and the non-member Python; everything by default.
typecheck *targets: _guard
    [ $# -gt 0 ] || set -- --all; uv run python scripts/typecheck.py "$@"

# --- Git hooks (pre-commit; ADR-0036) ---------------------------------------------------
# Once per clone -- the dev container does it for you.
# Install the git hooks into .git/hooks.
hooks: _guard
    uv run pre-commit install

# The branch guard is skipped: it exists to stop commits landing on the long-lived branches
# (`main` and `dev`, ADR-0038), not to fail a full-tree sweep. CI's `hygiene` job adds the
# hooks other jobs already run to $SKIP, and passes pre-commit flags through.
# Run every hook over the whole tree, as CI's `hygiene` job does.
hooks-all *flags: _guard
    SKIP="no-commit-to-branch${SKIP:+,$SKIP}" uv run pre-commit run --all-files "$@"

# Only the generic pre-commit-hooks repo carries a `rev`; the ruff / mypy / prettier /
# eslint hooks take their version from uv.lock and pnpm-lock.yaml, so those are bumped by
# updating the lockfiles instead.
# Bump the pinned hook revisions.
hooks-update: _guard
    uv run pre-commit autoupdate

# The same check the docs-set pre-commit hook runs (ADR-0041).
# Check the ADRs, epics, instruction files and skills and every reference to them, and
# regenerate their indexes; `--budget` prints each session's context budget.
docs-check *args: _guard
    uv run python scripts/docs_check.py "$@"

# The same check the kafka-map pre-commit hook runs.
# Write docs/architecture/kafka-cascades.yaml into the map page; `--check` only reports.
kafka-map *args: _guard
    uv run python scripts/kafka_map.py "$@"

# vale is a Go binary outside the uv and pnpm toolchains, so the dev container lacks it;
# .vale.ini pins the rule package, which `vale sync` downloads into the gitignored .vale/.
# Warns only. Without paths it reads the Markdown and Python files changed against the
# base, since the older docs, legacy ADRs among them, would bury a change's own findings.
# Flag AI tells in prose (docs/style.md), e.g. `just prose` or `just prose README.md`.
prose *paths:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v vale >/dev/null; then
        echo "error: vale is not installed: https://vale.sh/docs/install (tested with 3.24)" >&2
        exit 1
    fi
    [ -d .vale/styles/ai-tells ] || vale sync
    files=("$@")
    if [ ${#files[@]} -eq 0 ]; then
        mapfile -t files < <(
            { git diff --name-only --diff-filter=d "$(git merge-base origin/dev HEAD)"
              git ls-files --others --exclude-standard; } \
            | grep -E '\.(md|py)$' | grep -Ev '^(docs/epics|deploy/charts|\.agents/skills/angular-developer)/' | sort -u)
    fi
    [ ${#files[@]} -eq 0 ] && { echo "no changed Markdown or Python files"; exit 0; }
    vale --no-exit "${files[@]}"

# A root skill's eval suite, .agents/skills/<name>/evals.yaml, each case run with and without
# the skill in a pinned clone that scripts/skill-eval-scaffold.sh prepares
# (docs/agent-instructions.md). A pass is due when the skill's SKILL.md changes, and for
# every suite when SKILL_EVAL_MODEL in scripts/just/skill-eval.sh moves to a new default
# model. The report stays local; extra arguments go to `claude plugin eval`, e.g.
# `--case new-adr --runs 1`.
# Run a root skill's eval suite and print its scores, e.g. `just skill-eval adr`.
skill-eval name *args: _guard
    @scripts/just/skill-eval.sh "$@"

# The same check the service-docs pre-commit hook runs; `--check` writes nothing.
# Regenerate each service's config schema, example config, README parameters and OpenAPI spec.
service-docs *args: _guard
    uv run python scripts/service_docs.py "$@"

# One pytest per member, from the member directory, exactly as CI's check-python matrix
# runs it; scripts/tests and deploy/tests belong to no member and run from the root, as
# CI's hygiene job runs them. scripts/just/test.sh says why.
#
#   just test                                    # every member, then the non-member suites
#   just test libs                               # every member in one tier
#   just test services/auth-service              # one member
#   just test services/auth-service/tests/unit   # part of one member's suite
#   just test scripts/tests deploy/tests         # several targets
#
# Run tests; optionally scope to tiers, members or paths, e.g. `just test services/auth-service`.
test *targets: _guard sync-check
    @scripts/just/test.sh "$@"

# Print the workspace targets affected by the working tree vs a base ref.
# Defaults to the integration branch, which is what feature branches are cut from (ADR-0038).
# On a hotfix branch, which is cut from the release branch instead, pass `origin/main`.
affected base="origin/dev":
    uv run python scripts/affected_targets.py --base "$1"

# --- Worktrees (parallel work) ----------------------------------------------------------
# Worktrees go under .claude/worktrees/ of the main checkout, even when the recipe runs in
# a worktree: that is where Claude Code's `--worktree` puts its own, and /.claude/* in
# .gitignore hides them. Git records a worktree's path absolutely, and the host and the
# container see different paths, so only the container may create them.
# Each worktree gets its own .venv, which the uv cache makes a copy rather than a download,
# and its own node_modules, which the Prettier and ESLint hooks need for a portal commit.
#
#   just wt chore/GSI-1234-bump-hexkit       # .claude/worktrees/GSI-1234-bump-hexkit
#   just wt hotfix/ucs-retry origin/main     # from another base
#
# Create a worktree on a new branch and install its dependencies, e.g. `just wt feat/add-x`.
wt branch base="origin/dev": _guard-host
    #!/usr/bin/env bash
    set -euo pipefail
    branch=$1 base=$2
    main=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
    dir="$main/.claude/worktrees/$(basename "$branch")"
    git fetch origin
    # A branch tracking origin/dev would let a plain push or an editor sync land on dev.
    git worktree add --no-track "$dir" -b "$branch" "$base"
    cd "$dir" && just sync && just fe-install

# Leaves the branch: after a squash merge `git branch -d` refuses it, and deleting it with
# `-D` is the dev's call, not a recipe's.
# Remove a worktree created by `just wt`, given its directory name.
wt-rm name: _guard-host
    #!/usr/bin/env bash
    set -euo pipefail
    main=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
    git worktree remove "$main/.claude/worktrees/$1"

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
    @scripts/just/published-combo.sh "$@"

# Run CI's drift gate, e.g. before a merge: a lane member whose shipped content changed
# must declare a version PyPI does not already serve. Pass `origin/main` on a hotfix branch.
# Assert every changed PyPI-lane member declares an unpublished version.
pypi-drift base="origin/dev":
    @scripts/just/pypi-drift.sh "$@"

# --- Docs lane (ADR-0039) ---------------------------------------------------------------
# Build the published documentation. A member is documented iff it carries a
# `great-docs.yml`; scripts/docs_members.py is the same discovery docs-publish.yaml reads,
# so a local build cannot drift from the deployed one.
#
#   just docs-install      # once per clone
#   just docs              # every documented member
#   just docs libs/hexkit  # just one
#
# Output lands in <member>/great-docs/_site (gitignored). The workflow uploads exactly that
# directory, one per member, into the single Pages site under the member's own subpath.

# The toolchain gets its own venv rather than joining the workspace one: great-docs pulls a
# ~450M tree (Jupyter, IPython, Quarto plumbing) that no test needs, and installing the
# `docs` group into .venv makes `just sync-check` -- and therefore `just test` -- report the
# environment as not matching uv.lock. It is still resolved in the single root uv.lock
# (`[dependency-groups] docs`), so the pin stays locked and Renovate keeps tracking it;
# UV_PROJECT_ENVIRONMENT only redirects where uv installs it. --no-install-workspace keeps
# the members out: great-docs reads them from source (griffe prepends the package's src/ to
# its search path), so nothing here needs them importable.
# One-time: virtualenv for the docs toolchain (from uv.lock; not the workspace venv).
docs-install:
    UV_PROJECT_ENVIRONMENT=.venv-docs uv sync --locked --no-default-groups --group docs --no-install-workspace

# Build the documentation site(s) into <member>/great-docs/_site.
docs member="":
    @scripts/just/docs.sh "$@"

# --- Front end (data-portal, pnpm) ------------------------------------------------------
# The front-end member the fe-* recipes work in; CI's check-frontend matrix sets it per
# member, e.g. `just fe_dir=frontend/other fe-check`.
fe_dir := "frontend/data-portal"

fe-install:
    cd {{fe_dir}} && pnpm install --frozen-lockfile

fe-build:
    cd {{fe_dir}} && pnpm build

fe-test:
    cd {{fe_dir}} && pnpm test

fe-lint:
    cd {{fe_dir}} && pnpm lint

# Prettier owns formatting for the front end (ESLint does not check it).
fe-format:
    cd {{fe_dir}} && pnpm format

fe-format-check:
    cd {{fe_dir}} && pnpm format:check

# Run every front-end check CI's check-frontend job runs (Playwright E2E is the test bed's).
fe-check: fe-install fe-format-check fe-lint fe-test fe-build

# The four dev-server modes are the two independent switches --with-backend (real API
# instead of the MSW mocks) and --with-oidc (real login instead of the faked session);
# frontend/data-portal/README.md documents what each one needs. Per-developer settings
# and secrets go in frontend/data-portal/local.env (see local.env.example).

# Generates public/config.js (mock_api=true) and serves on http://localhost:8080.
# (Bare `pnpm start` won't work on its own: it skips the config.js generation this
# launcher does — that's why the server needs run.js, not plain `ng serve`.)
# Run the data-portal dev server with MOCKED api + oidc (MSW) — no backend needed.
fe-dev:
    cd {{fe_dir}} && node run.js --dev

# For what only a deployment shows: the optimized build and the sws.toml headers, on
# http://localhost:8080. The production build starts no MSW mocks, so API calls fail.
# Build the data-portal for production and serve it with static-web-server, as deployed.
fe-prod: fe-build
    cd {{fe_dir}} && node run.js

# Run the data-portal against a real backend (default: staging) instead of mocks.
fe-dev-backend:
    cd {{fe_dir}} && node run.js --dev --with-backend

# Run the data-portal against the real OIDC provider (mock API), on https://<backend host>/.
fe-dev-oidc: fe-dev-ssl
    cd {{fe_dir}} && node run.js --dev --with-oidc

# Run the data-portal against both the real backend and the real OIDC provider.
fe-dev-backend-oidc: fe-dev-ssl
    cd {{fe_dir}} && node run.js --dev --with-backend --with-oidc

# Create the dev server's self-signed certificate (idempotent, reissued per hostname).
fe-cert:
    {{fe_dir}}/create-cert.sh

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
    # plain grep, not -q: -q exits at the first match, and the writer's SIGPIPE then fails
    # the pipeline under pipefail
    if getcap "$node" | grep cap_net_bind_service > /dev/null; then exit 0; fi
    sudo setcap cap_net_bind_service=+ep "$node"
    echo "granted cap_net_bind_service to $node"

# --- Migration (see docs/migration/runbook.md) ------------------------------------------
# Dry-run the history-preserving import from the local .legacy_repos snapshot.
import-from-snapshot:
    LEGACY_DIR="$PWD/.legacy_repos" scripts/migration/import-all.sh

# One-way incremental sync from mainline (optionally limit to dests).
sync-mainline *args:
    scripts/migration/sync-from-mainline.sh "$@"

# --- Helm charts --------------------------------------------------------------------------
# Regenerate the per-service charts from workspace metadata + member chart-values.yaml.
# Passing no version reuses the committed one: release-charts.yaml publishes whatever is
# committed, so regenerating must not change it (ADR-0027).
charts version="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "$1" ]; then
        uv run python deploy/src/create_charts.py --version "$1"
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
# Python members use the shared Dockerfile (entrypoint = package name, ADR-0033);
# members shipping their own Dockerfile (the frontend) build with it in-place --
# a package.json rather than a pyproject.toml is what tells the two apart.
# Tags use the release registry scheme with tag 'local' so the charts' generated
# image references resolve with only a tag override (values-local.yaml).
# `tag` and trailing docker-build flags are overridable so CI reuses these recipes
# instead of duplicating the build commands — e.g. security-scan.yaml runs
# `just image-mono updated --pull`. dev-images.yaml deliberately does NOT: publishing
# attestations needs a docker-container buildx builder, which these `docker build`
# recipes cannot provide (see ADR-0037).
# Both stamp the version derived from the checkout (ADR-0046); a `--build-arg` in `flags`
# comes later on the command line and overrides it.
image target tag='local' *flags: check-members
    #!/usr/bin/env bash
    set -euo pipefail
    target=$1 tag=$2
    shift 2  # the rest are docker build flags
    version="$(python3 scripts/platform_version.py)"
    if [ -f "$target/package.json" ]; then
        name=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['name'])" "$target/package.json")
        docker build -f "$target/Dockerfile" --build-arg PLATFORM_VERSION="$version" "$@" -t "{{image_registry}}/$name:$tag" "$target"
    else
        name=$(python3 -c "import tomllib, sys; print(tomllib.load(open(sys.argv[1], 'rb'))['project']['name'])" "$target/pyproject.toml")
        docker build -f docker/Dockerfile --build-arg PACKAGE="$name" --build-arg PLATFORM_VERSION="$version" \
            --build-arg GIT_SHA="$(git rev-parse --short=7 HEAD)" "$@" -t "{{image_registry}}/$name:$tag" .
    fi

# One build instead of ~22 — the demo/CI image step drops from ~15-20 min to ~1 min.
# The charts start services with `command: [<executable>]`, so one image serves them all;
# see the mono stage in docker/Dockerfile for why this is demo/CI only.
# Build the mono image: EVERY Python member in one venv (docker/Dockerfile VARIANT=mono).
image-mono tag='local' *flags: check-members
    docker build -f docker/Dockerfile --build-arg VARIANT=mono \
      --build-arg PLATFORM_VERSION="$(python3 scripts/platform_version.py)" \
      --build-arg GIT_SHA="$(git rev-parse --short=7 HEAD)" "${@:2}" \
      -t "{{image_registry}}/platform:$1" .

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
    # an assignment, not a for-list, so a failing listing fails the recipe
    paths=$(python3 scripts/image_members.py --field path)
    for path in $paths; do
        echo "== building $path =="
        just image "$path"
    done

# Members shipping their own Dockerfile (the frontend) cannot be folded into the shared
# venv, so they are still built one by one.
# Build the mono profile: the single Python image plus the non-Python members.
demo-images-mono: image-mono
    #!/usr/bin/env bash
    set -euo pipefail
    paths=$(python3 scripts/image_members.py --kind frontend --field path)
    for path in $paths; do
        echo "== building $path =="
        just image "$path"
    done

# Loads only what the profile deploys; `reclaim=true` (CI) drops each docker copy once it
# is on the node. Safe to re-run, which is why `up`/`testbed-up` depend on it.
# Copy the profile's built images from the docker store into the kind node.
demo-load profile="" reclaim="false": cluster
    @IMAGE_REGISTRY={{quote(image_registry)}} scripts/just/demo-load.sh "$@"

# Read from the node, not the docker store: CI's reclaim drops the docker copies, and the
# docker image ID differs from containerd's anyway.
# Print the node's ID for every `:local` image, as JSON keyed by image reference.
[private]
_local-image-ids:
    @docker exec ghga-control-plane crictl images -o json \
      | jq -c '[.images[] | .id as $id | .repoTags[] | select(endswith(":local")) | {key: ., value: $id}] | from_entries'

# Reclaim BuildKit cache and dangling layers. Run occasionally: local image builds grew
# the cache to ~17 GB within days, and a full disk breaks builds AND testcontainers.
docker-prune:
    docker builder prune -f --keep-storage 5GB
    docker image prune -f

# --- Local cluster (kind in the devcontainer's docker; ADR-0028) ---------------------
# On hosts whose outer dockerd enforces an nftables FORWARD drop policy (e.g. a Lima
# docker VM), the nested bridges lose egress after every VM restart — exempt them in
# the sanctioned DOCKER-USER chain. Idempotent; skipped where iptables-nft is absent.
net-fix:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v iptables-nft > /dev/null || { echo "no iptables-nft; skipping"; exit 0; }
    # plain grep, not -q: see `fe-dev-ssl`
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
    # plain grep, not -q: see `fe-dev-ssl`
    kind get clusters 2>/dev/null | grep -x ghga > /dev/null || kind create cluster --config deploy/kind-config.yaml --wait 120s
    # The check above finds the cluster through docker's labels, but every recipe below
    # reaches it through the kind-ghga context in ~/.kube/config — and the two do not have
    # the same lifetime here: a devcontainer rebuild keeps docker's storage (a named
    # volume) and wipes the home directory. The cluster then still exists, creation is
    # skipped, and the first `--kube-context kind-ghga` fails with "context does not
    # exist". Re-exporting unconditionally costs nothing and closes that gap.
    kind export kubeconfig --name ghga > /dev/null

# Build the images first — `just demo-images` (one per member, as released) or
# `just demo-images-mono` (a single Python image; far faster, demo/CI only). Loading them
# into the node is handled here via `demo-load`, so re-running after a `just down` costs
# a reload, not a rebuild.
# `just up mono` installs against the mono image instead of the per-member ones.
# Bring up (or update) the whole demo on kind and wait until it actually serves.
up profile="": (demo-load profile)
    @scripts/just/install-demo.sh "$@"
    @echo "gateway: http://localhost/  (portal at /, issuer at /ghga)"

# Wait until the demo on kind actually serves, not only until helm says it is installed.
wait-ready:
    @scripts/just/wait-ready.sh

# Delete the kind cluster (the images on its node go with it; the docker store keeps them).
down:
    #!/usr/bin/env bash
    set -euo pipefail
    kind delete cluster --name ghga
    # the node's containerd went with it; say so, because the docker store still holds
    # the images and the next `just up` reloads them without rebuilding
    echo "cluster deleted — the node's images went with it; \`just up\` reloads them (no rebuild)"

# --- Integration testbed (BDD suite in testbed/; ADR-0028) -------------------------------
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
    @[ -f deploy/charts/ghga-demo/values-artifacts.yaml ] || just testbed-artifacts
    @docker manifest inspect ghga/test-oidc-provider:2.2.0 > /dev/null 2>&1 || true
    @scripts/just/install-demo.sh "$1" \
      -f deploy/charts/ghga-demo/values-artifacts.yaml \
      -f deploy/charts/ghga-demo/values-testbed.yaml

# The suite imports ghga-datasteward-kit and runs it and ghga-connector as CLIs, so both
# have to be the workspace source, never a PyPI release: they are exported from uv.lock
# and installed editable, with the lock's versions of everything under them. The
# suite's own requirements are resolved in the same step, so a pin there that disagrees
# with uv.lock fails the install instead of quietly replacing the workspace's version;
# the suite re-checks the result before its first test (steps/conftest.py).
# The UI phase drives a real browser, so the matching chromium build comes with it
# (playwright pins the build to the library version; a system chromium won't do).
# One-time: virtualenv for the testbed suite (not a workspace member; tools from uv.lock).
testbed-install:
    #!/usr/bin/env bash
    set -euo pipefail
    # The workspace Python: the export below comes frozen from uv.lock, which resolves
    # for the lock's requires-python only.
    uv venv .venv-testbed --allow-existing
    # uv exports the workspace paths relative to the root; made absolute so the file
    # means the same whichever directory the installer resolves them against
    uv export --frozen --no-hashes --no-dev --no-header \
      --package ghga-datasteward-kit --package ghga-connector \
      | sed "s|^-e \./|-e $PWD/|" > .venv-testbed/workspace-tools.txt
    VIRTUAL_ENV=$PWD/.venv-testbed uv pip install \
      -r .venv-testbed/workspace-tools.txt -r testbed/requirements.txt
    .venv-testbed/bin/playwright install chromium

# With no argument, lists what the last traced run left behind.
# Open a Playwright trace from a traced test-bed run (`TB_TRACE=1 just testbed -m frontend`).
testbed-trace file="":
    @scripts/just/testbed-trace.sh "$@"

# Make the in-cluster MinIO name resolve locally: services hand the connector
# pre-signed S3 URLs built from s3_endpoint_url, and those signatures are bound to
# that exact host — so the name must resolve both in-cluster and here.
testbed-hosts:
    #!/usr/bin/env bash
    set -euo pipefail
    grep -q "ghga-minio" /etc/hosts || echo "127.0.0.1 ghga-minio" | sudo tee -a /etc/hosts > /dev/null
    echo "ghga-minio resolves locally"

# Drops every service database and lets the services re-seed and rebuild their
# projections from events.
# Reset the identity state to a coherent cold start.
testbed-reset:
    @scripts/just/testbed-reset.sh

# Harvests tokens/keys from the cluster secrets, port-forwards the services the suite
# reaches directly, runs pytest.
# Run the testbed suite (optionally scoped, e.g. `just testbed steps/test_001_health_check.py`).
testbed *args:
    @scripts/just/testbed.sh "$@"

# The name is matched loosely, so the `ghga-` prefix is optional and a substring is enough.
# `just logs` with no argument lists the deployments and their ready counts.
# Follow a service's logs, e.g. `just logs auth-adapter` (no argument lists them).
logs name="":
    #!/usr/bin/env bash
    set -euo pipefail
    K="kubectl --context kind-ghga"
    name=$1
    if [ -z "$name" ]; then
        $K get deploy -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas --no-headers \
          | awk '{sub(/^ghga-/, "", $1); printf "%-28s %s\n", $1, $2}'
        exit 0
    fi
    # `|| true`: a non-matching grep exits 1, and under `set -e` that kills the recipe
    # before the message below ever prints
    match=$($K get deploy -o name | grep -- "$name" | head -1 || true)
    [ -n "$match" ] || { echo "error: no deployment matching '$name' — \`just logs\` lists them" >&2; exit 1; }
    echo "== $match ==" >&2
    # --all-containers: several workloads run a sidecar, and the default picks only one
    $K logs -f --tail=100 --all-containers "$match"
