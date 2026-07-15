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
| **Study** | `GHGA.YY.XXX.V` | `YY` = 2-digit year, **frozen at v1**. `XXX` = base32 `[A-Z2-7]{3}` (RFC 4648 alphabet, no `0/1/8/9`), **unique within the year `YY`** (not global) — giving ~32³ ≈ 32,768 studies/year of capacity. `V` = version counter, starts at **1**, increments per revision. Because `YY` is frozen at v1, `GHGA.YY.XXX` is still unique overall by construction (year + year-unique random), but a given `XXX` may recur in a different year. |
| **Study lineage identity** | `GHGA.YY.XXX` | Stable across all revisions of one study; only `.V` changes. |
| **Dataset** | `{study_pid}.DS.[A-Z2-7]{3}` | Random 3-char base32 block, **unique within the study lineage**. **Reuse rule:** if a dataset's file set is **exactly identical** to a predecessor-revision dataset, its `.DS.xxx` block is **reused**; otherwise a fresh one is generated. |
| **Every other entity** | `{study_pid}.{alias}` | `alias` = the entity alias from the submitted metadata. **Requires: aliases are unique across all entities within a study revision.** |

Consequences to internalize:

- Because `{study_pid}` embeds the version, **every non-study entity's accession changes on every
  revision** (e.g. `GHGA.24.ABC.1.mysample` → `GHGA.24.ABC.2.mysample`), even when the entity is
  unchanged. This is expected.
- `XXX` collisions are resolved by retry against a **per-year** uniqueness check (only against
  other `XXX` minted in the same `YY`); `.DS.xxx` collisions by retry within the lineage.

### 2.2 Versioning & replacement (offline)

- `--study-root-pid GHGA.YY.XXX` is an **optional** CLI flag naming the study **lineage** (the root,
  **no** version):
  - **omitted** → a brand-new study: dskit mints a fresh year-unique root `XXX` and starts at `V = 1`
    (`GHGA.YY.XXX.1`);
  - **present** → a revision of that root: offline dskit/metldata computes the next version
    (`V = current max + 1`) and mints `GHGA.YY.XXX.V`.
  There is **no** `--replaces`/`--superseded-by` flag — the steward never states supersede
  relationships; those are inferred service-side (§2.4).
- dskit determines the next version and the predecessor's metadata (its datasets' file-sets, its
  file-entity accessions) from a **local persistent lineage store** it accumulates across
  submissions — i.e. prior revisions are already on disk on the steward workstation from when they
  were submitted. No live-service query is required for submission. **The offline store holds
  submitted metadata only — it has no knowledge of physical file uploads / archived files** (those
  live in ucs/rs and are driven by the UCS upload path; dskit's old S3-upload + FIS-ingest path is
  deprecated and unused). *(Single-workstation assumption; see §7.)*
- **Why offline owns version numbering:** child accessions embed the study version
  (`{study_pid}.{alias}`), so the version must be fixed *before* accessions are minted and the
  metadata is transformed. Service-side metldata therefore cannot renumber after the fact — it can
  only interpret what it receives. This is what makes offline-owns-version the only
  internally-consistent option.

### 2.3 File reuse cardinality

- A physical uploaded file may back **many accessions** — one per study revision that reuses it.
  The registry service's current strict **1:1 `file_id`↔accession** constraint is **relaxed to
  1-file→many-accessions**.
- The steward expresses reuse in the submitted metadata by putting the **predecessor's GHGA file
  accession (PID)** in a dedicated file-entity slot (a new model slot — see §3, metldata/model).
  **dskit does not (and cannot) resolve that PID to a physical file** — the offline side has no view
  of uploads/archived files. It simply carries the prior PID through in the metadata. The binding to
  a physical file, and *all* validation of it, happens **later, at mapping time in the data portal
  (rs)** — see §2.5. The new revision's file entity gets its own `{study_pid}.{alias}` accession;
  rs then binds it to the same `file_id` as the referenced prior accession.

### 2.4 Deprecation & legacy semantics

- Deprecation is tracked **study-level only**, and is **inferred by service-side metldata — not
  declared by the steward.** The steward submits only a study root + version (§2.2); on load,
  metldata parses the lineage/version out of the study PID and applies the rule:
  **a study version is superseded ⇔ a higher version of the same root has been loaded; its
  `superseded_by` = the highest loaded version of that root.** This is monotonic and
  order-independent — re-loads and out-of-order loads converge on the same answer, and loading a new
  highest version supersedes all lower ones. (Consequence: versioning is inherently **linear** — no
  branching.)
