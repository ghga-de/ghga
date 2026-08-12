# Early Data Lifecycle Rollout (Giraffe)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope

### Outline:

GHGA has no notion of study identity, versioning or replacement.
A submission may in principle carry several studies — the loader silently keeps only the first —
and a re-submission mints fresh random accessions with no link back to what it supersedes.
At the same time, file upload and file-to-metadata mapping are welded together by two separate
guards in rs. A Research Data Upload Box only archives once every one of its files carries an
accession, and each mapping request must be a complete bijection over the box's active files — it
may not name a file twice, and it may not leave one out. Independently of that, a mapping request
against an archived box is refused outright. Since mapping is the only way to bind an accession to
a file and is always addressed to a specific box, that second guard is what makes reusing an
already-archived file in a later study impossible: the file's box is by definition archived, so no
further accession can ever be bound to anything in it.

The long-term plan solves this with schemapack and dedicated backend services (resource-registry,
resource-search, em-transformation-service), where the study is the defining scope of a submission
and receives a structured PID.
This epic delivers a smaller step first, on the existing LinkML plus offline `ghga-datasteward-kit`
stack, so lifecycle PIDs and study revisions are available before those services land.
The full design is agreed and written up in
[`docs/features/early-data-lifecycle.md`](../../features/early-data-lifecycle.md); this epic fixes
the scope and the per-component work.
Read that document and
[`docs/architecture/metadata-and-file-journeys.md`](../../architecture/metadata-and-file-journeys.md)
before starting.

### Terminology

`Study PID`: The lifecycle identifier of a study, `GHGA.YY.XXX.V` — 2-digit year, 3 base32
characters, version counter.

`Lineage root`: `GHGA.YY.XXX`, the part of a study PID stable across all revisions of one study.
Only `.V` changes.

`Legacy accession`: An identifier minted under the current flat scheme (`GHGAS`/`GHGAD`/`GHGAF` +
random digits). Not parseable into a root and a version.

`Superseded study`: A study for which a successor has been declared. Its datasets leave the search
index but stay reachable by URL/PID.

`Successor chain`: The forward path from a study to its successor, its successor's successor, and
so on. Single-valued, so it terminates at a unique newest study.

`Merge`: One successor declared as the replacement of more than one predecessor.

`Reuse slot`: A new slot on the ghga metadata model's file classes carrying the prior GHGA file accession
of a file the submission reuses rather than re-uploads.

`Ancestry collection`: The metldata collection holding the `predecessor PID -> successor PID`
relation, written by the loader and read by the data portal.

`RDUB` / `FUB`: Research Data Upload Box (rs-owned) and File Upload Box (ucs-owned).

### Included/Required:

- **One study per submission.** dskit must reject any submission whose metadata contains more than
  one study, and the metldata loader must assert the same rather than
  silently truncating. Every other item below is undefined for a multi-study submission: child
  accessions derive from *the* study PID, replacement is declared per study, supersede is
  study-level. The test bed's example metadata is currently a single submission containing two
  studies and must be split as part of this work.
- **Lifecycle PID scheme.** Studies and their children must be accessioned as `GHGA.YY.XXX.V`,
  `{study_pid}.DS.xxx` for datasets and `{study_pid}.{alias}` for everything else, minted in
  metldata with dskit supplying the parameters. `XXX` is unique within its year; `.DS.xxx` is
  unique within the lineage and is reused when a dataset's file set is unchanged from the
  predecessor revision. Aliases must be unique across all entities within a study revision.
- **Legacy accessions keep working, permanently.** The scheme is not applied retroactively and
  there is no re-accessioning migration. Both schemes coexist indefinitely in search results,
  artifact queries and portal URLs, and nothing may assume a predecessor PID is parseable.
- **Steward-declared replacement, two paths.** `dskit metadata submit --replaces <exact study PID>`
  (repeatable, to express a merge) and a new `dskit metadata replace-study <old PID> <new PID>` for
  two already-submitted studies. Both must fail when the named predecessor is already replaced, and
  when the predecessor's successor chain already reaches the successor.
- **Version derivation on submit.** One new-scheme predecessor continues its lineage at
  `V = predecessor version + 1`; a legacy predecessor starts a fresh root at `V = 1`; a merge
  prompts the steward to either continue one named predecessor's lineage or mint a fresh root.
