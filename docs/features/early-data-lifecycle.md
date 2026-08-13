# Early Data Lifecycle Rollout — Developer Guide

> **Audience.** Developers implementing the feature across dskit, metldata, the registry
> service, MASS, dins and the data portal.
>
> **Read first.** [`docs/architecture/metadata-and-file-journeys.md`](../architecture/metadata-and-file-journeys.md)
> — the current-state map this document builds on. RDUB, FUB, primary dataset source,
> legacy resource seeding and the mapping flow are defined there.
>
> **Status.** Design agreed, not yet implemented. §7 lists what is still open.

---

## 1. What we are trying to achieve

A submission could in principle contain several studies, but in practice each contains one, and
there is no notion of study identity, versioning or replacement. A re-submission mints fresh random
accessions with no link back to what it supersedes.

The long-term plan replaces LinkML with schemapack and adds dedicated backend services
(resource-registry, resource-search, experimental-metadata transformation) alongside the new
`ghga-registry-service`. There the study becomes the defining scope of a submission and every other
entity is semantically a child of it. Studies receive a structured PID and can be revised: a
revision supersedes the earlier version, which becomes *legacy* — reachable by URL/PID but hidden
from search.

This document describes a smaller step we can take first: rolling out the data lifecycle on the
existing stack — LinkML plus offline metadata management via `ghga-datasteward-kit` — so we can
issue lifecycle PIDs and handle revisions before the schemapack services land. It stays within
dskit, metldata, MASS, registry-service and data-portal. The schemapack services are out of scope.

Three user-visible outcomes:

1. **Studies get lifecycle PIDs and can be explicitly replaced.** A data steward declares that a
   study replaces one or more existing studies, either when submitting the successor or later, with
   a dedicated command for two already-submitted studies. Superseded studies drop out of search but
   stay reachable by URL/PID, and the portal shows an "updated version available" hint.
2. **File upload and file-to-metadata mapping are decoupled.** Files can be archived without being
   mapped to metadata. Mapping becomes study-centric and lets a new study reuse already-uploaded
   files by GHGA accession instead of re-uploading them.
3. **Data stewards can browse archived files.** Since files can now be archived without ever being
   mapped, a new file admin panel lists every archived file in GHGA with its identifiers,
   accessions, studies, the access policy and committee governing it, and its originating upload
   box.

All of this depends on one new restriction: a submission carries exactly one study, enforced at
submit time (§2.6).

---

## 2. Locked design decisions

### 2.1 PID scheme

| Entity | PID format | Notes |
|---|---|---|
| **Study** | `GHGA.YY.XXX.V` | `YY` = 2-digit year, unchanged by later revisions. `XXX` = 3 base32 characters (`[A-Z2-7]`, RFC 4648 — no `0/1/8/9`), unique within the year rather than globally, so 32³ = 32,768 studies per year. `V` = version counter, starts at 1 and increments per revision. Since `YY` never changes, `GHGA.YY.XXX` is still unique overall (year + year-unique random), though the same `XXX` may recur in a different year. |
| **Lineage root** | `GHGA.YY.XXX` | The study's lineage identity, stable across all revisions of one study; only `.V` changes. |
| **Dataset** | `{study_pid}.DS.[A-Z2-7]{3}` | Random 3-character base32 block, unique within the study lineage. **Reuse rule:** if a dataset's file set is identical to a predecessor-revision dataset, its `.DS.xxx` block is reused; otherwise a fresh one is generated. |
| **Every other entity** | `{study_pid}.{alias}` | `alias` = the entity alias from the submitted metadata. **Requires** aliases to be unique across all entities within a study revision. |

Consequences:

- Because `{study_pid}` embeds the version, every non-study accession changes on every revision
  (`GHGA.24.ABC.1.mysample` → `GHGA.24.ABC.2.mysample`), even for an unchanged entity. This is
  expected.
- `XXX` collisions are resolved by retry against a per-year uniqueness check, i.e. only against
  other `XXX` minted in the same `YY`. `.DS.xxx` collisions are resolved by retry within the
  lineage.
- **"Identical file set"** is compared over the reuse-slot accessions in the submitted metadata
  (§2.3), not over physical files and not over the entities' own accessions.

#### Existing studies keep their legacy identifiers

