---
status: accepted
date: 2026-06-30
tags: [deploy, testing]
---

# ADR-0030 — `state-management-service` is test-bed-only

## Summary

In the context of **an integration suite that resets Kafka, MongoDB, S3 and Vault
between scenarios**

facing **a service that can wipe all application state and must never run where real
data lives**

we decided for **deploying `state-management-service` only in the test-bed profile,
disabled by default in the umbrella chart**

and neglected **deploying it everywhere, as docker-compose did, and giving the tests
direct access to each store**

to achieve **resettable tests without a backdoor in the demo or production**

accepting that **the demo cannot reset its own state, and differs from the test bed by
this service**.

## Details

### Context

`state-management-service` lets the integration suite empty and seed MongoDB, clear and
publish Kafka topics, empty S3 buckets and reset Vault secrets, without direct access to
those stores. The suite uses it between BDD scenarios. It is not part of the
application, and anyone who can reach it can destroy all state.

### Decision

The umbrella chart ships the service disabled, and only the test-bed profile enables it.
It is never deployed in the demo or in production. The demo seeds its data steward
through a Job and `auth-service` configuration instead.

### Consequences

- Deploying the service in a real environment would be a severe security hole; the
  default and this record make that an explicit choice rather than an accident.
- Tests that reset state need the test-bed profile.

### Alternatives

- **Deploy it everywhere, as docker-compose did.** Unacceptable outside tests.
- **Direct store access from the tests.** Couples the suite to each store's internals,
  which the service already hides.
