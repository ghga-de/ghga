# `docker/` — shared container images

One Dockerfile builds **any** deployable workspace member from the repo root, parameterised by
`PACKAGE` (the member to install) and `EXECUTABLE` (its console-script ENTRYPOINT). This mirrors
the proven `file-services-backend` "one Dockerfile, ENTRYPOINT per service" approach, adapted to
the `uv` workspace (resolve from the single `uv.lock`, install only the target package + its
source-coupled deps).

- [`Dockerfile`](Dockerfile) — the canonical image, based on GHGA's **Docker Hardened
  Images** (`dhi.io`, authentication required: `docker login dhi.io` locally /
  `DOCKERHUB_USERNAME`+`DOCKERHUB_TOKEN` org secrets in CI). Build stages run on the DHI
  dev variant so the runtime libc matches; the runtime stage is the plain hardened base
  (non-root, shell-less).

```bash
# build from the REPO ROOT:
docker build -f docker/Dockerfile \
  --build-arg PACKAGE=auth-service --build-arg EXECUTABLE=auth-service .
```

> Scaffold: exercisable only after the workspace members + `uv.lock` exist (post-import). The
> per-member `PACKAGE`/`EXECUTABLE` values come from `[tool.ghga]`
> ([conventions](../docs/conventions.md)). The front end keeps its own bespoke Dockerfile under
> `frontend/`.

## Published tags

- `<member>:<platform-version>` — release artifacts, one image per member
  (`.github/workflows/release.yaml`, manual for now).
- `platform:dev` + `data-portal:dev` — mutable dev tags tracking `main`
  (`.github/workflows/dev-images.yaml`): the mono Python image (VARIANT=mono, all members
  in one venv) and the front-end image. Not release artifacts — they feed the daily
  vulnerability watch (`.github/workflows/security-scan.yaml`), which rescans them,
  trials a lockfile update, and opens a PR when the update fixes known CVEs.

## Base image updates

Renovate (`.github/workflows/renovate.yaml`, config in `renovate.json5`) tracks the
`PYTHON_BASE` ARG in `Dockerfile` and the `NODE_BASE` ARG in
`frontend/data-portal/Dockerfile.dhi` against the real tags available on `dhi.io`
(authenticated with the same `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` org secrets CI already
uses), and opens a PR per Dockerfile weekly. No automerge: a base-image bump is
security-sensitive, so it always waits for human review. Everything else (`uv.lock`,
`pnpm-lock.yaml`) stays with `security-scan.yaml`.

Each ARG holds the **whole** tag (`3.13.15-alpine3.24`), not a language version and an
alpine version in separate ARGs. `dhi.io` does not publish every combination of the two, so
tracking them as separate deps let Renovate maximise each independently and propose a tag
that was never published — a break that only surfaces at base pull, after merge. As one dep,
Renovate can only offer a tag string it actually found in the registry.

The trade-off: `versioning: docker` treats `-alpineX.Y` as a compatibility suffix and
compares only tags carrying the same alpine minor. So **Python/Node patch bumps arrive
automatically, alpine minor bumps do not** — moving to a new alpine is a deliberate hand
edit of the ARG (and of the `-sfw-dev`/`-sfw-ent-dev` variants' availability, which Renovate
does not check). That is intentional: an alpine minor is a distro change, not a patch.
