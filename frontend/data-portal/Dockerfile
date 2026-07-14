# Multi-stage Dockerfile for building a production image for the data portal

# BASE: a base image with updated packages
FROM node:24-alpine AS base
RUN apk upgrade --no-cache --available

# BUILDER: a container to build the service dist directory
FROM base AS builder
SHELL ["/bin/ash", "-o", "pipefail", "-c"]
# install pnpm via corepack
RUN corepack enable && corepack prepare pnpm@11.9.0 --activate
# install static web server (curl/jq/sudo/which are build-only, intentionally unpinned)
# hadolint ignore=DL3018
RUN apk add --no-cache curl jq sudo which \
 && curl --proto '=https' --tlsv1.2 -sSfL https://get.static-web-server.net | sed "s/cp -ax/cp -a/g" | sh
# build the service
WORKDIR /service
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN HUSKY=0 CI=true pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
# prepare runtime artifacts: base package.json with just name and version,
# js-yaml (symlinks resolved) for runtime, and a group-writable config.js
# (writable at runtime under any UID)
RUN jq '{name, version, type}' package.json > ./package.json.run \
 && mkdir -p /tmp/runtime-deps \
 && cp -rL node_modules/js-yaml /tmp/runtime-deps/ \
 && touch ./dist/data-portal/browser/config.js \
 && chmod g+w ./dist/data-portal/browser ./dist/data-portal/browser/config.js

# RUNNER: a container to run the service
FROM base AS runner
ARG UID=1000
WORKDIR /app
# remove npm and corepack to trim the image and avoid outdated dependencies
RUN rm -rf /usr/local/lib/node_modules /root/.cache /root/.npm
# install dist directory and run script
COPY --chown=${UID}:0 --from=builder /service/dist/data-portal/browser ./dist
# install static web server
COPY --from=builder /usr/local/bin/static-web-server /usr/local/bin/static-web-server
# copy the base package.json with name and version
COPY --chown=${UID}:0 --from=builder /service/package.json.run ./package.json
# install run script
COPY --chown=${UID}:0 run.js ./run.mjs
# copy runtime dependencies (js-yaml with resolved symlinks)
COPY --chown=${UID}:0 --from=builder /tmp/runtime-deps/js-yaml ./node_modules/js-yaml
# install configuration files
COPY --chown=${UID}:0 data-portal.default.yaml .
COPY --chown=${UID}:0 sws.toml .
USER ${UID}

ENTRYPOINT ["node"]
CMD ["/app/run.mjs"]
