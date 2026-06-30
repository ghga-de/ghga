# `testbed/` — Kubernetes integration test bed

The ex-`archive-test-bed` BDD (pytest-bdd) + Playwright suite (after import). It drives the full
user journey — registration → metadata → upload → access → download — against a real cluster.

- Runs **the same self-reliant `ghga-demo` umbrella** a user installs (test-bed profile), on
  **kind** (CI) / **minikube** (local)
  ([ADR-0009](../docs/adr/0009-testbed-kind-minikube.md)). "What you install == what CI tests."
- Because the edge is **Envoy Gateway**, the gate exercises the **real** Gateway-API routing +
  Envoy ext_authz path ([ADR-0012](../docs/adr/0012-self-contained-edge-envoy-gateway.md)).
- The test-bed profile additionally enables `state-management-service` to reset
  Kafka/Mongo/S3/Vault between scenarios
  ([ADR-0008](../docs/adr/0008-state-management-service-testbed-only.md)).

Migration to-do (tracked): re-point the suite's mint-a-user calls from the old
`test-oidc-provider` to `mock-oauth2-server`.
