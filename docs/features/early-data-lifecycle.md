# Early Data Lifecycle Rollout — Developer Guide

> **Audience.** Developers implementing the feature across dskit, metldata, the registry
> service, MASS, and the data portal.
>
> **Prerequisite reading.** [`docs/architecture/metadata-and-file-journeys.md`](../architecture/metadata-and-file-journeys.md)
> — the current-state map this document builds on. Terms like RDUB, FUB, primary dataset source,
> legacy resource seeding, and the mapping flow are defined there.
>
> **Status.** Design agreed; not yet implemented. Decisions in §2 are locked with the product
> owner. Section §7 lists what remains open.

---

## 1. What we are trying to achieve

Today every submission *could* contain multiple studies, but in practice each contains exactly
one, and there is **no notion of study identity, versioning, or replacement**. A re-submission
mints entirely fresh random accessions with no link back to what it supersedes.

The long-term plan replaces LinkML with schemapack and introduces dedicated backend services
(resource-registry, resource-search, experimental-metadata transformation) — alongside the
already-new `ghga-registry-service` — where the **study becomes the defining scope of a
submission** and every other entity is semantically a child of it. Studies will receive a new structured PID and can be **revised** — superseding an
earlier version, which then becomes *legacy* (reachable by URL/PID but hidden from search).

**This document is not that.** It is an **early rollout of the data lifecycle on the existing
stack** — LinkML + offline metadata management via `ghga-datasteward-kit` — so we can start
issuing lifecycle-style PIDs and handling revisions before the schemapack services land. It
deliberately stays within: **dskit + metldata + MASS + registry-service + data-portal.** The
future schemapack services are out of scope.

The two user-visible outcomes:

1. **Studies get lifecycle PIDs and can be replaced.** A data steward can declare that a new
   submission replaces an existing study; the new study keeps the predecessor's identity and
   increments a version counter. Superseded studies drop out of search but remain reachable by
   URL/PID, and the portal shows a "an updated version exists" hint.
2. **File upload and file-to-metadata mapping are decoupled and reuse-friendly.** Files can be
   archived without being mapped to metadata. Mapping becomes study-centric and lets a new study
   revision **reuse already-uploaded files** (by GHGA accession) instead of re-uploading them.

---

## 2. Locked design decisions

### 2.1 PID scheme

| Entity | PID format | Notes |
|---|---|---|
| **Study** | `GHGA.YY.XXX.V` | `YY` = 2-digit year, **frozen at v1**. `XXX` = base32 `[A-Z2-7]{3}` (RFC 4648 alphabet, no `0/1/8/9`), **globally unique** across all studies. `V` = version counter, starts at **1**, increments per revision. |
| **Study lineage identity** | `GHGA.YY.XXX` | Stable across all revisions of one study; only `.V` changes. |
| **Dataset** | `{study_pid}.DS.[A-Z2-7]{3}` | Random 3-char base32 block, **unique within the study lineage**. **Reuse rule:** if a dataset's file set is **exactly identical** to a predecessor-revision dataset, its `.DS.xxx` block is **reused**; otherwise a fresh one is generated. |
| **Every other entity** | `{study_pid}.{alias}` | `alias` = the entity alias from the submitted metadata. **Requires: aliases are unique across all entities within a study revision.** |

Consequences to internalize:

- Because `{study_pid}` embeds the version, **every non-study entity's accession changes on every
  revision** (e.g. `GHGA.24.ABC.1.mysample` → `GHGA.24.ABC.2.mysample`), even when the entity is
  unchanged. This is expected.
- `XXX` collisions are resolved by retry against a global uniqueness check; `.DS.xxx` collisions
  by retry within the lineage.

### 2.2 Versioning & replacement (offline)

- The steward declares replacement on the CLI by passing the **predecessor's full study PID**
  (e.g. `--replaces GHGA.24.ABC.1`). dskit trusts it and mints `GHGA.24.ABC.2`.
