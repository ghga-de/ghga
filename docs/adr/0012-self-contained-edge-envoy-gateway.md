# ADR-0012 — Self-contained edge & ext-authz via Envoy Gateway

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
Two priorities pull against each other: (a) integration tests should be close to production,
and (b) `helm install ghga` must be **self-reliant** — one install on a cluster you control,
**no external ops setup** (no pre-installed mesh, no cluster-admin sync Jobs, no operators to
stand up first).

Production's edge: **Istio + Gateway API** — a `Gateway`, per-service `HTTPRoute`, and an
`AuthorizationPolicy(action: CUSTOM)` → `envoyExtAuthzHttp` extensionProvider →
the auth-adapter `Service ext-authz:8080`. Because Istio extensionProviders have no CRD, prod
registers them with a privileged `istio-ext-authz-sync` Job that patches the global `istio`
MeshConfig ConfigMap. That Job is a *shared-Istio, multi-tenant* workaround — wrong to import
into a self-contained install. Full Istio is also heavy and needs istiod-readiness/sidecar
ordering that pushes toward a multi-step installer.

Key realisation: the **app charts emit Gateway API `HTTPRoute`s**, and the integration-critical
component — the **auth-adapter** — is GHGA's own code speaking **Envoy `ext_authz` (HTTP)** with
a known header contract. So the edge is the only variable.

## Decision
The self-contained edge is **[Envoy Gateway](https://gateway.envoyproxy.io/)** (the Envoy
project's Gateway API implementation): one controller, no mesh, no sidecars, no ConfigMap
patching. It consumes the **same `HTTPRoute`s** the charts already emit, and its
`SecurityPolicy.extAuth` runs **real Envoy ext_authz (HTTP)** against the **real auth-adapter**
with the same headers
(`includeRequestHeadersInCheck`/`headersToBackend` mirroring the prod
`envoyExtAuthzHttp` contract).

- The **same artifact** is `helm install ghga` *and* the per-PR testbed → "what you install ==
  what CI tests", data-path-faithful to prod.
- **No `istio-ext-authz-sync` Job** in the self-contained path; the ext-authz wiring is
  declarative (`SecurityPolicy`).
- **Full Istio** (mesh mTLS + `AuthorizationPolicy` + extensionProvider + `DestinationRule`)
  is **not** run per-PR; it is covered by the periodic **staging** check
  ([ADR-0006](0006-self-contained-demo-lightweight-infra.md)) and is available as an optional
  higher-fidelity umbrella profile.
- `helm install ghga` is **one umbrella, one command**: the Envoy Gateway subchart brings the
  Gateway API + its CRDs; the app CRs reconcile asynchronously (no ordering blocker).

## Consequences
- Both priorities met: self-reliant single install **and** real Gateway-API routing + real
  Envoy ext_authz against the real auth-adapter.
- Residual gap vs prod = the edge-auth **object type** (`SecurityPolicy` vs Istio
  `AuthorizationPolicy`/extensionProvider) and absence of mesh mTLS/`DestinationRule` — all
  declarative, validated in staging.
- Caveats (chart-handled, not "extra ops"): Helm `crds/` are install-only → **document CRD
  upgrades**; bare clusters have no LoadBalancer → the gateway Service **defaults to NodePort**
  (+ `port-forward`) in the self-contained profile.
- Inherent prerequisite: a cluster you control with permission to install cluster-scoped CRDs
  (kind/minikube/your own) — true of demo/testbed/eval by definition.

## Alternatives considered
- **Bundle full Istio into the install (declarative meshConfig, no sync Job).** Max fidelity,
  but heavy on kind and realistically needs a multi-step installer (CRDs → istiod → app).
  Kept as an optional profile + the staging check.
- **Hand-rolled standalone Envoy.** Faithful ext_authz, but its routing config diverges from
  the charts' `HTTPRoute`, creating a parallel routing definition. Rejected.
- **ingress-nginx + `auth_request`.** Different ext-authz semantics than Envoy ext_authz →
  would force auth-adapter changes; demo auth would diverge from prod. Rejected.