- **Three reuse warnings at submit.** Override-able confirmations, not errors, all decidable from
  the submission store without service calls: files reused with no declared predecessor; reused
  accessions absent from every ancestor; governance (`data_access_policy` and its nested
  `data_access_committee`) differing per file from what applied before. A non-interactive escape
  hatch must exist so scripted submissions do not hang.
- **Supersede recorded and propagated.** The metldata loader must mark each named predecessor
  superseded, emit `searchable_resource_deleted` for the superseded studies' primary-dataset
  resources so they leave the search index while remaining queryable through the artifacts API, and
  write the relation into a new ancestry collection with a read endpoint. Re-application of the
  same declaration must be idempotent.
- **Many-to-one accession-to-file relation.** rs must accept many accessions bound to one
  `file_id`, one per study reusing the file, while keeping `accession -> file` single-valued and
  immutable once bound.
- **Archival and mapping decoupled, dependency inverted.** Drop the "all files mapped" archival
  prerequisite; require instead that a box be archived before its files can be mapped.
- **Study-centric mapping surface in rs and the portal.** Mapping is driven by study rather than by
  a single box: entities carrying a reuse slot bind to the referenced file and report the other
  studies already using it; entities without one are matched by alias/filename against a pool of
  archived boxes with manual corrections.
- **File admin panel.** A steward-only, paginated, filterable listing over every archived file in
  GHGA — including files archived but never mapped, a population that only comes into existence
  once archival stops requiring mapping.
- **dins must key file information by file, not consume it.** Retain the per-file registration data
  instead of deleting it on first merge, serve it to any accession bound to that file however late
  it arrives, and clear all such accessions when the file is deleted.

### Optional:

- **"This study replaced A, B and C" view.** The reverse direction of the portal's "updated
  version available" hint. Merges make it meaningful, but nothing depends on it and the forward
  hint is the user-visible outcome this epic promises.

### Not included:

- **The schemapack services** — resource-registry, resource-search, `em-transformation-service` —
  and the schemapack migration itself. This epic is deliberately confined to the LinkML plus
  offline-dskit stack.
- **Re-accessioning existing studies.** Legacy identifiers are never rewritten.
- **Entity-level deprecation.** Deprecation is tracked study-level only.
- **Populating rs's `Study.superseded_by_id`.** This is a pre-existing, currently unused attribute
  on rs's `Study` model — it is not introduced by this epic. Since the portal resolves the successor from
  metldata's ancestry collection, nothing reads the field in this rollout; propagating it would
  mean adding a supersede pointer to the events rs consumes to serve no reader. Therefore it stays in the
  model, unset, for when rs takes ownership of study metadata.
- **Changes to `libs/ghga-event-schemas`.** See the API section — the design avoids needing any.
- **Changes to `services/mass`.** Hiding superseded datasets rides the existing deletion event.
- **A steward search that can still see superseded datasets.** There is no retained "hidden" flag;
  direct URL through the artifacts API is the guaranteed route to a superseded dataset.

## User Journeys

This epic covers the following user journeys.

**Submitting a successor study (offline, dskit):**

1. The submitter prepares the spreadsheet as usual, with **exactly one study**. For any file being
   reused from an earlier study, they put its prior GHGA file accession in that file entity's reuse
   slot instead of providing a new upload.
2. `dskit metadata submit --replaces GHGA.24.ABC.1 …` — repeat the flag to merge several
   predecessors, omit it entirely for a brand-new study. dskit rejects a multi-study submission or
   one naming an already-replaced predecessor, mints the study PID and the child accessions,
   reuses a dataset's `.DS.xxx` block where the file set is unchanged, runs the three reuse
   warnings for the steward to confirm, carries reuse slots through untouched, and records the
   declared replacement.
3. `dskit metadata transform` — unchanged.
4. `dskit load` — unchanged.

   *Or, for two studies already submitted:* `dskit metadata replace-study <old PID> <new PID>`.

**Serving:**

5. Service-side metldata records the declared replacement: each named predecessor is marked
   superseded, its datasets leave the search track while staying queryable by URL, and the relation
   lands in the ancestry collection.
