---
status: accepted
date: 2026-06-30
tags: [security, deploy]
related: [ADR-0031]
---

# ADR-0035 — Secrets and TLS: Kubernetes Secrets in the demo, Vault and cert-manager in production

## Summary

In the context of **services that need signing keys, Crypt4GH keys, a TOTP key, Vault
credentials and TLS certificates**

facing **a self-contained demo without a secret store, and a production platform that
already runs Vault**

we decided for **a pre-install Job writing plain Kubernetes Secrets in the demo, Vault
Agent injection and cert-manager in production, and charts that reference secrets only
by name**

and neglected **the External Secrets Operator, secrets in git, and generating production
secrets in the cluster**

to achieve **a demo that needs no external store, and production secrets that stay in
Vault**

accepting that **secrets arrive differently per environment, and the demo serves plain
HTTP**.

## Details

### Context

The docker-compose test bed generated its keys at start-up and mounted them. The
`ghga-common` chart already supports Vault Agent injection, and the key store service
already reads Crypt4GH keys from Vault. App charts reference secrets by name, whatever
produces them ([ADR-0031](0031-helm-chart-boundary-hybrid.md)).

### Decision

- **Demo and test bed:** a pre-install Job generates the keys and writes plain
  Kubernetes Secrets, keeping existing ones so an upgrade does not rotate them. Services
  read them as environment variables. Vault runs in dev mode only as the key store's
  backend, not for injecting secrets. The demo gateway serves HTTP, without TLS.
- **Production:** secrets come from Vault through Vault Agent injection, TLS
  certificates from cert-manager, and `auth-km-jobs` rotates the signing keys in Vault.
  The platform layer owns all of this; the charts reference secret names and switch the
  Vault Agent annotations on.

### Consequences

- The demo needs no secret store; production keeps using Vault.
- How a workload consumes secrets is a per-profile switch in `ghga-common`.
- TLS is a production concern only. Unencrypted traffic is fine on a local cluster, but
  not for a demo exposed to a network.

### Alternatives

- **External Secrets Operator.** Adds an operator where Vault Agent already does the
  job.
- **Sealed Secrets or SOPS, with secrets in git.** An option if the platform prefers it
  to Vault.
- **Generating production secrets in the cluster**, as the compose test bed did. A
  reinstall would rotate them, and nothing would be auditable.
