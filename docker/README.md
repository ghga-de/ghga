# `docker/` — shared container images

One Dockerfile builds **any** deployable workspace member from the repo root, parameterised by
`PACKAGE` (the member to install) and `EXECUTABLE` (its console-script ENTRYPOINT). This mirrors
the proven `file-services-backend` "one Dockerfile, ENTRYPOINT per service" approach, adapted to
the `uv` workspace (resolve from the single `uv.lock`, install only the target package + its
source-coupled deps).

- [`Dockerfile`](Dockerfile) — standard image.
- [`Dockerfile.dhi`](Dockerfile.dhi) — Docker Hardened Image variant (private `dhi.io` base),
  built in parallel by the release flavour matrix.

```bash
# build from the REPO ROOT:
docker build -f docker/Dockerfile \
  --build-arg PACKAGE=auth-service --build-arg EXECUTABLE=auth-service .
```

> Scaffold: exercisable only after the workspace members + `uv.lock` exist (post-import). The
> per-member `PACKAGE`/`EXECUTABLE` values come from `[tool.ghga]`
> ([conventions](../docs/conventions.md)). The front end keeps its own bespoke Dockerfile under
> `frontend/`.
