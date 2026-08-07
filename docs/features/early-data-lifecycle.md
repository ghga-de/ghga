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

The three user-visible outcomes:

1. **Studies get lifecycle PIDs and can be explicitly replaced.** A data steward **declares** that
   a study replaces one or more existing studies — either when submitting the successor or, later,
   with a dedicated command for two already-submitted studies.
   Superseded studies drop out of search but remain reachable by URL/PID, and the portal shows an
   "an updated version exists" hint.
2. **File upload and file-to-metadata mapping are decoupled and reuse-friendly.** Files can be
   archived without being mapped to metadata. Mapping becomes study-centric and lets a new study
   **reuse already-uploaded files** (by GHGA accession) instead of re-uploading them.
3. **Data stewards can browse archived files.** Because files can now be archived without ever
   being mapped to metadata, a new **file admin panel** lists every archived file in GHGA with its
   identifiers, accessions, studies, the access policy and committee governing it, and its
   originating upload box.

A supporting restriction makes the rest coherent: **one submission carries exactly one study**,
enforced at submit time (§2.6).

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

#### Existing studies keep their legacy identifiers

The new scheme is **not** applied retroactively. Studies already accessioned under the current
flat scheme (`GHGAS` + 14 random digits, and their `GHGAD`/`GHGAF`/… children) **keep those
accessions unchanged** — there is no re-accessioning migration, and their URLs stay valid.

A legacy study only enters the new scheme **when it changes**, i.e. when a successor study is
submitted that replaces it. The successor is a *new* study and is minted under the new scheme; the
legacy predecessor keeps its old PID and simply becomes superseded. Consequently:

- **the supersede relation must work across both schemes** — a `GHGA.YY.XXX.V` study may declare
  that it replaces a legacy `GHGAS…` study. Nothing may assume a predecessor PID is parseable into
  root + version;
- because a legacy PID carries no lineage, a successor replacing one **cannot continue a lineage**
  — it starts a fresh root at `V = 1` (see §2.2);
- both schemes coexist indefinitely in search results, artifact queries and portal URLs.

### 2.2 Replacement is declared by the steward (offline)

The steward **states** replacement explicitly, naming the study being replaced.

**Two ways to declare it:**

1. **At submission time** — `dskit metadata submit --replaces <exact study PID> …`. The flag names
   the **exact PID of the study being replaced** (e.g. `GHGA.24.ABC.1`, or a legacy `GHGAS…`), **not**
   a lineage root. It may be given **more than once** to merge several studies into the successor
   (§2.4).
2. **After the fact** — `dskit metadata replace-study <original study PID> <new study PID>` declares
   the relationship between **two studies that have both already been submitted**. This is the path
   for "we only realised afterwards that B supersedes A", and for merges assembled incrementally.

**Failure rule (both paths):** if the named predecessor **is already replaced** by some other study,
the command **fails**. A study may be replaced only once, so successors form a forest, not a tangle —
each superseded study has exactly one successor, while a successor may have many predecessors.

**Version derivation.** The successor's own PID depends on what it replaces:

- **exactly one predecessor, itself minted under the new scheme** → the successor continues that
  lineage: same root `GHGA.YY.XXX`, `V = predecessor version + 1`;
- **a legacy predecessor** (no parseable lineage — §2.1) → the successor starts a **fresh** root at
  `V = 1`;
- **more than one predecessor (a merge)** → **open**, see §7. A merge cannot continue two lineages
  at once; the choice is between minting a fresh root and designating one predecessor's lineage to
  continue.

**The local study store** (§4.1) holds the **submitted metadata of prior studies** so dskit can:

- compute the next version when continuing a lineage;
- diff dataset file-sets for `.DS.xxx` reuse (§2.1);
- resolve **ancestors** for the file-reuse warnings (§2.3).

It still holds **submitted metadata only** — it has no knowledge of physical file uploads or
archived files (those live in ucs/rs; dskit's old S3-upload + FIS-ingest path is deprecated and
unused). *(Single-workstation assumption; see §7.)*

**Why offline mints the accessions:** child accessions embed the study PID
(`{study_pid}.{alias}`), so the study's PID must be fixed *before* accessions are minted and the
metadata is transformed. Service-side metldata cannot renumber after the fact — it can only record
what it receives.

### 2.3 File reuse cardinality

