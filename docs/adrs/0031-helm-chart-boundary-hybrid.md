# ADR-0031 — Helm charts from `ghga-common` with a hybrid boundary

- **Status:** accepted
- **Date:** 2026-06-30

## Summary

In the context of **Helm charts for the GHGA services, built in this repo and used both
in production and in the self-contained demo**

facing **a production platform whose GitOps layer owns the edge, cluster auth and
per-environment config, and an existing chart system that already works there**

we decided for **adopting the `ghga-common` library chart and its generator, with app
charts owning the resources that belong to one workload, and the platform layer owning
everything cluster-wide**

and neglected **writing new charts, copying the old ones verbatim, and charts that own
either none or all of the platform resources**

to achieve **one app chart that runs unchanged under Istio in production and Envoy
Gateway in the demo, without re-deriving a design proven in production**

accepting that **the charts track the Gateway API and Strimzi APIs they emit, and carry
the Bitnami `common` library along**.

## Details

### Context

Helm charts are a product of this repo, and we want the same app chart in production and
in the demo ([ADR-0028](0028-self-contained-demo-lightweight-infra.md)). Production runs
Istio, Strimzi-managed Kafka and Vault, configured from the GitOps repo
`devops-kubernetes-hub`.

GHGA already had a chart system in the `charts` repo: the library chart `ghga-common`
and a generator that stamps out one chart per service. Its app charts already emitted
the resources tied to a single workload, such as `HTTPRoute`, `NetworkPolicy` and
`KafkaUser`, while the edge `Gateway` and the cluster auth policy lived in the GitOps
repo. We call this split the hybrid boundary.

### Decision

We adopt `ghga-common` and its generator into `deploy/`, and the per-service charts
become a generated build product. The generator reads workspace metadata
([ADR-0033](0033-capability-markers-and-placement.md)), and each member keeps its chart
values next to its code. What the old system carried but we no longer use stays behind:
the Emissary routing paths, and the `istio-ext-authz-sync` Job in the self-contained
path ([ADR-0032](0032-self-contained-edge-envoy-gateway.md)).

App charts own the resources that are one-to-one with a workload: `HTTPRoute`,
`DestinationRule`, `NetworkPolicy`, `KafkaUser` and `KafkaTopic`, and the way the
workload consumes secrets ([ADR-0035](0035-secrets-and-tls.md)). Each one can be
switched off in the values, so the chart works with or without Istio, Envoy Gateway or
Strimzi.

The platform layer owns what is cluster-wide: the edge `Gateway`, the edge auth object
(Istio `AuthorizationPolicy` in production, Envoy Gateway `SecurityPolicy` in the demo),
extension-provider registration and per-environment values. `devops-kubernetes-hub`
stays outside this repo.

App charts keep a binding contract, so the platform layer attaches its resources without
patching templates. The contract is listed in the [architecture
overview](../architecture/overview.md#35-helm--adopt-ghga-common-app-charts--demo-umbrella).

### Consequences

- We start from a chart design the teams know and production already runs.
- The demo umbrella plugs its own edge in where production plugs in Istio; the app
  charts do not change.
- The binding contract is a compatibility promise: renaming ports or ServiceAccounts
  breaks the platform layer.
- Library changes made upstream in the `charts` repo no longer apply as patches and are
  ported by hand ([runbook](../migration/runbook.md)).

### Alternatives

- **Write new app charts.** Months of work to re-derive a design that already works.
- **Copy `charts` verbatim.** Keeps the dead Emissary paths, the sync Job and a values
  tree that duplicates workspace metadata.
- **App charts own no platform resources.** Every `HTTPRoute` and `KafkaUser` would move
  into a parallel layer that has to mirror each workload, for no gain.
- **App charts own all of them, including the edge and cluster auth.** Those are
  environment-wide and belong to the platform team.
