---
status: current
date: 2026-11-25
tags: [security, deploy]
related: [ADR-0028, ADR-0030, ADR-0031, ADR-0035, AC-0003]
---

# AC-0011 — Production security boundaries

Several protections GHGA relies on are not in this repo: the app charts ship them switched off, and the platform layer switches them on in production ([ADR-0031](../adrs/adr-0031-helm-chart-boundary-hybrid.md)).
This page says which protections production has, so that a review of the code can rate a finding without access to the platform repo.
It names mechanisms, not hosts, accounts or secret paths; those stay in the platform repo.
The demo and the test bed run without most of them ([ADR-0028](../adrs/adr-0028-self-contained-demo-lightweight-infra.md)), so their values files are no evidence of what production does.

| Concern | Chart default and demo | Production |
|---|---|---|
| Traffic between workloads | Plain HTTP | mTLS through the Istio ambient mesh |
| Callers of an internal API | `authorizationPolicy.enabled: false` | An Istio `AuthorizationPolicy` per service |
| Kafka | `kafkaUser.enabled: false`, plaintext broker | TLS, one `KafkaUser` with ACLs per workload |
| Secrets | Kubernetes Secrets from a pre-install Job | Vault Agent injection ([ADR-0035](../adrs/adr-0035-secrets-and-tls.md)) |
| Logs | Container output | Readable by the DevOps team only |
| Test-only services | Off; on in the test-bed profile | Never deployed |

## Traffic between workloads

Production runs Istio in ambient mode.
Its ztunnel encrypts and authenticates all traffic between workloads with mTLS, including `auth-km-jobs` reaching Vault.
The demo has no mesh, so its traffic is plain HTTP ([ADR-0032](../adrs/adr-0032-self-contained-edge-envoy-gateway.md)).

## Internal APIs

Internal APIs, such as the claims API of `auth-service` and the key store (`ekss`), are not routed at the edge and do not check the caller themselves.
What limits their callers is an Istio `AuthorizationPolicy` that each service chart renders for its own workload when `authorizationPolicy.enabled` is set.
The allowed callers, with their methods and paths, are listed under `authorizationPolicy.callers` in the callee's `chart-values.yaml`; the platform layer adds the gateway.
In ambient mode only a waypoint can check paths and methods, so a policy with callers binds to the chart's Service through `targetRefs`.
A policy with `denyAll` has no path rules and selects the pods instead, where ztunnel enforces it.

A service that starts calling another service, or a new path on it, adds itself to the callee's `callers`; otherwise production denies the call.
The charts' `networkPolicy` stays off; the `AuthorizationPolicy` does that job in the mesh.

## Kafka

Production Kafka is managed by Strimzi and accepts TLS connections only.
Each workload authenticates as its own `KafkaUser`, which the chart renders when `kafkaUser.enabled` is set, with ACLs for the topics in that service's config.
A topic entry without `kafkaUser.operations` gets all operations on that topic, so a consumer could also produce to it.
Narrow new topic entries to the operations the service needs, as `access-request-service` does.
The demo broker runs plaintext without ACLs, which is why the charts default to `kafkaUser.enabled: false`.

## Secrets and logs

Production secrets come from Vault ([ADR-0035](../adrs/adr-0035-secrets-and-tls.md)), and `auth-km-jobs` rotates the signing keys there.
Only the DevOps team can read container logs and the log aggregation.
That does not make logs a place for secrets: a config field that holds one is typed as a pydantic `Secret`, which the startup log masks, and `just service-docs` fails on a field whose name marks it as a secret but whose type does not.

## Test-only services

The state management service (`sms`) and the test OIDC provider are switched on only by `values-testbed.yaml`, and never deployed in staging or production ([ADR-0030](../adrs/adr-0030-state-management-service-testbed-only.md)).
The test bed, in black-box and white-box mode, runs on synthetic test data only.

## Schema comparison

No deployed service compares schemas yet; `em-transformation-service` will, once it joins the workspace on `schemapack`.
`ghga-jsonsubschema` is used only by `schemapack`, and no service depends on `schemapack` so far.
Their inputs today are configs from the DevOps team, so they are trusted.
`ghga-jsonsubschema` resolves `$ref` through `jsonref`, which follows remote URLs by default.
Before `em-transformation-service` or any other service passes user-supplied schemas to either library, both need hardening: no remote `$ref`, and limits on schema size and depth.

## Metadata artifacts

The artifacts REST API of `metldata` serves, without access control, the resources of each artifact in `artifact_infos` that is not also in `publishable_artifacts`.
An artifact in `publishable_artifacts`, by default `added_accessions`, is not served but stored whole and sent on the `artifacts` topic, which only `rts` consumes.
Today all metadata GHGA holds is public, so every artifact is, including those the `ghga_archive` workflow names `embedded_restricted` and `resolved_restricted`.
Non-public metadata arrives with the [Apollo epic](../epics/epic-0089-apollo.md); until the API checks access, an artifact that holds it does not go into `artifact_infos`.

## Data Steward Kit

The [Data Steward Kit](../../tools/ghga-datasteward-kit/README.md) runs on the central data stewards' machines, not in the cluster.
Only central data stewards write its submission store and event store, and the kit trusts what it reads from them.
Keep those directories writable by central data stewards only.