6. MASS stops returning the superseded studies' datasets, as a consequence of the deletion events.
7. The portal shows the successor in search. Visiting a superseded dataset or study by URL shows
   an "updated version available" hint, resolved by following the successor chain to its terminal
   study.

**File mapping (study-centric, in the portal, after archival):**

8. Files are uploaded via the ucs box path and archived, with no mapping required. The steward
   opens the mapping view for a study and works against the archived box(es): entities referencing
   a prior PID are bound to that same file and show every study the file already maps to; entities
   with no reuse PID are matched by alias/filename against a pool of archived boxes, with manual
   corrections.

**Browsing archived files (portal, steward-only):**

9. The file admin panel lists every archived file in GHGA, including files archived but not yet
   mapped to any metadata.

## API Definitions:

### RESTful/Synchronous:

**metldata — new**

- `GET /ancestry/{study_pid}`: Resolve the successor chain for a study PID to its terminal study.
  Must answer for legacy `GHGAS…` predecessors that never had a lineage, and must resolve the whole
  chain rather than one hop. This is the sole online reader of the supersede relation in this
  rollout.

**rs — new**

- `GET /files`: Steward-only, paginated, filterable listing over all archived files. Each row
  carries the file UUID, its GHGA accession(s), the study/studies those accessions belong to, the
  originating upload box and the box alias. Filtering by mapped/unmapped state and by box is
  required; the governance columns are **not** served here (see below). Legacy files that never
  came through an upload box have no box and no alias — those fields are empty rather than omitted,
  and the response must not assume a box exists.
- A study-centric mapping endpoint set, extending the existing per-box surface, so mapping can be
  driven by study across a pool of archived boxes. For entities carrying a reuse slot the response
  must include the list of studies the referenced file already maps to.

**rs — changed**

**`POST /upload-boxes/{box_id}/file-ids`** -> Submit an accession map
(`upload_boxes.py`, `submit_accession_map`):
- Will no longer reject a map containing duplicate `file_id` values — that check is what enforces
  the current 1:1 relation and is exactly what relaxes.
- Will no longer require the map to cover every active file in the box.
- Will **invert** its archived-box guard: the endpoint currently returns an `AccessionMapError`
  with `error_type="archived"` when the box is archived; it must instead require the box to be
  archived and reject an unarchived one.
- Will keep rejecting an accession already bound to a different `file_id` or study.

**`PATCH /upload-boxes/{box_id}`** -> Update box state:
- The `locked -> archived` transition will no longer require every file to carry an accession.
  Archival will only require that no files are in `init` or `inbox` state at the ucs level.

**dskit — CLI surface**

- `dskit metadata submit --replaces <exact study PID>` — repeatable; names the exact PID, which may
  be a legacy accession, not a lineage root.
- `dskit metadata submit --yes` (or equivalent) — non-interactive confirmation of the reuse
  warnings.
- `dskit metadata replace-study <old PID> <new PID>` — new command.

### Payload Schemas for Events:

**No changes to `libs/ghga-event-schemas` are required.** 

- *The declared replacement* stays inside metldata — recorded on the submission record and in the
  ancestry collection, read from there by the portal. No supersede pointer is added to
  `MetadataDatasetOverview` or `SearchableResource`. Hiding superseded datasets travels on the
  existing `searchable_resource_deleted` event.
- *The many-to-one file relation* already fits `FileAccessionMapping`, which is emitted per
  accession carrying its `file_id`. *N* accessions on one file simply produce *N* events. wps
  stores and deletes by accession and is unaffected.

dins is the exception, and its change is a service change rather than a schema change: its
`PendingFileInfo` merge is keyed by `file_id` and **consumes** the record, so a second accession
mapped later finds nothing to merge.

Should rs later need `superseded_by_id` populated, that is the point at which a field gets added.
Keep any such change additive, and mind that this monorepo is source-coupled to a single schema
version — all consumers see the same one.

### Configuration:

Proposed new config fields. All must have safe defaults.

```python
# libs/metldata — lifecycle accession scheme
lifecycle_accession_prefix: str = "GHGA"   # leading block of the study PID
lifecycle_random_block_length: int = 3     # base32 chars; 32**3 = 32,768 studies per year
lifecycle_mint_max_retries: int = 10       # collision retries against the per-year bucket

# services/ghga-registry-service — file admin listing
max_file_listing_page_size: int = 1000     # matches the existing upload-listing cap
```