The new scheme is not applied retroactively. Studies already accessioned under the current flat
scheme (`GHGAS` + 14 random digits, and their `GHGAD`/`GHGAF`/… children) keep those accessions.
There is no re-accessioning migration, and their URLs stay valid.

A legacy study enters the new scheme only when a successor study replaces it. The successor is
minted under the new scheme; the legacy predecessor keeps its old PID and becomes superseded.
So:

- the supersede relation must work across both schemes — a `GHGA.YY.XXX.V` study may declare that it
  replaces a legacy `GHGAS…` study, and nothing may assume a predecessor PID is parseable into root
  + version;
- a legacy PID carries no lineage, so a successor replacing one starts a fresh root at `V = 1`
  (§2.2) — not `V = 2`, which would leave `GHGA.YY.XXX.1` permanently unresolvable and has no
  defined value when several legacy studies merge;
  (§2.2);
- both schemes coexist indefinitely in search results, artifact queries and portal URLs.

### 2.2 Replacement is declared by the steward (offline)

The steward states replacement explicitly, naming the study being replaced. There are two ways:

1. **At submission time** — `dskit metadata submit --replaces <exact study PID> …`. The flag names
   the exact PID of the study being replaced (e.g. `GHGA.24.ABC.1`, or a legacy `GHGAS…`), **not** a
   lineage root. It may be given more than once to merge several studies into the successor (§2.4).
2. **After the fact** — `dskit metadata replace-study <original study PID> <new study PID>` declares
   the relationship between two studies that have both already been submitted. This covers "we only
   realised afterwards that B supersedes A", and merges assembled incrementally.

**Failure rules (both paths).** The command fails if either holds:

1. the named predecessor is already replaced by another study. A study may be replaced only once, so
   each superseded study has exactly one successor, while a successor may have many predecessors;
2. following the predecessor's successor chain already reaches the successor. Rule 1 alone does not
   prevent this: after `A → B`, a steward correcting a mistake with `replace-study B A` passes rule 1
   (B is not yet replaced) and closes a cycle, after which "follow the chain to the newest study"
   (§2.4) never terminates.

Together the two rules keep the successor relation a forest. Both are decided offline by dskit,
walking the successor chain in the submission store; the loader trusts its payload and does not
re-derive the relation (§5).

**Version derivation.** The successor's own PID depends on what it replaces:

- **exactly one predecessor, itself minted under the new scheme** → the successor continues that
  lineage: same root `GHGA.YY.XXX`, `V = predecessor version + 1`;
- **a legacy predecessor** (no parseable lineage, §2.1) → the successor starts a fresh root at
  `V = 1`;
- **more than one predecessor (a merge)** → the steward chooses. A merge cannot continue two
  lineages at once, so dskit prompts at submit time: continue one named predecessor's lineage (that
  study's root, `V = its version + 1`), or mint a fresh root at `V = 1`.

**The submission store** (§4.2) holds the submitted metadata of prior studies, so dskit can compute
the next version when continuing a lineage, diff dataset file-sets for `.DS.xxx` reuse (§2.1), and
resolve ancestors for the file-reuse warnings (§2.3).

This is metldata's **existing** submission store, not a new one: with one study per submission
(§2.6) every prior study is already in it, and the declared replacement is added to the record.
It holds submitted metadata only. The store lives on the data steward VM, which is the trusted
source of truth and is backed up as a VM, so its durability is not a lifecycle concern.

**Why offline mints the accessions.** Child accessions embed the study PID (`{study_pid}.{alias}`),
so the study's PID must be fixed *before* accessions are minted and the metadata is transformed.
Service-side metldata cannot renumber after the fact; it can only record what it receives.

### 2.3 File reuse cardinality

- A physical uploaded file may back many accessions, one per study that reuses it. The
  accession↔file relation becomes **many-to-one**: `accession → file` stays single-valued (an
  accession always resolves to exactly one file, and that binding is immutable once set), while a
  file may be referenced by many accessions. Today the relation is 1:1; what relaxes is the registry
  service's per-request bijection.
- The steward expresses reuse in the submitted metadata by putting the prior GHGA file accession
  (PID) in that file entity's **reuse slot** (a new model slot, §4.2). dskit does not
  resolve that PID to a physical file and cannot — the offline side has no view of uploads or
  archived files. It carries the prior PID through in the metadata. The binding to a physical file
  happens later, at mapping time in the data portal (via rs), see §2.5: the new study's file entity gets
  its own `{study_pid}.{alias}` accession, and rs binds it to the same `file_id` as the referenced
  prior accession.

