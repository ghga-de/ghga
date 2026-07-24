# `deploy/` — Helm charts (a product of this repo)

We **adopt and evolve** GHGA's existing `ghga-common` chart system rather than build from
scratch ([ADR-0013](../docs/adr/0013-adopt-ghga-common-chart-system.md)). The system is
imported (history-preserving) from the `charts` repo; its own documentation lives in
[chart-system.md](chart-system.md). Current layout: `base/ghga-common` (library chart),
`charts/` (generated per-service charts), `src/` (generator + per-service values),
`scripts/` (chart tooling).

Planned structure (adoption target, per the steps below):

```
deploy/
  charts/
    ghga-common/          # Bitnami-common-based library chart (the binding contract)
    <per-service charts>/ # generated from ghga-common + workspace [tool.ghga] metadata
    ghga-demo/            # self-contained, single-command umbrella (== the test bed)
```

Key decisions:
- **Hybrid boundary** ([ADR-0011](../docs/adr/0011-helm-chart-boundary-hybrid.md)): app charts
  own app-coupled CRDs (HTTPRoute, DestinationRule[toggle], NetworkPolicy, KafkaUser[toggle]);
  the GitOps/platform layer (`devops-kubernetes-hub`, not in this repo) owns the edge `Gateway`,
  the edge-auth object, and per-env config.
- **Self-contained edge = Envoy Gateway**
  ([ADR-0012](../docs/adr/0012-self-contained-edge-envoy-gateway.md)): `helm install ghga` is
  one command, runs real Gateway-API routing + real Envoy ext_authz against the auth-adapter,
  no external ops. Full Istio is reserved for the periodic staging check.
- **Secrets**: K8s Secrets in the demo, Vault Agent + cert-manager in prod
  ([ADR-0016](../docs/adr/0016-secrets-and-tls.md)).

To prune on adoption: dead Emissary `Mapping`/`AuthService` paths and the
`istio-ext-authz-sync` Job (the self-contained path sets ext-authz declaratively).
