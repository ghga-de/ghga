# `deploy/` — Helm charts (a product of this repo)

We **adopt and evolve** GHGA's existing `ghga-common` chart system rather than build from
scratch ([ADR-0013](../docs/adr/0013-adopt-ghga-common-chart-system.md)). The system was
imported (history-preserving) from the `charts` repo; the upstream documentation lives in
[chart-system.md](chart-system.md).

Layout:

```
deploy/
  charts/
    ghga-common/          # Bitnami-common-based library chart (the binding contract)
    <per-service charts>/ # generated — do not edit; run `just charts [version]`
    ghga-demo/            # self-contained, single-command umbrella (== the test bed)
    aai/                  # local AAI subchart (mock-oauth2-server default; ADR-0007)
  src/                    # generator (create_charts.py), chart template, auxiliary values
  tests/                  # library chart tests (pytest renders the dummy chart via helm)
```

How the charts are produced: chart name/description/image/executable derive from the
workspace members enumerated by `scripts/image_members.py` (the same source the release
workflow uses); the chart version and `appVersion` are the platform version
(`just charts <version>`, image tags fall back to `appVersion`). Per-member deployment
values live in `<member>/chart-values.yaml`, co-located with the member. Generated charts
use `commandStyle: exec` — the monorepo's hardened images have no shell. Charts without a
workspace member (`test-oidc-provider`, `datahub-monitor`, `remotebackup`) are declared in
`src/auxiliary_charts.yaml` with values in `src/values/`.

The demo umbrella (`helm install ghga deploy/charts/ghga-demo`) bundles the Envoy Gateway
edge (GatewayClass/Gateway/EnvoyProxy, NodePort 30080 by default) with per-route
`SecurityPolicy` ext-authz against the auth adapter (headers mirror the prod
`envoyExtAuthzHttp` provider verbatim), lightweight infra (bitnami Kafka KRaft/MongoDB/
MinIO, `aai`), and the app charts behind enable conditions. Chart dependencies build
bottom-up — `just demo-template` does the ordered dep-up + render smoke check.

Demo wiring so far: auth-service deploys twice (aliases `auth-adapter`/`auth-rest`,
selected via `config.provide_apis`) — which is why generated charts flatten the library
defaults into their values.yaml at generation time (helm's `import-values` is not
processed for aliased instances). The aai issuer routes through the gateway at
`/<issuerId>` with no rewrite, so browser and adapter agree on one issuer URL; oidc_* and
DSN settings for the enabled slice live in the umbrella values (release name `ghga`
assumed — the config block is plain YAML, not templated). A pre-install secret-gen Job
(ADR-0006/0016) generates the internal auth JWK pair + TOTP key as plain K8s Secrets
(idempotent — keys survive upgrades; the adapter consumes the private half, the registry
instance the public half), and the demo data steward is seeded via
`add_as_data_stewards`. MailHog (SMTP sink, UI via port-forward) and Vault dev-mode
(functional ekss backend, not secret injection; a vault-init Job bootstraps the ekss
AppRole as in compose) round out the bundled infra. The file + metadata path is wired:
ekss/dcs/ucs/fis/ifrs/pcs/wps/rs/metldata with compose-derived configs (single MinIO
stands in for both hub localstacks, buckets provisioned by the chart), prod base paths
under an /api prefix, ext-authz on every /api/* route, and the full secret matrix
(distinct signing pairs per role, per-service tokens, crypt4gh file Secret for ekss).
The access/metadata/notification path is in too (ars, mass, dins, rts, ns, nos, dlqs;
sms ships disabled — testbed-only per ADR-0008 — the testbed profile enables it and adds
it to the protected routes), with a wiremock lox24 SMS-gateway mock beside MailHog. All
20 deployable services are in the bundle. Still to land: metldata's real artifact model
(testbed migration) and the host-cluster install (ADR-0017).

Adoption changes vs upstream: Emissary `Mapping`/`AuthService` paths pruned (routing is
Gateway-API `HTTPRoute`; the backend port lives at `httpRoute.port`), the
`istio-ext-authz-sync` Job is not carried into the self-contained path (Envoy Gateway sets
ext-authz declaratively), `charts_app_versions.yaml` and the per-repo version-plumbing
scripts are dissolved into workspace metadata.

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
