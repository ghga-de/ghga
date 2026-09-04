# ADR-0009 — Integration test bed on Kubernetes (kind in CI, minikube locally)

- **Status:** Accepted — local execution amended by
  [ADR-0017](0017-local-integration-host-cluster.md) (host-level cluster, no DinD/DooD in the
  devcontainer, image delivery per platform) — **amended 2026-09-04**: read that pointer as
  ADR-0017's *current* state, which is kind in the devcontainer (see below)
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
Integration today uses docker-compose (`archive-test-bed`). We want the test bed to exercise the
**same Helm charts** we deploy, so that `HEAD` being green means "the deployable system
integrates", and to keep `main` always integrated. The BDD + Playwright suite already drives the
full user journey (registration → metadata → upload → access → download) and uses
`state-management-service` to reset state between scenarios.

## Decision
The ex-`archive-test-bed` suite moves to `testbed/` and runs against a Kubernetes cluster by
installing **the same self-reliant `ghga-demo` umbrella** a user gets from `helm install ghga`
(test-bed profile adds `state-management-service`) — i.e. the Envoy Gateway edge + lightweight
infra ([ADR-0006](0006-self-contained-demo-lightweight-infra.md),
[ADR-0012](0012-self-contained-edge-envoy-gateway.md)). "What you install == what CI tests."
- **CI: kind** — fast cluster bring-up, trivial `kind load` of locally-built images;
- **Local: minikube / colima** — for cluster-style local work.

**Amended 2026-09-04 — the local bullet is no longer the answer.** ADR-0017 first moved
the local cluster out to the host; its own 2026-07-27 amendment then moved the *fast*
iteration loop back to **kind inside the devcontainer's inner docker daemon**, which is
what `just cluster` / `just up` do today. The host-level cluster stays the target for
persistent, closer-to-real local use. Reading this ADR's Decision alone therefore gives
the wrong answer for local work; CI's kind path is unchanged.

The per-PR gate's parenthetical below is stale for the same reason
[ADR-0007](0007-local-aai-generic-oidc.md) was amended: the test-bed profile runs the
original GHGA test OP rather than `mock-oauth2-server`, and the suite's mint-a-user calls
still `POST /login` against it unchanged (`testbed/fixtures/auth.py`).

The per-PR gate builds **only affected images**, pulls last-released tags for the rest, loads
them into kind, installs the umbrella, and runs the BDD suite (re-pointing the suite's
mint-a-user calls at `mock-oauth2-server`).

## Consequences
- The gate tests the actual deployment artifact (charts + images) **and** the real Gateway-API
  routing + Envoy ext_authz path — not a separate compose topology or a stand-in edge.
- The **image pipeline is the long pole** (~20 images): mitigated by affected-only builds +
  cached pulls.
- Still **not** validated per-PR: the prod Istio edge-auth CRs, mesh mTLS, and Strimzi specifics
  — covered by the periodic staging check ([ADR-0006](0006-self-contained-demo-lightweight-infra.md)).
- docker-compose for the test bed is retired; a lightweight local inner loop (single service +
  its deps) can still use compose or `uv run` if desired.

## Alternatives considered
- **minikube everywhere.** Rejected for CI: heavier/slower per run than kind.
- **Keep docker-compose as the integration gate.** Rejected: it would not test the charts, so a
  green gate would not imply a deployable system.