#### Reuse checks are offline warnings, not service-side rejections

Merging (§2.4) makes any "the reused file must belong to my own lineage" rule unworkable, since
after a merge there is no single lineage to belong to. The same-lineage hard check in the registry service is
therefore dropped. In its place, dskit warns at submit time and asks the steward to confirm. All
three checks are decidable from submitted metadata alone, so they need no view of physical files:

| # | condition | steward sees |
|---|---|---|
| 1 | the study reuses files but declares no predecessor | warning + confirm |
| 2 | the study declares predecessor(s), but some reused file accessions occur in no ancestor of those predecessors | warning + confirm, naming the offending accessions |
| 3 | for the reused files, the `data_access_policy` — including its nested `data_access_committee` — reachable via their dataset(s) does not match what applied before | warning that the submission would place files under new governance + confirm |

All three are warnings the steward may override, not errors. They catch accidental reuse and
accidental governance changes.

**Check 3 compares all DAP/DAC attributes, never accessions or aliases.** It runs per file, since a
file may sit in datasets with different policies. Comparing the alias segment is tempting, because
an unchanged committee usually keeps its alias, but it misses a steward who keeps the alias while
editing the committee's membership, has nothing to compare for legacy predecessors (§2.1), and means
nothing across a merge, where aliases from different lineages are unrelated strings. The attributes
are already in the submission store, so field-by-field comparison costs no service call; accessions
only name the differing entity in the message.

The case the check exists for is a file becoming subject to additional DACs — a governance change
even when every other attribute is untouched — so the warning must name the committees that would
gain authority. The standing view of who governs what is the file admin panel, which lists the DAP
and DAC for each archived file (§4.5).

#### DINS must key file information by file, not by accession

IFRS announces a file's size, checksum and storage alias **once**, at archival. DINS treats that as
a one-time hand-off: it parks the payload keyed by `file_id`, merges it into the first accession that
claims it, and **deletes it**.
Under reuse a second accession is mapped much later (§2.5), IFRS never re-announces, and nothing is
left to merge — so the dataset page shows blank size and checksum indefinitely, with only a "still
waiting for `FileInternallyRegistered`" log line to explain it.

DINS must therefore retain the per-file data instead of consuming it, serve it to any accession bound
to that file however late it appears, and clear all such accessions when the file is deleted
(`delete_file_information` currently resolves a `file_id` to just one).

### 2.4 Deprecation & legacy semantics

- Deprecation is tracked study-level only and is declared by the steward (§2.2): the declared
  relation travels with the submission, and metldata records it.
- **Many predecessors, one successor.** Several studies may be replaced by the same successor, which
  is how merging studies is expressed. Combined with "a study may be replaced only once", the
  successor relation is single-valued in the forward direction: from any study there is exactly one
  successor, so following the chain from a legacy study always terminates at a unique newest study.
  This is what makes the portal hint well-defined even under merges.
- **metldata is the single source of truth for supersede status** as served. rs, MASS and the portal
  are consumers: rs's `Study.superseded_by_id`/`status` are populated
  from the signal metldata emits, not computed by rs.
- **Legacy means a successor has been declared for this study.** Legacy studies' datasets are hidden
  from search but remain reachable by URL/PID (`/dataset/{id}`, `/study/{id}`). The portal shows an
  "updated version available" hint that resolves at study level, following the successor chain to its
  terminal study.
- A supersede relation may be established long after both studies were loaded (`replace-study`,
  §2.2), so loading is not the only moment supersede status can change — see §4.2.
- **Hidden from search must not mean deleted or unreachable.** The signal that removes an old version
  from the search index must still leave its artifacts reachable by accession *and* carry the
  supersede pointer, so the portal hint and rs's `superseded_by_id` can be set (§4.2).

### 2.5 Mapping / archival decoupling

The map↔archive dependency is inverted, not removed. Today mapping is a prerequisite for archival:
a box archives only once all its files are mapped. In the new model archival is a prerequisite for
mapping: files are archived first, with no mapping required, and mapping is a separate study-centric
activity performed afterwards against archived boxes. So drop the "all files mapped" archival gate
and the portal's submit-map-then-archive coupling, and instead require a box to be archived before
its files can be mapped.

### 2.6 One submission carries exactly one study

