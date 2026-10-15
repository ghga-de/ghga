---
status: accepted
date: 2026-06-30
amended: 2026-10-15
tags: [deploy, testing]
---

# ADR-0030 — `state-management-service` is test-bed-only

## Summary

In the context of **an integration suite that resets Kafka, MongoDB, S3 and Vault between scenarios**

facing **a service that can wipe all application state and must never run where real data lives**

we decided for **deploying `state-management-service` only in the test-bed profile, disabled by default in the umbrella chart**

and neglected **deploying it everywhere, as docker-compose did, and giving the tests direct access to each store**

to achieve **resettable tests without a backdoor in the demo or production**

accepting that **the demo cannot reset its own state, and differs from the test bed by this service**.

## Details

### Context

`state-management-service` lets the integration suite empty and seed MongoDB, clear and publish Kafka topics, empty S3 buckets and reset Vault secrets, without direct access to those stores.
The suite uses it between BDD scenarios.
It is not part of the application, and anyone who can reach it can destroy all state.

### Decision

The umbrella chart ships the service disabled, and only the test-bed profile enables it.
It is never deployed in the demo or in production.
The demo seeds its data steward through a Job and `auth-service` configuration instead.

**Amended 2026-10-15:** The e2e cluster that the test bed runs against from outside ([epic 0094](../epics/epic-0094-cuckoo-wasp.md)) is the one other environment where the service runs.
It holds test data only, and its deployment pins four guardrails: a non-empty `db_prefix`, so the service reaches only the databases named for the suite; a `db_permissions` list naming those databases, without a database wildcard; a Vault policy for the service that grants only the suite's secret path; and a token issued by Vault for that deployment, never a value shared between callers.
The test bed empties that secret path only when its configuration sets `allow_vault_reset`, which is off by default, since a reset at a wrong path loses secrets that no other store holds.
Its wildcard delete keeps the services' migration records, so `db_version_collection_suffix` stays at its default.

### Consequences

- Deploying the service in a real environment would be a severe security hole; the default and this record make that an explicit choice rather than an accident.
- Tests that reset state need the test-bed profile.

### Alternatives

- **Deploy it everywhere, as docker-compose did.**
  Unacceptable outside tests.
- **Direct store access from the tests.**
  Couples the suite to each store's internals, which the service already hides.
