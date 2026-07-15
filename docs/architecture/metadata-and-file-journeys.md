# Metadata & File Journeys — Current-State Reference

> **Purpose.** A durable, implementation-level map of how metadata and files flow through
> the GHGA platform **as built today** (LinkML + offline metadata management via
> `ghga-datasteward-kit`). It is written for both humans and future coding agents: read it
> before touching submission, accession, upload, file-mapping, or metadata-serving code so
> you start from ground truth rather than re-deriving it.
>
> **Status.** Describes the *current* system. The planned early "data lifecycle" changes are
> tracked separately in [`docs/features/early-data-lifecycle.md`](../features/early-data-lifecycle.md);
> where this document notes an invariant the feature will change, it links there.
>
> File:line anchors are provided as entry points. They drift — treat them as "start looking
> here", not as guarantees.

---

## 1. Component map

| Component | Kind | Owns / does |
|---|---|---|
| `tools/ghga-datasteward-kit` (**dskit**) | CLI | Offline driver: transpile xlsx→json, `submit` (mint accessions), `transform` (run workflow), `load` (push artifacts). Legacy S3 upload + FIS ingest. |
| `libs/metldata` | library + deployable API | The engine behind dskit. Submission registry, accession registry, transformation workflows, and the **combined loader + artifacts-query API** (`metldata run-api`). |
| `libs/ghga-event-schemas` | library | Shared Kafka event/payload models (upload boxes, file uploads, searchable resources, dataset overviews, artifacts). |
| `services/ghga-registry-service` (**rs**) | service | A **new, forward-looking** service (built with the upcoming metadata services in mind). Owns `ResearchDataUploadBox` (RDUB), `FileAccession` mapping records, and a first-class **`Study`** entity that already models lifecycle (`DRAFT`/`ARCHIVED` status, approval provenance, and a `superseded_by_id` deprecation link). Steward-facing box + mapping + grants API. Its Study/FileAccession state is *currently populated* by an interim bridge consuming metldata's `SearchableResource` events — **that ingestion path is the legacy part, not the entity**. |
| `services/ucs` | service | Owns `FileUploadBox` (FUB) + `FileUpload` records + the S3 inbox multipart uploads. One RDUB wraps exactly one FUB. |
| `services/work-package-service` (**wps**) | service | Issues per-file work-order tokens; tracks datasets/files a user may download. |
| `services/fis` | service | File **interrogation** coordinator: serves work lists to data hubs, ingests interrogation reports, deposits secrets with EKSS, emits interrogation events. |
| `services/datahub-file-service` (dhfs) | service | Performs interrogation / re-encryption at the data hub. |
| `services/ekss` | service | Crypt4GH secret store (store / get-envelope / delete). |
| `services/ifrs` | service | Registers interrogated files permanently; emits `FileInternallyRegistered`. |
| `services/dcs` | service | Makes registered files downloadable. |
| `services/mass` | service | Metadata **search** over searchable resources (dataset-centric). |
| `services/dataset-information-service` (dins) | service | Per-dataset file information for the portal. |
| `services/reverse-transpiler-service` (rts) | service | Renders accessioned metadata back to an xlsx workbook, served per study. |
| `services/access-request-service` (ars) | service | Access requests / grants against dataset accessions. |
| `tools/ghga-connector` | CLI | Uploader client for the **new** box path (`ubox`, `batch-upload`). |
| `frontend/data-portal` | Angular app | Browse/search datasets, dataset & study detail pages, steward upload-box + mapping UI. |

Not part of the metadata world today: `services/em-transformation-service` is an unmodified
template scaffold (package `my_microservice`, only `GET /greet/{name}`); the future
schemapack services (resource-registry, resource-search) do not exist yet.

---

## 2. Journey A — Metadata submission (offline: dskit + metldata)

Canonical sequence (see `tools/ghga-datasteward-kit/demo/run_steps.sh`):

