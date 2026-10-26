# Metadata & File Journeys — Current-State Reference

> **Purpose.**
> A durable, implementation-level map of how metadata and files flow through the GHGA platform **as built today** (LinkML + offline metadata management via `ghga-datasteward-kit`).
> It is written for both humans and future coding agents: read it before touching submission, accession, upload, file-mapping, or metadata-serving code so you start from ground truth rather than re-deriving it.
>
> **Status.**
> Describes the *current* system.
> The planned early "data lifecycle" changes are tracked separately in [`docs/epics/epic-0093-giraffe.md`](../epics/epic-0093-giraffe.md); where this document notes an invariant the feature will change, it links there.
>
> File:line anchors are provided as entry points.
> They drift — treat them as "start looking here", not as guarantees.
>
> **The same flows as a diagram.** [kafka-cascade-map.html](kafka-cascade-map.html) draws the event cascades these journeys describe, one tree per entrypoint; [kafka-cascade-map.md](kafka-cascade-map.md) says how to open and maintain it.

---

## 1. Component map

| Component | Kind | Owns / does |
|---|---|---|
| `tools/ghga-datasteward-kit` (**dskit**) | CLI | Offline driver: transpile xlsx→json, `submit` (mint accessions), `amend` (extend a flat-accessioned submission, keeping its accessions), `transform` (run workflow), `load` (push artifacts). `files delete-file` purges a file from all file services. |
| `libs/metldata` | library + deployable API | The engine behind dskit. Submission registry, accession registry, transformation workflows, and the **combined loader + artifacts-query API** (`metldata run-api`). |
| `libs/ghga-event-schemas` | library | Shared Kafka event/payload models (upload boxes, file uploads, searchable resources, dataset overviews, artifacts). |
| `services/ghga-registry-service` (**RS**) | service | A **new, forward-looking** service (built with the upcoming metadata services in mind). Owns `ResearchDataUploadBox` (RDUB), `FileAccession` mapping records, and a first-class **`Study`** entity that already models lifecycle (`DRAFT`/`ARCHIVED` status, approval provenance, and a `superseded_by_id` deprecation link). Steward-facing box + mapping + grants API. Its Study/FileAccession state is *currently populated* by an interim bridge consuming metldata's `SearchableResource` events — **that ingestion path is the legacy part, not the entity**. |
| `services/ucs` | service | Owns `FileUploadBox` (FUB) + `FileUpload` records + the S3 inbox multipart uploads. One RDUB wraps exactly one FUB. |
| `services/work-package-service` (**WPS**) | service | Issues per-file work-order tokens; tracks datasets/files a user may download. |
| `services/fis` | service | File **interrogation** coordinator: serves work lists to data hubs, ingests interrogation reports, deposits secrets with EKSS, emits interrogation events. |
| `services/datahub-file-service` (DHFS) | service | Performs interrogation / re-encryption at the data hub. |
| `services/ekss` | service | Crypt4GH secret store (store / get-envelope / delete). |
| `services/ifrs` | service | Registers interrogated files permanently; emits `FileInternallyRegistered`. |
| `services/dcs` | service | Makes registered files downloadable. |
| `services/mass` | service | Metadata **search** over searchable resources (dataset-centric). |
| `services/dataset-information-service` (DINS) | service | Per-dataset file information for the portal. |
| `services/reverse-transpiler-service` (RTS) | service | Renders accessioned metadata back to an xlsx workbook, served per study. |
| `services/access-request-service` (ARS) | service | Access requests / grants against dataset accessions. |
| `tools/ghga-connector` | CLI | Uploader client for the **new** box path (`ubox`, `batch-upload`). |
| `frontend/data-portal` | Angular app | Browse/search datasets, dataset & study detail pages, steward upload-box + mapping UI. |

Not part of the metadata world today: the future schemapack services (resource-registry, resource-search) do not exist yet, and `em-transformation-service` is developed upstream against the metldata 5.x schemapack line — it was removed from this monorepo until the workspace moves off the integrated metldata 4.x line (see `scripts/migration/repos.tsv`).