- **metldata is the single source of truth for supersede status.** rs, MASS and the portal are
  **consumers**: rs's `Study.superseded_by_id`/`status`
  ([`rs/core/models.py`](../../services/ghga-registry-service/src/rs/core/models.py)) are *populated
  from* the signal metldata emits, **not** computed by rs. (rs already having those fields is why the
  consumed value has a natural home — it is not an authoring role.)
- **Legacy = a newer revision of the same study lineage exists.** Legacy studies' datasets are
  **hidden from search** but remain reachable by URL/PID (`/dataset/{id}`, `/study/{id}`). The
  portal shows an "updated version available" hint that resolves **at study level** (old study →
  newest study revision).
- **Propagation subtlety:** "hidden from search" must **not** equal "deleted/unreachable." The
  signal that removes an old version from the search index must still leave its artifacts queryable
  *and* carry the supersede pointer, so the portal hint and rs's `superseded_by_id` can be set
  (see §4.2).

### 2.5 Mapping / archival decoupling

- **The map↔archive dependency is *inverted*, not removed.** Today mapping is a *prerequisite for*
  archival (a box archives only once all its files are mapped). In the new model, **archival is a
  prerequisite for mapping**: files are archived first (with no mapping required), and mapping is a
  separate, study-centric activity performed **afterwards, against archived boxes**. So: drop the
  "all files mapped" archival gate and the portal's submit-map-then-archive coupling, and instead
  require a box to be archived before its files can be mapped.

### 2.6 Scope

- **In scope:** `tools/ghga-datasteward-kit`, `libs/metldata`, `libs/ghga-event-schemas` (as
  needed), `services/ghga-registry-service`, `services/mass`, `frontend/data-portal`.
- **Out of scope:** the future schemapack services (resource-registry, resource-search),
  `em-transformation-service`, and the schemapack migration itself.

---

## 3. Target end-to-end journey

**Submitting a new revision (offline, dskit):**

1. Steward prepares the new submission's spreadsheet as usual. For any file being reused from a
   prior revision, they put its **prior GHGA file accession (PID)** in that file entity's reuse slot
   instead of providing a new upload. (No offline check is done on that PID — see step 2.)
2. `dskit metadata submit --study-root-pid GHGA.24.ABC ...`:
   - looks up the lineage in the **local lineage store** and computes the next version `V`
     (`= max + 1`; `1` for a brand-new root, in which case dskit also mints the root's year-unique
     `XXX`);
   - mints the new study PID `GHGA.24.ABC.V` and child accessions `{study_pid}.{alias}`; for
     datasets computes the file-set from the metadata and **reuses or regenerates** the `.DS.xxx`
     block accordingly;
   - **carries reuse slots through untouched** — it does not resolve them to physical files.
3. `dskit metadata transform` — unchanged in spirit; the accessions now carry lifecycle structure.
4. `dskit load` — pushes artifacts. **No deprecated-by link is sent** — the payload just carries
   version `V` of the lineage; supersede is inferred service-side.

**Serving:**

5. Service-side metldata loads the artifacts, parses lineage/version from the study PID, and
   **infers supersede** (§2.4): it marks every lower version of the same root as superseded by `V`,
   removes their datasets from the search track while keeping them queryable by URL, and propagates
   the supersede pointer.
6. MASS stops returning the old revisions' datasets. rs and the portal receive the supersede signal
   (rs sets `superseded_by_id`/`status`).
7. The portal shows the newest revision in search; visiting a legacy dataset/study by URL shows the
   "updated version available" hint (resolving to the newest revision of the root).

**File mapping (study-centric, in the data portal — after archival):**

8. Files are uploaded via the UCS box path and **archived** (no mapping required). The steward then
   opens the mapping view for a study/submission, operating on the **archived** box(es):
   - **Files referenced by prior PID** are validated by rs: the referenced accession **must already
     be mapped within the same study lineage**, otherwise mapping is **prevented**. When valid, the
     new file entity's accession is bound to the same `file_id`, and the steward sees the list of
     study revisions each reused file already maps to.
   - **File entities with no reuse PID** are mapped against the archived box(es) originally used as
     the candidate pool, by alias / filename with manual corrections — reusing today's matching UX,
     but now performed against archived boxes rather than gating archival.

---

## 4. Changes by component

### 4.1 `tools/ghga-datasteward-kit` (dskit)

