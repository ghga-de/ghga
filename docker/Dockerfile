# Shared hardened image for any deployable workspace member, built from the REPO ROOT:
#
#   docker build -f docker/Dockerfile \
#       --build-arg PACKAGE=auth-service \
#       --build-arg EXECUTABLE=auth-service \
#       --build-arg PLATFORM_VERSION=17.0.0 --build-arg GIT_SHA=<sha> .
#
# PACKAGE          = the workspace member's distribution name
# EXECUTABLE       = the member's console script, exposed as the ENTRYPOINT
# PLATFORM_VERSION = stamped onto the environment (ADR-0004); default marks dev builds
# VARIANT          = single (default, one member per image) | mono (all Python members
#                    in one venv; demo/CI only, PACKAGE is ignored) — `just demo-images-mono`
#
# Based on Docker Hardened Images (mirrors the template's Dockerfile.dhi):
# build ON the DHI dev variant so the runtime libc (musl/alpine) matches, run on the plain
# hardened base (non-root, no shell — hence the /app/entrypoint symlink instead of `sh -c`).
# NOTE: dhi.io requires authentication (Docker Hub credentials with DHI entitlement) —
# `docker login dhi.io` locally; DOCKERHUB_USERNAME/DOCKERHUB_TOKEN org secrets in CI.

# renovate: track=python-base
ARG PYTHON_BASE=3.14.7-alpine3.24
ARG BASE=dhi.io/python:${PYTHON_BASE}
# single = one member per image (the release artifact); mono = every Python member in
# one venv, for the demo and the integration gate only (see the mono stage below).
ARG VARIANT=single

# ---- workspace: the toolchain + sources both variants resolve against -------------------
# hadolint ignore=DL3006
FROM ${BASE}-sfw-dev AS workspace
# Toolchain for source-building native wheels where musllinux wheels are unavailable.
# hadolint ignore=DL3018
RUN apk upgrade --no-cache --available && \
    apk add --no-cache build-base gcc g++ libffi-dev zlib-dev python3-dev
# uv ships a static (musl-compatible) binary.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Copy the workspace (lock + all members) so source-coupled deps resolve.
# .dockerignore keeps this lean (no .venv, caches, .legacy_repos, …).
COPY pyproject.toml uv.lock ./
COPY libs ./libs
COPY services ./services
COPY tools ./tools
COPY scripts/stamp_platform_version.py /stamp_platform_version.py

# ---- venv-single: one member, stamped and released --------------------------------------
FROM workspace AS venv-single
ARG PACKAGE
# Convention: an image member's console script is named like its distribution,
# so the entrypoint defaults to the package name (see ADR-0014).
ARG EXECUTABLE=${PACKAGE}
ARG PLATFORM_VERSION=0.0.0+dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package "${PACKAGE}"

# Stamp AFTER dependency resolution: uv.lock and member pyprojects stay untouched.
RUN /app/.venv/bin/python /stamp_platform_version.py \
        --version "${PLATFORM_VERSION}" --package "${PACKAGE}"

# The hardened runtime has no shell, and exec-form ENTRYPOINT cannot expand variables —
# expose the member's console script behind a fixed path instead.
RUN ln -s "/app/.venv/bin/${EXECUTABLE}" /app/entrypoint && test -e /app/entrypoint

# ---- venv-mono: every Python member in one venv (demo + integration gate only) -----------
# One build instead of ~22 cuts the demo/CI image step from ~15-20 min to ~1 min, and
# `kind load` from ~2.4 GB to ~0.6 GB. Safe because the workspace already guarantees the
# members are co-installable — a single uv.lock, resolved exactly as `just sync` does —
# and their console scripts do not collide (ADR-0014 names each after its distribution).
# NOT a release artifact: production keeps one image per member.
FROM workspace AS venv-mono
ARG PLATFORM_VERSION=0.0.0+dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --all-packages

# No stamping: the script rewrites the version of exactly ONE released member, which is
# meaningless for an image carrying all of them. GHGA_PLATFORM_VERSION is still set below,
# so the runtime reports the platform version; only the dist-info rewrite is skipped.
# The entrypoint is a placeholder — the charts always render `command: [<executable>]`
# (commandStyle=exec), so ENTRYPOINT is never what starts a service here.
RUN ln -s /app/.venv/bin/python /app/entrypoint && test -e /app/entrypoint

# ---- builder: whichever variant was selected --------------------------------------------
# hadolint ignore=DL3006
FROM venv-${VARIANT} AS builder

# ---- runner: plain hardened base (non-root, no shell) -----------------------------------
# hadolint ignore=DL3006
FROM ${BASE} AS runner
ARG PLATFORM_VERSION=0.0.0+dev
ARG GIT_SHA=unknown
ARG UID=1000
COPY --from=builder --chown=${UID}:${UID} /app/.venv /app/.venv
COPY --from=builder /app/entrypoint /app/entrypoint
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    GHGA_PLATFORM_VERSION="${PLATFORM_VERSION}"
LABEL org.opencontainers.image.version="${PLATFORM_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}"
USER ${UID}
ENTRYPOINT ["/app/entrypoint"]
