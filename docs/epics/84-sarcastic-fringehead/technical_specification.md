# File Upload Path Pt. 2 (Sarcastic Fringehead)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
This epic includes all work required to bring the remaining file services into line with the new file upload concept. The first portion of work for the file services was executed under [Lynx Boreal](../76-lynx-boreal/technical_specification.md), and there was also a subsequent portion of work for the GHGA Connector which was carried out according to [Hedgehog Seahorse](../80-hedgehog-seahorse/technical_specification.md). When this epic is finished, all *backend* modifications required for the new upload concept to be realized will be complete. Frontend changes are *not* included in this epic, however, so more work will be required to bring the Data Portal up to speed.
As for the work to be completed within this epic, the services affected include the File Ingest Service (FIS), Encryption Key Store Service (EKSS), Internal File Registry Service (IFRS), the Well-Known Value Service (WKVS), the Upload Controller Service (UCS), the ghga-event-schemas library, and a new service called the Data Hub File Service (DHFS). Additionally, if it is discovered during implementation that further changes need to be made to other services *beyond what is described in this epic*, then tickets will be added ad-hoc and associated with this epic.

In Lynx Boreal, the UCS was rewritten, the Upload Orchestration Service (UOS) was implemented for the first time, the Claims Repository Service (CRS) was updated to manage permissions for Research Data Upload Boxes, and the Work Package Service (WPS) was updated to manage upload-type work packages. Taken together, these changes create the operational framework for remote file upload, but only to the point of initial ingest. In order to fully realize our file upload concept, we still need to decrypt the uploaded file, verify the integrity via checksum comparison, re-encrypt the file with a new file secret (securely stored in the Encryption Key Store Service, or EKSS), and move the file to a permanent storage bucket registered with the IFRS in what we call "archival".


### Included/Required:
All work described in the Additional Implementation Details section below is required.

### Not included:
- Data Portal updates or any upcoming metadata-related services. This is purely for file upload.
- Add email notifications for important events related to archival. This could include, for example, a notification conveying that all files in a Research Data Upload Box have been successfully archived, or that there was a problem with file XYZ during interrogation. To prevent scope creep, this should *probably* be done in another epic, but we should keep that potential requirement in mind during development.
- Event discovery or publication for auditing purposes

## User Journeys (optional)

All user journeys are already detailed in Lynx Boreal. The operations added in this epic will occur automatically without further action required on the part of either the user or GHGA personnel. 

## API Definitions:

### RESTful/Synchronous:

