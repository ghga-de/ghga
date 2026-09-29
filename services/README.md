# `services/` — deployable services

Workspace members that are deployed as container images and wired into the Helm charts.

`em-transformation-service` will join once the workspace moves to the metldata 5.x schemapack line (see `scripts/migration/repos.tsv`).

- Each service keeps a minimal `pyproject.toml` (name, version, build, `[tool.uv.sources]`, `[tool.ghga]`), and a `src/<pkg>/` layout with tests.
- Most services run as a **rest** + **consumer** pair — modelled in the chart as N Deployments sharing config with distinct `service_instance_id`s.
- `state-management-service` is **test-bed-only** and values-gated — never in demo/prod ([ADR-0030](../docs/adrs/adr-0030-state-management-service-testbed-only.md)).

## Running a service

A service's image, Helm chart and executable all carry the name of its distribution ([ADR-0033](../docs/adrs/adr-0033-capability-markers-and-placement.md)).
Its README gives that name, the commands the executable takes and the prefix of its settings; below they stand as `<name>`, `<command>` and `<prefix>`.
The same holds for `metldata`, which lives in `libs/` but ships as an image.

### Container image

Each platform release publishes the image `ghga/<name>` on Docker Hub, tagged with the platform version ([releases](../docs/releases.md#platform-lane)).
Start it with the command to run; a service without commands needs none:

```bash
docker run ghga/<name>:<platform-version> <command>
```

To build the image yourself, run `just image services/<directory>` from the repository root.
The base image comes from `dhi.io`, which needs a `docker login dhi.io` with a Docker Hub account entitled to Docker Hardened Images.

### Kubernetes

Each platform release also publishes the Helm chart `<name>`, whose README in [`deploy/charts/<name>/`](../deploy/charts/) lists its values:

```bash
helm install <name> oci://registry-1.docker.io/ghga/<name>-chart
```

### Without a container

In the dev container, start the service from the repository root:

```bash
uv run <name> <command>
```

### Configuration

The README's Parameters section lists the settings, and `example_config.yaml` next to it holds a complete set to adapt.
A service reads them from these sources, and the first one that sets a value wins:

1. environment variables named after the setting with the prefix `<prefix>_`, in upper or lower case, such as `DCS_HOST` for the `host` of `dcs`, with `__` between the levels of a nested setting;
2. a `.env` file in the working directory, then `/secrets/.env`;
3. the YAML file named by `<PREFIX>_CONFIG_YAML`, or else `.<prefix>.yaml` in the working directory, or else in the home directory.

In a container these paths are inside the container.

### Development

Work in the monorepo's dev container, as described in [Work inside the dev container](../README.md#work-inside-the-dev-container).
Run a service's tests with `just test services/<directory>`, and the linters with `just lint`.
After changing a service's settings or its REST API, run `just service-docs` to regenerate its `config_schema.json`, `example_config.yaml`, `openapi.yaml` and the Parameters section of its README.
