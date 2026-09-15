# ADR-0006 — Self-contained demo umbrella with lightweight bundled infra

- **Status:** Accepted (revised 2026-06-30 — edge is Envoy Gateway, demo == testbed; see
  [ADR-0012](0012-self-contained-edge-envoy-gateway.md)) — **amended 2026-09-04**: the
  Bitnami subcharts are gone (see below)
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
`helm install ghga` must yield a fully functional GHGA, including a local AAI, **self-reliantly**
— one install on a cluster you control, no external ops. The app charts own app-coupled CRDs but
not the edge or infra ([ADR-0011](0011-helm-chart-boundary-hybrid.md)), so a self-contained
experience needs an umbrella that supplies the **edge** + **infra**. Production uses
operator-managed infra (Istio, Strimzi, prometheus-operator); the demo/test bed runs on
kind/minikube where operators are heavy.

## Decision
Add `deploy/charts/ghga-demo`, a self-contained **single-command** umbrella that depends on the
app charts and bundles:
- the **edge**: **Envoy Gateway** (Gateway-API-native, runs real Envoy ext_authz against the
  auth-adapter — [ADR-0012](0012-self-contained-edge-envoy-gateway.md)), gateway Service
  defaulting to **NodePort** on bare clusters;
- **lightweight, operator-free infra**: Bitnami Kafka (KRaft, `KafkaUser`/`KafkaTopic` emission
  toggled off), standalone MongoDB, **MinIO** (replacing LocalStack), Vault dev-mode,
  **mock-oauth2-server** as the local AAI ([ADR-0007](0007-local-aai-generic-oidc.md)), MailHog;
- a pre-install **secret-gen Job** (plain K8s Secrets — [ADR-0016](0016-secrets-and-tls.md),
  replacing the `auth-km-jobs` shell script) and a **seed Job** (data-steward user via
  `auth-service`'s `add_as_data_stewards`).

This **same umbrella is the per-PR test bed** ([ADR-0009](0009-testbed-kind-minikube.md)), which
additionally enables `state-management-service`
([ADR-0008](0008-state-management-service-testbed-only.md)). "What you install == what CI tests."

**Amended 2026-09-04 — no Bitnami subcharts left.** The 2025 Bitnami catalogue gating
broke those pulls, so kafka, mongodb and minio are plain templates in `ghga-demo` itself
on official images (`apache/kafka`, `mongo`, `minio/minio`), not bundled subcharts. Vault
dev-mode, the AAI and MailHog were already in-chart. The decision — operator-free,
lightweight stand-ins supplied by the umbrella — is unchanged; only the mechanism is.

## Consequences
- One command on a cluster you control brings up a working GHGA with the **real** Gateway-API
  routing + Envoy ext_authz path.
- **Faithful where it matters, lightweight elsewhere**: the edge/auth data path matches prod;
  what still differs is the edge-auth *object type* (Envoy Gateway `SecurityPolicy` vs Istio
  `AuthorizationPolicy`/extensionProvider), mesh mTLS/`DestinationRule`, and Strimzi Kafka
  specifics (demo uses plain Kafka + topic auto-create).
- Those residual, declarative differences are covered by a **periodic staging check** that
  deploys the same app charts against the real Istio/Strimzi platform — not a per-PR gate.
- Caveats (chart-handled): Helm `crds/` are install-only → document CRD upgrades; NodePort +
  `port-forward` for access on bare clusters.

## Alternatives considered
- **Bundle full Istio in the demo** (max fidelity). Heavy on kind and wants a multi-step
  installer; kept as an optional umbrella profile + the staging check
  ([ADR-0012](0012-self-contained-edge-envoy-gateway.md)).
- **Single chart with `demo`/`prod` profile flag.** Viable, but a thin app chart + demo umbrella
  keeps the prod-reusable charts uncontaminated by demo dependencies.