- A physical uploaded file may back **many accessions** — one per study that reuses it. The
  accession↔file relation becomes **many-to-one**: `accession → file` stays **single-valued** (an
  accession always resolves to exactly one file, and that binding is immutable once set), while a
  file may be referenced by many accessions. Today the relation is 1:1; the registry service's
  per-request bijection is what relaxes.
- The steward expresses reuse in the submitted metadata by putting the **prior GHGA file
  accession (PID)** in a dedicated file-entity slot (a new model slot — see §3, metldata/model).
  **dskit does not (and cannot) resolve that PID to a physical file** — the offline side has no view
  of uploads/archived files. It simply carries the prior PID through in the metadata. The binding to
  a physical file happens **later, at mapping time in the data portal (rs)** — see §2.5. The new
  study's file entity gets its own `{study_pid}.{alias}` accession; rs then binds it to the same
  `file_id` as the referenced prior accession.

#### Reuse checks are offline warnings, not service-side rejections

Merging (§2.4) makes any "the reused file must belong to my own lineage" rule unworkable — after a
merge there is no single lineage to belong to. The same-lineage **hard check in rs is therefore
dropped**. In its place, **dskit warns at submit time and asks the steward to confirm**. All three
checks are decidable from submitted metadata alone, so they need no view of physical files:

| # | condition | steward sees |
|---|---|---|
| 1 | the study reuses files but **declares no predecessor** | warning + confirm |
| 2 | the study declares predecessor(s), but some reused file accessions **occur in no ancestor** of those predecessors | warning + confirm (naming the offending accessions) |
| 3 | for the reused files, the `data_access_policy` — **including its nested `data_access_committee`** — reachable via their dataset(s) does **not match exactly** what applied before | warning that the submission would **place files under new governance** + confirm |

All three are **warnings the steward may override**, not errors. They exist to catch accidental
reuse and accidental governance changes, not to prevent deliberate ones. Check 3 compares the
governing attributes per **file**, since a file may sit in datasets with different policies.

### 2.4 Deprecation & legacy semantics

- Deprecation is tracked **study-level only**, and is **declared by the steward** (§2.2) — never
  the declared relation travels with the submission, and metldata **records** it.
- **Many predecessors, one successor.** Several studies may be replaced by the *same* successor —
  this is how **merging** studies is expressed. Combined with the "a study may be replaced only
  once" rule (§2.2), the successor relation is **single-valued in the forward direction**: from any
  study there is exactly one successor, so following the chain from a legacy study always terminates
  at a unique newest study. This is what makes the portal hint well-defined even under merges.
- **metldata is the single source of truth for supersede status** *as served*. rs, MASS and the
  portal are **consumers**: rs's `Study.superseded_by_id`/`status`
  ([`rs/core/models.py`](../../services/ghga-registry-service/src/rs/core/models.py)) are *populated
  from* the signal metldata emits, **not** computed by rs. (rs already having those fields is why the
  consumed value has a natural home — it is not an authoring role.) metldata **persists and
  propagates what the steward declared**.
- **Legacy = a successor has been declared for this study.** Legacy studies' datasets are **hidden
  from search** but remain reachable by URL/PID (`/dataset/{id}`, `/study/{id}`). The portal shows an
  "updated version available" hint that resolves **at study level**, following the successor chain
  to its terminal study.
- **A supersede relation may be established long after both studies were loaded**
  (`replace-study`, §2.2), so loading is not the only moment supersede status can change — see §4.2.
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

### 2.6 One submission carries exactly one study

The study is the defining scope of a submission, and this stops being a convention and becomes an
**enforced restriction**: **dskit rejects any submission whose metadata contains more than one
study**, with a clear error naming the studies found.

This is what makes the rest of the design coherent — every child accession is derived from *the*
study PID (§2.1), replacement is declared per study (§2.2), and supersede is study-level (§2.4).
None of those have a defined meaning for a two-study submission.

It also retires a latent defect rather than preserving it. The current loader takes
`content["studies"][0]["accession"]` for publishable artifacts
([`load/collect.py:91`](../../libs/metldata/src/metldata/load/collect.py)) and **silently discards
any further studies** — a two-study submission loads today without error while only the first study
is attributed. Enforcing one study at submit turns that silent truncation into an up-front rejection.