The base32 alphabet is fixed to RFC 4648 (`[A-Z2-7]`, no `0/1/8/9`) and is not configurable —
changing it would invalidate previously minted PIDs.

## Additional Implementation Details:

The suggested landing order is: one-study enforcement first (everything else assumes it), then the reuse slot, then the
PID scheme and submission-store extensions, then the rs cardinality and
archival changes, then declared replacement end to end, then the rs mapping surface and admin panel
API, then the portal. Steps after the PID scheme are largely independent. The file admin panel
strand depends only on the archival/mapping inversion, not on PIDs or replacement.

---

### metldata — accession scheme and accession store

`AccessionRegistry` (`libs/metldata/src/metldata/accession_registry/accession_registry.py`) mints a
flat `prefix + random numeric suffix` per resource type from `prefix_mapping`. It will be
replaced or augmented by a lineage-aware accessioning path that, given a study lineage, a version,
an alias set and the dataset file sets, produces the structured PIDs:

1. Mint or continue the study PID: for a continued lineage, reuse the root and set
   `V = predecessor version + 1`; otherwise generate `XXX` and retry against the current year's
   bucket until free, up to `lifecycle_mint_max_retries`.
2. Mint `{study_pid}.DS.xxx` per dataset, reusing the predecessor revision's block where the
   dataset's file set is unchanged, else generating and retrying within the lineage.
3. Mint `{study_pid}.{alias}` for every other entity.

`AccessionStore` (`accession_store.py`) will be restructured by year, keyed by `YY`, so "is this
`XXX` free this year" is a lookup in that year's bucket rather than a linear scan over every
accession ever minted. It keeps a flat list alongside for legacy-scheme accessions, which have no
year to bucket by and stay reserved forever. The store is an index, not the authority — it must be
rebuildable from the submission store if lost.

The **submission store is the accession source of truth**: it records what was assigned together
with the metadata and the lineage that justify it. Version continuation is answered there, because
it needs the predecessor's submitted metadata and not just its accession string, as is
lineage-scoped `.DS.xxx` uniqueness — read at the same place the file-set diff already reads.

#### Work to be performed:
- [ ] Add the lifecycle accessioning path alongside `AccessionRegistry`, with the config fields above
- [ ] Restructure `AccessionStore` into per-year buckets plus a flat legacy list
- [ ] Extend the submission record to carry the assigned PIDs and the lineage that justifies them
- [ ] Add tests covering: PID format; per-year `XXX` uniqueness and collision retry;
      lineage-scoped `.DS.xxx` uniqueness; version continuation from a new-scheme predecessor;
      fresh root from a legacy predecessor; dataset file-set reuse hit and miss;
      alias-uniqueness violation surfaced as an error

---

### metldata — declared replacement, ancestry, and the loader

The declared relation `predecessor PID -> successor PID` is **received, never computed**. No PID
parsing is involved in deciding supersede, since a predecessor may be a legacy accession with no
version at all. metldata must enforce that a predecessor appears at most once as a key, so the
successor chain stays single-valued.

It is persisted in two places for two readers:

1. **On the submission record**, so the declared relation and the metadata it describes stay one
   object. This is what dskit reads offline for version continuation, ancestor resolution and the
   cycle check.
2. **In a new server-side ancestry collection**, written by the loader, exposed through
   `GET /ancestry/{study_pid}`. This is what the portal hint resolves against.

`load/collect.py:91` currently takes `content["studies"][0]["accession"]` for publishable artifacts
and silently discards any further studies. It must assert a single study and fail loudly. dskit
rejects multi-study submissions upstream, but the loader is a separate trust boundary and must not
depend on that.

The loader (`load/api.py`, `load/load.py`, `load/event_publisher.py`) must apply the replacement
carried in the payload:

1. Mark each named predecessor superseded by the successor.
2. Emit `searchable_resource_deleted` for the superseded studies' primary-dataset resources, so
   they leave the search track. The artifacts must stay in Mongo and queryable through the
   artifacts API — hidden from search must not mean deleted or unreachable.