The study is the defining scope of a submission, and this stops being a convention and becomes an
enforced restriction: **dskit rejects any submission whose metadata contains more than one study**,
with a clear error naming the studies found.

Every child accession is derived from *the* study PID (§2.1), replacement is declared per study
(§2.2), and supersede is study-level (§2.4). None of those have a defined meaning for a two-study
submission.

It also fixes a latent defect. The current loader takes `content["studies"][0]["accession"]` for
publishable artifacts and **silently discards
any further studies** — a two-study submission loads today without error while only the first study
is attributed. Enforcing one study at submit turns that silent truncation into an up-front rejection.

> **Implementation consequence.** The integration test bed's example metadata is currently a
> **single submission containing two studies** (`STUDY_A`, `STUDY_B`, mapped to separate upload boxes
> in `202_upload_completed.feature`). It exercises exactly the case this rule forbids, and would have
> to be split into two submissions. Its metadata-download scenario only asserts the workbook for
> `DS_A`, which is why the existing truncation goes unnoticed today.

### 2.7 Scope

- **In scope:** `tools/ghga-datasteward-kit`, `libs/metldata`, `libs/ghga-event-schemas` (as needed),
  `services/ghga-registry-service`, `services/mass`, `frontend/data-portal`,
  `services/dataset-information-service`.
- **Out of scope:** the future schemapack services (resource-registry, resource-search),
  `em-transformation-service`, and the schemapack migration itself.

---

## 3. Target end-to-end journey

**Submitting a successor study (offline, dskit):**

1. Submitter prepares the submission's spreadsheet as usual — **exactly one study** (§2.6). For any
   file being reused from an earlier study, they put its **prior GHGA file accession (PID)** in that
   file entity's reuse slot instead of providing a new upload.
2. `dskit metadata submit --replaces GHGA.24.ABC.1 …` (repeat the flag to merge several
   predecessors; omit it entirely for a brand-new study):
   - **rejects** a submission with more than one study, or one naming an already-replaced
     predecessor (§2.2);
   - **mints the study PID** — the predecessor's lineage continued, else a fresh root at `V = 1`;
   - **mints child accessions** `{study_pid}.{alias}`, reusing a dataset's `.DS.xxx` block when its
     file-set is unchanged;
   - **runs the three reuse warnings** (§2.3) for the steward to confirm;
   - **carries reuse slots through untouched** — no resolution to physical files;
   - **records the declared replacement** so it travels with the submission.
3. `dskit metadata transform` — unchanged.
4. `dskit load` — pushes artifacts **together with the declared replacement**.

   *Or, for two studies already submitted:* `dskit metadata replace-study <old PID> <new PID>`
   declares the relationship after the fact, failing if the old study is already replaced.

**Serving:**

5. Service-side metldata records the declared replacement (§2.4): each named predecessor is marked
   superseded, its datasets leave the search track while staying queryable by URL, and the relation
   lands in the ancestry collection.
6. MASS stops returning the superseded studies' datasets. rs receives the supersede signal and sets
   `status`; `superseded_by_id` stays unpopulated in this rollout (§4.3).
7. The portal shows the successor in search; visiting a superseded dataset or study by URL shows the
   "updated version available" hint, resolved by following the chain to its terminal study.

**File mapping (study-centric, in the data portal — after archival):**

8. Files are uploaded via the UCS box path and **archived** — no mapping required. The steward then
   opens the mapping view for a study and works against the **archived** box(es):
   - **files referenced by prior PID** — rs binds the new entity's accession to that same file and
     lists every study the file already maps to. No same-lineage gate; that judgement was made
     offline at submit time (§2.3).
   - **entities with no reuse PID** — matched by alias/filename against a pool of archived boxes,
     with manual corrections, reusing today's matching UX (§4.5).

**Browsing archived files (data portal, steward-only):**

9. The **file admin panel** lists every archived file in GHGA — including files that are archived but
   not (yet) mapped to any metadata, which nothing surfaces today (§4.3, §4.5).

---

## 4. Changes by component

### 4.1 `tools/ghga-datasteward-kit` (dskit)

- **Reject multi-study submissions (§2.6).** Validate at `submit` that the metadata contains exactly
  one study; error out naming the studies found.
