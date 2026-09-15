# ADR-0032 — Self-contained edge: Envoy Gateway

- **Status:** accepted
- **Date:** 2026-06-30

## Summary

In the context of **a self-contained install that should also test close to production**

facing **a production Istio edge that registers ext-authz through a privileged job
patching mesh configuration, and is heavy on a single-node cluster**

we decided for **Envoy Gateway as the self-contained edge, serving the charts' own
`HTTPRoute`s and calling the real auth adapter through Envoy ext_authz**

and neglected **bundling full Istio, a hand-written Envoy configuration, and
ingress-nginx**

to achieve **a one-command install whose routing and authorization path matches
production's**

accepting that **the edge auth object, mesh mTLS and `DestinationRule`s differ from
production and are tested only in staging**.

## Details

### Context

Two priorities pull against each other: integration tests close to production, and a
`helm install ghga` that needs no pre-installed mesh, no cluster-admin jobs and no
operators.

Production's edge is Istio with the Gateway API: a `Gateway`, an `HTTPRoute` per
service, and an `AuthorizationPolicy` that calls the auth adapter through an ext-authz
extension provider. Istio has no resource for that provider, so production registers it
with the privileged `istio-ext-authz-sync` Job, which patches the shared mesh
configuration.

The app charts already emit the `HTTPRoute`s, and the auth adapter is our own code
speaking Envoy ext_authz over HTTP. Only the edge varies.

### Decision

The self-contained edge is [Envoy Gateway](https://gateway.envoyproxy.io/): one
controller, no mesh and no sidecars. It serves the `HTTPRoute`s the app charts emit, and
its `SecurityPolicy` runs Envoy ext_authz against the real auth adapter, with the same
header contract as production. The umbrella chart brings Envoy Gateway and the Gateway
API resources as a dependency, so the install stays one command. Full Istio is not run
per pull request; staging covers it.

### Consequences

- The self-contained install and CI both exercise real Gateway API routing and ext_authz
  against the auth adapter.
- What differs from production is declarative and checked in staging: `SecurityPolicy`
  instead of `AuthorizationPolicy` and its provider, and no mesh mTLS or
  `DestinationRule`.
- Helm installs the CRDs but never upgrades them, so CRD upgrades are a manual step.
- Bare clusters have no load balancer, so the gateway Service uses a NodePort.
- The install needs a cluster where you may create cluster-scoped resources.

### Alternatives

- **Bundle full Istio.** Closest to production, but heavy on kind and in need of a
  multi-step installer. An optional Istio profile of the umbrella stays an open idea.
- **A hand-written Envoy configuration.** A second routing definition next to the
  `HTTPRoute`s.
- **ingress-nginx with `auth_request`.** Different ext-authz semantics would force
  changes to the auth adapter and let demo auth diverge from production.
