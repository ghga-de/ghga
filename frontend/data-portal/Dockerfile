# BASE: a base image with updated packages
FROM node:lts-alpine AS base
RUN apk upgrade --no-cache --available

# BUILDER: a container to build the service dist directory
FROM base AS builder
# install pnpm
RUN npm install --global corepack@0.32.0
RUN corepack prepare pnpm@10.11.1 --activate
# install static web server
RUN apk add curl jq sudo which
RUN curl --proto '=https' --tlsv1.2 -sSfL https://get.static-web-server.net | sed "s/cp -ax/cp -a/g" | sh
# build the service
WORKDIR /service
COPY package.json pnpm-lock.yaml ./
RUN pnpm install
COPY . .
RUN npm run build
# create base package.json with just name and version
RUN jq '{name, version, type}' package.json > ./package.json.run

# RUNNER: a container to run the service
FROM base AS runner
RUN adduser -D appuser
WORKDIR /home/appuser
USER appuser
# install dist directory and run script
COPY --from=builder /service/dist/data-portal/browser ./dist
# install static web server
COPY --from=builder /usr/local/bin/static-web-server /usr/local/bin
# copy the base package.json with name and version
COPY --from=builder /service/package.json.run ./package.json
# make the config file writeable to the appuser
USER root
RUN touch ./dist/config.js && chown appuser ./dist/config.js ./package.json
USER appuser
# install run script
COPY run.js ./run.mjs
# install dependencies for run script
RUN npm install js-yaml
# install configuration files
COPY data-portal.default.yaml .
COPY sws.toml .

ENTRYPOINT ["node"]
CMD ["/home/appuser/run.mjs"]
