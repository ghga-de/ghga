# ADR-0009 — Integration test bed on Kubernetes (kind in CI, minikube locally)

- **Status:** Accepted
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
