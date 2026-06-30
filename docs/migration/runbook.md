# GHGA Monorepo — Migration Runbook

> Executable, step-by-step migration plan. Decisions behind it:
> [ADR-0010](../adr/0010-history-preserving-migration.md) (migration),
> [ADR-0002](../adr/0002-uv-workspace-source-coupled-libs.md) (uv workspace),
> [ADR-0004](../adr/0004-versioning-and-release-by-tag.md) (release).
> Tooling: [scripts/migration/](../../scripts/migration/) — **review before running.**

## 0. Prerequisites

Install: `git`, [`git-filter-repo`](https://github.com/newren/git-filter-repo)
(`pipx install git-filter-repo`), `uv`, `just` ([ADR-0015](../adr/0015-task-runner.md)), `helm`,
`kind`, `kubectl`, `docker`, `pnpm`/`node`. (No mesh/Istio needed for the self-contained path —
the umbrella bundles Envoy Gateway, [ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md).)

Accounts/secrets for the **sandbox** ([ADR-0010](../adr/0010-history-preserving-migration.md)):
- GitHub: repo under **`github.com/lkuchenb`** (e.g. `lkuchenb/ghga-monorepo`).
- DockerHub: namespace **`lkuchenb`** + an access token → store as the `DOCKERHUB_TOKEN` Actions secret.
- Charts: GHCR under `lkuchenb` (uses the built-in `GITHUB_TOKEN`).
- **No PyPI** during the sandbox — pipelines exist but stay disabled.

The legacy clones already exist at [.legacy_repos/](../../.legacy_repos/) (snapshot). For the
initial import you may use them via `LEGACY_DIR`; **incremental sync must fetch from `ghga-de`**
(the live source).

## 1. Phase 1 — Monorepo skeleton

1. Initialise the repo and root scaffolding (hand-authored, replaces the retired template):
   ```bash
   cd /workspaces/ghga-monorepo
   git init -b main
   printf '.legacy_repos/\n.migration-work/\n' >> .gitignore   # never track these
   ```
2. Author the root workspace files (see [overview §3.1–3.2](../architecture/overview.md)):
   - root `pyproject.toml` with `[tool.uv.workspace] members = ["libs/*", "services/*", "tools/*"]`
     and the shared `ruff`/`mypy`/`pytest` config;
   - placeholder `libs/`, `services/`, `tools/`, `frontend/`, `deploy/`, `testbed/`, `docker/` dirs;
   - the consolidated `.github/workflows/` (added in Phase 5).
3. Commit:
   ```bash
   git add -A && git commit -m "Monorepo skeleton: uv workspace + shared toolchain"
   ```

> The skeleton commit must exist **before** the import (the import merges into it).

## 2. Phase 2 — History-preserving import

Run the import. Destinations are disjoint, so the unrelated-history merges don't conflict.

```bash
# from local snapshot (fast, offline):
LEGACY_DIR=$PWD/.legacy_repos scripts/migration/import-all.sh
# or from upstream:
scripts/migration/import-all.sh
```

What it does, per row in [scripts/migration/repos.tsv](../../scripts/migration/repos.tsv):
- whole-repo rows: drop centralised boilerplate (kind-specific list in
  [lib.sh](../../scripts/migration/lib.sh)), then move the rest into the destination subdir;
- `file-services-backend` rows: keep only the named `services/<svc>` subtree, placed at top level;
- merge with `--allow-unrelated-histories`, preserving authorship/dates; `git blame`/`log` follow
  files into their new paths.

Verify:
```bash
git log --oneline --graph --decorate | head -50
git -C . ls-files | cut -d/ -f1-2 | sort -u   # sanity-check the tree shape
```

## 3. Phase 3 — Harmonisation (root-only; keep service `src/` aligned)

Per [ADR-0010](../adr/0010-history-preserving-migration.md), do **all** of this at the root so
incremental sync stays low-conflict:

1. **Workspace wiring:** in each member's `pyproject.toml`, replace PyPI pins on internal libs
   with `[tool.uv.sources] <lib> = { workspace = true }`. This is the one per-service file the
   sync may later touch — keep the block minimal and stable.
2. **Lock:** `uv lock` → single root `uv.lock`. Resolve any genuine conflicts now (this is where
   today's `event-schemas 12 vs 13` / `transpiler <3 vs 3.0.0` skew gets reconciled).
3. **Toolchain:** one `ruff`/`mypy`/`pre-commit` config; delete per-member copies (already dropped
   on import).
4. **Containers:** one shared `docker/Dockerfile` (+ DHI), ENTRYPOINT chosen per service; the
   frontend keeps its bespoke Dockerfile.
5. **Per-package lib matrix:** a CI job that runs each `libs/*` standalone across its supported
   Python range ([ADR-0002](../adr/0002-uv-workspace-source-coupled-libs.md)).
6. Run `uv sync && uv run pytest` per affected target; commit.

## 4. Phase 4 — Charts & test bed

1. **Adopt `ghga-common`** ([ADR-0013](../adr/0013-adopt-ghga-common-chart-system.md)): move the
   library chart + generator into `deploy/`; prune the Emissary paths and the
   `istio-ext-authz-sync` Job; DRY the generator against `[tool.ghga]` markers
   ([ADR-0014](../adr/0014-capability-markers-and-placement.md)). App charts keep their
   app-coupled CRDs (HTTPRoute, DestinationRule[toggle], NetworkPolicy, KafkaUser[toggle]) —
   the *hybrid* boundary ([ADR-0011](../adr/0011-helm-chart-boundary-hybrid.md)).
2. `deploy/charts/ghga-demo` — single-command umbrella bundling the **Envoy Gateway** edge
   ([ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md); `SecurityPolicy.extAuth` →
   auth-adapter; gateway Service → NodePort) + lightweight infra + AAI + secret-gen/seed Jobs
   ([ADR-0006](../adr/0006-self-contained-demo-lightweight-infra.md),
   [ADR-0007](../adr/0007-local-aai-generic-oidc.md),
   [ADR-0016](../adr/0016-secrets-and-tls.md)).
3. Port the `testbed/` suite to target the umbrella; re-point its mint-a-user calls at
   `mock-oauth2-server`; gate `state-management-service` behind the test-bed profile
   ([ADR-0008](../adr/0008-state-management-service-testbed-only.md)).
4. Validate locally (same artifact users install):
   ```bash
   kind create cluster
   # build + load affected images, then:
   helm install ghga ./deploy/charts/ghga-demo -f deploy/charts/ghga-demo/values-testbed.yaml
   kubectl port-forward svc/<gateway> 8443:443   # bare cluster: no LoadBalancer
   uv run pytest testbed/
   ```
   > CRD note: Gateway API + Envoy Gateway CRDs ship in the chart's `crds/` (install-only);
   > CRD **upgrades** need a manual `kubectl apply` ([ADR-0012](../adr/0012-self-contained-edge-envoy-gateway.md)).

## 5. Phase 5 — CI/CD (sandbox targets)

- **PR gate:** affected-target lint/type/unit + the kind integration gate
  ([ADR-0009](../adr/0009-testbed-kind-minikube.md)).
- **Image/chart publish:** on `name/x.y.z` tags → DockerHub `lkuchenb` / GHCR `lkuchenb`
  ([ADR-0004](../adr/0004-versioning-and-release-by-tag.md)).
- **PyPI publish:** authored but **disabled** (sandbox).
- Push the repo to `github.com/lkuchenb/ghga-monorepo`.

## 6. Ongoing — one-way incremental sync

While developing the sandbox in parallel with mainline:
```bash
scripts/migration/sync-from-mainline.sh                 # all destinations
scripts/migration/sync-from-mainline.sh libs/hexkit     # just one
```
Conflicts are expected only in a service's `pyproject.toml` (`[tool.uv.sources]`); resolve,
`git commit`, re-run for the rest. Keep harmonisation root-only and don't restructure service
`src/` during the window, or conflicts multiply.

## 7. Cutover checklist (when the sandbox proves out)

- [ ] Final `sync-from-mainline.sh` against `ghga-de` HEAD; resolve remaining deltas.
- [ ] Freeze mainline repos (announce; protect branches / make read-only).
- [ ] Flip CD targets: DockerHub `lkuchenb` → `ghga`; GHCR → org registry; **enable PyPI**
      publishing for `libs/*` and `tools/*`.
- [ ] Reconcile versions so the first monorepo release of each component continues its PyPI/image
      series (no version regressions).
- [ ] Move the repo to `github.com/ghga-de/<monorepo>`; set CODEOWNERS per path.
- [ ] Archive the old repos (keep read-only for history/provenance); update external docs that
      point at per-repo locations.
- [ ] Verify external consumers of `ghga-connector` / `ghga-datasteward-kit` / `hexkit` /
      `schemapack` still install the expected versions from PyPI.
- [ ] Decommission the docker-compose test bed.

## Notes & caveats
- `git filter-repo` **rewrites SHAs**; old commit-message PR refs (`#NNN`) become dangling. The
  originals remain on `ghga-de`.
- Determinism (for incremental sync) assumes append-only mainline history and a **pinned
  `git-filter-repo` version** across runs.
- Historical release tags are **not** imported (they'd reference rewritten SHAs); the new scheme
  is `name/x.y.z` ([ADR-0004](../adr/0004-versioning-and-release-by-tag.md)).
- `.legacy_repos/` and `.migration-work/` must stay gitignored (nested `.git` dirs; scratch).