> **Implementation consequence.** The integration test bed's example metadata is currently a
> **single submission containing two studies** (`STUDY_A`, `STUDY_B`, mapped to separate upload
> boxes in `202_upload_completed.feature`). It exercises exactly the case this rule forbids, and
> would have to be split into two submissions. Its metadata-download scenario only asserts the
> workbook for `DS_A`, which is why the existing truncation goes unnoticed today.

### 2.7 Scope

- **In scope:** `tools/ghga-datasteward-kit`, `libs/metldata`, `libs/ghga-event-schemas` (as
  needed), `services/ghga-registry-service`, `services/mass`, `frontend/data-portal`.
- **Out of scope:** the future schemapack services (resource-registry, resource-search),
  `em-transformation-service`, and the schemapack migration itself.

---

## 3. Target end-to-end journey

**Submitting a successor study (offline, dskit):**

1. Steward prepares the submission's spreadsheet as usual — **exactly one study** (§2.6). For any
   file being reused from an earlier study, they put its **prior GHGA file accession (PID)** in that
   file entity's reuse slot instead of providing a new upload.
2. `dskit metadata submit --replaces GHGA.24.ABC.1 …` (the flag may be repeated to merge several
   predecessors; omitted entirely for a brand-new study):
   - **rejects** the submission if it contains more than one study, or if any named predecessor is
     already replaced (§2.2);
   - mints the study PID — continuing the predecessor's lineage where that is defined, otherwise a
     fresh root at `V = 1` (§2.2) — plus child accessions `{study_pid}.{alias}`, reusing or
     regenerating each dataset's `.DS.xxx` block from its file-set;
   - runs the three **reuse warnings** (§2.3) and asks the steward to confirm any that trigger;
   - **carries reuse slots through untouched** — it does not resolve them to physical files;
   - records the declared replacement so it travels with the submission.
3. `dskit metadata transform` — unchanged in spirit; the accessions now carry lifecycle structure.
4. `dskit load` — pushes artifacts **together with the declared replacement**.

   *Or, for two studies already submitted:* `dskit metadata replace-study <old PID> <new PID>`
   declares the relationship after the fact, failing if the old study is already replaced.

**Serving:**

5. Service-side metldata **records** the declared replacement (§2.4). Every
   named predecessor is marked superseded by the successor, their datasets leave the search track
   while staying queryable by URL, and the supersede pointer is propagated.
6. MASS stops returning the superseded studies' datasets. rs and the portal receive the supersede
   signal (rs sets `superseded_by_id`/`status`).
7. The portal shows the successor in search; visiting a superseded dataset/study by URL shows the
   "updated version available" hint, resolved by following the successor chain to its terminal
   study.

**File mapping (study-centric, in the data portal — after archival):**

8. Files are uploaded via the UCS box path and **archived** (no mapping required). The steward then
   opens the mapping view for a study, operating on the **archived** box(es):
   - **Files referenced by prior PID** — rs binds the new file entity's accession to the same
     `file_id` as the referenced accession, and shows the steward every study that file already maps
     to. There is **no same-lineage gate** here; the judgement was made offline at submit time via
     the §2.3 warnings.
   - **File entities with no reuse PID** are mapped against the archived box(es) originally used as
     the candidate pool, by alias / filename with manual corrections — reusing today's matching UX,
     but now performed against archived boxes rather than gating archival.

**Browsing archived files (data portal, steward-only):**

9. The **file admin panel** lists every archived file in GHGA — including files that are archived
   but not (yet) mapped to any metadata, which nothing surfaces today (§4.3, §4.5).

---

## 4. Changes by component

### 4.1 `tools/ghga-datasteward-kit` (dskit)

- **Reject multi-study submissions (§2.6).** Validate at `submit` that the metadata contains exactly
  one study; error out naming the studies found. This is the single most load-bearing new
  precondition — everything downstream derives from *the* study.
- **Local study store.** New persistent local store accumulating, per submitted study: its PID, the
  studies it declares it **replaces**, and its **submitted metadata** (datasets with their
  file-reference sets, entity accessions, and the `data_access_policy`/`data_access_committee`
  attributes needed by warning 3). Populated on every `submit` and updated by `replace-study`. It
  backs version continuation, `.DS.xxx` reuse, and **ancestor resolution** for the §2.3 warnings.
  **It holds metadata only** — no knowledge of physical uploads/archived files (dskit's old
  S3-upload + `ingest-upload-metadata` FIS path is deprecated and unused; uploads go through UCS).
