# ADR-0016 — Secrets & TLS: K8s Secrets in demo, Vault Agent + cert-manager in prod

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
GHGA needs JWK signing keys, Crypt4GH key pairs, a TOTP encryption key, Vault credentials, and
TLS certs. The docker-compose test bed generated these at startup (`auth-km-jobs` +
`set_env.sh`) and mounted them. The existing `ghga-common` chart already supports **Vault Agent
injection**, and EKSS already reads Crypt4GH keys from **Vault**. The app chart references
secrets by name regardless of how they are produced ([ADR-0011](0011-helm-chart-boundary-hybrid.md)).

## Decision
- **Demo / testbed:** a pre-install **secret-gen Job** generates keys + a **self-signed** TLS
  cert and writes plain **Kubernetes Secrets**; the chart consumes them via env-from-Secret.
  Simple, self-reliant, no external store ([ADR-0012](0012-self-contained-edge-envoy-gateway.md)).
- **Production:** secrets come from **Vault via Vault Agent injection** (already in use); TLS is
  issued by **cert-manager**. `auth-km-jobs` becomes the JWK-rotation CronJob writing to Vault.
  These are owned by the platform/GitOps layer; the chart only references secret names + toggles
  the Vault-Agent annotations on.

## Consequences
- The demo has no Vault/secret-store dependency; prod reuses the existing Vault investment.
- The secret-consumption shape is a per-profile toggle in `ghga-common`
  ([ADR-0013](0013-adopt-ghga-common-chart-system.md)) — Vault Agent vs env-from-Secret.
- TLS differs by environment (self-signed demo cert vs cert-manager) — a values concern, not a
  template fork.

## Alternatives considered
- **External Secrets Operator (ESO).** Viable, but adds an operator where Vault Agent already
  does the job; kept as an alternative.
- **Sealed Secrets / SOPS (secrets-in-git).** Fits a pure-GitOps model without an external
  store; an option if the platform prefers it over Vault.
- **Generate secrets in-cluster in prod (as in compose).** Rejected: reinstall would rotate
  secrets; not auditable.
