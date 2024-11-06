# BASE: a base image with updated packages
FROM node:lts-alpine AS base
RUN apk upgrade --no-cache --available

# BUILDER: a container to build the service dist directory
FROM base AS builder
WORKDIR /service
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
# install static web server
RUN apk add curl sudo which
RUN curl --proto '=https' --tlsv1.2 -sSfL https://get.static-web-server.net | sed "s/cp -ax/cp -a/g" | sh

# RUNNER: a container to run the service
FROM base AS runner
RUN adduser -D appuser
WORKDIR /home/appuser
USER appuser
# install dist directory and run script
COPY --from=builder /service/dist/data-portal/browser ./dist
# install static web server
COPY --from=builder /usr/local/bin/static-web-server /usr/local/bin
# make the index file writeable
USER root
RUN chown appuser ./dist/index.html
USER appuser
# install run script
COPY ./run.js .
# install dependencies for run script
RUN npm install js-yaml
# install default configuration file
COPY ./data-portal.default.yaml .

ENTRYPOINT ["node"]
CMD ["/home/appuser/run.js"]