1. `metadata generate-artifact-models` — build artifact models + `artifact_infos.json` from the LinkML model.
2. `metadata transpile input.xlsx input.json` — spreadsheet → JSON. Re-exported from
   `ghga_transpiler.cli.transpile`. **No schema validation here.**
3. `metadata submit` — validate + register a submission locally, mint accessions, publish a source event.
4. `metadata transform` — run the GHGA archive workflow → produce artifacts on disk.
5. `load` (top-level, **not** `metadata load`) — POST artifacts to the loader API.

### The submission object & store
- `Submission` model: `libs/metldata/src/metldata/submission_registry/models.py:60`.
  Fields: `id` (UUID4), `title`, `description`, `content` (`{anchor_slot: {alias: instance}}`),
  `accession_map` (`{anchor_slot: {alias: accession}}`), `status_history`.
- Persisted as **one JSON file per submission** (`{id}.json`) — `submission_store.py:61`.
  Full-document overwrite each save; not event-sourced at the store layer.
- Registry ops (`submission_registry.py`): `init_submission` → `upsert_submission_content`
  (validates via metldata's own `MetadataValidator`, regenerates the accession map, publishes a
  source event) → `complete_submission`. **Only `PENDING`→`COMPLETED` is ever used.**
- `SubmissionStatus` (`models.py:31`) *defines* `DEPRECATED_*`, `PUBLISHED`, `HIDDEN_*`,
  `EMPTIED_*`, `CANCELED`, `IN_REVIEW` — **none are ever set**. There is no replaces/replaced-by
  field and no versioning anywhere today. → [changed by the feature](../features/early-data-lifecycle.md).

### Accession generation (offline, random, no counter)
- Engine: `accession_registry/accession_registry.py:82`. Accession = `prefix + suffix`, where
  `suffix = "".join(secrets.randbelow(10) for _ in range(suffix_length))` — **decimal digits
  only**, cryptographically random, `suffix_length` = 14 in GHGA config. **No counter, no year,
  no structure.**
- Prefix per **LinkML class name** (current testbed config
  `testbed/example_data/metadata/metadata_config.yaml:6`): `Study→GHGAS`, `Dataset→GHGAD`,
  all `*File`→`GHGAF`, `DataAccessPolicy→GHGAP`, `DataAccessCommittee→GHGAC`, `Sample→GHGAN`,
  `Individual→GHGAI`, `Experiment→GHGAX`, `ExperimentMethod→GHGAQ`, `Analysis→GHGAR`,
  `AnalysisMethod→GHGAZ`, `Publication→GHGAU`.
- Persisted in a flat, append-only **text file** (`accession_store.py:56`), one accession per
  line; `exists()` is a linear scan. Up to 10 collision retries.
- Alias↔accession stability (`submission_registry/identifiers.py:102`): within one submission
  object, re-upserting the same alias **reuses** its accession; new aliases get new ones;
  dropped aliases fall out. **But `submit` always calls `init_submission` (fresh UUID, empty
  map), so a new `submit` run of the same aliases mints *fresh* accessions.** There is no
  cross-submission accession stability today. → [changed by the feature](../features/early-data-lifecycle.md).
- A **separate** catalog-accession scheme exists (`generate-catalog-accessions`,
  `catalog_accession_generator.py`): base `GHGAMC` + per-type letter + 14 digits. Distinct from
  submission accessions; not on the submission path.

### The LinkML model (current testbed model)
- Root/tree class `Submission`; every entity class is a required, multivalued, `inlined_as_list`
  slot of it. **The model permits multiple studies per submission** (used in fixtures:
  `STUDY_A`, `STUDY_B`), though operationally there has only ever been one.
- Entities reference each other **by alias** at submission time; `add_accessions` swaps aliases
  for accessions during transform.
- Study↔Dataset: `Dataset.study` is a **single** alias reference (`testbed/.../metadata.json`).
  Files (`ResearchDataFile`, `ProcessDataFile`, `*SupportingFile`) carry `alias`, a `name`
  (filename), a `dataset` ref, and an `ega_accession` slot. Study→datasets is *inferred* during
  transform (`Study<(study)Dataset`).
