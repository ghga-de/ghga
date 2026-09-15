# ADR-0007 — Local AAI via a generic OIDC provider

- **Status:** Accepted — **amended 2026-09-04**: the premise no longer holds, both OPs
  now ship (see below)
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
GHGA authenticates against **Life Science Login** (LS Login / ELIXIR AAI). For a self-contained
`helm install ghga` we need a local replacement. The docker-compose test bed used a GHGA image
`ghga/test-oidc-provider:2.2.0`, but **its source is not among the migrated repos**.

The `auth-service` auth-adapter expects an OP with discovery (`.well-known`), JWKS, and
userinfo, a trusted issuer, and a claim shape it maps to `ext_id`. Critically, the BDD suite
**mints tokens for arbitrary users non-interactively** (the old `POST /login` "log in as X").

## Decision
Ship a **generic, off-the-shelf OIDC provider** as a swappable `aai` subchart with profiles:
- **demo / test bed (default):** [`mock-oauth2-server` (Navikt)](https://github.com/navikt/mock-oauth2-server)
  — tiny, fully claim-configurable, issues tokens for any subject (a near drop-in for the old
  mint-a-user behaviour);
- **keycloak:** a more production-like self-hosted AAI option (LS Login is Keycloak-family),
  with Direct Access Grants for test token minting;
- **external:** point `oidc_*` config at real LS Login (production).

**Amended 2026-09-04 — premise falsified; both OPs now ship.** `ghga/test-oidc-provider`
*was* migrated after all: it is a workspace member (`services/test-oidc-provider/`) with
its own chart (`deploy/charts/test-oidc-provider/`), so "source not available in scope"
under Alternatives is no longer true. The decision above stands and the two now coexist as
profiles of the demo umbrella — the **demo** profile runs `mock-oauth2-server` via the
`aai` subchart, the **test-bed** profile (`values-testbed.yaml`) disables `aai` and swaps
in the original GHGA test OP, pointing the whole auth stack's `oidc_*` settings at it.
That also retires the second Consequence below: the test OP's `POST /login` mints tokens
non-interactively, so the BDD auth fixtures use it as-is rather than being re-pointed at
the mock's token endpoint.

## Consequences
- No dependency on an unavailable GHGA image; the local AAI is maintained config, not bespoke
  code.
- The test bed's mint-a-user calls must be re-pointed to the mock's token endpoint (a testbed
  migration task).
- The chart must template the `auth-service` and `data-portal` `oidc_*` settings from the
  selected AAI profile so issuer/JWKS/authorize/token/userinfo URLs stay consistent.

## Alternatives considered
- **Ship `ghga/test-oidc-provider`.** Blocked: source not available in scope.
- **Dex.** Good lightweight OIDC, but less convenient for arbitrary non-interactive test users.
- **Keycloak as the default.** Heavier than needed for the demo/test loop; kept as a profile.
