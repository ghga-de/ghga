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
#
# Based on GHGA's Docker Hardened Images (mirrors the template's Dockerfile.dhi):
# build ON the DHI dev variant so the runtime libc (musl/alpine) matches, run on the plain
# hardened base (non-root, no shell — hence the /app/entrypoint symlink instead of `sh -c`).
# NOTE: dhi.io requires authentication (Docker Hub credentials with DHI entitlement) —
# `docker login dhi.io` locally; DOCKERHUB_USERNAME/DOCKERHUB_TOKEN org secrets in CI.

ARG PYTHON_VERSION=3.13
ARG BASE=dhi.io/python:${PYTHON_VERSION}-alpine3.23

# ---- builder: resolve the workspace venv on the DHI dev variant -------------------------
# hadolint ignore=DL3006
FROM ${BASE}-sfw-dev AS builder
ARG PACKAGE
ARG EXECUTABLE
ARG PLATFORM_VERSION=0.0.0+dev
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

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package "${PACKAGE}"

# Stamp AFTER dependency resolution: uv.lock and member pyprojects stay untouched.
RUN /app/.venv/bin/python /stamp_platform_version.py \
        --version "${PLATFORM_VERSION}" --package "${PACKAGE}"

# The hardened runtime has no shell, and exec-form ENTRYPOINT cannot expand variables —
# expose the member's console script behind a fixed path instead.
RUN ln -s "/app/.venv/bin/${EXECUTABLE}" /app/entrypoint && test -e /app/entrypoint

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
