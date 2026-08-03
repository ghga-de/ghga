# GHGA Monorepo

One polyglot monorepo for GHGA: Python services, libraries, and CLIs (a single `uv` workspace)
alongside the Angular `data-portal`, with Helm charts and a Kubernetes integration test bed as
build products.

> **Status: scaffolding.** The source repos have **not** been imported yet. This is the
> Phase-1 skeleton (workspace + toolchain + structure) plus the planning docs. The
> history-preserving import, dependency lock, charts, and CI are deliberate next steps —
> see the runbook.

## Layout

| Path | Contents |
|---|---|
| [`libs/`](libs/) | Source-coupled internal libraries (hexkit, ghga-service-commons, …) |
| [`services/`](services/) | Deployable services |
| [`tools/`](tools/) | CLIs & jobs (ghga-connector, ghga-datasteward-kit, auth-km-jobs, …) |
| [`frontend/`](frontend/) | The Angular `data-portal` (own `pnpm` workspace) |
| [`deploy/`](deploy/) | Helm charts (adopted `ghga-common` library + generator, demo umbrella) |
| [`testbed/`](testbed/) | BDD + Playwright integration suite (runs on kind/minikube) |
| [`docker/`](docker/) | Shared Dockerfile(s) |
| [`scripts/`](scripts/) | Codegen, affected-targets, and migration tooling |
| [`docs/`](docs/) | Architecture, ADRs, migration runbook |

## Getting started (once members are imported)

```bash
uv sync                 # or: just sync
just lint && just test
```

## Task runner

Everything runs through [`just`](justfile) — a thin facade over uv / pnpm / helm / kind
([ADR-0015](docs/adr/0015-task-runner.md)). Run `just` with no arguments to list every
recipe with its description.

### Run the demo locally

The demo is the whole platform on a local kind cluster: all 20 deployable services behind
an Envoy Gateway edge, with lightweight infra (Kafka, MongoDB, MinIO, a mock OIDC issuer).

```bash
just demo-images-mono   # build the container images (one Python image — see "Image profiles")
just up mono            # create the cluster, load the images, install the umbrella, wait
```

Then open <http://localhost/> — the data portal at `/`, the OIDC issuer at `/ghga`.

`just up` is `helm upgrade --install`, so re-run it freely after chart or values edits.
`just down` deletes the cluster; the built images survive it, so the next `just up`
reloads rather than rebuilds.

#### Logging in as the data steward

The demo seeds one data steward ([ADR-0006](docs/adr/0006-self-contained-demo-lightweight-infra.md)),
configured in the umbrella's `auth-claims.config.add_as_data_stewards`:

| | |
|---|---|
| subject (`ext_id`) | `data.steward@ghga.dev` |
| name | `Data Steward` |
| email | `data.steward@ghga.dev` |
| IVA | Phone `+4915112345678`, seeded **unverified** |

**1. Verify the IVA first.** The steward role is only active while the IVA backing its
claim is verified, and there is no self-service path to verify it — creating a verification
code is itself a steward action. Roles are resolved when the session is created, so do this
*before* logging in (or log out and back in afterwards):

```bash
kubectl --context kind-ghga exec deploy/ghga-mongodb -- mongosh --quiet --eval \
  'db.getSiblingDB("auth-service").ivas.updateMany(
     {"__metadata__.deleted": {$ne: true}}, {$set: {state: "Verified"}})'
```

This writes state directly, bypassing the event flow, so downstream projections never see
an IVA-verified event. That is what the test bed does too, and it is fine for the demo.

**2. Sign in at the mock issuer.** Click login in the portal; you land on the
mock-oauth2-server form, which has exactly two fields:

- **username** — the subject, `data.steward@ghga.dev` (must match `ext_id` exactly)
- **claims** — a JSON object; `name` and `email` are required and must match the seeded
  user, or the portal treats it as changed contact data:

```json
{"name": "Data Steward", "email": "data.steward@ghga.dev"}
```

**3. Set up the second factor.** The user is already registered, so you go straight to
TOTP: add the offered secret to an authenticator app and enter the six-digit code.

Any other subject you type into that form is simply a new user and goes through normal
registration — that is how you get a non-steward account to test against. The test-bed
profile swaps the issuer and the steward identity (`id-of-data-steward@ghga.dev` /
`data.steward@home.org`, see `values-testbed.yaml`); the steps are otherwise identical.

### Run the test bed locally

The BDD + Playwright integration suite ([`testbed/`](testbed/)) against the same umbrella
plus the test-bed profile — state-management service, test OIDC provider, and the
generated metldata artifact model ([ADR-0009](docs/adr/0009-testbed-kind-minikube.md)).

```bash
just sync               # workspace env: the artifact generation needs ghga-datasteward-kit
just testbed-install    # one-time: .venv-testbed + the matching Playwright chromium
just demo-images-mono   # build the container images
just testbed-up mono    # deploy with the test-bed profile
just testbed            # run the suite
```

Scope a run with `just testbed steps/test_001_health_check.py`, and use
`just testbed-reset` to return the cluster to a coherent cold start between runs — the
suite starts from an empty state and its feature files are ordered by numeric prefix.

### Image profiles

Building and loading are separate steps: the build lands in the local docker store and
survives `just down`, the load copies into the kind node and does not.

| profile | build | what you get |
|---|---|---|
| **mono** (fast) | `just demo-images-mono` | one image with every Python member in a single venv, plus the frontend |
| per-member | `just demo-images` | one image per member, exactly as released |

The mono profile is **demo/CI only** — same lockfile, same base image, same commands, only
the packaging differs ([`docker/Dockerfile`](docker/Dockerfile) `VARIANT=mono`). Production
and the release workflow always build one image per member. It exists because it replaces
~22 builds with one; locally that is ~15-20 min down to ~1 min, and ~6 GB of images down to
~0.6 GB. Pass `mono` to `just up` / `just testbed-up` to deploy against it — that overlays
`values-mono.yaml`, which `just charts` generates.

### Recipe reference

| area | recipes |
|---|---|
| Python workspace | `sync`, `lock`, `lint`, `fmt`, `typecheck`, `test [target]`, `affected [base]` |
| Front end | `fe-install`, `fe-build`, `fe-test`, `fe-lint`, `fe-dev`, `fe-dev-backend` |
| Helm charts | `charts [version]`, `charts-test`, `demo-template` |
| Images | `image <target>`, `image-mono`, `demo-images`, `demo-images-mono`, `docker-prune` |
| Cluster & demo | `cluster`, `up [profile]`, `demo-load [profile] [reclaim]`, `wait-ready`, `down`, `net-fix` |
| Test bed | `testbed-install`, `testbed-artifacts`, `testbed-up [profile]`, `testbed`, `testbed-reset`, `testbed-hosts` |
| Migration | `import-from-snapshot`, `sync-mainline` |

## Where to read

- **[docs/architecture/overview.md](docs/architecture/overview.md)** — the target architecture.
- **[docs/adr/](docs/adr/)** — the decisions (and why), ADR-0001…0016.
- **[docs/migration/runbook.md](docs/migration/runbook.md)** — the phased migration plan.

## Conventions

See [docs/conventions.md](docs/conventions.md) — workspace layout, the `[tool.ghga]` capability
markers, naming, and the per-component release-tag scheme (`name/x.y.z`).
