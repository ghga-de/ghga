# File Leases for Multiple DHFS Instances (Leafcutter Ant)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the [Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline

A Data Hub runs one DHFS instance.
[Army Ant](./epic-0091-army-ant.md) made the *parts* of a single file process concurrently, but DHFS still works through files one at a time, so a hub whose bottleneck is compute cannot add throughput by adding instances.
That epic put multi-instance operation under "Not included" and called it a separate design challenge involving FIS.
This is that follow-up.

If a Data Hub were to attempt to run more than one instance today, each instance would receive the same unbounded list, and re-encrypt the same files.
[ADR-0048](../adrs/adr-0048-dhfs-instances-coordinate-through-file-leases.md) decides that instances coordinate through renewable file leases in FIS, and weighs the alternatives; this epic implements it.
Most of the new logic is in FIS.
DHFS sends a claimant ID when requesting a new file, renews the lease while it works, releases the file if interrogation is inconclusive, and stops sleeping between files.

### Included/Required

hexkit:

- Add `update_first` to the `Dao` protocol: it finds the first resource matching a filter in a given sort order and changes it, in one atomic call.
  See [The hexkit DAO method](#the-hexkit-dao-method).
- Implement it in the MongoDB provider, the in-memory DAO and the outbox `DaoPublisher`.

FIS:

- Add `leased_until`, `leased_by`, `claimed_at` and `times_claimed` to `FileUnderInterrogation`.
- Update the `GET /storages/{storage_alias}/uploads` handler to orchestrate file claims: serve one file, set `leased_until`, `leased_by`, `claimed_at` and `times_claimed`, and leave everything else unchanged.
- Add `POST /rpc/storages/{storage_alias}/uploads/{file_id}/renew` so an instance can extend its lease while it works on the file.
- Add `POST /rpc/storages/{storage_alias}/uploads/{file_id}/release` so an instance can hand a file back before its lease expires.
- Claim, renew and release each with one `update_first` call; see [The claim itself](#the-claim-itself).
- Add the compound index `{storage_alias: 1, state: 1, interrogated: 1, leased_until: 1, state_updated: 1}`.
  The `files` collection currently indexes only `object_id`.
- Add the configuration settings listed under [Configuration](#configuration).

DHFS:

- Generate a claimant ID once at startup, and send it on every claim, renewal and release, so FIS can tell one instance of a hub from another; see [The claimant ID](#the-claimant-id).
- Renew the lease from a background task while a file is in work, and stop that task before sending the report; see [The lease duration and renewal](#the-lease-duration-and-renewal).
- Call the release endpoint from the `InconclusiveError` branch of `interrogate_new_files()`, which today only logs, from the `ConclusiveError` branch when `report_failure` did not reach FIS, and after FIS refuses a renewal.
- Skip the poll interval after conclusively *or* inconclusively processing a file, and sleep only when the request for the next file comes back empty.
  Serving one file per claim makes this required; see [Serving one file per claim requires the poll pacing change](#serving-one-file-per-claim-requires-the-poll-pacing-change).
- Add jitter of up to 10% to `min_run_interval_seconds`, as a constant rather than a setting, so instances rolled out together stop polling in lockstep.

### Optional

- Give `S3Cleaner` a minimum object age, which bounds the cleanup race described under [The cleanup race widens](#the-cleanup-race-widens).

### Not included

- Progress reporting with renewals.
  A renewal says only that the instance is alive, not that its interrogation advances.
  The hold cap covers an instance that is alive but stuck; see [The lease duration and renewal](#the-lease-duration-and-renewal).
- Serving more than one file per claim/claim request.
- A give-up state after N failed attempts.
  [Shovelnose Guitarfish](./epic-0092-shovelnose-guitarfish.md) already gives Data Stewards a requeue path.
- Releasing the file in flight when the process is stopped (e.g. SIGTERM).
  A signal handler, cancellation of the running interrogation and a release inside the 30 second grace window is a lot of DHFS machinery for one file per stopped pod.
  That file waits out its lease instead, at most 22 minutes, and other files keep flowing; see [A stopped instance parks one file](#a-stopped-instance-parks-one-file).
- Per-instance identity in the JWT.
  `sub` is the storage alias, so two instances of one hub are indistinguishable to the authentication layer.
- Raising `replicaCount` for any hub.
  The chart already supports it; this epic only makes it safe.
  `deploy/charts/dhfs/values.yaml` is generated, so a hub that wants more instances raises `replicaCount` in `services/datahub-file-service/chart-values.yaml`.
  Again, that is only if they are using an orchestration layer comparable to Kubernetes.

## API Definitions

### RESTful/Synchronous

`GET /storages/{storage_alias}/uploads` keeps the same path, method and response model.
It now serves **at most one file**, and leases the file it serves.
The response shape still adheres to `BaseFileInformation`, which is unchanged.

New endpoints, both authenticated by the same Data Hub JWT and User-Agent check as the existing three Data Hub endpoints, and both carrying the caller's claimant ID:

- `POST /rpc/storages/{storage_alias}/uploads/{file_id}/renew`:
  - *Tell FIS that the caller is still working on a claimed file.*
  - Sets `leased_until` to `now + LEASE_SECONDS`, and changes nothing else.
  - Applies only when the caller still holds the lease; see [Only the DHFS instance holding the file may renew or release it](#only-the-dhfs-instance-holding-the-file-may-renew-or-release-it).
  - Returns:
    - 204 on success
    - 404 if the file is unknown, or belongs to another storage alias
    - 409 if the caller no longer holds the lease, the file is no longer waiting for interrogation, or the claim has reached `max_lease_hold_seconds`.
      Unlike release, the caller acts on this answer: it stops working on the file.
      The response body says which case applies, for the log; DHFS handles all three the same way.
- `POST /rpc/storages/{storage_alias}/uploads/{file_id}/release`:
  - *Tell FIS to release a claimed file.*
  - Sets the backoff, and sets `leased_by` and `claimed_at` to null, so a delayed renewal cannot turn the backoff back into a lease.
  - Applies only when the caller still holds the lease; see [Only the DHFS instance holding the file may renew or release it](#only-the-dhfs-instance-holding-the-file-may-renew-or-release-it).
  - Returns:
    - 204 on success, and also when the caller no longer holds the lease, because the caller cannot act on the difference
    - 404 if the file is unknown, or belongs to another storage alias

The storage alias check is required.
`_require_data_hub_jwt` only proves the caller is that hub; it does not prove the file belongs to it.
`handle_interrogation_report` omits this check today, so do not copy it from there.

## Additional Implementation Details

### What is a Lease?

Basically, it's the value set in `leased_until`.
That value encodes both states that a file can be held in: when claimed or renewed, it's set to `now + lease`, and when released, it's set to `now + backoff`.
If set to `null`, it means the file has never been claimed, or was requeued by a Data Steward after conclusive interrogation failure.
A claim prevents FIS from sending the file to another DHFS instance until the lease expires.

```mermaid
flowchart LR
    A[leased_until: null or in the past] -->|GET /uploads| B[set leased_until = now + lease]
    B -->|POST .../renew| B
    B -->|report success or failure| C[interrogated, leaves the pool]
    B -->|POST .../release| D[backed off until now + file-specific backoff]
    B -->|lease expires without renewal| A
    D -->|backoff expires| A
```

Because a conclusive report (be it successful or not) already sets `interrogated=True`, which removes the file from the candidate set, the report path doesn't need lease logic at all.

### The claim query

```python
filter_ = {
    "storage_alias": storage_alias,
    "state": "inbox",
    "interrogated": False,
    # The null branch must come first: the in-memory DAO evaluates $or lazily and
    # its $lt is a plain Python comparison, which raises TypeError on None.
    # Also note that GSI-2689 has been created for this.
    "$or": [{"leased_until": None}, {"leased_until": {"$lt": now}}],
}
```

hexkit allows this.
`validate_find_mapping` checks only that filter keys are model fields, and `validate_fields_in_model` drops keys starting with `$` (`libs/hexkit/src/hexkit/utils.py`), so a top-level `$or` passes.
Filter values are never inspected and go straight to pymongo.

`{"leased_until": None}` matches a missing field as well as a null one, so **no migration and no `DB_VERSION` bump are needed**.
A sentinel timestamp instead of null would need a backfill, because `$lt` against a Date matches neither null nor a missing field.
If the `$or` index union turns out to perform badly, the sentinel is the fallback, at the cost of that migration.

Sort ascending by `leased_until`, then by `state_updated`.
Null sorts before any date in both Mongo and the in-memory DAO, so never-claimed files come first and expired leases follow oldest-first.
The second key makes the order deterministic among files with the same `leased_until`.

### The hexkit DAO method

```python
async def update_first(
    self,
    *,
    filter_: Mapping[str, Any],
    changes: Mapping[str, Any],
    sort: list[str] | None = None,
) -> Dto:
```

- It selects the first resource that matches `filter_` in `sort` order, changes it and returns the changed resource, in one atomic call.
  It is the atomic form of `find_all(limit=1)` followed by `update`, so concurrent calls get different resources and none of them retries.
- `filter_` and `sort` work as in `find_all`.
- `changes` maps model fields to plain values and changes only those fields.
  Keys starting with `$` are MongoDB update operators, a documented extension in the same way as operators in filters.
  The in-memory DAO supports `$inc`, the only one FIS uses.
- It raises `NoHitsFoundError` when nothing matches, like `find_one`.
- A partial update skips whole-model validation.
  MongoDB applies the change on the server, so the provider cannot validate the merged document before the write.
  It validates and serializes each plain value against its field's type before the call, and validates the returned document after it; operator values are the caller's responsibility.
- `DaoPublisher` publishes the returned document, so it needs no extra read.

The name follows hexkit's terms rather than pymongo's `find_one_and_update`.
Other backends can do the same: PostgreSQL with `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`, and the in-memory DAO trivially.

### The claim itself

```python
claimed_file = await self._file_dao.update_first(
    filter_=filter_,  # the claim query above
    sort=["leased_until", "state_updated"],
    changes={
        "leased_until": now + timedelta(seconds=LEASE_SECONDS),
        "leased_by": claimant_id,
        "claimed_at": now,
        "$inc": {"times_claimed": 1},
    },
)
```

`NoHitsFoundError` means no file is waiting, and the GET returns an empty list.

The filter carries `state` and `interrogated`, and the call changes only the lease fields.
FIS runs the REST API and the outbox subscriber as two separate deployments (`fis` and `fis-consumer`), and the subscriber replaces whole documents.
A claim that replaced the whole document could overwrite a cancellation written in between and resurrect `state="inbox", can_remove=False`, the read-modify-write hazard of [ADR-0005](../adrs/adr-0005-db-event-consistency.md).
A partial update cannot.
The reverse, the subscriber overwriting a lease, happens only when it cancels, fails, archives or requeues the file, and each of those ends the lease anyway.

Two further rules for the claim path:

- **Never write `state_updated`.**
  `process_file_upload` drops events whose `state_updated` is not newer than the stored one.
  A claim that bumped it would make FIS discard the genuine cancelled or archived event that follows, so `can_remove` would never be set and the object would never be cleaned up.
- **Increment `times_claimed` at claim time, not at release.**
  An instance that is OOM-killed never releases, so a counter advanced only on release would never count a file that keeps crashing its instance.
  The increment is the `$inc` in the same call.

### Only the DHFS instance holding the file may renew or release it

A release that is not checked against the instance holding the lease can clear another instance's live lease.
Instance A claims a file, its lease expires while A is still working, B claims the file, and A then fails with an `InconclusiveError` and releases.
FIS overwrites B's lease with `now + backoff`, the next claim hands B's file to C, and two instances interrogate the same file again.

So the claim stores `leased_by`, and renewal and release put the caller's claimant ID into their `update_first` filter.
A release from any other instance changes nothing and FIS logs a warning; a renewal from any other instance gets a 409.
When the filter matches nothing, FIS reads the file once more to choose between 404 and the 409 or warning; that read only picks the response.
A release that finds `leased_by` null logs no warning: the file was already released, most often by a retry of the same release.
Either means a lease expired while an instance was still working, because its renewals did not reach FIS for a whole lease.

### The claimant ID

DHFS generates the claimant ID with `uuid4()` once per process, at startup, and FIS stores it as `leased_by`.
It is not a setting, so no deployment can make two instances share one; [ADR-0048](../adrs/adr-0048-dhfs-instances-coordinate-through-file-leases.md) explains why `service_instance_id` cannot serve instead.

A restarted process, whether its container was OOM-killed or its pod rescheduled, gets a new claimant ID and cannot renew or release the lease it held.
That file waits out its lease, at most 22 minutes; see [A stopped instance parks one file](#a-stopped-instance-parks-one-file).

DHFS logs its claimant ID at startup, in a record that also carries `service_instance_id` as `instance`, and in every claim, renewal and release log line.
FIS names `leased_by` in its warnings, so an operator can match a lease to the logs of the instance holding it.

### The lease duration and renewal

A lease lasts `LEASE_SECONDS`, a constant of 22 minutes in FIS, counted from the claim or from the latest renewal.
While DHFS works on a file, a background task renews the lease every `LEASE_RENEWAL_INTERVAL_SECONDS`, a constant of 4 minutes in DHFS.
A lease therefore survives four failed renewals in a row, each of which the retry transport has already retried.
It lasts 22 rather than 20 minutes so that the fifth renewal still lands 2 minutes before expiry, not at the moment of it.
The two constants live in different services, so comment each with a reference to the other: the lease must stay several renewal intervals long.

Both are constants rather than settings, since a renewed lease needs no tuning per hub ([ADR-0048](../adrs/adr-0048-dhfs-instances-coordinate-through-file-leases.md)).

The renewal task runs from the start of a file's interrogation until just before the report:

- **Stop renewing before sending the report.**
  `interrogate_file` calls `report_success` itself (`core/interrogator.py:854`), so the task has to end inside it, or that call moves out to the caller.
  A renewal that arrives after the report gets a 409, which would otherwise cancel the report.
- **A 409 cancels the interrogation of that file.**
  Cancelling it runs the existing `finally` in `interrogate_file` (`core/interrogator.py:800-803`), which aborts the multipart upload.
  DHFS then handles the file like an `InconclusiveError`: it releases the file and moves on.
  The release changes something only when the instance still holds the lease, which is the hold cap case, and there it sets the backoff.
- **Any other failure keeps the interrogation running.**
  On a connection error or a 5xx after retries, DHFS logs a warning and tries again at the next interval.
  If FIS stays unreachable for a whole lease, another instance can claim the file, which costs duplicate work, never data integrity ([ADR-0048](../adrs/adr-0048-dhfs-instances-coordinate-through-file-leases.md)).

A renewal is an `update_first` whose filter holds the file ID, `leased_by`, `state`, `interrogated` and the hold cap, and whose change sets only `leased_until`.
So it cannot resurrect a cancelled file, and like the claim it never writes `state_updated`.
It also succeeds after the lease has expired, as long as no other instance has claimed the file in the meantime.

**The hold cap guards against an instance that is alive but stuck.**
Its renewal task keeps running while its interrogation hangs, so renewal alone would hold the file forever.
FIS refuses a renewal once `now - claimed_at` exceeds `max_lease_hold_seconds`, through `{"claimed_at": {"$gt": now - cap}}` in the filter.
The default of 72 hours covers the 5 TB example from [Army Ant](./epic-0091-army-ant.md), which takes roughly 58 hours at 25 MiB/s.
A dead instance parks a file for one lease; only a stuck one can park it for the cap.

Renewal covers only the file DHFS is working on.
Serving several files at once would leave the later ones unrenewed while DHFS works through the batch serially, so their leases would expire before DHFS reached them.
So a claim serves one file, and no setting makes it serve more.

### One file per claim, but FIS's response is still in list format

The response stays `list[BaseFileInformation]`, now holding merely zero or one entry.
Keeping the list shape means DHFS needs no parsing change, and it leaves room to serve several files later should we do so.

DHFS's `for file in new_files` loop therefore needs no change: it iterates over zero or one item.
Leave the loop as it is.
`test_files_are_processed_one_at_a_time` (`tests/integration/test_interrogator.py:595`) already covers it, and keeping it lets FIS serve several files later without touching DHFS.

### Serving one file per claim requires the poll pacing change

`run_interrogator` sleeps out the remainder of `min_run_interval_seconds` after every round, whether or not the round did work.
One file per round therefore caps an instance at one file per interval: with the default of 60 seconds, a hub draining a thousand small files would take over sixteen hours per instance.

So DHFS must skip the sleep when the round processed a file, and sleep only when the claim came back empty.
Have `interrogate_new_files()` return whether it processed anything, and gate the existing sleep on that.

The backoff stops this from becoming a hot loop.
A file that fails inconclusively in a tenth of a second is released and backed off on the FIS side.
It is then absent from the next claim, which comes back empty and sends the instance to sleep.

The `except Exception` round in `run_interrogator` (`main.py:60`) reaches the same sleep.
It counts as a round that processed nothing, so an unhandled error does not spin the loop.

### Every path that ends without a report must release the file

A file is freed either by a report, which sets `interrogated=True`, or by a release.
Any path that produces neither leaves the file leased until expiry:

- `InconclusiveError` releases the file, which is the usual case.
- A renewal refused with a 409 cancels the interrogation and releases the file, as above.
- `ConclusiveError` where `report_failure` did not reach FIS must also release.
  `report_failure` catches `ConnectionFailedError`, `CentralAPIError` and bare `Exception` without re-raising (`core/interrogator.py:942-982`), and logs "DHFS will try re-processing this file later".
  That message is wrong once leases exist: the file waits out its lease instead of the next 60 second poll.
  So `report_failure` must return whether the report reached FIS, and the caller must release when it did not.
- `report_success` catching a `CentralAPIError` must **not** release.
  The comment at `interrogator.py:920-924` gives the reason: the round trip completed, so FIS may already have stored the report, and a second interrogation would use a different secret.
  Waiting is correct here, and the wait grows from 60 seconds to one lease, 22 minutes.
  Listed under [A success report that returned an error now waits a lease](#a-success-report-that-returned-an-error-now-waits-a-lease).
- A stopped or killed instance releases nothing and stops renewing, and the file waits out its lease.
  Lease expiry is the only mechanism here, by choice; see [A stopped instance parks one file](#a-stopped-instance-parks-one-file).

### Backoff

A release sets `leased_until = now + min(backoff_base * 2 ** (times_claimed - 1), backoff_cap)`.
It reads the file for `times_claimed`, then writes the backoff with an `update_first` filtered on the file ID and `leased_by`, which also sets `leased_by` and `claimed_at` to null.
Only a claim changes `times_claimed`, and a claim also changes `leased_by`, so the filter ensures the backoff comes from the current count.
Clearing `leased_by` makes a repeated release match nothing, which matters because the retry transport repeats a POST on 5xx and on connection failures.
Without a backoff, a file that fails in five seconds every time, one still being written to the inbox for example, is claimed, released and re-claimed in a tight loop by every instance.
A release always finds `times_claimed` at 1 or more, because only a claim sets `leased_by`, and every claim increments the counter.

`times_claimed` counts how often FIS handed the file out, including a claim stranded by a lost response and a claim the instance never started, so it runs ahead of the number of re-encryption attempts.
That is accurate enough for a backoff, and the name keeps anyone from reporting it to a Data Steward as a count of failed attempts.
This epic adds no give-up state, so the counter is the only signal that a file is stuck.
FIS must therefore log it: a warning at claim time, naming the file, once its count crosses a threshold constant.
A Data Steward uses that warning to decide whether to requeue the file through [Shovelnose Guitarfish](./epic-0092-shovelnose-guitarfish.md).

### Requeue

`_requeue_file` must also set `leased_until`, `leased_by` and `claimed_at` to null, and `times_claimed` to 0.
It already builds the new document from the event payload, which contains none of them, so this happens today by accident.
Make it explicit, because the same accident applies to the cancelled, failed and archived branch of `process_file_upload`.

### Configuration

All on FIS:

| Setting | Type | Default | Purpose |
|---|---|---|---|
| `max_lease_hold_seconds` | int | 259200 | Upper bound on how long one claim can be kept alive through renewals. |
| `claim_backoff_base_seconds` | int | 60 | First backoff after a release. |
| `claim_backoff_cap_seconds` | int | 3600 | Upper bound on the backoff. |

The lease length is a constant, not a setting; see [The lease duration and renewal](#the-lease-duration-and-renewal).
Set `max_lease_hold_seconds` to the longest single interrogation the team expects, since a stuck but live instance parks its file for that long.

### Known limitations

#### A lost response blocks a file for the lease duration

The claim is a side effect of a GET that the client retries.
A response lost after the write, or a 500 retried three times, leaves one to three files leased to no worker, idle until the lease expires.
The pacing change makes DHFS poll far more often, so there are many more claims to lose.
Each such file waits for expiry, which is one lease, 22 minutes, because no renewal follows.

#### A stopped instance parks one file

An instance that stops mid-file releases nothing, so that file stays leased until it expires.
SIGTERM is the common case, during a rolling update, and SIGKILL or a node failure behaves the same way.
DHFS installs no signal handler today, and Python's default SIGTERM ends the process outright, so no `finally` runs, including the multipart abort at `core/interrogator.py:800-803`: a stopped instance already leaves an orphaned upload behind.

The cost is one file per stopped instance, delayed by at most one lease, 22 minutes.
Nothing else stalls, because every other file stays claimable.
A mass event, such as every instance of a hub restarting, frees all their files within the same 22 minutes.

#### A stuck but live instance parks one file until the hold cap

An instance whose interrogation hangs while its renewal task keeps running holds its file until `max_lease_hold_seconds`, 72 hours by default.
Renewals carry no progress, so FIS cannot tell this instance from one working on a very large file.

#### More requests against FIS

One file per claim plus immediate re-polling turns one GET per batch of work into one GET per file.
Draining a thousand files across four instances means a thousand claims rather than a few hundred.
FIS already takes one report POST per file, so this is a change in degree, not in kind, but it is the first time the claim endpoint sees that volume.
Renewals add one POST every 4 minutes for each instance working on a file, which is small next to the claims.

#### A success report that returned an error now waits a lease

When `report_success` catches a `CentralAPIError`, DHFS deliberately leaves the file alone rather than re-interrogating it with a different secret.
That wait used to be one poll interval; it is now one lease, 22 minutes, since DHFS stops renewing once it has sent the report.

#### The cleanup race widens

Between `complete_upload` and FIS accepting the report, the re-encrypted object is unknown to FIS, so `check_if_removable` answers `True` and a concurrent cleanup run deletes it.
One instance exposes one object at a time; several instances expose several.
The optional minimum object age in `S3Cleaner` bounds this.

#### A late report for a cancelled file is still accepted

`handle_interrogation_report` has no state guard, so a success report arriving after a cancellation still publishes `interrogation_success`.
This is existing behaviour and leases do not change it, but more instances make the window easier to hit.

### Rollout

hexkit ships `update_first` first, in a release that FIS then requires.
FIS ships next.
Leases apply to every caller, so a DHFS that predates this epic keeps working; it never releases a file and waits out the lease on inconclusive ones.
It also never renews, so its lease expires after 22 minutes on any longer file.
With one instance per hub, no other instance claims the file in the meantime, so nothing changes for that hub.
A hub must not raise `replicaCount` before it runs a DHFS that renews, or its instances duplicate every file that takes longer than one lease.

Raise `dhfs_version_constraint` only after the hubs have upgraded, in a later release.
Raising it together with the feature is a flag day: a hub still on the old image gets 426, which DHFS turns into a `CriticalError`.
`run_interrogator` then returns, and the container crash-loops with no interrogation until that hub upgrades.
The same happens to the old pods during each hub's own rolling update.

### Route naming and generated docs

The claim stays on the GET ([ADR-0048](../adrs/adr-0048-dhfs-instances-coordinate-through-file-leases.md)).
Give the route a summary and docstring that say it claims rather than lists, rename `get_files_not_yet_interrogated` to match, and regenerate `services/fis/openapi.yaml`, `config_schema.json`, `example_config.yaml` and the README config block with `just service-docs`.
The three settings also go into `services/fis/dev_config.yaml` and `tests_fis/fixtures/test_config.yaml` by hand.

### Testing

Existing tests that change:

- `tests_fis/unit/test_core.py:340` `test_get_files_not_yet_interrogated` calls the method four times and expects the same files back.
  Rewrite it: the semantics are what changed.
- `tests_fis/unit/test_api.py:120` `test_list_uploads` inserts five files and expects five back, so it breaks once a claim serves one.
- `tests_fis/unit/test_core.py:282` `test_process_file_upload_requeue` must gain assertions on the four reset fields.
- Every DHFS test that takes the inconclusive path, once DHFS calls release: `CentralApiMock` raises `NotMockedError` for an unrouted path, so the mock needs a release route, and a renew route for the new renewal tests.
  Affected: `test_interrogator.py:254`, `:368`, `:701`, `:812`.

New unit tests, on the `rig` fixture, with the clock frozen rather than slept through:

- A claim serves and leases one file, a second claim returns none, and a claim after the lease expires serves it again.
- Never-claimed files are served before expired ones.
- A renewal by the holder extends the lease from now, keeps `times_claimed`, `claimed_at` and `state_updated`, and also succeeds after expiry when no other instance has claimed the file.
- A renewal from another instance, for a file that is no longer waiting, or past `max_lease_hold_seconds` returns 409 and changes nothing.
- A renewal after a release returns 409, because the release cleared `leased_by`.
- Release applies the backoff, the backoff cap holds, and a repeated release changes nothing and logs no warning.
- Renewing or releasing a file that belongs to another storage alias is rejected.
- A cancelled event for a leased file does not resurrect it, and the file is not served again.
- A claim over a collection that holds a `leased_until=None` document, which catches the in-memory DAO's `$lt` behaviour.

New integration tests, on `JointFixture` with the Mongo testcontainer, since the in-memory DAO cannot prove these:

- Two concurrent claims through `asyncio.gather` return disjoint sets whose union is everything available.
  Only this test proves that the claim is atomic in MongoDB.
- A renewal and a claim racing on an expired lease: exactly one of them wins.
- The claim filter matches a document inserted without `leased_until` at all, which proves no migration is needed.
- `explain()` on the claim query does not collection-scan.
  Assert the absence of a COLLSCAN rather than a single clean IXSCAN: `$or` plans as a SUBPLAN over one index scan per branch, with a blocking SORT on top.

New hexkit tests, for the MongoDB provider and the in-memory DAO alike:

- `update_first` respects the filter and the sort, changes only the given fields, applies `$inc`, and raises `NoHitsFoundError` when nothing matches.
- A plain value of the wrong type is rejected before anything is written.
- Concurrent calls against MongoDB return different resources.
- `DaoPublisher.update_first` publishes the returned document.

New DHFS tests:

- A round that processed a file polls again without sleeping, and a round that claimed nothing sleeps.
  Test the decision, not the wall clock.
- A response holding more than one file is still processed in full, which guards the untouched loop.
- The claimant ID stays the same for every claim, renewal and release of one process, and differs between two processes.
- Release is called for an inconclusive file, and for a conclusive one only when `report_failure` did not land; a failing release neither masks the original error nor stops the service.
- The renewal task renews while a file is in work and stops before the report.
  Drive it with a shortened interval or a fake clock, not the wall clock.
- A renewal refused with a 409 cancels the interrogation, aborts the multipart upload and releases the file.
- A renewal that fails with a connection error leaves the interrogation running.
- A release from an instance that no longer holds the lease leaves the lease untouched, and logs the warning.

## Human Resource/Time Estimation

Number of sprints required: 1

Number of developers required: 1 + LLM