- **`submit` gains `--replaces <exact study PID>`, repeatable** (§2.2). Not a lineage root — the
  exact PID, which may be a legacy `GHGAS…` accession. Repeating it expresses a **merge**. Fail if
  any named predecessor is already replaced. Derive the successor's own PID per §2.2.
- **New command `metadata replace-study <old PID> <new PID>`** declaring the relationship between
  two already-submitted studies, with the same already-replaced failure rule. Needed both for
  after-the-fact corrections and for assembling merges incrementally. Decide how the declaration
  reaches the services when no submission is in flight — it must produce something loadable rather
  than only mutating local state (§7).
- **Three reuse warnings at submit (§2.3),** each an override-able confirmation, not an error:
  no declared predecessor; reused accessions absent from every ancestor; governance
  (`data_access_policy` + nested `data_access_committee`) differing per file from what applied
  before. All are computed from the local study store — no service calls, no view of physical files.
  Provide a non-interactive escape hatch (e.g. `--yes`) so scripted submissions don't hang.
- **PID minting moves from "random per class" to the lifecycle scheme** (§2.1). This likely means
  dskit drives accession assignment (study PID, `{study_pid}.{alias}`, `{study_pid}.DS.xxx` with
  file-set-based reuse) rather than delegating to metldata's flat `AccessionRegistry`. Decide
  whether to (a) implement the scheme in dskit and feed a pre-built accession map into the
  submission, or (b) push the scheme into metldata's accession layer and have dskit supply the
  lineage context. **(b) keeps accession logic in one place — see §4.2.**
- **File-set-based dataset-suffix reuse.** Compute each dataset's file set from the metadata; diff
  against predecessor datasets in the study store; reuse `.DS.xxx` on exact match else mint.
  (Done purely from metadata — no physical-file knowledge needed.)
- **Carry reuse slots through untouched.** File entities referencing a prior GHGA file accession are
  passed through as-is; dskit performs **no** resolution to a physical file — the offline side
  can't (§2.3). What dskit *does* do is the metadata-level warning checks above; reuse is judged
  offline, not at mapping time.
- **Uniqueness on submit** — enforce alias uniqueness across all entities within the study
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
- **Declared-replacement state.** metldata must persist the **declared** relation
  `predecessor PID → successor PID` (many predecessors may point at one successor, §2.4). This is
  received rather than computed, and no PID parsing is involved in deciding supersede — a
  predecessor may be a legacy `GHGAS…` accession with no version at all (§2.1). Enforce the invariant that a predecessor appears **at most once** as a
  key, so the successor chain stays single-valued.
- **Model slot for reused-file accession.** The LinkML model's file classes need a slot to carry
  the **prior GHGA file accession** (distinct from the existing `ega_accession`). Add it to the
  GHGA model + regenerate artifact models.
- **`studies[0]` — enforce, don't tolerate.** With one study per submission now a hard rule (§2.6),
  `load/collect.py:91` should **assert** a single study and fail loudly otherwise, replacing today's
  silent `[0]` truncation. dskit rejects multi-study submissions upstream, but the loader is a
  separate trust boundary and should not depend on that.
- **Record supersede at load, and out of band.** The loader (`load/api.py`, `load/load.py`,
  `load/event_publisher.py`) applies the replacement **carried in the payload**: mark each named
  predecessor superseded by the successor, remove the superseded studies' primary-dataset resources
  from the search track (emit `searchable_resource_deleted`) **while keeping them queryable via the
  artifacts API** for direct URL access, and propagate the supersede pointer so the portal hint and
  rs's `superseded_by_id` can be set. Reject a declaration whose predecessor is already replaced.
  Two consequences of declaration-based supersede:
  - **it must also work with no submission in flight** — `replace-study` (§4.1) declares a relation
    between two already-loaded studies, so there needs to be a path that applies a replacement
    without re-loading artifacts (§7);
  - **load order matters.** A declaration naming a predecessor that has not been loaded yet has to
    be handled explicitly — reject, or hold pending. Decide which (§7). Re-applying the same
    declaration must stay idempotent.

### 4.3 `services/ghga-registry-service` (rs)