3. Write the relation into the ancestry collection.
4. Reject a declaration whose predecessor is already replaced.

Re-application of the same declaration must be idempotent, and an out-of-band `replace-study`
declaration must produce the same three effects as one arriving with a successor's artifacts. That
second path is easy to miss: supersede status can change without any new artifacts being loaded.

#### Work to be performed:
- [ ] Persist the declared replacement on the submission record, with the at-most-once-as-key invariant
- [ ] Add the ancestry collection and its loader write path
- [ ] Add `GET /ancestry/{study_pid}`, resolving a full chain, including legacy predecessors
- [ ] Replace the `studies[0]` truncation in `load/collect.py` with a hard assertion
- [ ] Apply supersede in the loader: mark, emit deletions, write ancestry
- [ ] Handle the out-of-band `replace-study` path through the same code
- [ ] Add the reuse-slot to the LinkML model's file classes, distinct from the existing
      `ega_accession`, and regenerate the artifact models
- [ ] Add tests covering: idempotent re-declaration; already-replaced predecessor rejected; legacy
      predecessor; merge with several predecessors; chain resolution over more than one hop;
      superseded artifacts still retrievable through the artifacts API after the deletion event

---

### dskit — submission validation, replacement declaration, and warnings

dskit reads prior studies from **metldata's existing submission store**, not a new one. With one
study per submission, every prior study is already in it. It needs, per previously submitted study,
its PID, the studies it declares it replaces, and its submitted metadata — datasets with their file
reference sets, entity accessions, and the `data_access_policy` / `data_access_committee`
attributes warning 3 compares. The store holds metadata only; it has no knowledge of physical
uploads or archived files, and dskit therefore cannot and must not resolve a reuse slot to a
physical file. That binding happens in rs at mapping time.

The store lives on the data steward VM, which is the trusted source of truth and is backed up as a
VM, so its durability is not a lifecycle concern here.

Both declaration paths must fail when:

1. the named predecessor is already replaced — a study may be replaced only once, so each
   superseded study has exactly one successor while a successor may have many predecessors;
2. following the predecessor's successor chain already reaches the successor. Rule 1 alone does not
   prevent this: after `A -> B`, a steward correcting a mistake with `replace-study B A` passes
   rule 1 and closes a cycle, after which "follow the chain to the newest study" never terminates.

The three reuse warnings are all computed from submitted metadata alone:

| # | condition | steward sees |
|---|---|---|
| 1 | the study reuses files but declares no predecessor | warning + confirm |
| 2 | the study declares predecessor(s), but some reused file accessions occur in no ancestor of those predecessors | warning + confirm, naming the offending accessions |
| 3 | for the reused files, the `data_access_policy` — including its nested `data_access_committee` — reachable via their dataset(s) does not match what applied before | warning + confirm, naming the committees that would gain authority |

Check 3 must compare **content, never accessions or aliases**. Comparing the alias segment is
tempting because an unchanged committee usually keeps its alias, but it misses a steward who keeps
the alias while editing the committee's membership, has nothing to compare for a legacy
predecessor, and means nothing across a merge, where aliases from different lineages are unrelated
strings. The attributes are already in the submission store, so a field-by-field comparison costs
no service call. The comparison is per file, since a file may sit in datasets with different
policies.

The case check 3 exists for is a file becoming subject to *additional* DACs — a governance change
even when every other attribute is untouched — so the message must name the committees that would
gain authority.

Note that the "reused file must belong to my own lineage" rule is deliberately **not** implemented
anywhere. Merging removes any single lineage to validate against, which is why the judgement moves
offline into these warnings and the hard check in rs is dropped.

#### Work to be performed:
- [ ] Reject multi-study submissions at `submit`, naming the studies found
- [ ] Enforce alias uniqueness across all entities within the study, with a clear error
- [ ] Read prior studies, their declared replacements and their metadata from the submission store
- [ ] Add repeatable `--replaces`, with the two failure rules and the merge prompt
- [ ] Add `metadata replace-study <old PID> <new PID>` with the same failure rules
- [ ] Implement the three reuse warnings plus a non-interactive escape hatch
- [ ] Compute dataset file sets and diff against predecessor datasets for `.DS.xxx` reuse
- [ ] Carry reuse slots through the submission untouched
- [ ] Add tests covering: two-study rejection; duplicate alias rejection; already-replaced
      predecessor; cycle closure via `replace-study`; merge lineage prompt, both answers;
      each warning firing and being overridden; the escape hatch suppressing all three