---

## 2. Journey A — Metadata submission (offline: dskit + metldata)

Canonical sequence, with a [metadata config](../../tools/ghga-datasteward-kit/metadata_config.md) and a [load config](../../tools/ghga-datasteward-kit/load_config.md):

1. `metadata generate-artifact-models` — build artifact models + `artifact_infos.json` from the LinkML model.

   ```bash
   ghga-datasteward-kit metadata generate-artifact-models --config-path metadata_config.yaml
   ```

2. `metadata transpile` — spreadsheet → JSON.
   Re-exported from `ghga_transpiler.cli.transpile`.
   **No schema validation here.**

   ```bash
   ghga-datasteward-kit metadata transpile metadata.xlsx metadata.json
   ```

3. `metadata submit` — validate + register a submission locally, mint accessions, publish a source event.
   For a submission with flat accessions that only gained files, `metadata amend --submission-id <id>` instead, which keeps them.

   ```bash
   ghga-datasteward-kit metadata submit --submission-title "<title>" \
       --submission-description "<description>" \
       --metadata-path metadata.json --config-path metadata_config.yaml
   ```

4. `metadata transform` — run the GHGA archive workflow → produce artifacts on disk.

   ```bash
   ghga-datasteward-kit metadata transform --config-path metadata_config.yaml
   ```

5. `load` (top-level, **not** `metadata load`) — POST artifacts to the loader API.

   ```bash
   ghga-datasteward-kit load --config-path loader_config.yaml
   ```

The test bed runs the same sequence against a deployment, in `testbed/steps/test_010_submit_metadata.py`, `test_011_transform_metadata.py` and `test_020_load_metadata.py`.

### The submission object & store

- `Submission` model: `libs/metldata/src/metldata/submission_registry/models.py:60`.
  Fields: `id` (UUID4), `title`, `description`, `content` (`{anchor_slot: {alias: instance}}`), `accession_map` (`{anchor_slot: {alias: accession}}`), `status_history`.
- Persisted as **one JSON file per submission** (`{id}.json`) — `submission_store.py:61`.
  Full-document overwrite each save; not event-sourced at the store layer.