- **`studies[0]` assumption:** the loader derives a publishable artifact's `study_accession` from
  `content["studies"][0]["accession"]` (`libs/metldata/src/metldata/load/collect.py:91`) — a
  hard one-study-per-submission assumption. → relevant to the feature.

### Transform artifacts
Workflow `builtin_workflows/ghga_archive.py:36`: normalize → **add_accessions** → embed_restricted
→ infer_multiway_references → merge_dataset_file_lists → remove_restricted_metadata →
aggregate_stats → embed_public. Artifacts produced: `added_accessions`, `embedded_restricted`,
`resolved_restricted`, `resolved_public`, `embedded_public`, `stats_public`. The **primary**
queryable artifact/class is `embedded_public` / `EmbeddedDataset`.

---

## 3. Journey B — File upload, interrogation, archival

### Upload boxes
- Schemas (`libs/ghga-event-schemas/src/ghga_event_schemas/pydantic_.py`):
  `UploadBoxState = "open" | "locked" | "archived"` (:501); `ResearchDataUploadBox` (rs, :504);
  `FileUploadBox` (ucs, :619). One RDUB wraps one FUB.
- Box lifecycle transitions (`rs/constants.py:28`): `open ⇄ locked`, `locked → archived`
  (terminal). No `open→archived`, no un-archiving.
- Creation: `POST /upload-boxes` (steward-only) → `RDUBManager.create_research_data_upload_box`
  → calls ucs `POST /boxes` (guarded by a `CreateFileBoxWorkOrder` token) → inserts RDUB
  (`open`, v0).
- Uploader access = **upload grants** (`/upload-grants`, steward-managed, tie user+iva+box+window)
  plus per-file **work-order tokens** issued by wps and verified at each ucs file endpoint.
  `ghga-connector` (`ubox`/`batch-upload`) is the uploader client.

### File upload state machine (who owns each transition)
- `FileUploadState = "init" | "inbox" | "failed" | "cancelled" | "interrogated" |
  "awaiting_archival" | "archived"` (`pydantic_.py:540`). `FileUpload` (:551) carries
  `alias` (unique within box), checksums, sizes, `secret_id`, storage refs.
- **init** — ucs `initiate_file_upload` (starts S3 multipart; captures alias, sizes, part_size).
- **inbox** — ucs `complete_file_upload` (verifies ETag/size/checksums).
- ucs publishes the change → **fis** ingests it as a `FileUnderInterrogation`.
- **dhfs** polls fis `GET /storages/{alias}/uploads`, re-encrypts, POSTs an `InterrogationReport`.
- fis on success deposits the Crypt4GH secret with **ekss**, sets `interrogated`, emits
  `InterrogationSuccess`; on failure emits `InterrogationFailure`.
- **interrogated** — ucs consumes success (records `secret_id`, new object refs).
- **ifrs** consumes success → permanently registers → emits `FileInternallyRegistered`.
- **archived** — ucs consumes `FileInternallyRegistered`; **dcs** consumes it to enable download.

### Archival (today)
- Triggered by `PATCH /upload-boxes/{box_id}` `state:"archived"` (steward-only); only valid from
  `locked`.
- **Prerequisite (today):** `_check_archival_prerequisites` (`rdub_manager.py:314`) rejects
  archival unless **every file in the box already has an accession mapped**; ucs additionally
  rejects if any `init`/`inbox` file remains. On archival every file flips to `awaiting_archival`.
  → **[this coupling is removed by the feature](../features/early-data-lifecycle.md).**
- After archival the box is **immutable**: accession maps, deletion, etc. are all rejected.
- **Retained after archival (important):** the RDUB, the FUB, and every `FileUpload`
  (alias, filename, checksums, sizes, accession) **remain stored and queryable** in both rs and
  ucs. `GET /upload-boxes/{box_id}/uploads` still works for archived boxes. This is what makes
  "select the boxes originally used" feasible later.

