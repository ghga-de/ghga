# Shared image for any deployable workspace member, built from the REPO ROOT:
#
#   docker build -f docker/Dockerfile \
#       --build-arg PACKAGE=auth-service \
#       --build-arg EXECUTABLE=auth-service .
#
# PACKAGE     = the workspace member's distribution name (`uv sync --package <PACKAGE>`)
# EXECUTABLE  = the member's console script (its [tool.ghga].executable), used as ENTRYPOINT
#
# Follows uv's canonical multi-stage workspace pattern: resolve from the single uv.lock,
# install only the target package + its (source-coupled) workspace deps, no dev deps.
#
# NOTE (scaffold): this is the initial containerisation approach. It can only be exercised once
# the workspace members + uv.lock exist (post-import). Pin the uv image digest before relying on
# it in CI. See docs/adr/0002 and docs/adr/0014.

ARG PYTHON_VERSION=3.13

# ---- builder: create the venv with the target package -----------------------------------
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder
ARG PACKAGE
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

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package "${PACKAGE}"

# ---- runner: minimal runtime image ------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runner
ARG EXECUTABLE
RUN useradd --create-home --uid 1000 appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    GHGA_EXECUTABLE="${EXECUTABLE}"
USER appuser
# Exec the member's console script (resolved on PATH inside the venv).
ENTRYPOINT ["sh", "-c", "exec \"${GHGA_EXECUTABLE}\" \"$@\"", "--"]
