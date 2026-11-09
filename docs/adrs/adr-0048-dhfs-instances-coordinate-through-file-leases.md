---
status: proposed
date: 2026-11-09
tags: [backend, deploy]
related: [ADR-0005]
---

# ADR-0048 — DHFS instances coordinate through file leases in FIS

## Summary

In the context of **a Data Hub running more than one DHFS instance against FIS**

facing **every instance receiving the same waiting files and re-encrypting each of them**

we decided for **a renewable lease per file in FIS, claimed through an atomic find-and-modify in the hexkit DAO: each claim serves one file to one instance, which renews the lease while it works**

and neglected **static sharding by `hash(file_id) % n`, leases sized from an assumed throughput, a compare-and-set over candidates and a separate claim endpoint**

to achieve **any number of instances sharing one queue without configuration**

accepting that **a new hexkit DAO method, one claim per file plus renewals, a unique ID per instance, and a claim that mutates on a GET**.

## Details

### Context

DHFS re-encrypts one file at a time, so a hub short on compute can add throughput only by adding instances.
`GET /storages/{storage_alias}/uploads` returns every waiting file to every caller, so two instances re-encrypt the same files.
Each re-encryption draws a new secret, so the second report conflicts with the first: FIS answers 409 or 500 and logs at CRITICAL.
That is wasteful and noisy, not unsafe.

The DHFS chart runs a Deployment, so pod names are random and `replicaCount` can change at any time, and some hubs do not run Kubernetes at all.

An *instance* is one running DHFS process, identified by its `service_instance_id`; "replica" refers only to `replicaCount`.

### Decision

- **Claim.**
  FIS stores `leased_until` and `leased_by` on each file.
  The GET serves at most one waiting file whose lease is null or expired, and leases it to the caller in one atomic find-and-modify.
- **Renewal.**
  A lease is a short constant, 20 minutes, and the instance renews it every 4 minutes while it works on the file.
  FIS refuses a renewal once a claim has been held longer than a hold cap, which guards against an instance that is alive but stuck.
- **Release.**
  An instance that gives up on a file releases it, and FIS backs the file off exponentially.
- **Holder check.**
  Renewal and release apply only for the instance named in `leased_by`.
- **Find-and-modify in the hexkit DAO.**
  A new method, `update_first`, selects, sorts and changes a resource in one call, and changes only the given fields.
  Changes map model fields to plain values; MongoDB update operators are a documented extension, as in filters, and FIS uses `$inc` for its claim counter.
  Other backends can implement it too, such as PostgreSQL with `SELECT … FOR UPDATE SKIP LOCKED`.
- **The claim stays on the GET.**
  Leases bind every DHFS from the moment FIS ships, including a DHFS that predates them.

[Leafcutter Ant](../epics/epic-0094-leafcutter-ant.md) specifies the implementation.

### Consequences

- Instances can be added or removed at any time, and no instance needs to know how many others run.
- A dead instance parks its file for at most one lease; a stuck but live one parks it until the hold cap.
- FIS takes one claim per file instead of one per batch, plus a renewal every 4 minutes per working instance.
- `service_instance_id` must be unique per instance, which the chart's `serviceInstanceId.fromPodName` provides; hubs without Kubernetes must provide it themselves.
- The retry transport can repeat the GET, stranding up to three leases until they expire.
- Lease writes filter on `state` and `interrogated` and change only lease fields, so they cannot overwrite a state the outbox subscriber writes ([ADR-0005](adr-0005-db-event-consistency.md)).
- Every hexkit DAO provider and `DaoPublisher` implement `update_first`, and providers validate each changed value, since a partial update skips whole-model validation.

### Alternatives

- **Static sharding by `hash(file_id) % n`.**
  Each instance filters the list down to the files matching its ordinal, which needs no change in FIS.
  Rejected: it needs stable ordinals, which a Deployment does not give, changing `n` moves files between instances mid-work, a shard stalls while its pod is down, and a few large files balance poorly.
- **A lease sized once from the file's size and an assumed throughput**, set per hub or derived by FIS from past claims and reports.
  Rejected: throughput differs between hubs and changes with their infrastructure, so the lease either parks a dead instance's file for hours or expires under a working one.
  It also cannot cover a multi-terabyte file.
- **A compare-and-set with `update(precondition=…)` over a window of candidates.**
  Needs no hexkit change, but instances that read the same candidates race for the same document and all but one lose.
  A random pick from the window, retries and re-reads only work around that, and replacing the whole document needs a precondition to avoid overwriting the subscriber's state changes.
- **Leases in their own collection.**
  The claim could no longer filter on lease state in MongoDB and would fetch every waiting file.
- **A `POST …/claim` endpoint, with the GET left read-only.**
  Cleaner, but it binds no DHFS until every hub has upgraded, unless FIS raises `dhfs_version_constraint` with it and crash-loops every hub on the old image.
