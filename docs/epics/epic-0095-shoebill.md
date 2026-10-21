# Upload Box Prioritization for Re-encryption (Shoebill)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the [Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline

DHFS re-encrypts files in whatever order FIS returns them, and FIS returns them in no defined order.
This epic lets a data steward rank research data upload boxes in the Data Portal, so that DHFS re-encrypts all files of a higher-ranked box before any file of a lower-ranked one.
Files in unranked boxes come after all files in ranked boxes, with no order among them.

RS stores the box ranking as one list and publishes it through the outbox.
FIS consumes it, and its existing `GET /storages/{storage_alias}/uploads` endpoint returns at most five waiting files, sorted by rank.
DHFS processes them in that order, and asks again right after a batch, instead of waiting for the next poll interval.

### Included/Required

- **RS** must store the priority list as a single document, holding an ordered list of entries and a `version` counter.
  Each entry holds the research data upload box ID and its file upload box ID, because data stewards rank research data upload boxes and FIS knows only file upload boxes.
  Index 0 is the highest priority.
- RS must expose the list to data stewards through a read and a replace endpoint (see [API definitions](#api-definitions)).
  The replace endpoint must reject a request whose `version` does not match the stored one, so that two stewards editing at the same time cannot overwrite each other unnoticed.
  Each saved edit increments the `version` counter.
- RS must reject a list with duplicate boxes, unknown boxes, or boxes that are already `"archived"`.
- RS must remove a box from the list when the box is deleted or archived.
  Each removal increments `version` (reiterating that from a few lines above, just to be clear).
- RS must publish the document through the outbox (`MongoKafkaDaoPublisherFactory`), with a fixed key on a compacted topic, so a FIS instance that starts later still receives the current list.
- **ghga-event-schemas** must define the payload schema for the priority list's event, as well as a config class for the new topic.
- **FIS** must consume the priority events and store the list, ignoring any event whose `version` is not higher than the stored one.
- FIS must store `box_id` (the file upload box ID) on each file.
  It is already part of the `FileUpload` event, and FIS currently drops it.
  The field is optional with default `None`, because files stored before this epic lack it until the backfill below.
- FIS must fill in a missing `box_id` when it receives a `FileUpload` event for a file it already has, even if the event is not newer than the stored file.
  This branch lets a UCS republish backfill the field (see [Rollout](#rollout)).
- FIS must sort not-yet-interrogated ("waiting") files with a MongoDB aggregation, as described in [Sorting the waiting files](#sorting-the-waiting-files).
- FIS must return at most five files per request, set by a hardcoded constant, e.g. `MAX_FILES_PER_REQUEST = 5`, not a config setting.
  At hundreds of thousands of waiting files, an unbounded response would move every file from MongoDB to FIS and on to DHFS on each poll.
- **DHFS** must process the files in the order FIS returns them.
  It already does so today; this just reiterates that requirement.
- DHFS must skip the `min_run_interval_seconds` wait after a round in which it concluded at least one file, whether it succeeded or reported a failure.
  It must still wait after a round in which FIS returned no file, or every file ended with an `InconclusiveError`.
- **Data Portal** must offer a page where data stewards view and edit the list, as described in [Data Portal page](#data-portal-page).
- **Testbed** must cover the feature end to end, as described in [Testbed](#testbed).

### Optional

- RS may expose each box's position in the list on the research data upload box responses, so a client can show it without a second request.
- The testbed may assert the order in which DHFS interrogates files, if that can be made deterministic (see [Testbed](#testbed)).

### Not included

- Changing priority does not interrupt a batch DHFS is already processing.
  The new order applies from the next batch.
- Single-file responses.
  Epic 94 (Leafcutter Ant) lowers the cap to one file, together with the changes that requires.
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

RS gets two endpoints on a new router.
Both require the Data Steward role through `StewardAuthContext`, like the existing steward-only RS endpoints, and both answer `401` without a valid token and `403` without the role.

- `GET /upload-box-priority`: return the current priority list.
  - `200`: the stored document, with `version` and `entries` as in the [event payload](#payload-schemas-for-events).
    If no list has been saved yet, the body is `{"version": 0, "entries": []}`, so the Data Portal needs no special case.
- `PUT /upload-box-priority`: replace the priority list.
  The body holds `version`, the version the steward edited, and `box_ids`, the ordered research data upload box IDs.
  RS resolves each file upload box ID itself.
  - `200`: the stored document with its new `version`.
    It returns the document instead of `204`, which the other RS write endpoints use, so the Data Portal can take the new `version` without a second request.
  - `404`: a box ID that does not exist.
  - `409`: either `version` does not match the stored one, or a box is archived.
    Each case gets its own `HttpCustomExceptionBase` subclass and `exception_id`, so the Data Portal can tell them apart and offer a reload only for the version conflict.
  - `422`: a malformed body, or a box ID that appears twice.

FIS keeps its paths and response models unchanged.
The list from `GET /storages/{storage_alias}/uploads` now holds at most five files, and its order, undefined until now, follows the rank, which DHFS relies on (see [Sorting the waiting files](#sorting-the-waiting-files)).

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

The main alternative was a rank field on each research data upload box, propagated to FIS through the existing box events.
Moving one box then rewrites the rank of every box between its old and new position, and readers can see a half-updated order, since MongoDB updates several documents without a transaction.
A single document changes in one write, carries the full state in one event, and lets consumers apply events idempotently.

Another alternative was to relay requests from RS to UCS and update all FileUploads within each affected box.
However, this is too clumsy and heavy-handed to be seriously considered.

### Sorting the waiting files

FIS should not use the hexkit DAO protocol to sift through the waiting files.
We need to perform a `$match` on `state` and `storage_alias`, try to find the box ID's rank in the priority collection (if applicable), and rank file results accordingly.
This can be done partially with a DAO and partially in memory, but requires either A) loading all waiting files into memory and ranking them there, or B) performing multiple queries (e.g. one for prioritized boxes and one for unprioritized boxes, or similar).
As the number of waiting files grows, so too does the amount of data we would have to pull back from the DB only to drop 99% of it.
Instead, we should add an outbound port, e.g. `InterrogationQueuePort`, and a MongoDB adapter that uses `ConfiguredMongoClient` directly, and allow the DB to perform the filtering and sorting.
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
    {"$limit": MAX_FILES_PER_REQUEST},
    {"$project": {"priority": 0, "rank": 0, "unprioritized": 0}},
]
```

- The `$lookup` does not depend on the file document, so MongoDB runs it once per query.
- `$indexOfArray` compares BSON types.
  If `file_upload_box_id` and `box_id` are stored with different types, such as a binary UUID and a string, every file counts as unprioritized and no error occurs.
  We could add a test to cover this with both values written through the hexkit DAOs, but it's not necessary.
  The most likely reason this kind of mixup would happen is a future Migration that writes a string directly to the DB.
  However, in that case it should be caught by model validation.
- The adapter must map `_id` back to `id` itself.
  Define both collection names as constants, as UCS does with `FILE_UPLOADS_COLLECTION`, and pass them to the DAO factory and the adapter alike.
- The aggregation is chosen because of the `$limit`.
  MongoDB combines it with the `$sort` and keeps only the top five documents in memory, so five documents cross the network and are validated per request.
  Sorting in Python after a DAO query would fetch and validate every waiting file first.
  Epic 94 lowers the limit to one.

### DHFS loop

`Interrogator.interrogate_new_files()` processes the files of a batch one after another, and `run_interrogator()` in `services/datahub-file-service/src/dhfs/main.py` waits for the rest of `min_run_interval_seconds` after every round.
`interrogate_new_files()` must tell the caller whether it concluded at least one file, and `run_interrogator()` must skip the wait if it did.

An `InconclusiveError` leaves the file uninterrogated in FIS, so the next request returns it again.
Waiting after a round in which every file was inconclusive keeps DHFS from requesting the same batch in a tight loop.
A file that stays inconclusive does not block the rest of its batch, as today.
It does take one of the five places in every batch, since it keeps its rank.
Five such files in the highest ranks fill every batch and stall interrogation for that storage alias, until a file stops failing or a data steward moves its box.
Epic 94's release backoff removes this; until then, it is a known limitation.

### Data Portal page

Add a page at `/upload-box-manager/priority`, linked from the Upload Box Manager and guarded like it by `guardDataSteward()`; register the route before `:id`, which would otherwise match it.
The page shows two panels: the ranked boxes in priority order on the left, and the remaining boxes on the right, with a search field and an **Add** button per box.
Archived boxes appear in neither panel.
Each ranked row shows its rank, title, storage alias, state and file count, and the steward re-ranks a row by dragging it (Angular CDK `cdkDropList`, already a dependency) or with move up, move down, move to top and remove buttons for keyboard users.
While a row is dragged, a bar in the gap between two rows marks where it will land; after a move, the row stays highlighted for about 1.5 seconds so the eye can find it again.
Edits stay local until **Save order** sends `PUT /upload-box-priority` with the version the page loaded; **Discard changes** restores the saved order.
On a version conflict (`409` with the version conflict's `exception_id`) the page says another steward saved a newer order and offers to reload it; the steward then repeats their edit.
On a `409` for an archived box, the page reloads the list of boxes, since that box has left the list in the meantime.

```text
Upload Box Manager / Re-encryption Priority
Manage Box Priority                       Version 7  [Discard changes] [Save order]
Files in ranked boxes are re-encrypted first, highest rank first.

| You have unsaved changes to the priority order.                                 |

+- Priority order ---------------------------------+ +- Unranked boxes ------------+
| :: (1) Box B                    [^] [v] [^^] [x] | | [Search by title, storage ] |
|        Tuebingen - locked - 8 files              | |                             |
|==================================================| | Box C               [Add]   |
| :: (2) Box A                    [^] [v] [^^] [x] | |   Heidelberg - 35 files     |
|        Heidelberg - open - 120 files             | | Box E               [Add]   |
|                                                  | |   Tuebingen - 12 files      |
| :: (3) Box D                    [^] [v] [^^] [x] | |                             |
|        Koeln - open - 60 files                   | | Archived boxes are not      |
|                                                  | | listed.                     |
| Drag a row or use the buttons to change its rank.| |                             |
+--------------------------------------------------+ +-----------------------------+

::    drag handle          ===  drop position while dragging
[^] [v]  move up, down     [^^] move to top          [x] remove from priority
```

### Rollout

ghga-event-schemas needs no release of its own: the service images build it from source ([releases](../releases.md)).

1. Deploy DHFS.
   The new DHFS works against a FIS from before this epic, because it skips the wait only after concluding a file.
   It goes first because of the cap: a DHFS from before this epic waits out `min_run_interval_seconds` after every batch, so against the new FIS it processes at most five files per interval, about 7,200 files per day at the default of 60 seconds.
2. Deploy RS and FIS.
   FIS ranks nothing until the first priority event arrives, so the order of these two does not matter.
3. Run `ucs publish-events --all` to republish every file upload.
   FIS fills in `box_id` for the files it already stores.
   Only files still waiting for interrogation need it, since the selection reads no other files.
4. Deploy the Data Portal.
   It needs the RS endpoints from step 2.

No database migration is needed: `box_id` defaults to `None`, and the republish fills it in.

### Testing

- FIS: the aggregation over ranked, unranked and missing-priority cases, against `MongoDbFixture`.
  With more than five waiting files, it returns exactly the five highest-ranked.
  `InMemDao` cannot run the pipeline, so unit tests of the interrogation handler use a fake of the new port.
- FIS: stale priority events are ignored; a republished `FileUpload` event fills in a missing `box_id` and changes nothing else.
- RS: version conflict, validation errors, and removal of a box from the list when it is archived or deleted.
- DHFS: the wait is skipped after a round that concluded at least one file, and kept after an empty response or a round in which every file was inconclusive.
- Data Portal: reordering by drag and by buttons, adding and removing boxes, discard, and the `409` reload path, against a mocked RS.

### Testbed

The upload features (`testbed/features/20x_*.feature`) go through RS and read FIS's MongoDB directly, so they can check every step up to FIS.

- Add a feature, e.g. `204_upload_box_priority.feature`, in which the data steward reads the list, replaces it, and gets `409` for a stale `version`, `404` for an unknown box and `422` for a duplicate box.
- After a replace, assert that FIS's priority document reaches the new `version` within a timeout.
- Assert that FIS stores `box_id` on files uploaded during the run.
- Extend the archival scenario in `203_upload_completed.feature` to assert that the archived box is no longer in the list.

Asserting the interrogation order is optional.
DHFS polls on its own schedule and interrogates a file soon after upload, so files of two boxes are rarely waiting at the same time.
A deterministic check needs at least two boxes in one storage, with their files uploaded while DHFS is idle, for example by setting a long `min_run_interval_seconds` for the run.
The FIS integration tests cover the sort order in any case.

## Human Resource/Time Estimation

Number of sprints required: 1

Number of developers required: 2