---

### rs — cardinality, archival inversion, mapping surface, admin panel

**Relaxing the accession-to-file relation needs no schema change or migration.** `FileAccession`
(`rs/core/models.py:88`) is already keyed by `pid` with `file_id` as an ordinary nullable field
(`id_field="pid"`, `rs/adapters/outbound/dao.py:89`, no unique index), so many accessions pointing
at one file already fit the store. What enforces 1:1 today is *request validation* in
`store_accession_map` (`rs/core/rdub_manager.py:1047`): the duplicate-`file_id` check plus the
"every active file in the box must be mapped" check together force each submission to be a
bijection over the box's files. Those two are what relax.

**Keep** the per-accession guard in `FileController.map_accessions_to_file_ids`
(`rs/core/files.py:37`) that rejects re-binding an already-mapped accession to a different
`file_id` or study. That is the single-valued `accession -> file` direction the design preserves.

**The archival/mapping dependency inverts, it is not removed.** Remove the
`_check_archival_prerequisites` requirement (`rdub_manager.py:350`) that every active file carry an
accession, so a box can be archived with no mapping at all — archival then only requires no
`init`/`inbox` files at the ucs level. Conversely, `store_accession_map` currently rejects archived
boxes with `error_type="archived"`; that guard inverts to *require* the box be archived.

**Study-centric mapping surface.** Mapping becomes driven by study rather than by a single box:

- **PID-referenced files** — for each file entity carrying a prior GHGA file accession, bind the new
  entity's accession to that file's `file_id` and report the list of studies the file already maps
  to. rs reads the reuse slot from the metldata artifacts it already consumes, so no new event field
  is needed to carry it. rs still verifies that the referenced accession exists and is mapped.
  There is **no same-lineage validation here** — that judgement was made offline at submit time.
- **Unreferenced files** — let the steward add a pool of archived boxes as candidates, then map by
  alias/filename with manual corrections, against the post-archival box/file inventory.

**File admin panel API.** Because files can now be archived without ever being mapped, no existing
surface is keyed to find them. `GET /upload-boxes/{box_id}/uploads` is file-first but scoped to one
named box, and returns ucs `FileUpload` records that carry no accession, so it cannot say whether a
file is mapped. `GET /studies/{study_id}/file-ids` is accession-first, so a file with no accession
never appears — that endpoint surfaces the opposite population, accessions still awaiting a file.
A steward can in principle reach such a file by listing archived boxes and paging through each
one's uploads, but that is an N+1 walk with no filter for the thing being looked for. The new
listing carries:

| field | source |
|---|---|
| file UUID (`file_id`) | ucs `FileUpload` |
| GHGA accession(s) — plural | `FileAccession` rows for that `file_id` |
| study/studies | `FileAccession.study_id` per accession |
| file upload box | the RDUB/FUB the upload belongs to |
| upload box alias | `FileUpload.alias` |

The governing `data_access_policy` and its nested `data_access_committee` are **not** served by rs.
That data lives in metldata, and the portal composes the column per accession from metldata's
artifacts. Two things follow. First, it is the same file -> dataset -> policy -> committee
resolution that reuse warning 3 performs, so the two should share one implementation rather than
drift apart. Second, because a file may back several accessions across several studies, and may sit
in datasets with different policies, the column is **per accession, not per file**, and can
legitimately show more than one policy for the same physical file. That is precisely the situation
warning 3 exists to make deliberate, which makes this panel its audit trail.

This is also the first read path that starts from `file_id` rather than from a box or an accession.
The collection is keyed by `pid`, so it needs an index on `FileAccession.file_id`.

**rs is a consumer of supersede status, not its author.** The steward authors the relation and
metldata records and propagates it; rs receives the signal and lands it in `Study.status`. Note
that rs's ingestion path (`rs/adapters/inbound/event_sub.py` -> `rs/core/legacy_resources.py`)
fills lifecycle fields with placeholders — a forced `ARCHIVED` status and a sentinel all-zero
creator — so this must be handled without disturbing that legacy seeding. `superseded_by_id` is
left unset in this rollout, as recorded under "Not included".

