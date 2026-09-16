# Initial Version of the GHGA Registry Service (Apollo)

**Epic Type:** Implementation Epic

## Scope

### Outline

The GHGA Registry Service (RS) is the core service responsible for ingesting and archiving metadata from data submitters.

Its function is currently implemented by the [GHGA Data Steward Kit](https://github.com/ghga-de/ghga-datasteward-kit) in conjunction with the submission store and accession store managed via the [metldata](https://github.com/ghga-de/metldata) library.

More precisely, the service replaces the Submission Registry and the Accession Registry managed via metldata and stored on the file system of a virtual machine operated by a GHGA central data steward. The submissions are now stored in a database owned by the RS.

The second crucial change introduced with the RS is the separation of Experimental Metadata from Persistent Administrative Metadata, Dynamic Administrative Metadata, and Datasets, which were previously bundled into an all-in-one [GHGA metadata schema](https://github.com/ghga-de/ghga-metadata-schema), and the move from the former dataset-centric metadata concept to a study-centric one.

The Experimental Metadata should be managed in a generic way, without semantic interpretation of its content besides generating an accession number for each entity.

As a reminder, Experimental Metadata (EM) is structured data describing how the research data (in the broader sense, all the data that we store in “files”) was generated. Persistent Administrative Metadata (PAM) is non-experimental study metadata (e.g. authors, description), and Dynamic Administrative Metadata (DAM) is business metadata (e.g. DAC contacts and policies). As the names indicate, PAM underlies the same archival immutability as the EM, while DAM is auditable.

An Experimental Metadata Ingress Model (EMIM) shall be used for validation. EMIMs shall be stored as schemapacks, and EM objects shall be stored in datapacks. Both structures are provided by the [schemapack](https://github.com/ghga-de/schemapack) library.

All units of data archived in GHGA (as files or structured metadata objects) that are subject to archival immutability can be retrieved by an accession number, a persistent identifier (PID) that always resolves to the exact same state of a resource. How PIDs are generated will be covered in more detail below.

Another change that needs to be considered in the implementation of the RS is the new authorization concept that assumes all metadata is non-public by default. Public access to metadata or access restricted to certain users needs to be explicitly granted on the study level.

Finally, the GHGA Registry Service should also manage the upload of the files referenced in the EM. To this end, it includes the functionality that had been implemented in the "Upload Orchestration Service" (UOS) and fully replaces it.

### Included/Required

- First implementation of the GHGA Registry Service
- REST API as detailed below
- Event publisher as detailed below
- UOS functionality as detailed below
- Accession number management
- Integration with EMTS (EM transformation service)
- Transition to a new PID schema
- Implementation of a new authorization concept for metadata

### Not included

The following features are not included in the first version of the GHGA registry service:

- Migration of the existing submission store to the new Registry Service.
- Change requests to existing studies. In the future, it should be possible to create a modified copy of an existing study.
- Implementation of an EMIM registry or EM validation service (for now we will only integrate the EMTS).
- Frontend to ingest submissions and manage dynamic administrative metadata and lookups.
- Populating and updating lookup tables from existing dictionaries and ontologies.
- Audit logging.

## Implementation Details

### Managed Entities

#### Study

In the new study-centric metadata concept, the Study serves as the central container for Dataset, Publication, and alternative accessions for each experimental metadata entity. It has a small number of attributes but plays a critical role as a container, as its lifecycle is linked to many other entities. It is immutable and receives a permanent accession number upon creation.

Attributes:

- `id: str` - the PID of the study (primary key)
- `title: str` - comprehensive title for the study
- `description: str` - detailed description (abstract) describing the goals of the study
- `types: list[StudyType]` - the type(s) of this study (as list of codes)
- `affiliations: list[str]` - the affiliation(s) associated with this study
- `status: StudyStatus` - the current status of the study (see below)
- `created: Date` - when the entry was first created
- `created_by: UUID` - the id of the user who uploaded the study
- `approved: Date | None` - when the study was approved
- `approved_by: UUID | None` - the id of the user who approved the study
- `superseded_by_id: str` - if deprecated, the PID of a newer study
- `has_em: bool` - computed field: True if EM has been uploaded already
- `num_datasets: int` - computed field: Number of datasets for this study
- `num_publications: int` - computed field: Number of publications for this study

The `status` field can be updated by the data steward. When newly created, the status of the study is `DRAFT`. In this state, the study is still editable. Once set to `ARCHIVED`, the study becomes immutable, and the status cannot be changed anymore.

The `approved_by` field is automatically set to the user ID of the data steward who set the state to `ARCHIVED`.

#### ExperimentalMetadata

The ExperimentalMetadata entity stores the actual experimental metadata belonging to a study as a generic JSON object.

Attributes:

- `id: str` - the PID of the study to which the experimental metadata belongs
- `metadata: JsonObject` - the experimental metadata exactly as submitted
- `model: str` - the name of the EMIM that can be used to validate the data
- `submitted: Date` - when the experimental metadata was submitted
- `submitted_by: UUID | None` - the id of the user who submitted the data

This entity model has been separated from the Study entity model because the metadata can be large (might require GridFS) and is usually accessed separately from the study after transformation.

#### Publication

The Publication is the citation reference for the study. It is managed independently of any study and is mutable, and a study is not required to have a publication.

Attributes:

- `id: str` - the internal ID of the publication (primary key)
- `title: str` - the title of the publication
- `abstract: str | None` - the abstract of the publication
- `authors: list[str]` - the author(s) of the publication
- `year: int` - the year of the publication
- `journal: str | None` - the name of the journal
- `doi: str | None` - the DOI identifier of the publication
- `study_id: str` - the PID of the study associated with this publication
- `created: Date` - when the entry was created

New Publication entity instances should only be created after verification that the corresponding Study entity instance exists. Normally, there will be one publication per study, but we also allow the case of zero or more than one publications.

#### DataAccessCommittee

The DataAccessCommittee entity describes a Data Access Committee (DAC). It is managed independently of any study and is mutable.

Attributes:

- `id: str` - the code of the DAC (short, uppercase) (primary key)
- `name: str` - human-readable name of the DAC
- `email: EmailStr` - the contact email address of the DAC
- `institute: str` - the institute the DAC belongs to
- `created: Date` - when the DAC entry was created
- `changed: Date` - when the DAC entry was last changed
- `active: bool` - whether the DAC is still active

Note: The `name` should be taken over from the `alias` in the old model, which is already human-readable. The `id` should then be derived from the name (shortened, converted to upper case, with underscores instead of blanks). We do not assign a citable accession number to DACs anymore.

#### DataAccessPolicy

The DataAccessPolicy entity describes a policy for data access (DAP). It is managed independently of a study, is mutable, and belongs to exactly one DataAccessCommittee.

Attributes:

- `id: str` - the code of the DAP (short, uppercase) (primary key)
- `name: str` - human-readable name of the DAP
- `description: str` - a longer description of the DAP
- `text: str` - the complete text for the DAP
- `url: Url | None` - if available, the URL for the DAP
- `duo_permission_id: DuoPermission` - the DUO id of the corresponding Data Use Permission
- `duo_modifier_ids: list[DuoModifier]` - the DUO id(s) of the corresponding Data Use Modifiers
- `dac_id: str` - the code of the DAC linked to this DAP
- `created: Date` - when the DAP entry was created
- `changed: Date` - when the DAP entry was last changed
- `active: bool` - whether the DAP is still active

The `id` should correspond to the `alias` in the old model, `text` and `url` correspond to `policy_text` and `policy_url`. We do not assign a citable accession number to DAPs anymore.

New DataAccessPolicy entity instances should only be created after verification that the corresponding DataAccessCommittee entity instance exists.

#### Dataset

The Dataset entity defines a subset of files in the EM and represents the smallest unit for which a data access request can be formulated. All attributes except `dap_id` (the DataAccessPolicy assigned to the Dataset) are immutable, and Dataset entity instances cannot be deleted unless the study still has the status `DRAFT`. However, new Dataset entity instances can be created after Study instance creation and assigned to a Study instance without violating its immutability, even if the study already has the status `ARCHIVED`. An immutable accession number is assigned upon creation. Every Dataset belongs to exactly one Study, but a Study can have multiple Datasets.

Attributes:

- `id: str` - the PID of the Dataset (primary key)
- `title: str` - comprehensive title for the dataset
- `description: str` - detailed description summarizing this dataset
- `types: list[DatasetType]` - the type(s) of this dataset (as list of codes)
- `study_id: str` - the PID of the study associated with this dataset
- `dap_id: str` - the code of the DAP for this dataset
- `files: list[str]` - the corresponding IDs (aliases) as specified in EM
- `created: Date` - when the dataset was created
- `changed: Date` - when the DAP for the dataset was last changed

New Dataset entity instances should only be created after verification that the corresponding Study and DataAccessPolicy entity instances exist, and that all specified files exist in EM and are specified only once.

#### ResourceType

The ResourceType entity holds the possible types for studies and datasets (could be also used for other resources).

Attributes:

- `id: UUID` - internal ID (primary key)
- `code: str` - the code of the resource type (short, uppercase with underscores)
- `resource: TypedResource` - the kind of resource this type belongs to
- `name: str` - the human-readable name of the resource type
- `description: str | None` - optional definition text or help text
- `created: Date` - when the resource type was created
- `changed: Date` - when the resource type was last changed
- `active: bool` - whether the resource type is still active

The corresponding collection should be created with a composite index on `code` and `resource`. Resources like Study or Dataset should use the `code` to reference the resource type. This makes the resource interpretable without needing to look up the full resource type and keeps it compatible with the types used by EGA.

The `name` is a human-readable form of the `code` (normal case, blanks instead of underscores, maybe slightly longer). The `description` should be a longer human-readable text that fully describes the resource type. The `name` will typically be used for faceting, while the `description` will be shown on detail pages or as help text to explain the exact meaning of the type.

The corresponding collection can be populated with the study types as defined in the existing GHGA metadata schema. The existing dataset types need to be extracted from the current submission store, as they are not defined in the existing GHGA schema. Note that currently we have an inconsistency in the data - study types are stored in `code` form, while `dataset` types are stored in `name` form. The migration step should fix this inconsistency.

#### Accession

The Accession entity stores all existing primary accessions. See also the sections on the Accession Registry below.

Attributes:

- `id: str` - the primary accession number (PID) (primary key)
- `type: AccessionType` - the entity type referenced by this accession
- `created: Date` - when the accession was created
- `superseded_by_id: str | None` - if deprecated, a new primary accession

Note that the `type` is not part of the primary key, i.e. we assume it is already determined by the accession. We store it as additional information that might help with resolving or validating accessions.

When we start introducing versioned accession numbers, we can consider splitting this into two entity models, one for holding the base accession numbers, and another one for holding the versioned ones.

#### AltAccession

The AltAccession entity stores all existing alternative accessions with a reference to the corresponding primary accession. See also the sections on the Accession Registry below.

Attributes:

- `id: str` - the alternative accession number (primary key)
- `pid: str` - the corresponding primary accession number (foreign key)
- `type: AltAccessionType` - the type of alternative accession
- `created: Date` - when the alternative accession was created

Note that we do not store the internal file IDs (UUIDs) using `AltAccession` and a special type, but using a separate model `FileAccession`.

The corresponding collection should have a unique composite index on `id` and `type`.

#### FileAccession

The FileAccession entity stores all existing File accessions together with their corresponding internal file IDs.

Attributes:

- `pid: str` - the primary file accession number (primary key)
- `file_id: UUID4 | None` - the corresponding internal file ID (if mapped)
- `study_id: str | None` - the corresponding study ID (if known)
- `created: Date` - when the file accession was created
- `mapped: Date | None` - when the file accession was mapped

The FileAccessions should never be updated other than adding a `file_id` and `mapped` date to an unmapped entry or removing the `study_id` when the file is completely removed from the study.

They should be sent as `FileAccessionMapping` event in adapted form via the outbox mechanism when the `file_id` is set.

#### EmAccessionMap

The EmAccessionMap entity stores mappings from submitted IDs to primary accessions.

Attributes:

- `id: str` - the PID of the study to which the experimental metadata belongs
- `maps: dict[str, dict[str, str]]` - per-resource-type accession maps

The `maps` attribute holds, for every resource in the experimental metadata, a mapping from the identifier used in the original submission (the "alias" field in the current metadata schema) to the primary accession generated by the Registry Service and stored as an Accession in the database.

Example:

```json
{
  "experiments": {
    "EXP_1": "GHGAX12345678901234",
    "EXP_2": "GHGAX12345678901235"
    ...
  },
  "experiment_methods": {
    "EXP_METHOD_1": "GHGAQ12345678901234",
    "EXP_METHOD_2": "GHGAQ12345678901235"
    ...
  },
  "samples": {
    "SAMPLE_1": "GHGAN12345678901234",
    "SAMPLE_2": "GHGAN12345678901235",
    ...
  },
  ...
}
```

These maps are automatically generated by the service after EM has been submitted.

This entity model has been separated from the Study entity model because the accession maps can be large (might require GridFS) and the original accessions are rarely needed after transformation.

Note: In the new PID schema, accessions are derived from the study ID and the original submission identifier. This means, in theory, we would not need to store these mappings. However, keeping them allows us to support accession numbers that cannot be directly derived, and to resolve accessions using the old PID schema if we choose not to generate new accession numbers for existing data.

#### ResearchDataUploadBox

The ResearchDataUploadBox entity stores Research Data Upload Box (RDUB) objects that reference corresponding raw FileUploadBoxes (FUB) provided by the download controller service (DCS).

Attributes:

- `id: UUID` - internal ID of the RDUB
- `version: int` - counter indicating the RDUB version
- `state: UploadBoxState` - current state of the RDUB
- `title: str` - short human-readable name for the RDUB
- `description: str` - describes the RDUB in more detail
- `changed: Date` - when the RDUB was last changed
- `changed_by: UUID` - user who performed the latest change
- `file_upload_box_id: UUID` - ID of the corresponding FUB in the DCS
- `file_upload_box_version: int` - counter indicating the FUB version
- `file_upload_box_state: UploadBoxState` - current state of the file upload box
- `file_count: int` - number of files in the box
- `size: int` - the total size of all files in the box
- `max_size: int` - the maximum number of bytes that can be uploaded to the box
- `storage_alias: str` - object storage alias to use for uploads

### Enums

#### AccessionType

The AccessionType enum holds the different types of primary accessions:

- for Experimental Metadata:
  - `ANALYSIS`
  - `ANALYSIS_METHOD`
  - `FILE`
  - `EXPERIMENT`
  - `EXPERIMENT_METHOD`
  - `INDIVIDUAL`
  - `SAMPLE`
- for Administrative Metadata:
  - `DATASET`
  - `PUBLICATION`
  - `STUDY`

#### AltAccessionType

The AltAccessionType enum holds the different kinds of alternative accessions:

- `EGA` - EGA accession
- `GHGA_LEGACY` - legacy GHGA accession (after switching to new PID schema)

#### DatasetType

The DatasetType enum lists all possible Dataset types. It is populated at service start with the codes of the ResourceType instances belonging to the `DATASET` resource. The service therefore needs to be restarted in order to make new entries available.

#### DuoModifier

The DuoModifier enum lists all existing [DUO](https://www.ga4gh.org/product/data-use-ontology-duo/) modifiers. These are descendants of `DUO:0000017: data use modifier` (e.g. `DUO:0000043`).

The existing DUO IDs, their shorthands, labels, and descriptions are available in a [CSV file](https://github.com/EBISPOT/DUO/blob/master/duo.csv). It currently contains 20 modifiers. The enum member name should be the shorthand, and the value should be the identifier:

```python
class DuoModifier(StrEnum):
    RS = "DUO:0000012"
    HMB = "DUO:0000006"
    ...
```

#### DuoPermission

The DuoPermission enum lists all existing [DUO](https://www.ga4gh.org/product/data-use-ontology-duo/) permissions. These are descendants of `DUO:0000001: data use permission` (e.g. `DUO:0000004`).

The existing DUO IDs, their shorthands, labels, and descriptions are available in a [CSV file](https://github.com/EBISPOT/DUO/blob/master/duo.csv). It currently contains 5 permissions. The enum member name should be the shorthand, and the value should be the identifier:

```python
class DuoPermission(StrEnum):
    NPOA = "DUO:0000004"
    NMDS = "DUO:0000015"
    ...
```

#### StudyType

The StudyType enum lists all possible Study types. It is populated at service start with the codes of the ResourceType instances belonging to the `STUDY` resource. The service therefore needs to be restarted in order to make new entries available.

#### TypedResource

The TypedResource enum lists all resources whose types are managed by this service:

- `DATASET`: Dataset
- `STUDY`: Study

#### StudyStatus

The StudyStatus enum describes all possible states of a Study:

- `DRAFT` (study is still editable and in preview mode only)
- `ARCHIVED` (study has been archived and has become immutable)

We might add more status values like `FROZEN` or `APPROVED` when we introduce a review and approval process involving multiple users later.

#### UploadBoxState

The UploadBoxState enum lists all possible states that an RDUB or FUB can have.

- `OPEN`
- `LOCKED`
- `ARCHIVED`

### Core functionality

The Registry Service can be accessed through a REST API to submit and query DAM, PAM, EM, and lookup values (ResourceType entries). It also supports updates to DAM and lookup values. The REST API is described below.

A newly submitted study will always be created with the status `DRAFT`.

The service has several endpoints for submitting all data belonging to a study. Any endpoint shall validate the received data immediately and reject it in case of a validation error. In particular, it should not be possible to submit invalid EM.

When any such data has been successfully modified, the service shall check which studies are affected by the change. These can be multiple if, for example, the name of a DAC is changed. For all affected studies that have corresponding EM, a new AnnotatedEMPack shall be created and published for consumption by the EM transformation service (EMTS). This will update these studies in the data portal.

The service also provides endpoints with functionality that helps create research data upload boxes for uploading the research data files belonging to a study and mapping these files to corresponding entries in the submitted EM.

### Accessions (PIDs)

The entire service and client stack must be agnostic regarding the structure of accessions and be able to process arbitrary strings.

The previously issued accessions (`GHGA[A-Z][0-9]{14}`) will be kept for already accepted studies, either remaining as their primary accessions or as special AltAccession entries of type `GHGA_LEGACY`; this still needs to be decided.

Newly accepted studies, as well as future revisions of those early studies, will follow the new schema.

TBD: This section shall be updated when we decide the exact schema (handling of version numbers, global uniqueness of metadata identifiers for one study, etc.).

### Accession registry

The first implementation of the Registry Service shall also contain an initial implementation of an accession registry. Later, this can be outsourced to a separate, dedicated service.

Resources archived in GHGA are immutable and should get accession numbers that are globally unique, persistent, and long-term resolvable. To emphasize these qualities, we also call these accession numbers persistent identifiers (PIDs). A PID must always resolve to the exact same state of a resource.

Particularly, the following entity types get PIDs:

- studies
- all research data files
- datasets (sets of research data files)
- entity instances that are part of the experimental metadata

Currently, the accession numbers used by GHGA have a format that starts with the uppercase letters "GHGA", followed by another uppercase letter indicating the resource type (e.g. "S" for study, "D" for Dataset, "U" for publication), followed by a random 14-digit number. The prefixes and number of digits are defined in the [metadata configuration](https://github.com/ghga-de/metadata-config/blob/main/configuration/metadata_config.yaml).

We are referring to these accession numbers as "legacy accessions", since we plan to replace them with a new PID schema that should reflect the study-centric metadata concept better and should also contain the year and version number.

We will continue to use the legacy accession numbers until the new PID schema is fully defined, which is not covered in this epic.

In addition to GHGA accession numbers, which we also refer to as our primary (canonical) accessions, the accession registry should also keep track of alternative accessions (alt accessions) and resolve them to the corresponding primary accessions. For instance, the accession number under which a resource is archived in EGA should be stored as alternative accession. After switching to the new PID schema, the legacy accession numbers should also be stored as alternative accessions.

The accession store shall also contain a mapping from file accessions to internal file IDs.

### Authorization

With the introduction of study-centric metadata processing, we also introduce authorization for metadata. Instead of assuming all metadata is public, we now require access grants for metadata, similarly to the access grants for downloading datasets and uploading files to research data upload boxes. Only data stewards will be able to view all metadata, independently of any existing grants.

These metadata access grants will be managed by the claims repository service (CRS), just like the existing access grants for download and upload.

If, during the upload process, users other than the supporting data steward should also be able to review uploaded studies before archival, they need to be explicitly granted access. When the study is archived, it can be made accessible to more individual users or be made fully public. When a study is made public, the CRS will automatically remove all existing individual grants for the study.

If some parts of a study with public metadata shall not be made public, these parts must be provided as files contained in a dataset that needs to be requested like other datasets, and not be provided along with the other metadata.

Since this service does not provide a public interface for security reasons, the GHGA Registry Service provides endpoints that allow management of the metadata access grants, acting as a proxy to the CRS.

## User Journeys

### New Study

Typical user journey for a data steward creating a new study:

- data steward logs into the data portal
- submits a new study type via `POST /resource-types` if needed
- submits the study via `POST /studies`
- submits the experimental metadata via `POST /metadata`
- optionally, submits the publication via `POST /publications`
- submits a new data access committee via `POST /dacs` if needed
- submits a new data access policy via `POST /daps` if needed
- submits a new dataset type via `POST /resource-types` if needed
- optionally, submits one or more datasets via `POST /datasets`
- verifies that the preview looks good in the data portal
- creates a Research Data Upload Box for the study
- uploads all corresponding files using the connector
- fetches filenames with the `GET /filenames` endpoint
- maps the EM filenames to the uploaded filenames
- sends the mapping to the `POST /file-ids` endpoint
- data steward sets status to `ARCHIVED` via `PATCH /studies`
- data steward adds a public grant via `POST /study-grants`

## API Definitions

### RESTful/Synchronous

The service provides an API that is accessible via the Data Portal. Through this API, data stewards can modify resources within the immutability constraints outlined in this document. In the first implementation, some read-only endpoints are also exposed publicly. This may be tightened later when the same information is available elsewhere (for example via the upcoming resource registry service API), or made configurable.

To support migration of existing dataset-centric metadata that has already been imported into GHGA, the API will need additional parameters or endpoints for taking over existing accession numbers or performing bulk imports without the data portal. Similar APIs may be added later to ingest metadata directly from other sources.

#### Study API

##### `POST /studies`

- Auth: internal auth token with data steward role
- Request Body: `Study` (without `id`, `status`, user and date related fields)
- Response Body: `Study`
- Returns: 201 or error code

The PID will be automatically created.

After this request, the new Study will have the status `DRAFT`.

##### `GET /studies`

- Auth: internal auth token (optional)
- Query parameters (all optional):
  - `status: StudyStatus` - filter for specific status
  - `type: StudyType` - filter for specific type
  - `text: str` - text filter (partial match in any plain text field)
  - `skip: int`, `limit: int`: used for pagination
- Response Body: `list[Study]`
- Returns: 200 or error code

If not requested by a data steward, only returns studies that are either public or accessible to the user.

The response also returns the computed fields. The user related fields should only be returned if the request is made by a data steward.

##### `GET /studies/{id}`

- Auth: internal auth token (optional)
- Response Body: `Study`
- Returns: 200 or error code (particularly, 403 or 404)

If not requested by a data steward, only returns studies that are either public or accessible to the user.

The response also returns the computed fields. The user related fields should only be returned if the request is made by a data steward.

##### `GET /studies/{id}/file-ids`

- Auth: internal auth token with data steward role
- Response Body: `dict[str, UUID]`
- Returns: 200 or error code (particularly, 403 or 404)

The response returns the mapping from all file accessions of the study with th given ID to their corresponding file IDs, which can be null if the file is still unmapped.

##### `PATCH /studies/{id}`

- Auth: internal auth token with data steward role
- Request Body: partial update of Study fields
- Response Body: `Study`
- Returns: 200 or error code

The `status` can only be changed from `DRAFT` to `ARCHIVED`; otherwise, the service returns 409.

The response also returns the computed fields. The user related fields should only be returned if the request is made by a data steward.

##### `DELETE /studies/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

The study must have the status `DRAFT`; otherwise, the service returns 409.

Also deletes the corresponding experimental metadata, publications, and datasets, as well as all corresponding accessions.

#### ExperimentalMetadata API

##### `POST /metadata`

- Auth: internal auth token with data steward role
- Request Body: `ExperimentalMetadata` (only `metadata` and `model`)
- Returns: 204 or error code

Validates the submitted metadata and upserts the corresponding ExperimentalMetadata instance. If the validation fails, returns error code `422`.

The corresponding study must have the status `DRAFT`; otherwise, the service returns 409.

For validating the passed metadata, the RS uses the schema corresponding to the provided model name. To this end, the RS can either request the schema from the EMTS and validate the metadata itself or ask the EMTS to validate the metadata using a synchronous query.

##### `GET /metadata/{id}`

- Auth: internal auth token with data steward role
- Response Body: `ExperimentalMetadata`
- Returns: 200 or error code (particularly, 403 or 404)

The `id` must be the PID of the corresponding study.

This endpoint can only be accessed by data stewards, normal users can only fetch the transformed metadata.

Returns the corresponding submitted, unprocessed ExperimentalMetadata instance.

##### `DELETE /metadata/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

The `id` must be the PID of the corresponding study.

The study must have the status `DRAFT`; otherwise, the service returns 409.

#### Publication API

##### `POST /publications`

- Auth: internal auth token with data steward role
- Request Body: `Publication` (without `id`, `created`)
- Response Body: `Publication`
- Returns: 201 or error code

Upserts the corresponding Publication instance.

The PID will be automatically created.

The corresponding study must have the status `DRAFT`; otherwise, the service returns 409.

##### `GET /publications`

- Auth: internal auth token (optional)
- Query parameters (all optional):
  - `year: int` - filter for specific year
  - `text: str` - text filter (partial match in any plain text field)
  - `skip: int`, `limit: int`: used for pagination
- Response Body: `list[Publication]`
- Returns: 200 or error code

If not requested by a data steward, only returns publications for studies that are either public or accessible to the user.

##### `GET /publications/{id}`

- Auth: internal auth token (optional)
- Response Body: `Publication`
- Returns: 200 or error code (particularly, 403 or 404)

If not requested by a data steward, only returns publications for studies that are either public or accessible to the user.

##### `DELETE /publications/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

The corresponding study must have the status `DRAFT`; otherwise, the service returns 409.

Also deletes the accession number for the publication.

#### DataAccessCommittee API

##### `POST /dacs`

- Auth: internal auth token with data steward role
- Request Body: `DataAccessCommittee` (without `created` and `changed`)
- Returns: 204 or error code

Creates a new DataAccessCommittee instance.

##### `GET /dacs`

- Auth: None
- Response Body: `list[DataAccessCommittee]`
- Returns: 200 or error code

Gets all DataAccessCommittee instances.

##### `GET /dacs/{id}`

- Auth: None
- Response Body: DataAccessCommittee
- Returns: 200 or error code

Returns the DataAccessCommittee instance with the given `id`.

##### `PATCH /dacs/{id}`

- Auth: internal auth token with data steward role
- Request Body: partial `DataAccessCommittee` (without `id`, `created`, and `changed`)
- Returns: 204 or error code

Updates one or more attributes of an existing DataAccessCommittee instance.

##### `DELETE /dacs/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

If the corresponding DAC is referenced by any DAP, the service returns 409.

Deletes a DataAccessCommittee instance.

#### DataAccessPolicy API

##### `POST /daps`

- Auth: internal auth token with data steward role
- Request Body: `DataAccessPolicy` (without `created` and `changed`)
- Returns: 204 or error code

Creates a new DataAccessPolicy instance.

##### `GET /daps`

- Auth: None
- Response Body: `list[DataAccessPolicy]`
- Returns: 200 or error code

Gets all DataAccessPolicy instances.

##### `GET /daps/{id}`

- Auth: None
- Response Body: DataAccessPolicy
- Returns: 200 or error code

Returns the DataAccessPolicy instance with the given `id`.

##### `PATCH /daps/{id}`

- Auth: internal auth token with data steward role
- Request Body: partial `DataAccessPolicy` (without `id`, `created`, and `changed`)
- Returns: 204 or error code

Updates one or more attributes of an existing DataAccessPolicy instance.

##### `DELETE /daps/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

If the corresponding DAP is referenced by any dataset, the service returns 409.

Deletes a DataAccessPolicy instance.

#### Dataset API

##### `POST /datasets`

- Auth: internal auth token with data steward role
- Request Body: `Dataset` (without `id`, `created`, `changed`)
- Response Body: `Dataset`
- Returns: 201 or error code

Upserts the corresponding Dataset instance.

The PID will be automatically created.

The corresponding study must have the status `DRAFT`; otherwise, the service returns 409.

##### `GET /datasets`

- Auth: internal auth token (optional)
- Query parameters (all optional):
  - `type: DatasetType` - filter for specific type
  - `study_id: str` - filter for specific study
  - `text: str` - text filter (partial match in any plain text field)
  - `skip: int`, `limit: int`: used for pagination
- Response Body: `list[Dataset]`
- Returns: 200 or error code

If not requested by a data steward, only returns datasets for studies that are either public or accessible to the user.

##### `GET /datasets/{id}`

- Auth: internal auth token (optional)
- Response Body: `Dataset`
- Returns: 200 or error code (particularly, 403 or 404)

If not requested by a data steward, only returns datasets for studies that are either public or accessible to the user.

##### `PATCH /datasets/{id}`

- Auth: internal auth token with data steward role
- Request Body: new `dap_id`
- Returns: 204 or error code

Changing the `dap_id` will be allowed even when the study is already in status `ARCHIVED`.

##### `DELETE /datasets/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

The corresponding study must have the status `DRAFT`; otherwise, the service returns 409.

Also deletes the accession number for the dataset.

#### ResourceType API

##### `POST /resource-types`

- Auth: internal auth token with data steward role
- Request Body: `ResourceType` (without `id`, `created`, `changed`)
- Response Body: `ResourceType`
- Returns: 201 or error code

Creates a new ResourceType instance.

##### `GET /resource-types`

- Auth: None
- Query parameters (all optional):
  - `resource: TypedResource` - filter for specific type
  - `text: str` - text filter (partial match in any plain text field)
  - `skip: int`, `limit: int`: used for pagination
- Response Body: `list[ResourceType]`
- Returns: 200 or error code

Gets all ResourceType instances.

##### `GET /resource-types/{id}`

- Auth: None
- Response Body: `ResourceType`
- Returns: 200 or error code

Returns the ResourceType instance with the given internal ID.

##### `PATCH /resource-types/{id}`

- Auth: internal auth token with data steward role
- Request Body: new `name`, `description`, `active`
- Returns: 204 or error code

Modifies the ResourceType instance with the given internal ID.

##### `DELETE /resource-types/{id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code

If the resource type is still referenced by a corresponding resource, the service returns 409.

Deletes a ResourceType instance.

#### Accession API

##### `GET /accession/{id}`

- Auth: None
- Returns: 200 or error code 404 if accession doesn't exist

Returns the Accession instance with the given primary accession number.

##### `GET /accession/{id}?type={type}`

- Auth: None
- Returns: 200 or error code 404 if accession doesn't exist

Returns the AltAccession instance with the given alternative accession number and type.

#### Access Grants

The following endpoints are for managing metadata access grants.

##### `POST /study-grants`

- Auth: internal auth token with data steward role
- Request body:
  - `study_id: str`
  - `user_ids: list[UUID] | None`
- Returns: 204 or error code

Creates a metadata access grant for the given Study PID and the given list of users. If the list of users is empty, all existing grants for the study will be removed and only data stewards will be able to view the study and its metadata. If it is `None`, then a grant will be created that allows any user to view the study and its metadata, and all existing user-related grants for the study will be removed. Otherwise, grants for all the specified users will be created, and all other grants for this study, including public grants, will be removed.

Note that no expiration date needs to be passed, since these grants never expire. Also, these grants are not bound to an IVA.

The SR must use the CRS to store the access grants in the claims repository.

##### `GET /study-grants`

- Auth: internal auth token with data steward role
- Query parameters:
  - `study_id?: str`
  - `user_id?: UUID`
- Response Body: object with study PIDs as key and a list of user IDs or `None` as value
- Returns: 200 or error code

Returns a list of all metadata access grants, filtered according to the specified query parameters. If a user ID is specified, only grants for that user will be returned. If `None` is specified as a user ID, then public grants are returned. If no user ID is passed, all public grants and user-related grants will be returned (these can be many).

The response will return an object whose entries correspond to the existing metadata access grants. The keys refer to the study PIDs, and the values will be either `None` if there is a public grant, or a non-empty list of the IDs of all users who are allowed to view the study and its metadata.

The SR must use the CRS to fetch the access grants from the claims repository.

##### `DELETE /study-grants/{study_id}`

- Auth: internal auth token with data steward role
- Returns: 200 or error code (particularly, 404 if no such study)

Deletes all access grants for the Study with the given PID.

To delete an access grant for individual users, use the `GET` endpoint with the corresponding study PID, remove the users from the returned list, and submit it with the same study PID via the `POST` endpoint.

The SR must use the CRS to remove the access grants from the claims repository.

##### `POST /upload-grants`

- Auth: internal auth token with data steward role
- Request body:
  - `box_id: UUID`
  - `user_id: UUID`
  - `iva_id: UUID`
  - `valid_from: Date`
  - `valid_until: Date`
- Response body:
  - `grant_id: UUID`
- Returns: 201 or error code

Creates an upload grant for the given RDUB to the given user with the given IVA. The validity period must also be passed in the request body. If successful, returns the ID of the created upload grant.

##### `GET /upload-grants`

- Auth: internal auth token with data steward role
- Query parameters:
  - `box_id?: UUID`
  - `user_id?: UUID`
  - `iva_id?: UUID`
  - `valid?: bool`
- Response body: `list[GrantWithBoxInfo]`
- Returns: 200 or error code

Endpoint to get the list of all upload access grants with additional information, filtered by the specified query parameters. Results are sorted by validity, box ID, user ID, IVA ID, and grant ID.

The returned `GrantWithBoxInfo` objects contain the following fields:

- `box_id: UUID`
- `user_id: UUID4`
- `iva_id: UUID`
- `valid_from: Date`
- `valid_to: Date`
- `user_name: str`
- `user_email: EmailStr`
- `user_title: str | None`
- `box_title: str`
- `box_description: str`
- `box_state: UploadBoxState`
- `box_version: int`

##### `DELETE /upload-grants/{grant_id}`

- Auth: internal auth token with data steward role
- Returns: 204 or error code (particularly, 404 if no such grant exists)

Revokes the upload grant with the given ID.

#### File Upload API

The following endpoints are for managing file upload.

##### `GET /filenames/{study_id}`

- Auth: internal auth token with data steward role
- Response Body: map from file accessions to objects with `name` and `alias` properties
- Returns: 200 or error code

Returns a mapping from all file accessions for the study with the given PID to the corresponding filenames and aliases as they are submitted in the EM.

This endpoint is called by the frontend file mapping tool at the end of the upload process.

##### `POST /upload-boxes`

- Auth: internal auth token with data steward role
- Request Body:
  - `title: str`
  - `description: str`
  - `storage_alias: str`
- Response Body:
  - `box_id: UUID`
- Returns: 200 or error code

This endpoint is used to create a new RDUB. If successful, returns the ID of the RDUB.

##### `GET /upload-boxes`

- Auth: internal auth token
- Request params:
  - `skip?`: int
  - `limit?`: int
  - `state?`: UploadBoxState
- Response body:
  - `count: int`
  - `boxes: list[ResearchDataUploadBox]`
- Returns: 200 or error code

Fetches a list of RDUBs. Results are sorted first by locked status (unlocked followed by locked), then by most recently changed, then by box ID.

The query parameters can be used to paginate the results or filter for a given state. The total number of unpaginated results is returned in the `count` field.

Data stewards have access to all boxes, while regular users may only access boxes to which they have been granted upload access.

##### `GET /upload-boxes/{box_id}`

- Auth: internal auth token
- Response body: `ResearchDataUploadBox`
- Returns: 200 or error code (particularly, 403 or 404)

Returns the details of an existing RDUB.

Data stewards have access to all boxes, while regular users may only access boxes to which they have been granted upload access.

##### `PATCH /upload-boxes/{box_id}`

- Auth: internal auth token with data steward role
- Request Body:
  - `version: int`
  - `title?: str`
  - `description?: str`
  - `state: UploadBoxState`
- Returns: 204 or error code

This endpoint is used to update the modifiable details for a RDUB, including the description, title, and state. When modifying the state, users are only allowed to move the state from OPEN to LOCKED, and all other changes are restricted to data stewards.

Once archived, the box may no longer be modified, and files in the box will be moved to permanent storage. If any files in the box have yet to be re-encrypted, if the box is still open, or if there are any files that lack an accession number, archival is denied.

##### `GET /upload-boxes/{box_id}/uploads`

- Auth: internal auth token
- Response body: `list[FileUploadWithAccession]`
- Returns: 200 or error code (particularly, 403 or 404)

Lists the details of all file uploads for the specified RDUB.

The `FileUploadWithAccession` contains all the fields from the shared GHGA event schema `FileUploadWithAccession` plus an optional file accession (for files that have been already mapped).

Data stewards have access to all boxes, while regular users may only access boxes to which they have been granted upload access.

##### `POST /upload-boxes/{box_id}/file-ids`

- Auth: internal auth token with data steward role
- Request Body:
  - `version: int` - the current RDUB version
  - `mapping: dict[str, UUID]` - mapping from file accessions to internal file IDs
  - `study_id: str` - the ID of the corresponding study
- Returns: 204 or error code

Ingests a filename mapping for the Research Data Upload Box with the given ID.

As a safety measure, the SR must verify that all accessions in the mapping belong to the study with the specified PID and that all file IDs in the mapping belong to the box with the given ID, and respond with an error code 409 otherwise.

The service should then upsert corresponding `FileAccession` instances for all entries in the passed map.

The service should then republish the passed map for consumption by DINS and WPS.

### Payload Schemas for Events

The service publishes events that communicate the state of its entity instances.

In particular, it publishes Annotated Experimental Metadata (AEM). This consists of the original, unmodified experimental metadata together with additional annotations. These annotations contain all other study-related information and can be consumed by the experimental metadata transformation service and integrated into downstream transformed AEM.

The published AEM events shall have the following schema:

- `metadata: JSONObject` - the actual experimental metadata from ExperimentalMetadata
- `accessions: JSONObject` - the corresponding maps from EmAccessionMap
- `study: Study` - the corresponding study with nested publication
- `datasets: list[Dataset]` - the associated datasets with nested DAP and DAC

The payload should use slightly modified classes with embeddings instead of references.

The service also republishes filename mappings from accessions to internal file IDs via the REST API. The payload should be the exact same mapping; study PID and box id are not needed.

## Human Resource/Time Estimation

Number of sprints required: 3

Number of developers required: 2