---

## 4. Journey C — File-to-metadata mapping (current, box-centric)

**Today the mapping is portal-driven and box-centric.** The steward maps *metadata file
accessions* → *upload-box file IDs*.

- Endpoint: `POST /upload-boxes/{box_id}/file-ids` (steward-only) →
  `RDUBManager.store_accession_map` (`rdub_manager.py:939`). Body: `{box_version, study_id,
  mapping: {accession → file_id}}`.
- Constraints enforced today:
  - box **not archived** (optimistic version lock on `box_version`);
  - **strict 1:1** — each file_id appears once; an accession already mapped elsewhere / to another
    study → `ConflictingAccessionError`. → **[relaxed to one file → many accessions by the
    feature](../features/early-data-lifecycle.md).**
  - **every active file in the box must be mapped** (no leftovers);
  - the accession must **already exist as an *unmapped* `FileAccession`** — those rows are
    pre-seeded by an **interim ingestion bridge** consuming metldata's `SearchableResource`
    events (`ResourceSubTranslator` → `LegacyResourceManager.upsert_resource` →
    `FileController.register_unmapped_accessions`; `rs/adapters/inbound/event_sub.py:65`,
    `rs/core/legacy_resources.py:109`, `rs/core/files.py:100`). The same bridge also inserts the
    embedded `Study` into rs's **forward-looking** `Study` store — but with *placeholder* values
    (forced `ARCHIVED` status, sentinel creator) because a searchable resource carries no
    lifecycle info. It is the **bridge** that is legacy (*"remove once this service owns studies"*),
    **not** the `Study` entity, which already models `DRAFT`/`ARCHIVED` status and
    `superseded_by_id`.
- Mapping produces a `FileAccession` (`pid` accession ↔ `file_id` ↔ `study_id`), persisted in the
  `fileAccessions` collection and emitted via outbox. Read back via
  `GET /studies/{study_id}/file-ids` (`{accession: file_id | null}`),
  `GET /studies?with_unmapped_files=true`, and `GET /upload-boxes/{box}/uploads`
  (`FileUploadWithAccession`).
- Portal (`frontend/data-portal/src/app/upload/features/upload-box-mapping/`): appears when the
  box is **locked**; steward picks a study + a `MappedField` (`alias | name`); auto-matches box
  file alias against the metadata file's `alias` or `name`, with manual overrides; then
  **submits the map and archives in one action** (`onConfirmAndArchive`).

---

## 5. Journey D — Load → serve → browse

### Load API
- metldata's **combined** app (`libs/metldata/src/metldata/combined.py`, run via `metldata run-api`)
  mounts the loader (`POST /rpc/load-artifacts`, bearer loader-token) + the artifacts query API.
  **Not** a `services/` microservice.
- `dskit load` collects artifacts from the local event store and POSTs `ArtifactResourceDict`
  (`{artifact_name: [{study_accession, artifact_name, content}]}`).
- The loader **diffs DB-vs-payload** (full-state reconciliation, no tombstones/versioning):
  - per-resource diff (`load/load.py:192`) → new/changed/removed resources;
  - whole-artifact diff for `publishable_artifacts` (`added_accessions`) keyed by
    `(artifact_name, study_accession)`.

### Events emitted (`load/event_publisher.py`) & consumers
| Event (topic / type) | Payload | Consumers |
|---|---|---|
| `searchable_resources` upsert/delete | `SearchableResource` / `SearchableResourceInfo` | **mass** (search index); **rs** (interim bridge seeding its forward-looking Study + unmapped FileAccession state) |
| `metadata_datasets` created/deleted | `MetadataDatasetOverview` / `MetadataDatasetID` | **wps** (`register_dataset`); **dins** (`register_dataset_information`); claims/auth (deletion) |
| `artifacts` upserted/deleted | `Artifact` / `ArtifactTag` | **rts** (filters `added_accessions:` key prefix) |

