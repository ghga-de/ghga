# ADR-0029 — Local AAI via generic OIDC providers

- **Status:** accepted
- **Date:** 2026-06-30

## Summary

In the context of **a self-contained GHGA that cannot use Life Science Login**

facing **services that need a trusted OIDC provider, and a test suite that logs in as
arbitrary users without a browser**

we decided for **the off-the-shelf `mock-oauth2-server` in the demo, GHGA's own test
OIDC provider in the test bed, and Life Science Login in production, chosen through
configuration**

and neglected **Dex and Keycloak**

to achieve **a demo AAI that is configuration rather than code, and a test bed whose
login fixtures work unchanged**

accepting that **we run two local providers, and neither of them is Life Science
Login**.

## Details

### Context

GHGA authenticates users against Life Science Login, and a self-contained install needs
a local replacement. The auth adapter in `auth-service` needs an issuer it trusts, with
discovery, JWKS, userinfo and a claim it maps to the external user ID. The BDD suite
creates tokens for arbitrary users without a browser, through the `POST /login` endpoint
of GHGA's test OIDC provider.

### Decision

- **Demo:** [`mock-oauth2-server`](https://github.com/navikt/mock-oauth2-server),
  through the `aai` chart. It is small, configurable per claim, and issues tokens for
  any subject.
- **Test bed:** GHGA's test OIDC provider, `services/test-oidc-provider`, which the
  login fixtures use as they are.
- **Production:** Life Science Login.

The umbrella points the `oidc_*` settings of `auth-service` and the data portal at the
selected provider, so the issuer and endpoint URLs stay consistent.

### Consequences

- The demo's AAI is configuration of a maintained image, not code of ours.
- The test bed needs no change to its login fixtures, at the price of a second provider
  that we maintain.
- Login against Life Science Login itself is exercised only outside the demo and test
  bed.

### Alternatives

- **Dex.** Lightweight, but less convenient for non-interactive test users.
- **Keycloak.** Closer to Life Science Login, but heavier than the demo needs.
