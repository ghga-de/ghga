# Upload Box Prioritization for Re-encryption (Shoebill)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the [Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline

DHFS re-encrypts files in whatever order FIS returns them, and FIS returns them in no defined order.
This epic lets a data steward rank research data upload boxes through RS, so that DHFS re-encrypts all files of a higher-ranked box before any file of a lower-ranked one.
Files in unranked boxes come after all files in ranked boxes, with no order among them.

RS stores the ranking as one list and publishes it through the outbox.
FIS consumes it, and its `GET /storages/{storage_alias}/uploads` endpoint returns the waiting files sorted by rank.
DHFS processes them in that order, and asks again right after a batch, instead of waiting for the next poll interval.

### Included/Required

- **RS** must store the priority list as a single document, holding an ordered list of entries and a `version` counter.
  Each entry holds the research data upload box ID and its file upload box ID, because data stewards rank research data upload boxes and FIS knows only file upload boxes.
  Index 0 is the highest priority.
- RS must expose the list to data stewards through a read and a replace endpoint (see [API definitions](#api-definitions)).
  The replace endpoint must reject a request whose `version` does not match the stored one, so that two stewards editing at the same time cannot overwrite each other unnoticed.
- RS must reject a list with duplicate boxes, unknown boxes, or boxes in a state that cannot receive files.
- RS must remove a box from the list when the box is deleted, archived, or otherwise reaches a state where it can no longer receive files.
  Each removal increments `version`.
- RS must publish the document through the outbox (`MongoKafkaDaoPublisherFactory`), with a fixed key on a compacted topic, so a FIS instance that starts later still receives the current list.
- **ghga-event-schemas** must define the event payload schema and a config class for the new topic.
- **FIS** must consume the priority events and store the list, ignoring any event whose `version` is not higher than the stored one.
- FIS must store `box_id` (the file upload box ID) on each file.
  It is already part of the `FileUpload` event, and FIS currently drops it.
  The field is optional with default `None`, because files stored before this epic lack it until the backfill below.
- FIS must fill in a missing `box_id` when it receives a `FileUpload` event for a file it already has, even if the event is not newer than the stored file.
  This branch lets a UCS republish backfill the field (see [Rollout](#rollout)).
- FIS must sort the waiting files with a MongoDB aggregation, as described in [Sorting the waiting files](#sorting-the-waiting-files).
  It still returns all waiting files of the storage alias.
- **DHFS** must process the files in the order FIS returns them.
  It does so today; this epic makes the order a requirement.
- DHFS must skip the `min_run_interval_seconds` wait after a round in which it concluded at least one file, whether it succeeded or reported a failure.
  It must still wait after a round in which FIS returned no file, or every file ended with an `InconclusiveError`.
- **Testbed** must cover the feature end to end, as described in [Testbed](#testbed).

### Optional

- RS may expose each box's position in the list on the research data upload box responses, so a client can show it without a second request.
- The testbed may assert the order in which DHFS interrogates files, if that can be made deterministic (see [Testbed](#testbed)).

### Not included

- Data Portal UI for viewing and editing the list.
  Until it exists, data stewards use the RS endpoints directly.
- Changing priority does not interrupt a batch DHFS is already processing.
  The new order applies from the next batch.
- Changing how many files FIS returns per request.
  Epic 94 (Leafcutter Ant) switches FIS to single-file responses, together with the changes that switch requires.
- No order within a box, and no order among unranked boxes.
  Files of the same rank are ordered by `_id` only, so that the result is deterministic.
- Running more than one DHFS instance per storage alias.
  FIS has no claim mechanism, so two instances would receive and process the same file.
  Epic 94 (Leafcutter Ant) adds what multi-instance operation needs.
- Prioritizing individual files.
- A priority list per storage alias.
  The list is global, and FIS filters by storage alias before ranking, so each Data Hub sees the global order restricted to its own files.

## API Definitions

### RESTful/Synchronous

RS, data steward role required:

- `GET /upload-box-priority`: return the current priority list.
- `PUT /upload-box-priority`: replace the priority list.
  The body holds `version` (the version the steward edited) and `box_ids`, the ordered research data upload box IDs.
  RS resolves each file upload box ID itself.
  It returns `409 Conflict` if `version` is stale, and `422` if the list fails validation.

FIS, changed:

- `GET /storages/{storage_alias}/uploads`: the response holds the same files as before, sorted by rank.
  The response schema does not change.

### Payload Schemas for Events

The outbox publishes the stored document on a new topic, e.g. `upload-box-priority`, keyed by the fixed document ID.
The event types are the outbox's `upserted` and `deleted`.

```json
{
  "id": "global",
  "version": 7,
  "entries": [
    {
      "research_data_upload_box_id": "4f0b3c1e-8a9d-4b7e-9c2a-1d3e5f7a9b0c",
      "file_upload_box_id": "a1c2e3f4-5b6d-4e8f-9a0b-1c2d3e4f5a6b"
    },
    {
      "research_data_upload_box_id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
      "file_upload_box_id": "0e1f2a3b-4c5d-4e6f-8a7b-9c0d1e2f3a4b"
    }
  ]
}
```

FIS reads only `version` and `entries[].file_upload_box_id`.

## Additional Implementation Details

### Why one list

The alternative was a rank field on each research data upload box, propagated to FIS through the existing box events.
Moving one box then rewrites the rank of every box between its old and new position, and readers can see a half-updated order, since MongoDB updates several documents without a transaction.
A single document changes in one write, carries the full state in one event, and lets consumers apply events idempotently.

### Sorting the waiting files

FIS cannot run this through the hexkit DAO protocol, which has no aggregation.
Add an outbound port, e.g. `WaitingFileFinderPort`, and a MongoDB adapter that uses `ConfiguredMongoClient` directly.
`services/mass/src/mass/adapters/outbound/aggregator.py` and `services/ucs/src/ucs/adapters/outbound/box_stats.py` follow the same pattern.

```python
pipeline = [
    {"$match": {"storage_alias": storage_alias, "state": "inbox", "interrogated": False}},
    {"$lookup": {
        "from": priority_collection_name,
        "pipeline": [{"$match": {"_id": PRIORITY_DOC_ID}}, {"$project": {"_id": 0, "entries": 1}}],
        "as": "priority",
    }},
    {"$set": {"rank": {"$indexOfArray": [
        {"$ifNull": [{"$first": "$priority.entries.file_upload_box_id"}, []]},
        "$box_id",
    ]}}},
    {"$set": {"unprioritized": {"$eq": ["$rank", -1]}}},
    {"$sort": {"unprioritized": 1, "rank": 1, "_id": 1}},
    {"$project": {"priority": 0, "rank": 0, "unprioritized": 0}},
]
```

- The `$lookup` does not depend on the file document, so MongoDB runs it once per query.
- `$indexOfArray` compares BSON types.
  If `file_upload_box_id` and `box_id` are stored with different types, such as a binary UUID and a string, every file counts as unprioritized and no error occurs.
  A test must cover this with both values written through the hexkit DAOs.
- The adapter must map `_id` back to `id` itself, and read both collection names from the config the DAOs use.
- Sorting the full list in Python after a DAO query would perform about the same while FIS returns every waiting file.
  The aggregation is chosen because epic 94 adds `$limit: 1` to it, so that only one document crosses the network and is validated per request.

### DHFS loop

`Interrogator.interrogate_new_files()` processes the files of a batch one after another, and `run_interrogator()` in `services/datahub-file-service/src/dhfs/main.py` waits for the rest of `min_run_interval_seconds` after every round.
`interrogate_new_files()` must tell the caller whether it concluded at least one file, and `run_interrogator()` must skip the wait if it did.

An `InconclusiveError` leaves the file uninterrogated in FIS, so the next request returns it again.
Waiting after a round in which every file was inconclusive keeps DHFS from requesting the same batch in a tight loop.
A file that stays inconclusive does not block the rest of its batch, as today.

### Rollout

1. Release ghga-event-schemas with the new schema and config.
2. Deploy RS and FIS.
   FIS ranks nothing until the first priority event arrives, so the order of these two does not matter.
3. Run `ucs publish-events --all` to republish every file upload.
   FIS fills in `box_id` for the files it already stores.
   Only files still waiting for interrogation need it, since the selection reads no other files.
4. Deploy DHFS.
   A DHFS from before this epic already processes files in the order FIS returns them, so prioritization works before this step; DHFS only keeps waiting between batches until then.

No database migration is needed: `box_id` defaults to `None`, and the republish fills it in.

### Testing

- FIS: the aggregation over ranked, unranked and missing-priority cases, against `MongoDbFixture`.
  `InMemDao` cannot run the pipeline, so unit tests of the interrogation handler use a fake of the new port.
- FIS: stale priority events are ignored; a republished `FileUpload` event fills in a missing `box_id` and changes nothing else.
- RS: version conflict, validation errors, and removal of a box from the list when it is archived or deleted.
- DHFS: the wait is skipped after a round that concluded at least one file, and kept after an empty response or a round in which every file was inconclusive.

### Testbed

The upload features (`testbed/features/20x_*.feature`) go through RS and read FIS's MongoDB directly, so they can check every step up to FIS.

- Add a feature, e.g. `204_upload_box_priority.feature`, in which the data steward reads the list, replaces it, and gets `409` for a stale `version` and `422` for an unknown or duplicate box.
- After a replace, assert that FIS's priority document reaches the new `version` within a timeout.
- Assert that FIS stores `box_id` on files uploaded during the run.
- Extend the archival scenario in `203_upload_completed.feature` to assert that the archived box is no longer in the list.

Asserting the interrogation order is optional.
DHFS polls on its own schedule and interrogates a file soon after upload, so files of two boxes are rarely waiting at the same time.
A deterministic check needs at least two boxes in one storage, with their files uploaded while DHFS is idle, for example by setting a long `min_run_interval_seconds` for the run.
The FIS integration tests cover the sort order in any case.

## Human Resource/Time Estimation

Number of sprints required: 1

Number of developers required: 1