- **Read prior studies from the submission store.** dskit needs, per previously submitted study, its
  PID, the studies it declares it replaces, and its submitted metadata (datasets with their
  file-reference sets, entity accessions, and the `data_access_policy`/`data_access_committee`
  attributes needed by warning 3). This is metldata's existing submission store extended with the
  declared replacement (§4.2), not a second store; it is already written on every `submit`, and
  `replace-study` updates it. It backs version continuation, `.DS.xxx` reuse and ancestor resolution
  for the reuse warnings, and holds metadata only — no knowledge of physical uploads or archived files
  (dskit's old S3-upload + `ingest-upload-metadata` FIS path is deprecated and unused; uploads go
  through UCS).
- **`submit` gains `--replaces <exact study PID>`, repeatable** (§2.2). Not a lineage root — the exact
  PID, which may be a legacy `GHGAS…` accession. Repeating it expresses a merge. Fail if any named
  predecessor is already replaced. Derive the successor's own PID — for a merge, prompt the
  steward to either continue one named predecessor's lineage or mint a fresh root.
- **New command `metadata replace-study <old PID> <new PID>`** declaring the relationship between two
  already-submitted studies, with the same already-replaced failure rule. Needed both for
  after-the-fact corrections and for assembling merges incrementally.
- **Three reuse warnings at submit (§2.3),** each an override-able confirmation, not an error: no
  declared predecessor; reused accessions absent from every ancestor; governance
  (`data_access_policy` + nested `data_access_committee`) differing per file from what applied
  before. All are computed from the submission store — no service calls, no view of physical files.
  Provide a non-interactive escape hatch (e.g. `--yes`) so scripted submissions don't hang.
- **PID minting moves from "random per class" to the lifecycle scheme** (§2.1) but stays in metldata.
  dskit supplies the parameters — the submitted content, the named predecessors, and the lineage
  chosen for a merge (§2.2); metldata generates and mints the study PID, `{study_pid}.{alias}` and
  `{study_pid}.DS.xxx`, and writes them into the submission as it does today. The submission store is
  the accession source of truth; dskit holds no accession authority of its own.
- **File-set-based dataset-suffix reuse.** Compute each dataset's file set from the metadata, diff
  against predecessor datasets in the submission store, reuse `.DS.xxx` on exact match else mint.
  Done purely from metadata — no physical-file knowledge needed.
- **Carry reuse slots through untouched.** File entities referencing a prior GHGA file accession are
  passed through as-is; dskit performs no resolution to a physical file — the offline side can't
  (§2.3). What it does instead is the metadata-level warning checks above.
- **Uniqueness on submit** — enforce alias uniqueness across all entities within the study (§2.1) and
  surface a clear error otherwise.

### 4.2 `libs/metldata`

- **Accession scheme.** Replace/augment the flat random `AccessionRegistry`
  (`accession_registry/accession_registry.py:82`) so studies and their children follow the lifecycle
  scheme. Preferred: a lineage-aware accessioning path that, given a study lineage + version + alias
  set + dataset file-sets, produces the structured PIDs, with per-year uniqueness for study `XXX`
  (scoped to the `YY` block) and lineage-scoped uniqueness for `.DS.xxx`.
- **The submission store is the accession source of truth** (§4.1): it records what was assigned
  together with the metadata and lineage that justify it. Version continuation is answered there,
  since it needs the predecessor's submitted metadata and not just its accession string — as is
  lineage-scoped `.DS.xxx` uniqueness, read where the file-set diff already reads.
- **The accession store stays, restructured by year.** `AccessionStore` (`accession_store.py`) becomes
  keyed by `YY`, so "is this `XXX` free this year" is a lookup in that year's bucket rather than a
  linear scan of every accession ever minted. It keeps a flat list alongside for legacy-scheme
  accessions, which have no year to bucket by and stay reserved forever (§2.1). It is an index, not
  the authority — rebuildable from the submission store if lost.
- **Declared-replacement state.** metldata must persist the declared relation
  `predecessor PID → successor PID` (many predecessors may point at one successor, §2.4). This is
  received rather than computed, and no PID parsing is involved in deciding supersede — a predecessor
  may be a legacy `GHGAS…` accession with no version at all (§2.1). Enforce the invariant that a
  predecessor appears at most once as a key, so the successor chain stays single-valued. It is
  persisted in two places, for two readers: on the submission record itself, so the declared relation
  and the metadata it describes stay one object — that record is what dskit reads offline for version
  continuation, ancestor resolution and the cycle check (§4.1); and, once loaded, in a server-side
  ancestry collection (below) that the portal queries.