- **Relax the accession↔file relation from 1:1 to many-to-one.** No schema change or migration is
  needed: `FileAccession` is already keyed by `pid` with `file_id` as an ordinary nullable field
  (`id_field="pid"`, no unique index), so many accessions pointing at one file already fit the
  store. What enforces 1:1 today is **request validation** in `store_accession_map`
  (`rs/core/rdub_manager.py`, `store_accession_map`): the no-duplicate-`file_id` check plus the
  "every active file in the box must be mapped" check together force each submission to be a
  bijection over the box's files. Those are what relax. **Keep** the per-accession guard in
  `FileController.map_accessions_to_file_ids` (`rs/core/files.py:37`) that rejects re-binding an
  already-mapped accession to a different `file_id` or study — that is exactly the single-valued
  `accession → file` direction the design preserves (§2.3).
- **Invert the archival↔mapping dependency.** Remove the "all files mapped" archival prerequisite
  (`_check_archival_prerequisites`, `rdub_manager.py:314`) and the requirement that
  `store_accession_map` covers every active file, so a box can be archived with no mapping (archival
  then only requires no `init`/`inbox` files at the ucs level). **Conversely, make archival a
  precondition for mapping:** `store_accession_map` today *rejects* archived boxes — that guard
  **inverts** to *require* the box be archived. Files must be archived before they can be mapped.
- **Study-centric mapping surface.** Add/extend endpoints so mapping is driven by study rather
  than by a single box:
  - **PID-referenced files** — for each file entity carrying a prior GHGA file accession, bind the
    new entity's accession to that file's `file_id` (the many-to-one case) and report the **list of
    studies the file already maps to** (the "for administrative reasons" list — naturally available
    once the relation is many-to-one). **There is no same-lineage validation here.** Merging (§2.4)
    removes any single lineage to validate against; the judgement is made offline instead, by the
    §2.3 warnings the steward confirms at submit time. rs still verifies the referenced accession
    exists and is mapped.
  - **Unreferenced files** — let the steward add a **pool of archived boxes** (the ones originally
    used) as candidates, then map by alias/filename with manual corrections. The retained
    post-archival box/file inventory (§ Journey B) is the data source.
  - The prior-PID reference must be available to this step (from metldata artifacts or a propagated
    field) so rs can resolve it to the existing `file_id` (§7).
- **File admin panel API (new).** Because files can now be archived without ever being mapped, no
  existing surface lists them — the box view is per-box and the study view only shows mapped
  accessions. Add a steward-only, paginated, searchable listing over **all archived files**, each
  row carrying:
  | field | source |
  |---|---|
  | file UUID (`file_id`) | ucs `FileUpload` |
  | GHGA accession(s) — **plural** | `FileAccession` rows for that `file_id` (many-to-one) |
  | study/studies | `FileAccession.study_id` per accession |
  | **governing `data_access_policy` + nested `data_access_committee`** | resolved per accession via that file entity's dataset(s) in the metadata artifacts |
  | file upload box | the RDUB/FUB the upload belongs to |
  | upload box alias | `FileUpload.alias` |
  
  Legacy files that never came through an upload box have **no box and no alias** — those columns
  are empty rather than omitted, and the listing must not assume a box exists.

  Two notes on the governance column. It is the **same file → dataset → policy → committee**
  resolution the reuse warning uses (§2.3, warning 3), so the two should share one implementation
  rather than drift apart. And because a file may back several accessions across several studies —
  and may sit in datasets with different policies — the column is **per accession, not per file**,
  and can legitimately show more than one policy for the same physical file. That is precisely the
  situation warning 3 exists to make deliberate, so seeing it here is the audit trail for it.

  This is also the first read path that starts from `file_id` rather than from a box or an
  accession, so it wants an index on `FileAccession.file_id` (none today — the collection is keyed
  by `pid`). The governance lookup additionally reaches into metldata's artifacts, so decide whether
  rs joins that at read time or the portal fetches it alongside (§7).
- **Study deprecation — rs is a *consumer*, not the author.** The steward authors the relation
  (§2.2) and metldata records and propagates it (§4.2). rs's job is to **receive** the supersede
  signal and land it in the fields its `Study` already has (`superseded_by_id`, `status`) — it
  neither computes nor originates it. Note `superseded_by_id` is single-valued, which matches the
  single-valued successor direction (§2.4); it is the *predecessor* side that is many. This likely means the signal rs consumes must carry the supersede pointer (today
  it only gets embedded studies via `SearchableResource`; see §4.6). Separately, plan the transition
  off the interim ingestion bridge (`rs/adapters/inbound/event_sub.py:65` `ResourceSubTranslator` →
  `rs/core/legacy_resources.py`), which fills lifecycle fields with placeholders (forced `ARCHIVED`,
  sentinel creator). **Open:** whether rs even needs `superseded_by_id` populated for the early
  rollout depends on whether the portal hint is served from rs or resolved directly from metldata
  (§4.5) — decide this.