#### Work to be performed:
- [ ] Remove the duplicate-`file_id` check and the "all active files mapped" check from `store_accession_map`
- [ ] Invert the archived-box guard in `store_accession_map` to require archival
- [ ] Remove the accession requirement from `_check_archival_prerequisites`
- [ ] Keep and test the re-binding guard in `FileController.map_accessions_to_file_ids`
- [ ] Add the study-centric mapping endpoints, including the "already maps to studies X, Y" report
- [ ] Verify a referenced reuse accession exists and is mapped before binding
- [ ] Add the paginated, filterable archived-file listing
- [ ] Add an index on `FileAccession.file_id`
- [ ] Land the supersede signal in `Study.status` without disturbing legacy placeholder seeding
- [ ] Add tests covering: N accessions on one `file_id`; re-binding an accession rejected; archiving
      a box with zero mappings; mapping against an unarchived box rejected; mapping against an
      archived box accepted; listing a file with no box and no alias (legacy); listing an
      archived-but-unmapped file; filtering by mapped/unmapped and by box

---

### dins — retain per-file information instead of consuming it

IFRS announces a file's size, checksum and storage alias **once**, at archival. dins treats that as
a one-time hand-off: `store_accession_map` (`dins/core/information_service.py:189`) parks the
payload as a `PendingFileInfo` keyed by `file_id`, merges it into the first accession that claims
it, and then deletes the pending record.

Under file reuse a second accession is mapped much later, IFRS never re-announces, and nothing is
left to merge. The dataset page then shows blank size and checksum indefinitely, with only a "still
waiting for `FileInternallyRegistered`" log line to explain it. This is a required service change,
not an assumption to test.

dins must therefore:

1. Retain the per-file record rather than deleting it after the first merge.
2. Serve it to any accession bound to that file, however late that accession appears.
3. Clear **all** such accessions when the file is deleted. `delete_file_information`
   (`information_service.py:106`) currently resolves a `file_id` to a single accession via
   `find_one` and deletes only that one.

#### Work to be performed:
- [ ] Stop deleting the per-file record after a successful merge
- [ ] Merge the retained record into every later accession bound to the same `file_id`
- [ ] Make `delete_file_information` clear every accession bound to the file, not just the first
- [ ] Add tests covering: two accessions mapped to one file, the second arriving long after the
      registration event, both serving size and checksum; deletion clearing both; the existing
      single-accession path unchanged

---

### MASS — no change required

MASS is event-driven and does no diffing, so hiding superseded datasets is achieved entirely by the
upstream deletion signal: when a replacement is declared, the superseded studies' datasets receive
`searchable_resource_deleted` and drop out of the index. This now also has to fire for an
out-of-band `replace-study` declaration, not only as part of loading a successor's artifacts — that
is a metldata obligation, not a MASS one.

There is no retained "hidden" flag and no steward search that can still see superseded datasets.
They remain reachable by direct URL through the artifacts API, which is the only guaranteed route
to them once they leave the index.

#### Work to be performed:
- [ ] Confirm by integration test that a declared replacement removes the predecessor's datasets
      from search while leaving them retrievable by URL

---

### data portal — hint, mapping rework, admin panel

- **"Updated version available" hint.** On `dataset/:id` and `study/:id`, detect that the entity
  belongs to a superseded study and render a hint linking to its successor, following the chain to
  the terminal study. The successor is resolved from metldata's ancestry endpoint; rs is not
  involved. Because merges exist, the hint may lead from several old studies to the same successor.
- **Study-centric mapping UI.** Rework
  `frontend/data-portal/src/app/upload/features/upload-box-mapping/` and its services from
  box-centric to study-centric: select a study; show confirmed reused-file entities together with
  the "already maps to studies X, Y" information; for unmapped entities let the steward choose a
  pool of archived boxes and map by alias/filename with manual corrections, reusing today's
  matching UX. Remove the submit-map-then-archive coupling — archival becomes an independent action.
  This reworks the mapping tool delivered in
  [Archaeopteryx](../86-archaeopteryx/technical_specification.md).