- **Ancestry collection (new).** metldata keeps a queryable collection of the
  `predecessor PID → successor PID` relation, written by the loader, and exposes a read endpoint over
  it. This is what the portal's "updated version available" hint resolves against (§4.5) — the sole
  online reader of the supersede relation in the early rollout, which is why rs's `superseded_by_id`
  is left unpopulated (§4.3). It must resolve a chain to its terminal study, not just one hop (§2.4),
  and answer for legacy `GHGAS…` predecessors that never had a lineage.
- **Model slot for reused-file accession.** The LinkML model's file classes need a slot to carry the
  prior GHGA file accession (distinct from the existing `ega_accession`). Add it to the GHGA model and
  regenerate artifact models.
- **`studies[0]` — enforce, don't tolerate.** With one study per submission now a hard rule (§2.6),
  `load/collect.py:91` should assert a single study and fail loudly otherwise, replacing today's
  silent `[0]` truncation. dskit rejects multi-study submissions upstream, but the loader is a
  separate trust boundary and should not depend on that.
- **Record supersede at load, and out of band.** The loader (`load/api.py`, `load/load.py`,
  `load/event_publisher.py`) applies the replacement carried in the payload: mark each named
  predecessor superseded by the successor, remove the superseded studies' primary-dataset resources
  from the search track (emit `searchable_resource_deleted`) while keeping them queryable via the
  artifacts API for direct URL access, and write the relation into the ancestry collection the portal
  hint reads (above). Reject a declaration whose predecessor is already replaced, and keep
  re-application of the same declaration idempotent.

### 4.3 `services/ghga-registry-service` (rs)

- **Relax the accession↔file relation from 1:1 to many-to-one.** No schema change or migration is
  needed: `FileAccession` is already keyed by `pid` with `file_id` as an ordinary nullable field
  (`id_field="pid"`, no unique index), so many accessions pointing at one file already fit the store.
  What enforces 1:1 today is request validation in `store_accession_map`
  (`rs/core/rdub_manager.py`): the no-duplicate-`file_id` check plus the "every active file in the box
  must be mapped" check together force each submission to be a bijection over the box's files. Those
  are what relax. **Keep** the per-accession guard in `FileController.map_accessions_to_file_ids`
  (`rs/core/files.py:37`) that rejects re-binding an already-mapped accession to a different `file_id`
  or study — that is the single-valued `accession → file` direction the design preserves (§2.3).
- **Invert the archival↔mapping dependency.** Remove the "all files mapped" archival prerequisite
  (`_check_archival_prerequisites`, `rdub_manager.py:314`) and the requirement that
  `store_accession_map` covers every active file, so a box can be archived with no mapping (archival
  then only requires no `init`/`inbox` files at the ucs level). Conversely, make archival a
  precondition for mapping: `store_accession_map` today *rejects* archived boxes — that guard inverts
  to *require* the box be archived.