- **Local lineage store.** New persistent local store accumulating, per study lineage: the root
  `GHGA.YY.XXX`, the current max version, and each revision's **submitted metadata** (datasets with
  their file-reference sets, and entity accessions). Populated on every `submit`. This is the
  offline source of truth for versioning and dataset-suffix reuse (§2.2). **It holds metadata
  only** — no knowledge of physical uploads/archived files (dskit's old S3-upload +
  `ingest-upload-metadata` FIS path is deprecated and unused; uploads now go through UCS).
- **`submit` gains `--study-root-pid GHGA.YY.XXX`** (there is no `--replaces`/`--superseded-by`).
  When present: resolve the lineage in the store and compute the next version `V = max + 1`. When
  absent: this is a brand-new study — mint a fresh year-unique root `XXX` and start at `V = 1`.
- **PID minting moves from "random per class" to the lifecycle scheme** (§2.1). This likely means
  dskit drives accession assignment (study PID, `{study_pid}.{alias}`, `{study_pid}.DS.xxx` with
  file-set-based reuse) rather than delegating to metldata's flat `AccessionRegistry`. Decide
  whether to (a) implement the scheme in dskit and feed a pre-built accession map into the
  submission, or (b) push the scheme into metldata's accession layer and have dskit supply the
  lineage context. **(b) keeps accession logic in one place — see §4.2.**
- **File-set-based dataset-suffix reuse.** Compute each dataset's file set from the metadata; diff
  against predecessor datasets in the lineage store; reuse `.DS.xxx` on exact match else mint.
  (Done purely from metadata — no physical-file knowledge needed.)
- **Carry reuse slots through untouched.** File entities referencing a prior GHGA file accession are
  passed through as-is; dskit performs **no** resolution or existence check — the offline side
  can't (§2.3). All reuse validation happens later in rs at mapping time.
- **Uniqueness on submit** — enforce alias uniqueness across all entities within the revision
  (§2.1) and surface a clear error otherwise.

### 4.2 `libs/metldata`

- **Accession scheme.** Replace/augment the flat random `AccessionRegistry`
  (`accession_registry/accession_registry.py:82`) so studies and their children follow the
  lifecycle scheme. Preferred: a lineage-aware accessioning path that, given a study lineage +
  version + alias set + dataset file-sets, produces the structured PIDs, with **per-year**
  uniqueness for study `XXX` (scoped to the `YY` block) and lineage-scoped uniqueness for
  `.DS.xxx`. Keep the accession store, but note the flat-text, linear-scan store
  (`accession_store.py`) is weak for structured uniqueness/version queries — consider a structured
  store.
- **Lineage & version state.** The study PID already encodes lineage (`GHGA.YY.XXX`) and version
  (`V`), so these need not become separate `Submission` fields
  (`submission_registry/models.py:60`). What metldata *does* need is somewhere to persist
  **"highest loaded version per root"** for the supersede inference below — a small registry keyed
  by root. No steward-supplied `replaces` link is stored; supersede is derived.
- **Model slot for reused-file accession.** The LinkML model's file classes need a slot to carry
  the **prior GHGA file accession** (distinct from the existing `ega_accession`). Add it to the
  GHGA model + regenerate artifact models.
- **`studies[0]` assumption.** Revisit `load/collect.py:91` and the one-study-per-submission
  assumptions now that the study is the explicit submission scope. At minimum assert/handle it
  cleanly.
- **Supersede inference at load (metldata is the source of truth).** The loader (`load/api.py`,
  `load/load.py`, `load/event_publisher.py`) must parse the study PID into `root = GHGA.YY.XXX` +
  `version = V`, track the **highest loaded version per root**, and apply the §2.4 rule: on loading
  version `V`, mark every lower version of the same root as superseded by `V`. This is derived
  entirely from the loaded payloads — the steward sends no supersede information. Downstream effect:
  the superseded revisions' primary-dataset resources are **removed from the search track** (emit
  `searchable_resource_deleted`) **while remaining queryable via the artifacts API** for direct URL
  access, and the supersede pointer is propagated so the portal hint + rs's `superseded_by_id` can
  be set. Keep it idempotent/order-independent (re-loads and out-of-order loads must converge). Note
  the loader is today stateless full-state reconciliation, so "highest version per root" is new
  persistent state to add.

### 4.3 `services/ghga-registry-service` (rs)