- dskit obtains everything it needs about the predecessor (its stable prefix, current max version,
  its datasets' file-sets, its file accessions/identities) from a **local persistent lineage
  store** that dskit accumulates across submissions — i.e. prior revisions are already on disk on
  the steward workstation from when they were submitted. No live-service query is required for
  submission. *(Single-workstation assumption; see §7.)*

### 2.3 File reuse cardinality

- A physical uploaded file may back **many accessions** — one per study revision that reuses it.
  The registry service's current strict **1:1 `file_id`↔accession** constraint is **relaxed to
  1-file→many-accessions**.
- The steward expresses reuse in the submitted metadata by putting the **predecessor's GHGA file
  accession** in a dedicated file-entity slot (a new model slot — see §3, metldata/model). dskit
  resolves that prior accession → the physical file identity via the local lineage store, and the
  new revision's file entity (with its new `{study_pid}.{alias}` accession) is mapped to the same
  physical file.

### 2.4 Deprecation & legacy semantics

- Deprecation is tracked **study-level only.** At `load` time the steward submits "deprecated-by"
  information linking the predecessor study revision to its successor. Datasets and other entities
  of the old revision inherit legacy status via their study.
- **The registry service already has the backing model for this.** rs's `Study`
  ([`rs/core/models.py`](../../services/ghga-registry-service/src/rs/core/models.py)) carries a
  **`superseded_by_id`** field ("the PID of a newer study superseding this one") plus a
  `DRAFT`/`ARCHIVED` `status`. So study-level deprecation largely exists in the target model — the
  work is populating it through a first-class path rather than the interim bridge (see §4.3).
- **Legacy = a newer revision of the same study lineage exists.** Legacy studies' datasets are
  **hidden from search** but remain reachable by URL/PID (`/dataset/{id}`, `/study/{id}`). The
  portal shows an "updated version available" hint that resolves **at study level** (old study →
  newest study revision).

### 2.5 Mapping / archival decoupling

- **Fully decoupled.** Drop the rule that a box can be archived only once all its files are
  mapped, and drop the portal's submit-map-then-archive coupling. Files become archivable
  immediately, unmapped. Mapping becomes a separate, study-centric activity done later against
  (possibly archived) boxes.

### 2.6 Scope

- **In scope:** `tools/ghga-datasteward-kit`, `libs/metldata`, `libs/ghga-event-schemas` (as
  needed), `services/ghga-registry-service`, `services/mass`, `frontend/data-portal`.
- **Out of scope:** the future schemapack services (resource-registry, resource-search),
  `em-transformation-service`, and the schemapack migration itself.

---

## 3. Target end-to-end journey

**Submitting a replacement study (offline, dskit):**

1. Steward prepares the new submission's spreadsheet as usual. For any file being reused from a
   prior revision, they fill the **prior GHGA file accession** slot on that file entity instead of
   providing a new upload.
2. `dskit metadata submit --replaces GHGA.24.ABC.1 ...`:
   - looks up the predecessor in the **local lineage store**;
   - mints the new study PID `GHGA.24.ABC.2` (same lineage, `V+1`);
   - mints child accessions `{study_pid}.{alias}`; for datasets computes the file-set and
     **reuses or regenerates** the `.DS.xxx` block accordingly;
   - resolves reused-file slots to physical file identities and records the reuse.
3. `dskit metadata transform` — unchanged in spirit; the accessions now carry lifecycle structure.
4. `dskit load` — pushes artifacts **plus the study-level deprecated-by link** (predecessor →
   successor).

**Serving:**

5. metldata loads artifacts, emits searchable-resource / dataset-overview events as today, **plus**
   propagates the deprecation so that superseded datasets are removed from / hidden in search.
6. MASS stops returning the old revision's datasets. The registry service records the study
   lineage/version and deprecation.
7. The portal shows the newest revision in search; visiting a legacy dataset/study by URL shows
   the "updated version available" hint.

**File mapping (study-centric):**

8. Steward opens the mapping view for a study/submission. Entities that carry a GHGA file
   accession are **confirmed upfront** (those files exist); the steward sees the list of study
   revisions each reused file already maps to. For entities with no accession, the steward selects
   the **archived upload box(es) originally used** as the candidate pool, then maps by alias /
   filename with manual corrections — reusing today's matching UX, but no longer gated on the box
   being unarchived or fully mapped.

---

## 4. Changes by component

### 4.1 `tools/ghga-datasteward-kit` (dskit)

- **Local lineage store.** New persistent local store accumulating, per study lineage: stable
  prefix `GHGA.YY.XXX`, current max version, per-revision datasets with their file-sets and
  accessions, and file-accession → physical-file identity. Populated on every `submit`. This is
  the offline source of truth for revisions (§2.2).
- **`submit` gains `--replaces <study_pid>`.** When present: resolve the predecessor from the
  lineage store; validate the PID exists and is the latest version (or handle branching per §7);
  carry the lineage forward.
- **PID minting moves from "random per class" to the lifecycle scheme** (§2.1). This likely means
  dskit drives accession assignment (study PID, `{study_pid}.{alias}`, `{study_pid}.DS.xxx` with
  file-set-based reuse) rather than delegating to metldata's flat `AccessionRegistry`. Decide
  whether to (a) implement the scheme in dskit and feed a pre-built accession map into the
  submission, or (b) push the scheme into metldata's accession layer and have dskit supply the
  lineage context. **(b) keeps accession logic in one place — see §4.2.**
- **File-set-based dataset-suffix reuse.** Compute each dataset's file set from the metadata; diff
  against predecessor datasets in the lineage store; reuse `.DS.xxx` on exact match else mint.
- **Reused-file resolution.** For file entities carrying a prior GHGA accession, resolve to the
  physical file identity and record the new-accession→file mapping so `load`/mapping can bind it.
- **`load` carries deprecated-by info.** Extend the load payload/flow so the predecessor→successor
  study link travels to metldata (§4.2).
- **Uniqueness on submit** — enforce alias uniqueness across all entities within the revision
  (§2.1) and surface a clear error otherwise.

### 4.2 `libs/metldata`

- **Accession scheme.** Replace/augment the flat random `AccessionRegistry`
  (`accession_registry/accession_registry.py:82`) so studies and their children follow the
  lifecycle scheme. Preferred: a lineage-aware accessioning path that, given a study lineage +
  version + alias set + dataset file-sets, produces the structured PIDs, with global uniqueness
  for study `XXX` and lineage-scoped uniqueness for `.DS.xxx`. Keep the accession store, but note
  the flat-text, linear-scan store (`accession_store.py`) is weak for structured
  uniqueness/version queries — consider a structured store.
- **Submission model — versioning fields.** Add lineage/version/replaces fields to `Submission`
  (`submission_registry/models.py:60`). The status enum already defines `DEPRECATED_*` /
  `PUBLISHED`; wire actual transitions if we use them, or model deprecation as an explicit
  predecessor/successor link — pick one and be consistent.
- **Model slot for reused-file accession.** The LinkML model's file classes need a slot to carry
  the **prior GHGA file accession** (distinct from the existing `ega_accession`). Add it to the
  GHGA model + regenerate artifact models.
- **`studies[0]` assumption.** Revisit `load/collect.py:91` and the one-study-per-submission
  assumptions now that the study is the explicit submission scope. At minimum assert/handle it
  cleanly.
- **Load API carries deprecation.** Extend the loader (`load/api.py`, `load/load.py`,
  `load/event_publisher.py`) so a study-level predecessor→successor link is accepted and turned
  into the right downstream signal — i.e. the superseded revision's primary-dataset resources
  should be **removed from / marked hidden in** search. Simplest path that fits today's model:
  when revision `V+1` loads, treat revision `V`'s datasets as removed for the *searchable* track
  (emit `searchable_resource_deleted`) while leaving them queryable via the artifacts API for
  direct URL access. Confirm this matches the "hidden from search but reachable by URL" rule
  before implementing.

### 4.3 `services/ghga-registry-service` (rs)

- **Relax file mapping cardinality to 1-file→many-accessions.**
  `FileController.map_accessions_to_file_ids` / `store_accession_map`
  (`rs/core/files.py:37`, `rs/core/rdub_manager.py:939`) currently reject a `file_id` bound to
  more than one accession and an accession mapped elsewhere. Change the model + validation so one
  `file_id` can carry many `FileAccession` rows (one per revision), while keeping per-accession
  integrity.
- **Decouple archival from mapping.** Remove the "all files mapped" archival prerequisite
  (`_check_archival_prerequisites`, `rdub_manager.py:314`) and the requirement that
  `store_accession_map` covers every active file. Archival now only requires no `init`/`inbox`
  files (ucs-level), not full mapping.
- **Study-centric mapping surface.** Add/extend endpoints so mapping is driven by study rather
  than by a single box:
  - given a study, report which file entities reference a GHGA accession that already resolves to
    an existing file (confirmed) vs which need mapping;
  - for confirmed reused files, report the **list of study revisions each file already maps to**
    (the "for administrative reasons" list) — naturally supported once cardinality is many;
  - allow the steward to add a **pool of (archived) boxes** as mapping candidates for the
    unmapped entities, then map by alias/filename. The retained post-archival box/file inventory
    (§ Journey B) is the data source.
- **Study lineage & deprecation.** rs's `Study` entity is **new and forward-looking**, and already
  models most of what we need: `id` is the study PID (so version + lineage are encoded in it per
  §2.1), `status` is `DRAFT`/`ARCHIVED`, and **`superseded_by_id`** already holds the
  predecessor→successor link. The work is therefore *not* to build a new store but to **populate
  these fields authoritatively** (correct `status`, `superseded_by_id`, provenance, `num_datasets`,
  etc.) when a revision is loaded. Today they are only filled by the **interim ingestion bridge**
  (`rs/adapters/inbound/event_sub.py:65` `ResourceSubTranslator` → `rs/core/legacy_resources.py`),
  which sets *placeholders* (forced `ARCHIVED`, sentinel creator) because metldata's
  `SearchableResource` events carry no lifecycle info. Feed rs from the new deprecation-carrying
  signals (§4.2) so `superseded_by_id`/`status` reflect reality, and plan the transition off the
  bridge. (If a dedicated version field beyond the PID is wanted, add it — but the PID already
  encodes it.)

### 4.4 `services/mass`

- **Hide superseded datasets from search.** MASS is event-driven and does no diffing, so hiding is
  achieved by the upstream deletion signal (§4.2): on revision, the old datasets receive
  `searchable_resource_deleted` and drop out of the index. Verify no MASS change is needed beyond
  that; if we instead want a "hidden" flag retained in MASS (e.g. for an admin/steward search that
  *can* see legacy), add a filterable field + query option.

### 4.5 `frontend/data-portal`

- **"Updated version available" hint.** On `dataset/:id` and `study/:id`, detect that the entity
  belongs to a superseded study revision and render a hint linking to the newest revision
  (study-level resolution per §2.4). Needs an API to resolve lineage/newest-version (from rs
  and/or metldata artifacts).
- **Study-centric mapping UI.** Rework
  `frontend/data-portal/src/app/upload/features/upload-box-mapping/` and related services from
  box-centric to study-centric: select a study; show confirmed reused-file entities + the "already
  maps to revisions X, Y" info; for unmapped entities let the steward choose a pool of archived
  boxes and map by alias/filename with manual corrections. Remove the submit-map-then-archive
  coupling; archival becomes an independent action.
- **Reused-file affordances.** Surface, in the mapping view, which entities are satisfied by a
  prior GHGA accession vs need a physical file.

### 4.6 `libs/ghga-event-schemas`

- Add any new fields required to carry **study lineage/version** and **deprecation** through the
  events that rs/mass/wps/dins consume (e.g. on `MetadataDatasetOverview` / `SearchableResource`),
  if the chosen deprecation propagation (§4.2) needs them. Keep changes additive and mind the
  single-version source-coupling in this monorepo (all consumers see one schema version).

---

## 5. Cross-cutting invariants to preserve

- **Alias uniqueness within a revision** is now load-bearing (child accessions derive from alias).
  Enforce at submit.
- **Legacy reachability:** legacy datasets/studies must stay resolvable via the artifacts query
  API and portal URLs even after leaving search. Don't delete their stored artifacts when hiding
  them from search.
- **Idempotency:** downstream consumers already tolerate missing targets; keep re-load /
  re-deprecate operations idempotent.

---

## 6. Suggested implementation order

1. **PID scheme + lineage store in dskit/metldata** (§4.1, §4.2 accession parts) — everything else
   depends on the new accessions existing. Land with unit tests for format, uniqueness, version
   increment, and dataset file-set reuse.
2. **Model slot for reused-file accession + reuse resolution** (§4.2, §4.1).
3. **rs: relax cardinality + decouple archival** (§4.3) — independent of PIDs; unblocks the mapping
   redesign.
4. **Deprecation propagation: load → search hiding** (§4.2, §4.4).
5. **rs study-centric mapping surface** (§4.3).
6. **Portal: mapping UI rework + legacy hint** (§4.5).

Steps 1–2, 3, and 4 are largely independent and can proceed in parallel once the PID scheme is
fixed.

---

## 7. Open questions / risks

- **Lineage store durability & single-workstation assumption.** The offline lineage store is the
  sole source of truth for revisions. What happens if a different steward / machine submits a
  revision, or the store is lost? (Backup/sync story, or a bootstrap-from-service import.)
- **Branching / out-of-order revisions.** `--replaces` targets a specific PID. Do we forbid
  replacing anything but the latest version, or allow branches? Current design assumes linear.
- **Deprecation representation in a full-reconciliation loader.** metldata's loader is stateless
  full-state reconciliation. Confirm whether study-level deprecation is best expressed as
  "old revision's datasets removed from the searchable track on new-revision load" vs a persisted
  hidden flag — affects whether event-schema changes are needed (§4.6).
- **Interim ingestion bridge retirement.** rs currently derives its (forward-looking) Study +
  unmapped-FileAccession state from metldata's `SearchableResource` events via the interim bridge,
  filling lifecycle fields with placeholders. As rs is fed real lifecycle data, clarify the
  transition: does the bridge still seed unmapped accessions in the early rollout, or does a new
  study-centric flow replace it — and when is the `ResourceSubTranslator`/`LegacyResourceManager`
  consumer removed?
- **Dataset file-set equality definition.** "Exactly identical set of files" — by physical file
  identity (reused accession / file_id) or by the metadata file entities? Nail this down; it
  drives `.DS.xxx` reuse and therefore URL stability of datasets across revisions.
- **`ega_accession` vs new reuse slot.** Ensure the new prior-GHGA-accession slot is clearly
  distinct from the existing `ega_accession` slot and from each entity's own minted accession.
