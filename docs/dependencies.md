# Dependency updates

How the repo's dependencies are kept current, and which ones we deliberately keep behind their latest version.

## How dependencies are updated

- **Lockfiles:** the daily `security-scan.yaml` workflow updates `uv.lock` and `pnpm-lock.yaml` within the ranges the members declare.
- **Base images:** Renovate bumps only the DHI base-image tags, as configured in [renovate.json5](../renovate.json5).
- **Declared ranges** (`pyproject.toml`, `package.json`) and the tool versions in CI, Dockerfiles and the devcontainer are raised by hand, in a pull request.
- **Front-end overrides** of transitive dependencies follow the rules in the [data-portal README](../frontend/data-portal/README.md#dependency-overrides).

## Held-back versions

Pins that can take a comment point here; `package.json` cannot, which is why the front-end holds are only recorded in this file.
Review the table when you look at the weekly Renovate dashboard issue.

| Dependency | Held at | Latest | Why | Lift when | Expected | Checked |
|---|---|---|---|---|---|---|
| `typescript` | ~6.0 | 7.0.2 | `@angular/compiler-cli` and `@angular/build` require `>=6.0 <6.1`, `typescript-eslint` requires `<6.1.0` | All three accept 7 in a stable release | Not announced; stable 22.2 still requires 6.0 | 2026-09-25 |
| Node.js, `@types/node` | 24 | 26 | 24 is the active LTS line; the types must match the runtime, or code can use APIs that fail on it | Node 26 enters LTS. Move CI `node-version`, the front-end `Dockerfile` with its `NODE_BASE` bound in `renovate.json5`, the devcontainer and `@types/node` in one change | Node 26 LTS: 2026-10-28 | 2026-09-25 |
| Python | 3.14 | 3.15 | The platform baseline ([ADR-0026](adrs/adr-0026-uv-workspace-source-coupled-libs.md)); every suite and release image runs on it, and `renovate.json5` bounds the base image to it | The team moves the baseline: `.python-version`, `uv.lock` and the members' `requires-python` in one change | Team decision | 2026-10-15 |
| Python floor, PyPI lane | `>=3.11` | `>=3.12` | The published libraries and CLIs share one floor, set for external consumers rather than for this workspace ([ADR-0026](adrs/adr-0026-uv-workspace-source-coupled-libs.md)) | Python 3.11 reaches EOL. Raise `requires-python` and the classifiers on every lane member, and drop 3.11 from `TEST_PYTHONS` in `scripts/pypi_members.py` | Python 3.11 EOL: 2027-10 | 2026-10-15 |

Dates come from the [Angular release schedule](https://angular.dev/reference/releases), the [Node.js release schedule](https://github.com/nodejs/Release#release-schedule) and the [Python release cycle](https://devguide.python.org/versions/).
They are the projects' own estimates and can slip.

### Checking a hold

Most holds are peer-dependency ranges, which a query answers:

```sh
cd frontend/data-portal
pnpm outdated
pnpm view @angular/build@latest peerDependencies
pnpm view @angular/compiler-cli@latest peerDependencies
pnpm view typescript-eslint@latest peerDependencies
```

When a signal has fired, lift the hold in its own change and remove the row.
When it has not, update the `Latest`, `Expected` and `Checked` columns.
Add a row whenever a review decides not to take a version.
