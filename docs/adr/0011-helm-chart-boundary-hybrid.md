# ADR-0011 — Helm chart boundary = hybrid (app charts own app-coupled CRDs)

- **Status:** Accepted (supersedes [ADR-0005](0005-helm-app-chart-services-and-config-only.md))
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
[ADR-0005](0005-helm-app-chart-services-and-config-only.md) proposed a strict "services +
config only" app chart that owns **no** CRDs. Investigating the existing `charts/` and
`devops-kubernetes-hub` repos showed that is **not** how GHGA actually works: the
`charts/base/ghga-common` library chart already emits **app-coupled CRDs** per service —
`HTTPRoute` (Gateway API), `DestinationRule` (Istio), `NetworkPolicy`, `KafkaUser` (Strimzi) —
plus Vault Agent annotations, while the **edge** (`Gateway`), the **cluster auth policy**
(`AuthorizationPolicy` for ext-authz), the **extensionProvider registration** (the
`istio-ext-authz-sync` Job), and **per-env config** live in the GitOps repo.

That is the "hybrid" boundary, and it is proven in production.

## Decision
The monorepo's app charts own the **app-coupled CRDs** that are 1:1 with a workload:
`HTTPRoute`, `DestinationRule` (toggle), `NetworkPolicy`, `KafkaUser`/`KafkaTopic` (toggle),
plus the secret-consumption shape (Vault Agent annotations or env-from-secret). The
**GitOps/platform layer owns cluster-edge concerns**: the edge `Gateway`, the edge-auth object
(Istio `AuthorizationPolicy` in prod / Envoy Gateway `SecurityPolicy` in the self-contained
demo — see [ADR-0012](0012-self-contained-edge-envoy-gateway.md)), extensionProvider
registration, and per-environment values.

Every app-coupled CRD is **values-toggleable** so the same chart works whether the cluster has
Istio, Envoy Gateway, or Strimzi present.

The binding-contract requirements from [ADR-0005](0005-helm-app-chart-services-and-config-only.md)
(label/annotation passthrough, named ports, per-workload ServiceAccounts, injectable config,
Job sidecar-injection control) are carried forward unchanged.

## Consequences
- Matches the existing, working chart design; minimal divergence from what teams know.
- The app chart is portable across edges/operators via toggles (Istio prod, Envoy Gateway demo).
- The chart must track the CRD APIs it emits (Gateway API, Strimzi) — acceptable, already true.
- The split point (edge/auth/per-env in GitOps) is the seam where the demo umbrella plugs in a
  self-contained edge instead of the platform's Istio.

## Alternatives considered
- **Strict "services + config only" ([ADR-0005](0005-helm-app-chart-services-and-config-only.md)).**
  Reversed: contradicts the existing `ghga-common` chart and would mean re-homing HTTPRoute/
  KafkaUser into a parallel layer for no benefit.
- **Chart owns *all* CRDs incl. edge Gateway + AuthorizationPolicy.** Rejected: edge + cluster
  auth are environment-wide, owned by the platform/GitOps layer.