- **Study-centric mapping surface.** Add/extend endpoints so mapping is driven by study rather than by
  a single box:
  - **PID-referenced files** — for each file entity carrying a prior GHGA file accession, bind the new
    entity's accession to that file's `file_id` (the many-to-one case) and report the list of studies
    the file already maps to, so the steward can see where else it is in use. rs reads the reuse slot
    from the metldata artifacts it already consumes — no new event field is needed to carry it.
    **There is no same-lineage validation here.** Merging (§2.4) removes any single lineage to
    validate against; the judgement is made offline instead, by the §2.3 warnings the steward confirms
    at submit time. rs still verifies the referenced accession exists and is mapped.
  - **Unreferenced files** — let the steward add a pool of archived boxes (the ones originally used) as
    candidates, then map by alias/filename with manual corrections. The data source is the
    post-archival box/file inventory retained per
    [Journey B](../architecture/metadata-and-file-journeys.md#3-journey-b--file-upload-interrogation-archival).
- **File admin panel API (new).** Because files can now be archived without ever being mapped, no
  existing surface lists them — the box view is per-box and the study view only shows mapped
  accessions. Add a steward-only, paginated, searchable listing over all archived files, each row
  carrying:
  | field | source |
  |---|---|
  | file UUID (`file_id`) | ucs `FileUpload` |
  | GHGA accession(s) — plural | `FileAccession` rows for that `file_id` (many-to-one) |
  | study/studies | `FileAccession.study_id` per accession |
  | governing `data_access_policy` + nested `data_access_committee` | not from rs — resolved per accession by the portal, via that file entity's dataset(s) in metldata's artifacts |
  | file upload box | the RDUB/FUB the upload belongs to |
  | upload box alias | `FileUpload.alias` |

  Legacy files that never came through an upload box have no box and no alias — those columns are
  empty rather than omitted, and the listing must not assume a box exists.

  Two notes on the governance column. It is the same file → dataset → policy → committee resolution
  the reuse warning uses (§2.3, warning 3), so the two should share one implementation rather than
  drift apart. And because a file may back several accessions across several studies — and may sit in
  datasets with different policies — the column is per accession, not per file, and can legitimately
  show more than one policy for the same physical file. That is the situation warning 3 exists to make
  deliberate, so this panel is the audit trail for it.

  This is also the first read path that starts from `file_id` rather than from a box or an accession,
  so it wants an index on `FileAccession.file_id` (none today — the collection is keyed by `pid`). The
  governance data lives in metldata and the portal fetches it from metldata directly; rs does not join
  it at read time. So rs's listing returns the file/accession/study/box columns only, and the portal
  composes the governance column per accession from metldata's artifacts (§4.5).
- **Study deprecation — rs is a consumer, not the author.** The steward authors the relation (§2.2)
  and metldata records and propagates it (§4.2). rs's job is to receive the supersede signal and land
  it in the fields its `Study` already has (`superseded_by_id`, `status`). `superseded_by_id` is
  single-valued, which matches the single-valued successor direction (§2.4); it is the *predecessor*
  side that is many. Note that rs's ingestion path (`rs/adapters/inbound/event_sub.py:65`
  `ResourceSubTranslator` → `rs/core/legacy_resources.py`) fills lifecycle fields with placeholders
  (forced `ARCHIVED`, sentinel creator).

  **`superseded_by_id` is not populated in the early rollout.** The portal resolves the successor from
  metldata's ancestry collection, not from rs (§4.5), so nothing reads the field — and propagating it
  would mean adding a supersede pointer to the events rs consumes (§4.6) to serve no reader. The field
  stays in the model for when rs takes ownership of study metadata; until then it is left unset rather
  than filled with a value nobody derives.

### 4.4 `services/mass`

- **Hide superseded datasets from search.** MASS is event-driven and does no diffing, so hiding is
  achieved by the upstream deletion signal (§4.2): when a replacement is declared, the superseded
  studies' datasets receive `searchable_resource_deleted` and drop out of the index. This now also has
  to fire for an out-of-band `replace-study` declaration (§4.1), not only as part of loading a
  successor's artifacts. **No MASS change is needed** — the deletion signal is sufficient, and there
  is no retained "hidden" flag or steward search that can still see superseded datasets. They remain
  reachable by direct URL through the artifacts API (§5), which is the only guaranteed route to them
  once they leave the index.

### 4.5 `frontend/data-portal`

- **"Updated version available" hint.** On `dataset/:id` and `study/:id`, detect that the entity
  belongs to a superseded study and render a hint linking to its successor — following the chain to
  the terminal study (§2.4). The successor is resolved from metldata, against the ancestry collection
  it maintains (§4.2); rs is not involved. Because merges exist, the hint may lead from several old
  studies to the *same* successor; the reverse ("this study replaced A, B and C") is a separate,
  optional affordance.
- **Study-centric mapping UI.** Rework
  `frontend/data-portal/src/app/upload/features/upload-box-mapping/` and related services from
  box-centric to study-centric: select a study; show confirmed reused-file entities plus the "already
  maps to studies X, Y" info; for unmapped entities let the steward choose a pool of archived boxes
  and map by alias/filename with manual corrections. Remove the submit-map-then-archive coupling;
  archival becomes an independent action.
- **Reused-file affordances.** Surface, in the mapping view, which entities are satisfied by a prior
  GHGA accession vs need a physical file.
- **File admin panel (new, steward-only).** A browsable table over every archived file in GHGA, backed
  by the rs listing (§4.3): file UUID, GHGA accession(s), study/studies, the governing
  `data_access_policy` and its nested `data_access_committee`, upload box, and box alias — with the
  box columns empty for legacy files that never came through a box. This is the only place an
  archived-but-unmapped file becomes visible, which is why it is part of this feature rather than a
  follow-up: decoupling archival from mapping (§2.5) is what creates files that no other view can
  reach. Expect it to be used to *find* the files a later mapping pass needs, so filtering by
  mapped/unmapped and by box matters more than pretty formatting.