[UCS HTTP API](#ucs-http-api)  
[UOS HTTP API](#uos-http-api)  
[WKVS HTTP API](#wkvs-http-api)  
[EKSS HTTP API](#ekss-http-api)  
[FIS HTTP API](#fis-http-api)  

### Payload Schemas for Events:

#### ResearchDataUploadBox
```python
id: UUID4
version: int
state: Literal["open", "locked", "archived"]
title: str
description: str
last_changed: UTCDatetime
changed_by: UUID4
file_upload_box_id: UUID4
file_upload_box_version: int 
file_upload_box_state: Literal["open", "locked", "archived"]
file_count: int
size: int
storage_alias: str
```

#### FileUploadBox
```python
id: UUID4
version: int
state: Literal["open", "locked", "archived"]
file_count: int
size: int
storage_alias: str
```

#### FileUploadState
```python
INIT = "init"  # unchanged, means the file is being uploaded to the inbox
INBOX = "inbox"  # unchanged, means the file is in the inbox awaiting interrogation
FAILED = "failed"  # new state, means problem with interrogation, upload, etc.
CANCELLED = "cancelled"  # new state, means the file was removed by user or DS
INTERROGATED = "interrogated"  # new state, means file interrogation was valid
AWAITING_ARCHIVAL = "awaiting_archival"  # new state, means file can be archived by IFRS
ARCHIVED = "archived"  # now means the file is officially in permanent storage
```

#### FileUpload
> Outbox event owned by UCS
```python
id: UUID4       # Unique identifier for the file upload
box_id: UUID4   # The ID of the FileUploadBox this FileUpload belongs to. There should be a compound unique index on this field and alias.
alias: str      # The filename or other alias that allows mapping files to study metadata (unique within the box)
state: FileUploadState = "init"  # The state of the FileUpload
state_updated: UTCDatetime  # Timestamp of when state was updated
storage_alias: str  # A string identifying which Data Hub the file will be stored at
bucket_id: str  # The name of the S3 bucket where the file currently resides
object_id: UUID4 # The ID of the file in its current S3 bucket
decrypted_size: int     # The size of the unencrypted file
encrypted_size: int  # The size of the encrypted file. When in the inbox, this includes the Crypt4GH envelope. After re-encryption by the DHFS, the envelope is removed so this value decreases slightly.
part_size: int  # The number of bytes in each file part (last part is likely smaller)
# The following fields are None until later in the process
secret_id: str | None
decrypted_sha256: str | None  # SHA-256 checksum of the entire unencrypted file content
encrypted_parts_md5: list[str] | None     # Is None until DHFS finishes with file
encrypted_parts_sha256: list[str] | None  # Is None until DHFS finishes with file
failure_reason: str | None
```

#### InterrogationSuccess
> Persistent event published by FIS on behalf of DHFS
```python
file_id: UUID4
secret_id: str | None  # The internal ID of the DHFS-generated decryption secret
storage_alias: str  # A string identifying which Data Hub the file will be stored at
bucket_id: str  # The name of the interrogation bucket where the file is stored
object_id: UUID4  # The ID of the object in the interrogation bucket
interrogated_at: UTCDatetime  # Time that the report was generated
encrypted_parts_md5: list[str]  # The MD5 checksum for each file part, in sequence
encrypted_parts_sha256: list[str] # The SHA256 checksum for each file part, in sequence
encrypted_size: int  # The size of the encrypted file content without envelope
```

#### InterrogationFailure
> Persistent event published by FIS on behalf of DHFS
```python
file_id: UUID4
storage_alias: str  # A string identifying which Data Hub the file will be stored at
interrogated_at: UTCDatetime  # Time that the report was generated
reason: str  # The text of the error that caused interrogation to fail
```

#### FileInternallyRegistered
> Persistent event owned by the IFRS
```python
# content_offset is removed because objects are stored without an envelope
# bucket_id is removed because storage_alias should already point to specific bucket
file_id: UUID4  #  Renamed from object ID. This same field used to hold the accession.
archive_date: UTCDatetime  # renamed from upload_date
storage_alias: str  # renamed from s3_endpoint_alias
bucket_id: str  # The name of the permanent storage bucket the file is stored in
secret_id: str      # renamed from decryption_secret_id
decrypted_size: int     # unchanged
encrypted_size: int     # unchanged
decrypted_sha256: str   # unchanged
encrypted_parts_md5: list[str]    # unchanged
encrypted_parts_sha256: list[str] # unchanged
part_size: int  # renamed from encrypted_part_size
```
---
### Other Schemas

#### FileUnderInterrogation
> This schema represents what FIS checks for validation when consuming a `FileUpload` event with the `inbox` state, and is used by FIS to track minimal data concerning interrogation progress. It is not itself an event schema.
```python
class BaseFileInformation(BaseModel):
    """The minimal set of fields served to DHFS via the list_uploads endpoint."""
    id: UUID4  # Unique identifier for the file upload
    storage_alias: str  # A string identifying which Data Hub the file will be stored at
    bucket_id: str  # The name of the bucket where the file is currently stored
    object_id: UUID4  # The ID of the file specific to its S3 bucket
    decrypted_sha256: str  # SHA-256 checksum of the entire unencrypted file content
    decrypted_size: int  # The size of the unencrypted file
    encrypted_size: int  # The encrypted size of the file
    part_size: int  # The number of bytes in each file part (last part is likely smaller)

class FileUnderInterrogation(BaseFileInformation):
    """Internal FIS model tracking interrogation progress."""
    state: FileUploadState = "init"  # The state of the FileUpload
    state_updated: UTCDatetime  # Timestamp of when state was updated
    interrogated: bool = False  # Indicates whether interrogation has been completed
    can_remove: bool = False  # Indicates whether file can be deleted from `interrogation` bucket
```

#### InterrogationReport
> This schema represents the format expected by the FIS when DHFS submits via HTTP request the results of file interrogation. It covers both success and failure.
```python
class InterrogationReportWithSecret(BaseModel):
    """Contains the results of file interrogation"""
    file_id: UUID4
    storage_alias: str  # A string identifying which Data Hub the file will be stored at
    interrogated_at: UTCDatetime # Timestamp showing when interrogation finished
    passed: bool
    bucket_id: str | None  # Conditional upon success - interrogation bucket ID
    object_id: UUID4 | None  # Conditional upon success - ID of file in interrogation bucket
    secret: SecretBytes | None = None  # Encrypted file encryption secret
    encrypted_parts_md5: list[str] | None = None  # Conditional upon success
    encrypted_parts_sha256: list[str] | None = None  # Conditional upon success
    encrypted_size: int | None = None  # Conditional upon success - size without envelope
    reason: str | None = None  # Conditional upon failure, contains reason for failure
```

#### PendingFileUpload
> This schema represents what IFRS checks for validation when consuming a `FileUpload` event with the `awaiting_archival` state. It is not itself an event schema.
```python
class PendingFileUpload(BaseModel):
    """Contains all the information needed for a file to be permanently archived"""
    id: UUID4
    storage_alias: str
    bucket_id: str  # The name of the interrogation bucket where the file is stored
    secret_id: str
    decrypted_sha256: str
    decrypted_size: int
    encrypted_size: int
    part_size: int
    encrypted_parts_md5: list[str]
    encrypted_parts_sha256: list[str]
```

#### FileAccessionMap
```python
class FileAccessionMap(BaseModel):
    """Model that maps file IDs to GHGA accession numbers"""
    mapping: dict[UUID4, str]  # this could instead be a list of tuples or similar object
```

## Additional Implementation Details:

> For a comprehensive overview, please see the [Service Diagrams](#service-diagrams) section below.

### GHGA-Event-Schemas:
- Set the `ResearchDataUploadBoxState` schema to match what is defined above
- Set the `FileUploadState` schema to match what is defined above
- Set the `FileUpload` schema to match what is defined above
- Set the `FileUploadBox` schema to match what is defined above
- Set the `FileInternallyRegistered` schema to match what is defined above
- Replace `FileUploadValidationSuccess` with `InterrogationSuccess` as defined above
- Replace `FileUploadValidationFailure` with `InterrogationFailure` as defined above
- Rename `_FileInterrogationsConfig` to `_InterrogationEventsConfig` *(not done — class retains its original name)*
- Rename `FileInterrogationSuccessEventsConfig` to `InterrogationSuccessEventsConfig` *(not done — class retains its original name)*
- Rename `FileInterrogationFailureEventsConfig` to `InterrogationFailureEventsConfig` *(not done — class retains its original name)*
- Remove the `FileUploadReport` schema
- Remove the `FileUploadReportEventsConfig` stateless config class
- Rename `NonStagedFileRequested.s3_endpoint_alias` to `storage_alias`

> Note: `FileAccessionMapping` (not `FileAccessionMap`) is the class name in the library for individual file-to-accession mappings. The corresponding config class is `FileAccessionMappingEventsConfig`. Services should use these names when referencing this schema. The `FileAccessionMap` name used elsewhere in this spec refers to the concept; the actual library class name is `FileAccessionMapping`.

### UCS:
The UCS takes on an expanded role from what was defined in Lynx Boreal. Previously, the UCS was only concerned with getting files into the `inbox` bucket, and after that it didn't care what happened. However, further consideration has resulted in the viewpoint that the UCS is actually the source of truth for files all the way up until they are copied into permanent storage. Intermediate steps that occur in other services provide subsequent information to the UCS regarding the `FileUpload`, but those services do not assume ownership of the essential file information. Not only that, but the relationship between `FileUpload` IDs and accession numbers should and will be managed by the UCS during the interim phase while official accession management is still under development. The UCS operates two instances - an HTTP API and an event consumer.

#### UCS Event Consumer
The UCS event consumer instance subscribes to the `InterrogationSuccess` and `InterrogationFailure` *persistent events* published by the FIS. It also subscribes to the `FileInternallyRegistered` events published by the IFRS, and to `FileDeletionRequested` events. The schemas are [detailed above](#interrogationsuccess).

When a new `InterrogationSuccess` or `InterrogationFailure` event arrives, UCS:
- Finds the matching `FileUpload` in its database and raises an error if it can't.
- Checks the `FileUpload` state:
  - If the state is `init`, the event is ignored (the file never reached the inbox).
  - If the state is `inbox`, the event is processed as described below.
  - For any other state (e.g. already `interrogated`, `failed`, `cancelled`, `awaiting_archival`, or `archived`), UCS logs that the file was already in a terminal/post-inbox state and returns without further action (idempotent behaviour).

If the event is `InterrogationSuccess`, UCS also:
- Sets `FileUpload.state` to `interrogated`
- Sets `state_updated` to the current timestamp
- Sets `secret_id`, `bucket_id`, `object_id`, `encrypted_size`, `encrypted_parts_md5`, `encrypted_parts_sha256` based on the information in the event

However, if the event is `InterrogationFailure`, UCS sets `FileUpload.state` to `failed`, `FileUpload.state_updated` to the current timestamp, and `FileUpload.failure_reason` to the reason from the event.

In both cases, UCS deletes the file from the `inbox` bucket. At this point, the event consumer instance is finished processing the event and waits for the next event. The updates to the `FileUpload` will be published as an outbox event.

When UCS receives a `FileDeletionRequested` event, it calls `remove_file_upload` for the given file ID, which sets the state to `cancelled` and removes the object from the inbox bucket if applicable.

When the UCS receives a `FileInternallyRegistered` event, it locates the corresponding `FileUpload` and updates its state to `archived` and publishes it as an outbox event.

As a final note on the UCS, the UCS is the place where `box_id` is populated for `FileUpload` objects. You can read about that process in Lynx Boreal, but the long-short is that a Data Steward manually creates a `ResearchDataUploadBox` in the UOS, which has a separate ID, and that automatically triggers the creation of a subordinate `FileUploadBox` in the UCS, which has an independent ID. Whenever a new file is added for that box, the `FileUpload` gets the `box_id` of the parent `FileUploadBox`.

#### UCS HTTP API
You can read about the existing UCS endpoints in the Lynx Boreal epic. I will only detail the updates here.

> Note: The GET /boxes/{box_id}/uploads endpoint needs to exclude the secret_id and checksum fields

The UCS operates the following new endpoints:
- `PATCH /boxes/{box_id}`: This endpoint already exists, but is augmented here to allow `FileUploadBox` *archival*.
  - Authorized by a token signed by the UOS with the work type `"archive"` and including the `box_id`
  - Returns `204 NO CONTENT`
  - Description: 
    - The UCS finds the `FileUploadBox` in its database and raises an error if it can't.
    - The UCS verifies that the `FileUploadBox` state is not `open`.
    	- If the state is `open`, the UCS raises an error.
      - If the state is `archived`, the UCS returns early as it assumes that the work is already done.
      - If the state is `locked`, the UCS continues.
    - The UCS looks up every `FileUpload` associated with the box and verifies that each one has a state of `interrogated` or else raises an error and rejects the box archival.
      - UCS sets each `FileUpload.state` to `awaiting_archival` and likewise updates the `FileUpload.state_updated` timestamp.
      - If every `FileUpload` already has a state of `awaiting_archival`, the UCS skips to updating the `FileUploadBox`.
    - The UCS publishes an outbox event for each modified `FileUpload`.
    - The UCS sets `FileUploadBox` state to `archived` and publishes the updated object as an outbox event.

Side note:  
The work to provide a deletion endpoint accessible by GHGA Connector is *not* meant to be part of this epic. For now, assume all deletions/cancellations will be triggered from the Data Portal -> UOS -> UCS rather than from the GHGA Connector. Additionally, in case it wasn't clear, file deletions (or cancellations, rather) do not result in a `dao.delete()` call. The full document data remains, but the state is set to `cancelled`. When the GHGA Connector is enabled to perform deletions, the state might potentially be allowed to be set to `failed` in addition to `cancelled`. More thought is required here on the requirements for work order tokens, use cases, and alias vs file ID specifiers.

#### UCS Configuration
The UCS needs the following config changes:
- Add event sub config for `InterrogationSuccess` and `InterrogationFailure` events
  - ghga-event-schemas -> `FileInterrogationSuccessEventsConfig`
  - ghga-event-schemas -> `FileInterrogationFailureEventsConfig`
  - ghga-event-schemas -> `FileInternallyRegisteredEventsConfig`
  - ghga-event-schemas -> `FileDeletionRequestEventsConfig`
- Remove event sub config for `FileUploadReport` events
- Add config that maps Data Hub string to inbox storage alias

#### Work to be performed for the UCS
- Get schema updates from ghga-event-schemas
- Implement new endpoints
- Exclude `secret_id` and checksum fields from `FileUpload` objects returned by `GET /boxes/{box_id}/uploads`
- Remove existing subscription to `FileUploadReport` events
- Add event subscriber for `InterrogationSuccess` and `InterrogationFailure` events
- Add core behavior to handle `InterrogationSuccess` and `InterrogationFailure`
- Add event subscriber for `FileInternallyRegistered` events
- Add core behavior to handle `FileInternallyRegistered` events
- Add event subscriber and core behavior for `FileDeletionRequested` events
- Change existing deletion behavior to update `FileUpload.state` to `cancelled` instead of actually deleting content
- Modify the logic for the "change box" endpoint to work with state field instead of booleans
- Assign `storage_alias` and `bucket_id` to new file uploads
- Validate `storage_alias` when boxes are created by Data Stewards

---

### UOS:
The UOS remains mostly unchanged from its initial implementation in Lynx Boreal, except for gaining a new, temporary responsibility to send **accession maps** to the IFRS upon box archival. UOS will be considered the owner of accession maps. Through a new HTTP API endpoint, the UOS will take in objects that map file IDs from `FileUpload` objects to an accession number. This is temporary because it fills in a functional gap in the overall system that still has to be planned out. In the future, this endpoint will be removed (or at least no longer used). The UOS operates both an HTTP API instance and an event consumer instance.

#### UOS HTTP API
> [Return to API list](#restfulsynchronous)

The UOS gets the following new endpoint:  
`PATCH /boxes/{box_id}/accessions`: Accept a file-to-accession mapping in order to relay it to the UCS
- Authorization uses auth context protocol and requires a Data Steward role
- Request body must contain a payload conforming to the `FileAccessionMap` [schema](#fileaccessionmap)
- Returns `204 NO CONTENT`
- Description:
  - UOS looks for the `ResearchDataUploadBox` in its database with an ID that matches the value in the path parameter, and returns a `404 NOT FOUND` if it doesn't find it.
  - UOS ensures the `ResearchDataUploadBox` is not already ARCHIVED, and raises an error if it is. This might return a `409 CONFLICT` status code.
  - UOS stores the accession mapping in its accessions collection. If any of the accessions aren't globally unique, UOS returns a `400 BAD REQUEST` error.

The UOS gets updates to the following existing endpoints:  
`PATCH /boxes/{box_id}`: This endpoint gains the responsibility of ensuring all files in a FileUpload box are assigned a unique accession before allowing archival of the `ResearchDataUploadBox`. Ignoring use cases where other box attributes are modified and focusing solely on the box archival operation:
- UOS ensures the `ResearchDataUploadBox` is in the `locked` state and raises an error if it isn't.
- UOS looks at its accession mapping collection in the database and confirms that all files in the box have a globally unique accession assigned, and raises an error if not.
- UOS self-signs a `ChangeFileBoxWorkOrder` token and makes a PATCH request to the UCS's `/boxes/{box_id}` endpoint.
- If the UCS returns a failure response, UOS does as well.
- If the UCS returns a successful response, UOS publishes a Persisted event containing the accession map for all files in the box as a simple dictionary where the file IDs are the keys. This should be published to a dedicated `accession-mappings` topic.

> Note: In the future when we replace the temporary accession map solution, we will need to perform a migration that combs through the Persisted events store and selectively deletes entries for accession mappings while leaving audit logs in place.


#### UOS Configuration
- EventPubConfig for `FileAccessionMap` events topic
- Mapping for Data Hub to inbox storage alias

#### Work to be performed for the UOS
- Get schema updates from ghga-event-schemas
- Add the new API endpoint described above
- Add the FileAccessionMap definition somewhere in the UOS (not in a library)
- Rename final box state to `archived` instead of `closed`
- Add a new `"archive"` option to the `ChangeFileBoxWorkOrder` for the work type literal that represents final, permanent sealing of `FileUploadBox`
- Add an event publisher for `FileAccessionMap` events
- Add a DAO for file accession data
- Add an outbound UCS call in the `FileBoxClient` with the same structure as `lock_file_upload_box()` and `unlock_file_upload_box()`, called `archive_file_upload_box()`
- Call `FileBoxClient.archive_file_upload_box()` from the UOS core when moving a `ResearchDataUploadBox` to `archived` state (formerly labeled `closed`).
- Modify the "update box" calls to the UCS so they specify state instead of the locked/archived booleans
- Validate `storage_alias` when Data Stewards create a new `ResearchDataUploadBox`

---

### WKVS:
- Provides the Data Hub Crypt4GH public keys via public HTTP API

#### WKVS HTTP API
> [Return to API list](#restfulsynchronous)

The WKVS would get the following new endpoint:  
`GET /values/data_hub_public_keys`:
- No authentication required
- Returns `200 OK` and a mapping of storage alias to public key

#### Work to be performed for the WKVS
- Provide a way to retrieve Crypt4GH public keys for Data Hubs. This can be a dictionary where the keys are storage aliases and the values are the public keys.

---

### GHGA Connector:
The Connector performs initial file encryption and upload from the user's machine. In order to properly encrypt the file for a specific Data Hub, the Connector needs to contact the WKVS to obtain the appropriate Crypt4GH public key based on the storage alias assigned to the `ResearchDataUploadBox`/`FileUploadBox` created by the Data Steward.

Per-part encryption process needs to be updated to the following:
1. Update the unencrypted content SHA-256 checksum
2. Encrypt the part and calculate the MD5 & SHA-256 checksums of the encrypted part
3. Decrypt the part and update the second unencrypted content SHA-256 checksum
4. Compare the decrypted checksums to make sure they're the same at each step in the process.

#### Work to be performed for the GHGA Connector
- Fetch and use Data Hub public key for file encryption
- Submit file part size
- Make sure we decrypt encrypted parts again and calculate a second, confirmatory checksum over the unencrypted content.

---

### EKSS:

The EKSS is responsible for interfacing with Vault to deposit and retrieve secrets. Before the introduction of this epic, there were *two* services that directly communicated with Vault: EKSS and FIS. The changes proposed here would make EKSS the sole service with Vault access.

Only small changes are required for EKSS, namely with expected format of ingested secrets. In the past, EKSS expected a full Crypt4GH envelope. Going forward, however, EKSS will expect a secret directly encrypted with the GHGA public key. Because the EKSS API is not publicly exposed, we do not need to perform extra verification of the sender. The reason for the move away from the envelope is that the research data files aren't stored with a Crypt4GH envelope when they rest in the `interrogation` or `permanent` buckets, and so DHFS won't generate an envelope when it creates the new file encryption secret. Therefore, creating the envelope just to discard it doesn't serve a purpose.

#### EKSS HTTP API
> [Return to API list](#restfulsynchronous)

The `POST /secrets` endpoint will be updated to work as described here:
- No special authentication token is required because the API is only internally accessible.
- Request body must include a file encryption secret encrypted with the GHGA public key (or the public key configured for the EKSS, if a distinction is made).
- EKSS decrypts the file secret and stores it in Vault using `vault.store_secret()`.
- EKSS returns a `201 CREATED` response containing the Vault ID of the deposited secret.

#### Work to be performed for the EKSS
- Rewrite `post_encryption_secret()` to work as described above

---

### FIS:
The FIS straddles the border between the file services group and everything else, similar to the role played by the UOS. In the past, the FIS acted as a way to ingest file upload metadata and tell other services when a manually validated ("interrogated") file was ready for permanent storage. This had to be done as a temporary solution until the remote file upload and automatic file interrogation was implemented, which is the work proposed in this epic.

The new role of the FIS is to inform the DHFS when new files arrive in the DHFS's `inbox` bucket. To do this, the FIS operates as an event consumer in one instance, and runs an HTTP API in another instance. Both instances are described below.

#### FIS Event Consumer
The FIS subscribes to `FileUpload` *outbox events* from the UCS.

When a new `FileUpload` event arrives with the state `inbox` FIS first checks its database to see if it has a copy already stored in its database. If it does, FIS either ignores the event or raises an error depending on specific criteria (implementation detail). If the event is new, FIS stores the event as a `FileUnderInterrogation` using the [FileUnderInterrogation schema](#FileUnderInterrogation) so that it can be later relayed to the DHFS.

When a `FileUpload` event arrives with a state other than `init` or `inbox`, FIS checks whether the new state is one of `cancelled`, `failed`, or `archived`. If it is, FIS updates its local `FileUnderInterrogation` copy and sets `can_remove=True`. For other states (e.g. `interrogated`, `awaiting_archival`), FIS ignores the event since it doesn't affect the interrogation bucket. FIS should never store any information for a `FileUpload` with the state `init`.

> Note: FIS does **not** subscribe separately to `FileInternallyRegistered` events from the IFRS. The `can_remove` signal for successfully archived files is received via the `FileUpload` outbox event when UCS sets the state to `archived` after consuming the `FileInternallyRegistered` event.

#### FIS HTTP API
> [Return to API list](#restfulsynchronous)

The Data Hub public keys used for JWT verification are loaded directly from configuration (`data_hub_auth_keys`) rather than being fetched from the WKVS at startup.

In addition to implementing the endpoints defined here, the existing functionality and config that directly interacts with Vault should be removed so that EKSS is the sole middleman for Vault activity.

> See the [diagram](#example-auth-token-structure-for-dhfs-calls-to-fis-api) for an illustration of the proposed auth token structure for inbound requests to the FIS API

**JWT Authentication:**  
The FIS's endpoints which are meant for the DHFS require a JWT (JSON Web Token) signed with the Data Hub's private key. The `sub` field should contain the storage alias. The `aud` and `iss` fields should both be `GHGA`.

The FIS operates an HTTP API with these endpoints:
1. `GET /storages/{storage_alias}/uploads`: Serve a list of new file uploads (yet to be interrogated)
   - Authorization requires a JWT as described above.
     - FIS tries to verify the JWT using the public key associated with the `storage_alias` supplied in the endpoint.
   - Returns `200 OK` and a list of `BaseFileInformation` objects for files awaiting interrogation
   - Description:
     - FIS queries for `FileUnderInterrogation` records matching the requested `storage_alias` with `state="inbox"` and `interrogated=False`.
     - FIS returns the results projected to `BaseFileInformation` (which contains the fields needed for DHFS to perform interrogation but omits internal tracking fields like `state`, `interrogated`, `can_remove`, and `state_updated`).
2. `POST /storages/{storage_alias}/uploads/can_remove`: Returns a list of IDs indicating which files can be removed from the `interrogation` bucket
   - Authorization requires a JWT as described above.
     - FIS tries to verify the JWT using the public key associated with the `storage_alias` supplied in the endpoint.
   - Request body must contain the File IDs in question
   - Returns `200 OK` and list containing a subset of the IDs specified in the query parameters.
   - Although this operation is a retrieval, which would normally be a `GET` operation, we use `POST` because URL size could otherwise exceed several KB quite quickly.
   - Description:
     - For each file specified in the request body, FIS finds the existing `FileUnderInterrogation` in its database, raising an error if it doesn't find it. 
       - If the `FileUnderInterrogation` data isn't found for a given file, then the file should be considered removable (should be translated to True as an HTTP response but logged within the service as an error).
       - If the value of `FileUnderInterrogation.can_remove` is `True`, FIS adds the file ID to the list of removable files.
3. `POST /storages/{storage_alias}/interrogation-reports`: Accept an interrogation report
   - Authorization requires a JWT as described above.
     - FIS tries to verify the JWT using the public key associated with the `storage_alias` supplied in the endpoint.
   - Request body must contain a payload conforming to the `InterrogationReportWithSecret` [schema](#interrogationreport)
   - Returns `201 CREATED`
   - Description:
     - FIS finds the matching `FileUnderInterrogation` in its database based on the `file_id` (or raises an error).
     - If `InterrogationReport.passed` is True, FIS:
       - Sends the encrypted `InterrogationReport.secret` to the EKSS.
       - Updates `FileUnderInterrogation.secret_id` with the value obtained from EKSS.
       - Publishes an `InterrogationSuccess` event.
     - If `InterrogationReport.passed` is False, FIS publishes an `InterrogationFailure` event.
     - FIS sets both `FileUnderInterrogation.interrogated` and `FileUnderInterrogation.can_remove` to True

#### FIS Configuration
The FIS needs the following configuration:
- MongoKafkaConfig
- MigrationConfig
- ApiConfigBase
- LoggingConfig
- OpenTelemetryConfig
- EventPubConfig:
  - ghga-event-schemas -> `FileInterrogationSuccessEventsConfig`
  - ghga-event-schemas -> `FileInterrogationFailureEventsConfig`
- OutboxSubConfig:
  - ghga-event-schemas -> `FileUploadEventsConfig`
- ekss_api_url (via `SecretsClientConfig`)
- `data_hub_auth_keys`: a mapping of storage alias to public key string (used for JWT verification instead of fetching from WKVS)

#### FIS Migrations
The current FIS implementation has a persisted events collection, `fisPersistedEvents`, that contains previously published `FileInterrogationSuccessEvents` (`type_` is `"file_interrogation_success"`). These events are essentially the same as the events that will, going forward, be published by the UCS upon file archival. Therefore, we *also* need to make sure the FIS can publish to the same outbox topic as the UCS. The required migration for the persisted events collection in FIS essentially needs to convert the `payload` of the stored persisted events into outbox events with the new `FileUpload` [schema](#fileupload). This migration should be reversible. FIS will only publish to the `FileUpload` outbox topic if we *republish* events from the FIS. In other words, this is historical data that we are preserving here in FIS for continuity. The historical `FileUpload` information and the local copies of new `FileUpload` objects must use different DAOs. The former should use an outbox DAO while the latter uses a regular DAO. 
- **One alternative** is to manually exfiltrate the data to UCS.
- **A second alternative** is to simply drop the data since the files have already been archived and all relevant information is actually stored by IFRS.

There is one **problem**: IFRS has different object IDs than FIS. If we keep the event data which FIS currently has, we will need to update the information so that the file IDs in FIS are set to the file IDs (object IDs) known to IFRS, using the accession to match. That action would not be reversible, of course.

The `ingestedFiles` collection, which contains unassociated accessions, should be dropped.

Finally, FIS data migration should be moved to the init container style. Instead of executing `run_db_migrations()` as part of every entrypoint, the migrations should be run as their own command. 

#### Work to be performed for the FIS
- Ensure DLQ is enabled
- Add local definition for `FileUnderInterrogation`
- Swap persistent publisher in favor of outbox publisher for `FileUpload` events.
  - again, these are the historical data, the old events previously published by FIS.
- Add outbox subscriber for `FileUpload` events
  - These are the real, actually new uploads published by the UCS
- Add persistent publisher that compacts & stores `InterrogationSuccess` and `InterrogationFailure` events
- Add HTTP endpoints as [outlined above](#fis-http-api)
- Write migrations and address existing persisted event data as [described above](#fis-migrations).
- Move migrations to own CLI command so they can be run as an init container
  - Work with DevOps to get this configured in k8s

---

### DHFS:
The DHFS is a new service that is operated by the Data Hubs for the purpose of performing file validation and re-encryption, and to keep file ingest in general as a federated operation. The DHFS operates two instances: an `interrogate` instance, which performs the interrogation work and runs in a continuous polling loop; and a `cleanup` instance, which runs on demand (or on a schedule via an external orchestrator) and deletes files from the `interrogation` bucket once they've been copied to permanent storage. One crucial thing to note here is that the DHFS is not connected to an event stream, and so has no direct knowledge of the information conveyed by the events in GHGA Central's event stream. The DHFS primarily interacts with the GHGA Central API (operated by the FIS) in order to get that information, which is limited to only what the DHFS needs to operate.

#### DHFS Interrogator (primary instance)
It polls the GHGA Central API to get a list of `FileUploads` for files that have been recently uploaded to its `inbox` bucket. The DHFS decrypts each file and re-encrypts it using a new, individually created file secret before uploading it to the Data Hub's `interrogation` bucket. Along the way, it calculates the:
- Cumulative SHA-256 checksum of the entire unencrypted file
  - > Used to verify that the decrypted file is identical to what was uploaded by the user
- MD5 checksum of each individual, re-encrypted file part
  - > Used to verify that the `interrogation` bucket content matches what DHFS intended to upload
- SHA-256 checksum of each individual, re-encrypted file part
  - > Can be used to perform periodic integrity checks
  - > If we deviated from the GA4GH DRS Object spec for download, the GHGA Connector could verify file parts as they were downloaded, retrying parts that don't match. But that is out of scope for this epic.
When the whole file has been re-encrypted and uploaded to the Data Hub's `interrogation` bucket, the DHFS compares the unencrypted content's SHA-256 checksum against the value obtained from the corresponding `FileUpload`. It also calculates an aggregate MD5 checksum using the individually calculated parts' MD5 checksums and compares that against the MD5 ETag calculated by S3 in the `interrogation` bucket.
If a checksum discrepancy is found, the DHFS rejects the upload and posts an `InterrogationReport` to the FIS's HTTP API which indicates that the file did not pass inspection (`passed=False`) and provides a `reason` why the interrogation failed. If checksums match and there are no other errors during upload, the DHFS accepts the upload and the `InterrogationReport` sent to the FIS reflects that the file passed inspection (`passed=True`). The authentication mechanism for the DHFS-FIS calls is described in the [FIS HTTP API](#fis-http-api) section.

#### Interrogation Process in List Format
- [Per File]
  - Verifies that the file exists in the inbox bucket before proceeding
  - Derives the Crypt4GH envelope size (offset) from `FileUpload.encrypted_size` and `decrypted_size` (computed property on the `FileUpload` model)
  - Fetches the Crypt4GH envelope via a byte-range download (bytes 0 through `offset`)
  - Decrypts the envelope using the configured private key (specific to the Data Hub) to obtain the original file secret
  - Generates a new file secret for re-encryption (32 random bytes)
  - Initiates a multipart upload with the Data Hub's `interrogation` bucket
  - Streams the object from the Data Hub's `inbox` bucket part-by-part using either `FileUpload.part_size` or an adjusted value that keeps both the part count under 10k and the part size evenly divisible by the cipher segment size for optimal processing.
  - [Per Encrypted File Part]
    - Downloads and decrypts the part using the original secret
    - Re-encrypts the part using the newly generated file secret
    - Decrypts the re-encrypted content again (confirmatory decryption)
    - Updates the cumulative SHA-256 checksum over the re-decrypted content
    - Buffers the re-encrypted data; when the buffer reaches the adjusted part size:
      - Calculates the MD5 and SHA-256 checksums over the buffered part and appends each to their respective lists
      - Uploads the buffered part to the Data Hub's `interrogation` bucket
  - Compares the unencrypted file's SHA-256 checksum against the one reported by the submitter during upload (found in `FileUpload.decrypted_sha256`); aborts the multipart upload if there is a mismatch
  - Completes the multipart upload and verifies the S3 ETag matches the aggregate MD5 calculated from part checksums; removes the object from the interrogation bucket if there is a mismatch
  - Sends an `InterrogationReport` to the GHGA Central API
    - In the successful case, the `InterrogationReport` includes the new file encryption secret encrypted with the Central API's Crypt4GH public key.

#### DHFS Cleanup Job (secondary instance)
The secondary duty of the DHFS is to clean up files from the `interrogation` bucket. Files must be removed once they have been fully copied to the permanent bucket, as well as on occasions that files are deleted from their parent box. Neither the FIS, UCS, nor IFRS can perform this action because they don't have write access to the `interrogation` bucket. Each time this DHFS instance runs, it retrieves a list of all objects (files) currently in the `interrogation` bucket. Then the DHFS makes a single POST request to the GHGA Central API's `POST /storages/{storage_alias}/uploads/can_remove` endpoint and supplies the file IDs in the request body. As stated in the FIS section, although this operation is a retrieval and would normally be a `GET` operation, we use `POST` because URL size could otherwise exceed several KB quite quickly. For authentication, the DHFS signs a JWT with its private key. In response, the DHFS expects to get a list containing the IDs of files which may be deleted from the interrogation bucket. The DHFS will then *delete* each listed file from the `interrogation` bucket.

#### DHFS Configuration
The DHFS needs the following configuration:
- `LoggingConfig` (hexkit)
- `S3Config` (hexkit) — S3 endpoint URL, access key ID, and secret access key
- `central_api_url`
  - The base URL of the GHGA Central API (FIS)
- `central_api_crypt4gh_public_key`
  - The Crypt4GH public key of the Central API, used to encrypt the new file encryption secret before including it in the interrogation report
- `data_hub_crypt4gh_private_key_path`
  - Path to the Data Hub's Crypt4GH private encryption key, used to decrypt the file envelope
- `crypt4gh_private_key_passphrase` (optional)
  - Passphrase to decrypt the private key file, required only if the key is itself encrypted
- `data_hub_signing_key`
  - The Data Hub's private JWK (EC/ES256), used to sign JWT auth tokens sent to the GHGA Central API
- `storage_alias`
  - An identifier for this Data Hub instance (e.g. `"HD"`, `"TUE"`, `"B"`), coordinated with GHGA Central
- `interrogation_bucket_id` (default: `"interrogation"`)
  - Name of the S3 bucket used to store re-encrypted files
- `min_run_interval_seconds` (default: `60`)
  - Minimum number of seconds to wait between interrogation polling cycles
- `service_name` (default: `"dhfs"`)
  - Short name for this service instance
- HTTP client settings (`http_request_timeout_seconds`, caching capacity/TTL, retry count, and exponential backoff max)

#### Work to be performed for the DHFS
- Implement the `interrogate` CLI command with continuous polling loop support (`--forever` flag)
- Implement the `cleanup` CLI command for one-shot interrogation bucket cleanup
- Implement file interrogation core logic (envelope fetch, decrypt/re-encrypt/confirmatory-decrypt cycle, checksum calculation, multipart upload, report submission)
- Implement the S3 client adapter (multipart upload initiation/completion/abort, byte-range downloads, presigned URL caching)
- Implement the GHGA Central API client adapter (fetch new uploads, submit interrogation reports, query removable files)
- JWT auth token generation (ES256) signed with the Data Hub's private JWK
---

### IFRS:
The role of the IFRS is to shepherd files into archival, by copying them from a Hub's `interrogation` bucket into the `permanent` bucket located at the same Data Hub. This only occurs once the Data Hub in question has completed the interrogation process, as detailed in the [DHFS section](#dhfs) above. This is the last step for a file in the Upload Path. Unlike the FIS and DHFS, the IFRS operates only as an event consumer. The other responsibility of the IFRS is to listen for inbound `FileAccessionMapping` events.

#### IFRS Event Consumer
The IFRS subscribes to `FileAccessionMapping` events from the UOS. When a new one arrives, the IFRS first checks each accession in the map to make sure there isn't already a `DrsObject` with the same accession. If there is, it verifies that the S3 object ID matches the file ID in the received mapping and log it as *critical* if there's a discrepancy. If no `DrsObject` yet exists, then IFRS proceeds to look for a `PendingFileUpload` in its database (this is a `FileUpload` with a state of `awaiting_archival`). If no such entry exists, IFRS merely updates its accession mappings collection with the received information. If an entry does exist, however, then IFRS combines the `PendingFileUpload` data and the accession in order to perform the file registration procedure.

The IFRS subscribes to `FileUpload` outbox events from the UCS but only acts when it encounters an event with the state `awaiting_archival`. It further validates the event using the [PendingFileUpload schema](#PendingFileUpload). If the event represents a valid `PendingFileUpload`, IFRS first checks that it doesn't already have this file registered. If it's indeed a new upload, IFRS checks for an accession number in its accession mappings collection in the database. If no accession exists, the IFRS stores the `PendingFileUpload` in its pending files collection in the database. If an accession does exist, however, then the file registration procedure occurs.

**File Registration Procedure**  
IFRS copies the file from the `interrogation` bucket specified by `FileUpload.bucket_id` and `FileUpload.storage_alias` into the same location's `permanent` bucket. Once that is successful, the IFRS issues a `FileInternallyRegistered` event. This process is already in place within the IFRS, but some small tweaks are required. For example, the IFRS currently generates a *new* file ID when it registers a new file, meaning the a file would have one object ID in what is currently the inbox bucket, and a different object ID in permanent storage. This should change so the file ID is used as the object ID and remains constant from the time it is generated in the UCS through its lifespan at GHGA.

#### A note on file IDs and file accessions in the IFRS
In the future, file accessions will not exist in the file services. For now though, we will still identify files by the file ID and/or accession number depending on the context. For example, during file upload we point to files using the file ID, but during file download a user specifies a file using the accession number. There is no mechanism external to the file services that performs that linkage in a decoupled way -- but there will be, one day! 

Finally, the UUID4 file IDs generated by the recently revamped UCS during file upload are now also used as the object IDs in S3 storage. This does not have to be the case, and we can choose to generate a separate object ID if that layer of indirection is desired. At the time of writing though, this is not planned.

> Note: In the future when we replace the temporary accession map solution, we will need to drop both the pending files and accession mappings collections. No migration will be necessary.

#### Migrating existing IFRS data
The `file_metadata` collection needs the following changes:
- Remove `content_offset` field. The encrypted files are stored without an envelope, meaning the content offset is always 0.
- Rename `object_id` to `file_id` (`_id` in the database).
- Rename `object_size` to `encrypted_size`.
- Rename `decryption_secret_id` to merely `secret_id`.
- Rename `encrypted_part_size` to `part_size`.
- The list `encrypted_parts_sha256` is not currently used, but we are going to keep it for now. Originally the idea was for it to serve as another integrity check, but currently we only use the decrypted content's SHA-256 and the encrypted content's MD5 checksums for verification. In the spirit of "better to have it and not need it", we will keep this data (and continue producing it during re-encryption) for the time being.

The `ifrsPersistedEvents` collection needs similar changes to the `payload` field:
- Rename `file_id` (`_id` in the database) to `accession`.
- Rename `object_id` to `_id` to make it the primary field.
- Rename `s3_endpoint_alias` to `storage_alias`.
- Rename `decryption_secret_id` to `secret_id`.
- Delete `content_offset` because it is always zero (files stored without envelope).
- Rename `encrypted_part_size` to `part_size`.
- Replace the accession number in the compaction key field (`_id`) with the file ID
- Replace the value of the event `key` field with the file ID

Likewise, the `ifrsPersistedEvents` collection needs updates to the top-level fields:
- Set `published` to False
- Set `key` to the stringified UUID4 `file_id`
- Replace the accession value in the compaction key field (`_id`) with the file ID

IFRS data migration should be moved to the init container style. Instead of executing `run_db_migrations()` as part of every entrypoint, the migrations should be run as their own command.

> **Once IFRS data is migrated, all persisted events should be republished**.

#### IFRS Configuration
- OutboxSubConfig:
  - ghga-event-schemas -> `FileUploadEventsConfig`
- EventSubConfig:
  - ghga-event-schemas -> `FileAccessionMappingEventsConfig` (topic and type for `FileAccessionMapping` events from UOS)

#### Work to be performed for the IFRS
- Add local definition for `PendingFileUpload`
- Add event subscriber for `FileAccessionMapping` events
- Add DAO for `PendingFileUpload` and `FileAccessionMapping` data
- Make archival wait for an accession before proceeding (currently IFRS archives immediately upon receiving `awaiting_archival` without checking for an accession)
- Upon receiving a `FileUpload` with the state `awaiting_archival`, copy the file from the `interrogation` bucket to the IFRS's permanent bucket
- Use the `FileUpload.id` as the permanent-bucket object ID instead of generating a new UUID (to keep the file ID consistent across all services)
- Get the updated `ghga-event-schemas` version and adapt IFRS for changes to `FileInternallyRegistered`
- Migrate existing data in the `file_metadata` collection
- Create new collection to preserve existing file accession-to-file ID associations
- Migrate existing data in the `ifrsPersistedEvents` collection
- Move migrations to own CLI command so they can be run as an init container
  - Work with DevOps to get this configured in k8s

---

### DINS:
The Dataset Information Service (DINS) is only relevant here because it consumes `FileInternallyRegistered` events, stores that info in its database, and provides the information to public via HTTP API. DINS needs to be updated to use the new `FileInternallyRegistered` event schema. The data in the database already uses different field names, so no migration should be necessary. However, the code verbiage should be updated because it currently uses `file_id` to refer to a file accession. So instances of `file_id` should be changed to `accession`.

#### Work to be performed for the DINS
- Get the updated `ghga-event-schemas` version and adapt DINS for changes to `FileInternallyRegistered`. 

---

### DCS:
The DCS subscribes to `FileInternallyRegistered` events from the IFRS to learn about which files are available for download from GHGA. The changes in that event schema, which are described in the [schema definition](#fileinternallyregistered) above, necessitate database migrations and code updates in the DCS.

To make the file ID consistent across file services, the DCS should be modified so that
when it receives a `FileInternallyRegistered` event it updates the file ID stored on
the DRS object in its database. This could result in a one-time interruption for any
ongoing downloads, which will have to be restarted once the IFRS stages the same file to
the download bucket with the new object ID.

#### Migrating existing DCS data
The `drs_objects` collection needs the following migration changes applied:
- Rename `decryption_secret_id` to `secret_id`.
- Rename `s3_endpoint_alias` to `storage_alias`.

The `dcsPersistedEvents` collection needs the following changes to the `payload` field:
- Where `type_` == `drs_object_served`:
  - Rename `s3_endpoint_alias` to `storage_alias`.
  - Rename `decryption_secret_id` to `secret_id`
  - Replace accessions in `_id` and `key` with file ID
- Where `type_` == `drs_object_registered`:
  

Another note about the DCS migrations is that they should be moved to the init container style. Instead of executing `run_db_migrations()` as part of every entrypoint, the migrations should be run as their own command. 

#### Work to be completed for the DCS
- Get the updated `ghga-event-schemas` version
- Adapt code for schema updates
- Write migrations
- Move migrations to own CLI command so they can be run as an init container
  - Work with DevOps to get this configured in k8s

## Diagrams:

### Service Diagrams:
#### Service Map
![Service Map](./images/service_map.png)

#### S3 Bucket Access Permissions
![S3 Bucket Access Permissions](./images/bucket_access.png)

#### Normal Upload Sequence Diagram (Beginning as the Upload Completes)

```mermaid
sequenceDiagram
    box rgb(0, 150, 210, 0.5) Topics
        participant FileUploads
        participant InterrogationSuccess
        participant FileInternallyRegistered
        participant AccessionMappings
    end
    box rgb(255, 255, 200, .5) Services
        participant Connector
        participant UCS
        participant UOS
        participant EKSS
        participant FIS
        participant DHFS
        participant IFRS
    end
    box rgb(200, 75, 35, 0.5) S3 Buckets
        participant inbox
        participant interrogation
        participant permanent
    end
    
    Connector->>UCS: Finalize File Upload<br>to inbox bucket
    UCS->>FileUploads: UPSERT: FileUpload(state: INBOX)
    FileUploads->>FIS: UPSERT: FileUpload(state: INBOX)
    FIS->>FIS: Store FileUpload as FileUnderInterrogation
    DHFS->>FIS: GET (polling)
    FIS-->>DHFS: 200: list[BaseFileInformation]
    note left of DHFS: We will assume only one file is<br>returned. In reality, the list<br>returned by the FIS will contain<br>multiple files, and the DHFS will<br>process them in parallel.
    DHFS->>inbox: Fetch first file chunk to get envelope
    DHFS->>DHFS: Decrypt envelope with private key
    DHFS->>DHFS: Generate new file secret
    DHFS->>interrogation: Initiate multipart upload
    DHFS->>DHFS: Generate download URL
    rect rgb(30, 30, 30, .4)
        loop For each file chunk
            inbox->>DHFS: Stream file chunk
            DHFS->>DHFS: Decrypt with old secret
            DHFS->>DHFS: Re-encrypt with new secret
            DHFS->>DHFS: Decrypt the re-encrypted data
            DHFS->>DHFS: Update checksums
            DHFS->>interrogation: Upload file chunk
        end
    end
    DHFS->>DHFS: Compare checksums
    rect rgb(30, 90, 30, .8)
        alt Interrogation is successful
            DHFS->>interrogation: Complete multipart upload
            DHFS->>FIS: POST InterrogationReportWithSecret(passed=True)
            FIS->>EKSS: Submit encrypted secret
            EKSS-->>FIS: Secret ID
            FIS->>InterrogationSuccess: Publish: InterrogationSuccess
            InterrogationSuccess->>UCS: Consume: InterrogationSuccess
            UCS->>FileUploads: UPSERT: FileUpload(state=INTERROGATED)
        end
    end
    rect rgb(90, 30, 30, .8)
        alt Interrogation fails
            DHFS->>interrogation: Abort multipart upload
            DHFS->>FIS: POST InterrogationReportWithSecret(passed=False)
            FIS->>InterrogationSuccess: Publish: InterrogationFailure
            InterrogationSuccess->>UCS: Consume: InterrogationFailure
            UCS->>FileUploads: UPSERT: FileUpload(state=FAILED)
        end
    end
    UCS->>inbox: Delete File
    note right of FIS: Assume interrogation success
    note right of UCS: Data Steward submits<br>file accession map
    note right of UCS: At some point<br>UOS requests to<br>archive the box
    UOS->>UCS: PATCH archive the box
    UOS->>AccessionMappings: Publish: FileAccessionMap
    AccessionMappings->>IFRS: Consume: FileAccessionMap
    rect rgb(30, 30, 30, .4)
        loop For each file in box
            UCS->>FileUploads: UPSERT: FileUpload(state=AWAITING_ARCHIVAL)
            FileUploads->>IFRS: UPSERT: FileUpload(state=AWAITING_ARCHIVAL)
            IFRS->>interrogation: Copy File from interrogation to permanent bucket
            interrogation-->>permanent: Copy File
            IFRS->>FileInternallyRegistered: Publish FileInternallyRegistered
            FileInternallyRegistered->>FIS: Consume FileInternallyRegistered
            FIS->>FIS: Set FileUnderInterrogation.can_remove=True
            note right of FIS: DHFS cleanup job asynchronously<br>gets files with can_remove=True
            FileInternallyRegistered->>UCS: Consume FileInternallyRegistered
            UCS->>FileUploads: UPSERT: FileUpload(state=ARCHIVED)
        end
    end
```

#### DHFS Cleanup Job Sequence Diagram
```mermaid
sequenceDiagram
    box rgb(255, 255, 200, .5) Services
        participant FIS
        participant DHFS
    end
    box rgb(200, 75, 35, 0.5) S3 Buckets
        participant interrogation
    end
    
    DHFS->>interrogation: List object IDs (polling)
    interrogation-->>DHFS:
    DHFS->>FIS: POST (file IDs in request body)
    rect rgb(30, 30, 30, .8)
        loop For each file specified in query params
          FIS->>FIS: Retrieve FileUnderInterrogation
          FIS->>FIS: If can_remove, append ID to list
        end
    end
    FIS-->>DHFS: List of files to delete
    rect rgb(30, 30, 30, .8)
        loop For each file in list
          DHFS->>interrogation: Delete file
        end
    end
```

#### `FileUpload` State Diagram
```mermaid
stateDiagram-v2
    [*] --> init: UCS - Upload initiated
    init --> inbox: UCS - Upload completed
    inbox --> interrogated: DHFS report -> FIS (passed)
    inbox --> failed: DHFS report -> FIS (failed)
    inbox --> cancelled: UCS - file deleted
    interrogated --> awaiting_archival: UCS approves archival request
    awaiting_archival --> archived: UCS consumes FileInternallyRegistered
    archived --> [*]
    failed --> [*]
    cancelled --> [*]

    note left of inbox
      Source of truth:
      - State set by UCS
      - Transitions driven by InterrogationSuccess/InterrogationFailure published by FIS
    end note
```


## Human Resource/Time Estimation:

Number of sprints required: 4

Number of developers required: 1-2