Resource/dataset events fire **only for the primary dataset source** (`embedded_public` /
`EmbeddedDataset`). `MetadataDatasetOverview` is assembled from the embedded dataset content
(title, description, DAC alias/email, file list). Downstream consumers are idempotent about
missing targets.

### Search (mass)
- `GET /search?class_name=...&filter_by=...&value=...&query=...&skip=&limit=` and
  `GET /search-options`. Searchable classes are **config-driven**; the portal searches
  `class_name=EmbeddedDataset` only — **there is no Study search class**. Upsert/delete are purely
  event-driven; mass does no diffing.
  → **[search hiding of superseded datasets is added by the feature](../features/early-data-lifecycle.md).**

### Portal (`frontend/data-portal/src/app/app-routes.ts`)
- `browse` (datasets, `class_name=EmbeddedDataset`), `dataset/:id`, `study/:id` (and `s/:id`).
- Dataset detail: `GET {metldata}/artifacts/embedded_public/classes/EmbeddedDataset/resources/{id}`;
  summary from `stats_public/.../DatasetStats/...`; study detail from
  `embedded_public/.../Study/...`; file info from dins `GET /dataset_information/{id}`; metadata
  xlsx from rts `GET /studies/{accession}`.
- `loadStudiesMap()` is an explicitly temporary fan-out (EmbeddedDataset → stats → Study) labeled
  *"until we switch to a study-based backend"*.
- **No versioning/deprecation UI anywhere** — re-load silently replaces.
  → **[the "updated version available" hint is added by the feature](../features/early-data-lifecycle.md).**

---

## 6. Journey E — Download (brief)

dataset accession → **ars** access request/grant (`dataset_id: Accession`) → **wps** work package
+ per-file download work-order token → **ghga-connector** → **dcs** `GET /objects/{id}` (+
`/envelopes`), keys via **ekss**. Dataset accessions live on ars requests/grants, the wps dataset
collection (from `MetadataDatasetOverview`), and dins.

---

## 7. Invariants the data-lifecycle feature will change

Collected here as a checklist; details in
[`docs/features/early-data-lifecycle.md`](../features/early-data-lifecycle.md).

1. **Accession format** is `{prefix}{14 random digits}` with no structure/version → studies move
   to `GHGA.YY.XXX.V`; child entities to `{study_pid}.{alias}`; datasets to `{study_pid}.DS.xxx`.
2. **No cross-submission stability / no versioning** → studies gain a stable lineage
   (`GHGA.YY.XXX`) with an incrementing version; study-level deprecation is **inferred service-side**
   by metldata (highest loaded version wins), with rs/mass/portal as consumers.
3. **File mapping is 1:1 and box-centric, with mapping as a prerequisite for archival** →
   many-accessions-per-file, study/submission-centric mapping, and the dependency **inverted**:
   files are archived first, then mapped against archived boxes.
4. **Search shows everything; no legacy handling** → superseded studies' datasets are hidden from
   search but reachable by URL/PID, with an "updated version" hint.
5. **`studies[0]` one-study-per-submission assumption** in the loader — the study becomes the
   submission scope.

---

## 8. Glossary

- **Accession / PID** — a public GHGA identifier for an entity.
- **RDUB / FUB** — ResearchDataUploadBox (rs) / FileUploadBox (ucs); 1:1.
- **Mapping** — binding a metadata file entity's accession to a physical uploaded file
  (`file_id`).
- **Artifact** — a transformed metadata product (e.g. `embedded_public`); the query/serve unit.
- **Primary dataset source** — `embedded_public` / `EmbeddedDataset`; the only source that emits
  searchable-resource and dataset-overview events.
- **Interim ingestion bridge** (a.k.a. the "legacy resource" consumer) — rs populating its
  **forward-looking** Study + unmapped-FileAccession state by consuming metldata's
  `SearchableResource` events. The *bridge* is interim (removed once rs owns studies); rs's
  `Study` entity is not legacy.
