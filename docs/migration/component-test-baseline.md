# Component-test baseline (post-import, integrated HEAD)

> Snapshot from 2026-06-30, right after the import + first `uv.lock`. Ran `pytest` per workspace
> member with **no Docker daemon** available, so testcontainers-based tests error as expected.
> Purpose: catalogue what the HEAD unification actually broke, by root cause. Will go stale as
> fixes land — it is a worklist, not living docs.

## Update — mechanical fixes applied (2026-06-30)

Two low-risk fixes landed (commit follows this doc):
- **linkml ecosystem bumped** `1.6.x` → `1.11.1` (relaxed the hard pins in `metldata` +
  `ghga-validator`). Clears the `typing.re` py3.13 breakage.
- **Recovered test deps** added to the root dev group: `aiosmtpd`, `openapi-core`, `cryptography`.

Result (re-ran the 4 affected suites): **clean win, no new code regressions.**
- `ghga-validator`: 9 errors → **9 pass, green**.
- `notification-service`: missing-dep errors gone (7 pass; rest are Kafka/Docker).
- `metldata`: 28 collection-errors → **155 pass** (remaining 13 "failures" are all Docker —
  its session fixture starts a Mongo container).
- `ghga-datasteward-kit`: 3 collection-errors → **57 pass** (remaining 11 are Docker, plus a few
  `FileNotFoundError: tests/fixtures/...` that are a **cwd artifact** of running `pytest` from the
  repo root rather than the member dir — not a regression).

**Still open = the 2 real code regressions below** (crypt4gh, transpiler→schemapack-4) plus the
Docker-bound suites (need DinD/testbed). Two test-invocation notes for whoever runs these next:
run member suites with `cwd` = the member dir, and set `<SVC>_CONFIG_YAML` for the services.

## Headline

- **~1450 tests pass** against the single integrated HEAD; **0 real failures in the services**.
- ~785 tests **error on Docker** (no daemon) — expected; they need DinD or the kind testbed.
- All non-Docker problems fall into **5 categories**, only **2** of which are real code regressions.

## Real code regressions (HEAD unification surfaced these — need code work)

| Component | Count | Cause | Fix |
|---|---|---|---|
| `ghga-service-commons` | 4 fail | `crypt4gh.keys.generate()` now requires a `comment` arg (crypt4gh 1.8.6). `src/ghga_service_commons/utils/crypt4gh.py:153` | add the `comment` argument |
| `ghga-transpiler` | 2 err (collection) | `pydantic` ValidationError — `schemapack` 2.0.0→4.2.0 API change (transpiler had pinned `==2.0.0`) | migrate transpiler to schemapack 4.x |

## Dependency / environment gaps (mechanical — not logic regressions)

| Symptom | Affected | Cause | Fix |
|---|---|---|---|
| `ImportError: cannot import name 're' from 'typing'` + `linkml_runtime` circular import | `metldata` (28), `ghga-validator` (9), `ghga-datasteward-kit` (3) | **`linkml_runtime` 1.6.0** (old) uses `from typing import re`, removed in Python 3.13. These were pinned to 3.12. | bump linkml / linkml-runtime to a 3.13-compatible release; verify metldata's linkml usage |
| `ModuleNotFoundError` (e.g. `aiosmtpd`, `jsonschema_path`) | `notification-service`, others | per-member **test** deps lived in the dropped `lock/requirements-dev*.in` | restore per-member test-dep declarations (from `.legacy_repos/*/lock/requirements-dev*.in`) |
| pydantic config ValidationError (`db_name`, `kafka_servers`, … missing) | FSB-style services (auth/dlq/fis/ifrs/…) | tests were run without `<SVC>_CONFIG_YAML` pointing at the service `dev_config.yaml` | a test-invocation detail (CI sets these env vars); not a code fix |

## Docker-bound (expected failures)
Most service + hexkit/connector integration tests need Kafka/Mongo/S3/Vault via testcontainers.
They error without a Docker daemon. hexkit's 2 "failures" are S3-integration-adjacent, not logic.
These get real coverage from DinD locally or the kind testbed in CI.

## Suggested order of attack
1. **Mechanical, low-risk:** restore per-member test deps; bump the linkml ecosystem to a
   3.13-compatible release (clears metldata/validator/datasteward-kit collection).
2. **Small code fixes:** crypt4gh `comment` arg in ghga-service-commons.
3. **Real migration (needs care):** ghga-transpiler → schemapack 4.x.
4. Re-run with a Docker daemon (DinD) to clear the ~785 expected Docker errors.
