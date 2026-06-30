# ADR-0008 — `state-management-service` is test-bed-only and values-gated

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
`state-management-service` (SMS) is a deliberate **test backdoor**: it lets the integration
suite manipulate application state — empty/seed MongoDB, clear/publish Kafka topics, empty S3
buckets, reset Vault secrets — without the harness needing direct driver access. The
`archive-test-bed` uses it in its `reset_state` cascade between BDD scenarios. It is not part of
the application's runtime behaviour, and it is highly security-sensitive (it can wipe all state).

## Decision
SMS is a **test-bed-profile-only** component. In the umbrella chart it sits behind a values gate
(e.g. `testbed.enabled` / `stateManagement.enabled: false` by default) and is **never** deployed
in the demo or production profiles. Demo/prod seeding (e.g. the data-steward user) is done by a
**seed Job** + `auth-service`'s `add_as_data_stewards` config, not via SMS.

## Consequences
- The demo (`helm install ghga`) and the test bed diverge by exactly this component: the test
  bed layers SMS on top so scenarios can reset state.
- Deploying SMS in a real environment would be a severe security hole; the default-off gate and
  this ADR make that an explicit, reviewed mistake rather than an accident.
- Tests that reset state require the test-bed profile; the demo cannot reset itself via SMS
  (intentional).

## Alternatives considered
- **Always deploy SMS (as in compose).** Rejected: unacceptable in demo/prod.
- **Replace SMS with per-test direct driver access.** Rejected: SMS is the existing, working
  abstraction and keeps the suite decoupled from infra internals.