- **Reused-file affordances.** Surface, in the mapping view, which entities are satisfied by a
  prior GHGA accession and which still need a physical file.
- **File admin panel.** A browsable table over every archived file, backed by the rs listing, with
  the governing `data_access_policy` and nested `data_access_committee` composed per accession from
  metldata's artifacts. Box columns are empty for legacy files that never came through a box. This
  is the only place an archived-but-unmapped file becomes findable, which is why it belongs to this
  epic rather than a follow-up: decoupling archival from mapping is what creates that population in
  the first place. Expect it to be used to *find* the files a later mapping pass needs, so filtering
  by mapped/unmapped and by box matters more than presentation.

#### Work to be performed:
- [ ] Resolve and render the "updated version available" hint on `dataset/:id` and `study/:id`
- [ ] Rework `upload-box-mapping/` and its services from box-centric to study-centric
- [ ] Remove the submit-map-then-archive coupling; make archival an independent action
- [ ] Distinguish reuse-satisfied entities from those needing a physical file
- [ ] Build the file admin panel with mapped/unmapped and box filters
- [ ] Compose the governance column per accession from metldata artifacts, sharing the resolution
      logic with the reuse warning where practical

---

### Test bed

The integration test bed's example metadata (`testbed/example_data/metadata/metadata.json`) is a
**single submission containing two studies** — `STUDY_A` and `STUDY_B`, mapped to separate upload
boxes in `testbed/features/202_upload_completed.feature`. It exercises exactly the case this epic
forbids and must be split into two submissions. Its metadata-download scenario only asserts the
workbook for `DS_A`, which is why today's silent truncation goes unnoticed.

Splitting it is part of the one-study enforcement step, not a follow-up — every later step assumes
one study per submission.

Feature files referencing the two studies and needing review:
`202_upload_completed.feature`, `320_search_datasets.feature`, `350_combined_browsing.feature`,
`502_data_portal_uploads.feature`.

#### Work to be performed:
- [ ] Split the example metadata into two single-study submissions
- [ ] Update the affected feature files and their step implementations
- [ ] Add a scenario covering a superseded study: absent from search, reachable by URL, hint shown
- [ ] Add a scenario covering file reuse across two studies end to end, including dins serving size
      and checksum for the later accession

## Cross-cutting invariants to preserve:

- **One study per submission** — dskit `submit`, asserted again in the loader.
- **Aliases unique within a study revision** — dskit `submit`; child accessions derive from the alias.
- **A study is replaced at most once** — dskit, on both declaration paths; keeps the successor chain
  single-valued.
- **The successor relation is acyclic** — dskit alone, walking the chain in the submission store.
- **`accession -> file` single-valued and immutable once bound** — rs
  `FileController.map_accessions_to_file_ids`; only `file -> accession` becomes many.
- **Legacy PIDs stay valid forever** — never rewritten, never assumed parseable into root and version.
- **Superseded artifacts stay resolvable by URL after leaving search** — the loader hides them from
  the index without deleting the artifacts.
- **Re-load and re-declare are idempotent** — consumers already tolerate missing targets.

## Exploratory Part / Open Questions:

- **Scale of the file admin panel.** The listing is unbounded by design: every archived file in
  GHGA. Confirm during implementation that pagination and filtering are sufficient at the expected
  archive size, and measure the reverse lookup once the `FileAccession.file_id` index is in place.
  If they are not, the fallback is to require a filter (by box, study or mapped state) rather than
  serving an unfiltered first page.

## Human Resource/Time Estimation:

Number of sprints required: 3

Number of developers required: 3

This is at the upper end of what a single epic should carry, and the estimate assumes three
developers working largely in parallel along the natural seams: one on the offline side
(dskit plus metldata accessioning and replacement), one on the backend services (rs and dins), one
on the data portal. The one-study enforcement step and the PID scheme must land before the other
two strands can finish, so the first sprint is the least parallel.

If the epic has to be cut down, the file admin panel strand (rs archival/mapping inversion -> rs
listing -> portal panel) is the one that can ship on its own: it depends only on the
archival/mapping inversion, not on PIDs or replacement. It should not be deferred past that
inversion, though — decoupling archival from mapping is exactly what creates archived-but-unmapped
files that no other view can reach.
