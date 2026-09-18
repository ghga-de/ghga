# `frontend/` — Angular front end

Home of `data-portal`. It uses the **JS toolchain** (`pnpm` workspace, Vitest, Playwright)
with its **own lockfile** — it is *not* part of the `uv` workspace.

- Runtime config is injected via `window.config` (YAML + env overrides at container start), so
  the same image runs in demo and prod with different `oidc_*`/API URLs — no rebuild per
  environment.
- Built and served as a static SPA (static-web-server) behind the edge.
- Local AAI defaults to `mock-oauth2-server`
  ([ADR-0029](../docs/adrs/adr-0029-local-aai-generic-oidc.md)); prod points at Life Science Login.

> `data-portal` carries an `angular-developer` skill in `.agents/skills/`, symlinked into
> `.claude/skills/` like every other skill in this repository.