- **Relax file mapping cardinality to 1-file→many-accessions.**
  `FileController.map_accessions_to_file_ids` / `store_accession_map`
  (`rs/core/files.py:37`, `rs/core/rdub_manager.py:939`) currently reject a `file_id` bound to
  more than one accession and an accession mapped elsewhere. Change the model + validation so one
  `file_id` can carry many `FileAccession` rows (one per revision), while keeping per-accession
  integrity.
- **Invert the archival↔mapping dependency.** Remove the "all files mapped" archival prerequisite
  (`_check_archival_prerequisites`, `rdub_manager.py:314`) and the requirement that
  `store_accession_map` covers every active file, so a box can be archived with no mapping (archival
  then only requires no `init`/`inbox` files at the ucs level). **Conversely, make archival a
  precondition for mapping:** `store_accession_map` today *rejects* archived boxes — that guard
  **inverts** to *require* the box be archived. Files must be archived before they can be mapped.
- **Study-centric mapping surface.** Add/extend endpoints so mapping is driven by study rather
  than by a single box:
  - **PID-referenced files** — for each file entity carrying a prior GHGA file accession, validate
    that the referenced accession **is already mapped within the same study lineage**; if not,
    **prevent the mapping** (hard error — a steward may only reuse files already belonging to their
    own lineage). When valid, bind the new entity accession to that file's `file_id` (the
    one-file→many-accessions case) and report the **list of study revisions the file already maps
    to** (the "for administrative reasons" list — naturally available once cardinality is many).
  - **Unreferenced files** — let the steward add a **pool of archived boxes** (the ones originally
    used) as candidates, then map by alias/filename with manual corrections. The retained
    post-archival box/file inventory (§ Journey B) is the data source.
  - The prior-PID reference must be available to this step (from metldata artifacts or a propagated
    field) so rs can enforce the same-lineage rule (§7).
- **Study lineage & deprecation — rs is a *consumer*, not the author.** Ground truth for supersede
  lives in service-side metldata (§4.2). rs's job is to **receive** the supersede signal and land it
  in the fields its `Study` already has (`superseded_by_id`, `status`) — it does **not** compute
  supersede itself. This likely means the signal rs consumes must carry the supersede pointer (today
  it only gets embedded studies via `SearchableResource`; see §4.6). Separately, plan the transition
  off the interim ingestion bridge (`rs/adapters/inbound/event_sub.py:65` `ResourceSubTranslator` →
  `rs/core/legacy_resources.py`), which fills lifecycle fields with placeholders (forced `ARCHIVED`,
  sentinel creator). **Open:** whether rs even needs `superseded_by_id` populated for the early
  rollout depends on whether the portal hint is served from rs or resolved directly from metldata
  (§4.5) — decide this.

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
2. **Model slot for reused-file accession** (§4.2) — metadata carries the prior PID; resolution +
   validation are deferred to rs at mapping time (§4.3), not done offline.
3. **rs: relax cardinality + invert archival↔mapping** (§4.3) — independent of PIDs; unblocks the
   mapping redesign.
4. **Supersede inference at load → search hiding + supersede propagation** (§4.2, §4.4).
5. **rs study-centric mapping surface** (§4.3).
6. **Portal: mapping UI rework + legacy hint** (§4.5).

Steps 1–2, 3, and 4 are largely independent and can proceed in parallel once the PID scheme is
fixed.

---

## 7. Open questions / risks

- **Lineage store durability & single-workstation assumption.** The offline lineage store is the
  sole source of truth for revisions. What happens if a different steward / machine submits a
  revision, or the store is lost? (Backup/sync story, or a bootstrap-from-service import.)
- **Branching / out-of-order revisions.** With `--study-root-pid` + "highest loaded version wins"
  supersede (§2.4), versioning is inherently **linear** — no branching, and loading an older version
  never un-supersedes. Confirm linear-only is acceptable, and decide what should happen if a version
  arrives out of order or the sequence has a gap.
- **Persistent supersede state in a stateless loader.** metldata's loader is today stateless
  full-state reconciliation, but supersede inference needs to remember the **highest loaded version
  per root** across loads (§4.2). Decide where that state lives, and how "hide from search but keep
  reachable + carry the supersede pointer" is expressed on the wire (event-schema changes — §4.6).
- **Reuse-reference propagation to mapping.** The prior-PID reuse slot is set in offline metadata;
  rs needs it at mapping time to enforce the same-lineage rule and bind the new accession to the
  existing `file_id`. Decide the channel — read from metldata artifacts vs a propagated event field.
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