### 4.4 `services/mass`

- **Hide superseded datasets from search.** MASS is event-driven and does no diffing, so hiding is
  achieved by the upstream deletion signal (§4.2): when a replacement is declared, the superseded
  studies' datasets receive `searchable_resource_deleted` and drop out of the index. Note this now
  also has to fire for an **out-of-band** `replace-study` declaration (§4.1), not only as part of
  loading a successor's artifacts. Verify no MASS change is needed beyond
  that; if we instead want a "hidden" flag retained in MASS (e.g. for an admin/steward search that
  *can* see legacy), add a filterable field + query option.

### 4.5 `frontend/data-portal`

- **"Updated version available" hint.** On `dataset/:id` and `study/:id`, detect that the entity
  belongs to a superseded study and render a hint linking to its successor — following the chain to
  the terminal study (§2.4). Needs an API to resolve the successor (from rs and/or metldata
  artifacts). Because merges exist, the hint may lead from several old studies to the *same*
  successor; the reverse ("this study replaced A, B and C") is a separate, optional affordance.
- **Study-centric mapping UI.** Rework
  `frontend/data-portal/src/app/upload/features/upload-box-mapping/` and related services from
  box-centric to study-centric: select a study; show confirmed reused-file entities + the "already
  maps to studies X, Y" info; for unmapped entities let the steward choose a pool of archived
  boxes and map by alias/filename with manual corrections. Remove the submit-map-then-archive
  coupling; archival becomes an independent action.
- **Reused-file affordances.** Surface, in the mapping view, which entities are satisfied by a
  prior GHGA accession vs need a physical file.
- **File admin panel (new, steward-only).** A browsable table over every archived file in GHGA,
  backed by the rs listing (§4.3): file UUID, GHGA accession(s), study/studies, the governing
  `data_access_policy` and its nested `data_access_committee`, upload box, and box alias — with the
  box columns empty for legacy files that never came through a box. This is the
  only place an **archived-but-unmapped** file becomes visible, which is why it is part of this
  feature rather than a follow-up: decoupling archival from mapping (§2.5) is what creates files
  that no other view can reach. Expect it to be used to *find* the files a later mapping pass needs,
  so filtering by mapped/unmapped and by box matters more than pretty formatting.

### 4.6 `libs/ghga-event-schemas`

- Add any new fields required to carry the **declared replacement** through the events that
  rs/mass/wps/dins consume (e.g. on `MetadataDatasetOverview` / `SearchableResource`), per the
  propagation chosen in §4.2. Keep changes additive and mind the single-version source-coupling in
  this monorepo (all consumers see one schema version).
- **No change is needed for the many-to-one file relation.** `FileAccessionMapping` is already
  emitted per accession carrying its `file_id`, so *N* accessions on one file simply produce *N*
  events; both consumers (dins, wps) store and delete **by accession**, not by file. Worth a test
  rather than an assumption in dins, whose `PendingFileInfo` merge is keyed by `file_id` and is the
  one place a shared file meets a reverse lookup.

---

## 5. Cross-cutting invariants to preserve

- **One study per submission** (§2.6) — enforced in dskit and asserted in the loader.
- **Alias uniqueness within a study** is now load-bearing (child accessions derive from alias).
  Enforce at submit.
- **A study may be replaced at most once**, so the successor chain stays single-valued and the
  portal hint always resolves (§2.2, §2.4).
- **`accession → file` stays single-valued and immutable once bound**; only the file → accession
  direction becomes many (§2.3).
- **Legacy PIDs remain valid forever.** Existing `GHGAS…`-style accessions are never rewritten, and
  nothing may assume a study PID is parseable into root + version (§2.1).
- **Legacy reachability:** superseded datasets/studies must stay resolvable via the artifacts query
  API and portal URLs even after leaving search. Don't delete their stored artifacts when hiding
  them from search.
- **Idempotency:** downstream consumers already tolerate missing targets; keep re-load /
  re-declare operations idempotent.

---

## 6. Suggested implementation order

0. **One-study enforcement** (§2.6) — small, and every later step assumes it. Splitting the test
   bed's two-study example metadata is part of this step, not a follow-up.