- Registry ops (`submission_registry.py`): `init_submission` → `upsert_submission_content` (validates via metldata's own `MetadataValidator`, regenerates the accession map, publishes a source event) → `complete_submission`.
  **Only `PENDING`→`COMPLETED` is ever used.**
  `upsert_submission_content` refuses anything but `PENDING`, and nothing in metldata amends a completed submission.
  dskit does that itself (`ghga_datasteward_kit/amendment/`), driving `SubmissionStore`, `generate_accession_map` and `SourceEventPublisher` directly rather than through the registry — see Journey A's accession notes below.
- `SubmissionStatus` (`models.py:31`) *defines* `DEPRECATED_*`, `PUBLISHED`, `HIDDEN_*`, `EMPTIED_*`, `CANCELED`, `IN_REVIEW` — **none are ever set**.
  There is no replaces/replaced-by field and no versioning anywhere today. → [changed by the feature](../epics/epic-0093-giraffe.md).

### Accession generation (offline, random, study PIDs)

- Engine: `AccessionRegistry` in `accession_registry/accession_registry.py`.
  A study gets the PID `GHGA.YY.XXX.1`: `YY` is the two-digit UTC year, `XXX` three random RFC 4648 base32 characters, unique within the year.
  Only fresh lineages are minted; the version counter stays at `1` until predecessors can be declared → [changed by the feature](../epics/epic-0093-giraffe.md).
- A dataset gets `{study_pid}.DS.xxx`, unique within its study; every other entity gets `{study_pid}.{alias}`, with the alias normalized by `normalize_alias` in `metadata_utils.py`.
  It is stripped and lowercased, and every character other than `a–z`, `0–9`, `_` and `-` becomes `-`, so the accession is safe in URLs and file names and holds no further dot.
  The metadata and the accession map keep the alias as submitted.
  Which classes are the study and the dataset is set by `study_class_name` and `dataset_class_name` in the config.
- A random block is drawn up to 100 times; if every draw collides, one is picked from the blocks still unused, and `AccessionGenerationError` is raised when none is left.
- Aliases must hold ASCII characters only and be unique across all entities of a submission once normalized, checked by `MetadataValidator.check_aliases_are_ascii` and `check_alias_uniqueness` before anything is minted.
- Persisted in **one JSON file** (`accession_store.py`): `years` holds the minted `XXX` blocks per `YY`, and `legacy` holds the flat accessions (`GHGAS…`, `GHGAF…`), those minted before study PIDs and those dskit's `amend` mints.
  Dataset and alias accessions are not stored there: a dataset's `xxx` is drawn against the accessions its submission already holds, and an alias accession is unique once the study PID is.
  The file is an index; the submission store holds which accession belongs to which entity.
- Alias↔accession stability (`generate_accession_map` in `submission_registry/identifiers.py`): within one submission object, re-upserting the same alias **reuses** its accession; new aliases get new ones; dropped aliases fall out.
  `submit` always calls `init_submission` (fresh UUID, empty map), so a new `submit` run of the same aliases mints *fresh* accessions.
  **`dskit metadata amend --submission-id <id>` extends a submission accessioned in the flat scheme**, whose study accession is `GHGA`, one letter and 14 digits.
  A submission with a study PID is refused with `AccessionNotLegacyError`, so study PIDs are only ever minted by `submit`.
  It loads the completed submission, validates the new metadata against the model, and checks that no alias is repeated within its class; a flat accession holds no alias, so uniqueness across classes is not needed.
  It hands the stored map to `generate_accession_map` with dskit's `LegacyAccessionRegistry` (`amendment/legacy_accessioning.py`), which mints `prefix + 14 digits` for each new alias and registers it under `legacy`, so a flat accession is never given out twice.
  It writes the result back under the same ID and republishes the source event, so existing accessions survive and only new aliases are minted.
  Before writing, it reports the dropped, new and kept files of the five file classes, each with its count and up to 20 aliases.
  It asks for confirmation when files would be dropped or none kept, and refuses such an amendment when stdin is not a terminal, so a pipe cannot answer for a steward.
  The other classes follow the same alias matching without being reported; the study keeps its accession even under a new alias.
  A field changed on an already-accessioned resource is not an accession change at all — no report entry, no prompt, and the next `load` upserts that resource.
  Confining amendments to added files is an operational rule, not one the tool enforces.
  All of it lives in dskit (`ghga_datasteward_kit/amendment/`); metldata provides `generate_accession_map` and the `AccessionRegistry` that dskit subclasses.
  There is still no accession stability *across* submissions. → [changed by the feature](../epics/epic-0093-giraffe.md).

### The LinkML model (current testbed model)

- Root/tree class `Submission`; every entity class is a required, multivalued, `inlined_as_list` slot of it.
  **The model holds exactly one study per submission**: the `studies` slot has a minimum and maximum cardinality of 1, which metldata checks when it loads the model.
  The fixtures are therefore two submissions, `metadata_study_a.json` (`STUDY_A`) and `metadata_study_b.json` (`STUDY_B`).
- Entities reference each other **by alias** at submission time; `add_accessions` swaps aliases for accessions during transform.
- Study↔Dataset: `Dataset.study` is a **single** alias reference (`testbed/.../metadata_study_a.json`).
  Files (`ResearchDataFile`, `ProcessDataFile`, `*SupportingFile`) carry `alias`, a `name` (filename), a `dataset` ref, and an `ega_accession` slot.
  Study→datasets is *inferred* during transform (`Study<(study)Dataset`).
- **`studies[0]` assumption:** the loader derives a publishable artifact's `study_accession` from `content["studies"][0]["accession"]` (`libs/metldata/src/metldata/load/collect.py:91`) — a hard one-study-per-submission assumption. → [made a hard rule by the feature](../epics/epic-0093-giraffe.md).

### Transform artifacts

Workflow `builtin_workflows/ghga_archive.py:36`: normalize → **add_accessions** → embed_restricted → infer_multiway_references → merge_dataset_file_lists → remove_restricted_metadata → aggregate_stats → embed_public.
Artifacts produced: `added_accessions`, `embedded_restricted`, `resolved_restricted`, `resolved_public`, `embedded_public`, `stats_public`.
The **primary** queryable artifact/class is `embedded_public` / `EmbeddedDataset`.

---

## 3. Journey B — File upload, interrogation, archival

### Upload boxes

- Schemas (`libs/ghga-event-schemas/src/ghga_event_schemas/pydantic_.py`): `UploadBoxState = "open" | "locked" | "archived"` (:501); `ResearchDataUploadBox` (RS, :504); `FileUploadBox` (UCS, :619).
  One RDUB wraps one FUB.
- Box lifecycle transitions (`rs/constants.py:28`): `open ⇄ locked`, `locked → archived` (terminal).
  No `open→archived`, no un-archiving.
- Creation: `POST /upload-boxes` (steward-only) → `RDUBManager.create_research_data_upload_box` → calls UCS `POST /boxes` (guarded by a `CreateFileBoxWorkOrder` token) → inserts RDUB (`open`, v0).
- Uploader access = **upload grants** (`/upload-grants`, steward-managed, tie user+IVA+box+window) plus per-file **work-order tokens** issued by WPS and verified at each UCS file endpoint.
  `ghga-connector` (`ubox`/`batch-upload`) is the uploader client.

### File upload state machine (who owns each transition)

- `FileUploadState = "init" | "inbox" | "failed" | "cancelled" | "interrogated" | "awaiting_archival" | "archived"` (`pydantic_.py:540`).
  `FileUpload` (:551) carries `alias` (unique within box), checksums, sizes, `secret_id`, storage refs.
- **init** — UCS `initiate_file_upload` (starts S3 multipart; captures alias, sizes, part_size).
- **inbox** — UCS `complete_file_upload` (verifies ETag/size/checksums).
- UCS publishes the change → **FIS** ingests it as a `FileUnderInterrogation`.
- **DHFS** polls FIS `GET /storages/{alias}/uploads`, re-encrypts, POSTs an `InterrogationReport`.
- FIS on success deposits the Crypt4GH secret with **EKSS**, sets `interrogated`, emits `InterrogationSuccess`; on failure emits `InterrogationFailure`.
- **interrogated** — UCS consumes success (records `secret_id`, new object refs).
- **IFRS** consumes success → permanently registers → emits `FileInternallyRegistered`.
- **archived** — UCS consumes `FileInternallyRegistered`; **DCS** consumes it to enable download.

### Archival (today)

- Triggered by `PATCH /upload-boxes/{box_id}` `state:"archived"` (steward-only); only valid from `locked`.
- **Prerequisite (today):** `_check_archival_prerequisites` (`rdub_manager.py:314`) rejects archival unless **every file in the box already has an accession mapped**; UCS additionally rejects if any `init`/`inbox` file remains.
  On archival every file flips to `awaiting_archival`. → **[this coupling is inverted by the feature](../epics/epic-0093-giraffe.md)** — archival stops requiring mapping, and mapping starts requiring archival.
- After archival the box is **immutable**: accession maps, deletion, etc. are all rejected.
- **Retained after archival (important):** the RDUB, the FUB, and every `FileUpload` (alias, filename, checksums, sizes, accession) **remain stored and queryable** in both RS and UCS.
  `GET /upload-boxes/{box_id}/uploads` still works for archived boxes.
  This is what makes "select the boxes originally used" feasible later.

---

## 4. Journey C — File-to-metadata mapping (current, box-centric)

**Today the mapping is portal-driven and box-centric.**
The steward maps *metadata file accessions* → *upload-box file IDs*.

- Endpoint: `POST /upload-boxes/{box_id}/file-ids` (steward-only) → `RDUBManager.store_accession_map` (`rdub_manager.py:939`).
  Body: `{box_version, study_id, mapping: {accession → file_id}}`.
- Constraints enforced today:
  - box **not archived** (optimistic version lock on `box_version`);
  - **strict 1:1** — each file_id appears once; an accession already mapped elsewhere / to another study → `ConflictingAccessionError`. → **[relaxed to one file → many accessions by the feature](../epics/epic-0093-giraffe.md).**
  - **every active file in the box must be mapped** (no leftovers);
  - the accession must **already exist as an *unmapped* `FileAccession`** — those rows are pre-seeded by an **interim ingestion bridge** consuming metldata's `SearchableResource` events (`ResourceSubTranslator` → `LegacyResourceManager.upsert_resource` → `FileController.register_unmapped_accessions`; `rs/adapters/inbound/event_sub.py:65`, `rs/core/legacy_resources.py:109`, `rs/core/files.py:100`).
    The same bridge also inserts the embedded `Study` into RS's **forward-looking** `Study` store — but with *placeholder* values (forced `ARCHIVED` status, sentinel creator) because a searchable resource carries no lifecycle info.
    It is the **bridge** that is legacy (*"remove once this service owns studies"*), **not** the `Study` entity, which already models `DRAFT`/`ARCHIVED` status and `superseded_by_id`.
- Mapping produces a `FileAccession` (`pid` accession ↔ `file_id` ↔ `study_id`), persisted in the `fileAccessions` collection and emitted via outbox.
  Read back via `GET /studies/{study_id}/file-ids` (`{accession: file_id | null}`), `GET /studies?with_unmapped_files=true`, and `GET /upload-boxes/{box}/uploads` (`FileUploadWithAccession`).
- Portal (`frontend/data-portal/src/app/upload/features/upload-box-mapping/`): appears when the box is **locked**; steward picks a study + a `MappedField` (`alias | name`); auto-matches box file alias against the metadata file's `alias` or `name`, with manual overrides; then **submits the map and archives in one action** (`onConfirmAndArchive`).

---

## 5. Journey D — Load → serve → browse

### Load API

- metldata's **combined** app (`libs/metldata/src/metldata/combined.py`, run via `metldata run-api`) mounts the loader (`POST /rpc/load-artifacts`, bearer loader-token) + the artifacts query API.
  **Not** a `services/` microservice.
- `dskit load` collects artifacts from the local event store and POSTs `ArtifactResourceDict` (`{artifact_name: [{study_accession, artifact_name, content}]}`).
- The loader **diffs DB-vs-payload** (full-state reconciliation, no tombstones/versioning):
  - per-resource diff (`load/load.py:192`) → new/changed/removed resources;
  - whole-artifact diff for `publishable_artifacts` (`added_accessions`) keyed by `(artifact_name, study_accession)`.

### Events emitted (`load/event_publisher.py`) & consumers

| Event (topic / type) | Payload | Consumers |
|---|---|---|
| `searchable_resources` upsert/delete | `SearchableResource` / `SearchableResourceInfo` | **MASS** (search index); **RS** (interim bridge seeding its forward-looking Study + unmapped FileAccession state) |
| `metadata_datasets` created/deleted | `MetadataDatasetOverview` / `MetadataDatasetID` | **WPS** (`register_dataset`); **DINS** (`register_dataset_information`); claims/auth (deletion) |
| `artifacts` upserted/deleted | `Artifact` / `ArtifactTag` | **RTS** (filters `added_accessions:` key prefix) |

Resource/dataset events fire **only for the primary dataset source** (`embedded_public` / `EmbeddedDataset`).
`MetadataDatasetOverview` is assembled from the embedded dataset content (title, description, DAC alias/email, file list).
Downstream consumers are idempotent about missing targets.

### Search (MASS)

- `GET /search?class_name=...&filter_by=...&value=...&query=...&skip=&limit=` and `GET /search-options`.
  Searchable classes are **config-driven**; the portal searches `class_name=EmbeddedDataset` only — **there is no Study search class**.
  Upsert/delete are purely event-driven; MASS does no diffing. → **[search hiding of superseded datasets is added by the feature](../epics/epic-0093-giraffe.md).**

### Portal (`frontend/data-portal/src/app/app-routes.ts`)

- `browse` (datasets, `class_name=EmbeddedDataset`), `dataset/:id`, `study/:id` (and `s/:id`).
- Dataset detail: `GET {metldata}/artifacts/embedded_public/classes/EmbeddedDataset/resources/{id}`; summary from `stats_public/.../DatasetStats/...`; study detail from `embedded_public/.../Study/...`; file info from DINS `GET /dataset_information/{id}`; metadata xlsx from RTS `GET /studies/{accession}`.
- `loadStudiesMap()` is an explicitly temporary fan-out (EmbeddedDataset → stats → Study) labeled *"until we switch to a study-based backend"*.
- **No versioning/deprecation UI anywhere** — re-load silently replaces. → **[the "updated version available" hint is added by the feature](../epics/epic-0093-giraffe.md).**

---

## 6. Journey E — Download (brief)

dataset accession → **ARS** access request/grant (`dataset_id: Accession`) → **WPS** work package

- per-file download work-order token → **ghga-connector** → **DCS** `GET /objects/{id}` (+ `/envelopes`), keys via **EKSS**.
  Dataset accessions live on ARS requests/grants, the WPS dataset collection (from `MetadataDatasetOverview`), and DINS.

---

## 7. Invariants the data-lifecycle feature will change

Collected here as a checklist; details in [`docs/epics/epic-0093-giraffe.md`](../epics/epic-0093-giraffe.md).

1. **Accession format** was `{prefix}{14 random digits}` with no structure/version → done: `submit` mints `GHGA.YY.XXX.1` for studies, `{study_pid}.{alias}` for child entities and `{study_pid}.DS.xxx` for datasets (see [accession generation](#accession-generation-offline-random-study-pids)); only `amend` still mints flat accessions, for submissions accessioned before.
2. **No cross-submission stability / no versioning** → studies gain a stable lineage (`GHGA.YY.XXX`) with an incrementing version; study-level supersession is **declared by the steward** (`--replaces` / `replace-study`) and recorded by metldata — never inferred from version order, since a predecessor may be a legacy accession that carries no version at all.
   The portal is the only online reader, via metldata's successor endpoint; RS's `superseded_by_id` stays unset and MASS only ever sees the existing `searchable_resource_deleted`.
3. **File mapping is 1:1 and box-centric, with mapping as a prerequisite for archival** → many-accessions-per-file, study/submission-centric mapping, and the dependency **inverted**: files are archived first, then mapped against archived boxes.
4. **Search shows everything; no legacy handling** → superseded studies' datasets are hidden from search but reachable by URL/PID, with an "updated version" hint.
5. **`studies[0]` one-study-per-submission assumption** in the loader — the study becomes the submission scope.

---

## 8. Glossary

- **Accession / PID** — a public GHGA identifier for an entity.
- **RDUB / FUB** — ResearchDataUploadBox (RS) / FileUploadBox (UCS); 1:1.
- **Mapping** — binding a metadata file entity's accession to a physical uploaded file (`file_id`).
- **Artifact** — a transformed metadata product (e.g. `embedded_public`); the query/serve unit.
- **Primary dataset source** — `embedded_public` / `EmbeddedDataset`; the only source that emits searchable-resource and dataset-overview events.
- **Interim ingestion bridge** (a.k.a. the "legacy resource" consumer) — RS populating its **forward-looking** Study + unmapped-FileAccession state by consuming metldata's `SearchableResource` events.
  The *bridge* is interim (removed once RS owns studies); RS's `Study` entity is not legacy.
