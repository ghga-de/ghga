---
status: proposed
date: 2026-11-09
tags: [backend, deploy]
related: [ADR-0005]
---

# ADR-0050 — DHFS instances coordinate through file leases in FIS

## Summary

In the context of **a Data Hub running more than one DHFS instance against FIS**

facing **every instance receiving the same waiting files and re-encrypting each of them**

we decided for **a renewable lease per file in FIS, claimed through an atomic find-and-modify in the hexkit DAO: each claim serves one file to one instance, which renews the lease while it works**

and neglected **static sharding by `hash(file_id) % n`, leases sized from an assumed throughput, a compare-and-set over candidates and a separate claim endpoint**

to achieve **any number of instances sharing one queue without configuration**

accepting that **a new hexkit DAO method, one claim per file plus renewals, a restarted instance losing its lease, and a claim that mutates on a GET**.

## Details

### Context

DHFS re-encrypts one file at a time, so a hub short on compute can add throughput only by adding instances.
`GET /storages/{storage_alias}/uploads` returns every waiting file to every caller, so two instances re-encrypt the same files.
Each re-encryption draws a new secret, so the second report conflicts with the first: FIS answers 409 or 500 and logs at CRITICAL.
That is wasteful and noisy, not unsafe.

The DHFS chart runs a Deployment, so pod names are random and `replicaCount` can change at any time, and some hubs do not run Kubernetes at all.

An *instance* is one running DHFS process; "replica" refers only to `replicaCount`.

### Decision

- **Claim.**
  FIS stores `leased_until` and `leased_by` on each file.
  The GET serves at most one waiting file whose lease is null or expired, and leases it to the caller in one atomic find-and-modify.
  It serves one file because an instance renews only the file it works on: the rest of a batch would wait unrenewed while DHFS works through it serially, and their leases would expire.
- **Renewal.**
  A lease is a short constant, 22 minutes, and the instance renews it every 4 minutes while it works on the file.
  So a lease survives four failed renewals in a row, each already retried by the retry transport, and the fifth renewal still arrives 2 minutes before expiry.
  Both values are constants, since renewal, not the lease length, adapts to the file size and the hub's throughput.
  FIS refuses a renewal once a claim has been held longer than a hold cap, which guards against an instance that is alive but stuck: its renewal task keeps running while its interrogation hangs, and renewals carry no progress.
  The cap is a setting; its default of 72 hours covers the 5 TB file from [Army Ant](../epics/epic-0091-army-ant.md), about 58 hours at 25 MiB/s.
- **Release.**
  An instance that gives up on a file releases it, and FIS backs the file off exponentially.
  Without the backoff, every instance would claim and release a file that fails within seconds, such as one still being written to the inbox, in a tight loop.
  A stopped instance releases nothing.
  Releasing on SIGTERM would need a signal handler, cancelling the interrogation and a release inside the 30 second grace period: a lot of DHFS code to save one file per stopped instance a wait of one lease.
- **Claimant ID.**
  Each instance generates a random claimant ID at startup and sends it with every claim, renewal and release.
  Renewal and release apply only for the claimant ID stored in `leased_by`.
  Without that check, a release could end another instance's live lease: A's lease expires while A still works, B claims the file, and A's release replaces B's lease with a backoff, after which C claims the file while B still works on it.
- **Find-and-modify in the hexkit DAO.**
  A new method, `update_first`, selects, sorts and changes a resource in one call, and changes only the given fields.
  Changes map model fields to plain values; MongoDB update operators are a documented extension, as in filters, and FIS uses `$inc` for its claim counter.
  Other backends can implement it too, such as PostgreSQL with `SELECT … FOR UPDATE SKIP LOCKED`.
- **The claim stays on the GET.**
  Leases bind every DHFS from the moment FIS ships, including a DHFS that predates them, so FIS ships leases without raising `dhfs_version_constraint`.
  Raising it with them would be a flag day: a DHFS on an old image gets 426, stops on a `CriticalError` and crash-loops until its hub upgrades, and so do the old pods during each hub's own rolling update.

[Leafcutter Ant](../epics/epic-0094-leafcutter-ant.md) specifies the implementation.

### Consequences

- Instances can be added or removed at any time, and no instance needs to know how many others run.
- A dead instance parks its file for at most one lease; a stuck but live one parks it until the hold cap.
- FIS takes one claim per file instead of one per batch, plus a renewal every 4 minutes per working instance.
- DHFS must poll again right after each file, because sleeping one poll interval per file caps an instance at one file per interval, over sixteen hours for a thousand files at the default of 60 seconds.
  The backoff keeps a file that fails fast from turning this into a hot loop: the file is missing from the next claim, which comes back empty and sends the instance to sleep.
- The claimant ID is unique without any deployment setting, but a restarted instance gets a new one, so the file it held waits out one lease.
- The retry transport can repeat the GET, stranding up to three leases until they expire.
- Lease writes filter on `state` and `interrogated` and change only lease fields, so they cannot overwrite a state the outbox subscriber writes.
  FIS runs its API and the subscriber as separate deployments, `fis` and `fis-consumer`, and the subscriber replaces whole documents.
  A claim that replaced the whole document could overwrite a cancellation written in between and return the file to the inbox, the read-modify-write hazard of [ADR-0005](adr-0005-db-event-consistency.md).
  The subscriber overwrites a lease only when it cancels, fails, archives or requeues the file, which ends the lease anyway.
- A DHFS that predates leases keeps working as a hub's only instance: it never renews or releases, so its leases expire after 22 minutes, but no other instance claims the file.
  A hub must run a DHFS that renews before it adds instances, or they duplicate every file that takes longer than one lease.
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
- **`service_instance_id` as the claimant ID.**
  Deployments set it per Deployment: the charts give every replica one constant, such as `rs_1`, so two instances would pass every `leased_by` check without a warning.
  It is unique only with the chart's `serviceInstanceId.fromPodName`, which is off by default and exists only on Kubernetes.
  An ID that survived restarts, so that a restarted container kept its lease, would need persistent identity per instance, such as a StatefulSet, tying the code to one kind of deployment.
- **A `POST …/claim` endpoint, with the GET left read-only.**
  Cleaner, but it binds no DHFS until every hub has upgraded, unless FIS raises `dhfs_version_constraint` with it, the flag day described under the decision.
