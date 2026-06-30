# ADR-0005 — Helm app chart is "services + config only"; platform CRDs live elsewhere

- **Status:** **Superseded by [ADR-0011](0011-helm-chart-boundary-hybrid.md)** (2026-06-30)
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

> **Superseded.** Investigation of the existing `charts/` and `devops-kubernetes-hub` repos
> showed the real, working boundary is *hybrid*: the `ghga-common` app charts already emit
> app-coupled CRDs (HTTPRoute, DestinationRule, NetworkPolicy, KafkaUser). The strict
> "services + config only" rule below was reversed in favour of that hybrid boundary —
> see [ADR-0011](0011-helm-chart-boundary-hybrid.md). The binding-contract requirements below
> still hold and are carried forward.

## Context
Production deploys with Istio (mesh + ingress), Strimzi-managed Kafka, and
Loki/Prometheus/Grafana — all cluster-wide platform components owned by a platform/GitOps
layer, not by the application. We want the *same* app-layer chart to be reusable in that
environment, not a demo-only chart with overrides bolted on later.

A service-mesh + operator platform needs more than on/off toggles: it needs the app workloads
to expose a stable surface that platform CRDs (`Gateway`/`VirtualService`/`AuthorizationPolicy`,
`KafkaUser`/`KafkaTopic`, `ServiceMonitor`) can bind to.

## Decision
The reusable app chart `deploy/charts/ghga` emits **only** Deployments / Services / ConfigMaps
and a **rest/consumer role abstraction** (N Deployments sharing config with distinct
`service_instance_id`s). It consumes all infra through **injected connection values + secret
refs**. It owns **no** platform CRDs — those are the platform/GitOps layer's responsibility.

The chart honours a **binding contract** so the platform layer attaches CRDs without patching
templates:
- pod/service **label + annotation passthrough**;
- **named ports with `http-`/`grpc-` prefixes**, stable Service names;
- **per-workload ServiceAccounts**;
- injectable OTLP / Kafka / Mongo / S3 / Vault / OIDC config; customisable probes;
- seed/secret-gen **Jobs default to `sidecar.istio.io/inject: "false"`**.

## Consequences
- The app chart is clean and reusable; prod overrides values and supplies its own CRDs.
- The platform team maintains a parallel CRD layer (mesh, Strimzi users/topics, monitors).
- The binding contract must be respected from day one; retrofitting named ports / SAs later is
  a breaking change.
- The self-contained `helm install ghga` experience is delivered by a separate **demo umbrella**
  ([ADR-0006](0006-self-contained-demo-lightweight-infra.md)), not by this chart.

## Alternatives considered
- **Chart emits the platform CRDs behind provider flags.** Rejected by the operator: they want
  CRDs owned by their GitOps layer.
- **Hybrid (chart owns app-coupled CRDs only).** Rejected for now in favour of the cleanest
  separation; can be revisited.