1. **PID scheme + study store in dskit/metldata** (§4.1, §4.2 accession parts) — everything else
   depends on the new accessions existing. Land with unit tests for format, uniqueness, version
   continuation, legacy-predecessor handling, and dataset file-set reuse.
2. **Model slot for reused-file accession** (§4.2) — metadata carries the prior PID; binding to a
   physical file is deferred to rs at mapping time (§4.3).
3. **rs: relax the cardinality validation + invert archival↔mapping** (§4.3) — independent of PIDs;
   unblocks both the mapping redesign and the admin panel.
4. **Declared replacement: `--replaces` + `replace-study` → recording, search hiding, propagation**
   (§4.1, §4.2, §4.4), including the reuse warnings (§2.3) that depend on the study store.
5. **rs study-centric mapping surface + file admin panel API** (§4.3).
6. **Portal: mapping UI rework, legacy hint, file admin panel** (§4.5).

Steps 1–2, 3, and 4 are largely independent once step 0 and the PID scheme are fixed. The **file
admin panel (3 → 5 → 6) is the one strand that can ship on its own**: it depends only on the
archival↔mapping inversion, not on PIDs or replacement, and it is what keeps archived-but-unmapped
files from becoming invisible the moment that inversion lands.

---

## 7. Open questions / risks

- **What PID does a merge successor get?** (§2.2) A study replacing **two or more** predecessors
  cannot continue two lineages. Options: mint a fresh root at `V = 1`, or designate one
  predecessor's lineage to continue. This is the one PID rule the design does not yet fix, and it
  also decides whether `.DS.xxx` reuse can span a merge.
- **Study store durability & single-workstation assumption.** The offline store is the sole source
  of ancestor metadata for the reuse warnings and of version continuation. What happens if a
  different steward / machine submits, or the store is lost? (Backup/sync story, or a
  bootstrap-from-service import.) Note the warnings degrade **silently** — a missing ancestor looks
  like "reused file not found in any ancestor", i.e. warning 2 fires spuriously.
- **How does an out-of-band `replace-study` reach the services?** (§4.1, §4.2) Declaring a relation
  between two already-loaded studies has no artifacts to ride along with. Decide whether it produces
  a loadable payload, calls a dedicated endpoint, or emits its own event — and how it is
  authenticated, since it changes what the public sees without a submission.
- **Declaration arriving before its predecessor is loaded.** (§4.2) Reject, or hold pending and
  apply later?
- **Confirmation UX for the reuse warnings.** (§2.3) They are interactive prompts in a CLI that is
  also run from scripts and CI. Decide the non-interactive contract (`--yes`, per-warning flags, or
  a machine-readable pre-flight) so automation neither hangs nor silently auto-confirms governance
  changes.
- **Governance comparison scope.** (§2.3, warning 3) "All properties match exactly" — which
  properties, and how deep into the nested `data_access_committee`? Field-by-field equality, or
  identity of the policy/committee entity? A file may also sit in several datasets with different
  policies; define whether *any* mismatch warns or only a net change.
- **Reuse-reference propagation to mapping.** The prior-PID reuse slot is set in offline metadata;
  rs needs it at mapping time to resolve it to the existing `file_id`. Decide the channel — read
  from metldata artifacts vs a propagated event field.
- **Interim ingestion bridge retirement.** rs currently derives its (forward-looking) Study +
  unmapped-FileAccession state from metldata's `SearchableResource` events via the interim bridge,
  filling lifecycle fields with placeholders. As rs is fed real lifecycle data, clarify the
  transition: does the bridge still seed unmapped accessions in the early rollout, or does a new
  study-centric flow replace it — and when is the `ResourceSubTranslator`/`LegacyResourceManager`
  consumer removed?
- **Dataset file-set equality definition.** "Exactly identical set of files" — by physical file
  identity (reused accession / file_id) or by the metadata file entities? Nail this down; it
  drives `.DS.xxx` reuse and therefore URL stability of datasets across revisions.
- **Scale of the file admin panel.** (§4.3, §4.5) The listing is unbounded by design — every
  archived file in GHGA. Confirm pagination/filtering are enough, and add the `FileAccession.file_id`
  index the reverse lookup needs.
- **`ega_accession` vs new reuse slot.** Ensure the new prior-GHGA-accession slot is clearly
  distinct from the existing `ega_accession` slot and from each entity's own minted accession.