### 4.6 `libs/ghga-event-schemas`

- **No change is needed to carry the declared replacement.** The relation stays inside metldata —
  recorded in its ancestry collection and read from there by the portal (§4.2, §4.5) — so no supersede
  pointer has to be added to `MetadataDatasetOverview` or `SearchableResource`. Hiding superseded
  datasets travels on the existing `searchable_resource_deleted` event (§4.4). Should rs later need
  `superseded_by_id` populated, that is the point at which a field gets added; keep any such change
  additive and mind the single-version source-coupling in this monorepo (all consumers see one schema
  version).
- **No change is needed for the many-to-one file relation.** `FileAccessionMapping` is already emitted
  per accession carrying its `file_id`, so *N* accessions on one file simply produce *N* events. wps
  stores and deletes by accession and is unaffected; dins is not — its `PendingFileInfo` merge is
  keyed by `file_id` and consumes the record, which is a required service change rather than an
  assumption to test (§2.3).

---

## 5. Cross-cutting invariants to preserve

- **One study per submission** (§2.6) — dskit `submit`, asserted again in the loader.
- **Aliases unique within a study** (§2.1) — dskit `submit`; child accessions derive from the alias.
- **A study is replaced at most once** (§2.2) — dskit, on both declaration paths; keeps the
  successor chain single-valued.
- **The successor relation is acyclic** (§2.2) — dskit alone, walking the chain in the submission
  store.
- **`accession → file` single-valued, immutable once bound** (§2.3) — rs
  `FileController.map_accessions_to_file_ids`; only file → accession becomes many.
- **Legacy PIDs stay valid forever** (§2.1) — never rewritten, never assumed parseable into
  root + version.
- **Superseded artifacts stay resolvable by URL after leaving search** (§2.4) — the metldata loader
  hides them from the index without deleting the artifacts.
- **Re-load and re-declare are idempotent** — consumers already tolerate missing targets.

---

## 6. Suggested implementation order

0. **One-study enforcement** (§2.6) — small, and every later step assumes it. Splitting the test bed's
   two-study example metadata is part of this step, not a follow-up.
1. **PID scheme + submission-store extensions in dskit/metldata** (§4.1, §4.2 accession parts) —
   everything else depends on the new accessions existing. Land with unit tests for format,
   uniqueness, version continuation, legacy-predecessor handling, and dataset file-set reuse.
2. **Model slot for reused-file accession** (§4.2) — metadata carries the prior PID; binding to a
   physical file is deferred to rs at mapping time (§4.3).
3. **rs: relax the cardinality validation + invert archival↔mapping** (§4.3) — independent of PIDs;
   unblocks both the mapping redesign and the admin panel.
4. **Declared replacement: `--replaces` + `replace-study` → recording, search hiding, propagation**
   (§4.1, §4.2, §4.4), including the reuse warnings (§2.3) that depend on the submission store.
5. **rs study-centric mapping surface + file admin panel API** (§4.3).
6. **Portal: mapping UI rework, legacy hint, file admin panel** (§4.5).

Steps 1–2, 3, and 4 are largely independent once step 0 and the PID scheme are fixed. The file admin
panel (3 → 5 → 6) is the one strand that can ship on its own: it depends only on the archival↔mapping
inversion, not on PIDs or replacement, and it is what keeps archived-but-unmapped files from becoming
invisible the moment that inversion lands.

---

## 7. Open questions / risks

- **Scale of the file admin panel** (§4.3, §4.5). The listing is unbounded by design — every archived
  file in GHGA. hexkit's offset-based `find_all(skip=…, limit=…)` and `FindResult.total_count()`
  bound a page, so response size is handled; two questions are not:
  - **Governance fan-out.** The portal composes governance per accession from metldata (§4.3), so a
    page of N rows costs N cross-service lookups unless batched into one artifact query.
  - **Mapped/unmapped filtering.** "Archived but never mapped" is a `FileUpload` with no
    `FileAccession` row — an anti-join `find_all` cannot express, needing an aggregation pipeline or
    a denormalized flag on the upload record.

  Either way, add the `FileAccession.file_id` index the reverse lookup needs.
