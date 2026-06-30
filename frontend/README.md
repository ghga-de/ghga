# `frontend/` — Angular front end

Home of `data-portal` (after import). It uses the **JS toolchain** (`pnpm` workspace, Vitest,
Playwright) with its **own lockfile** — it is *not* part of the `uv` workspace.

- Runtime config is injected via `window.config` (YAML + env overrides at container start), so
  the same image runs in demo and prod with different `oidc_*`/API URLs — no rebuild per
  environment.
- Built and served as a static SPA (static-web-server) behind the edge.
- Local AAI defaults to `mock-oauth2-server`
  ([ADR-0007](../docs/adr/0007-local-aai-generic-oidc.md)); prod points at Life Science Login.

> The `data-portal` repo ships an `angular-developer` skill under `.claude/skills` — it will
> come along with the import.
