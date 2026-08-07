# Upload Metadata Ingest and Unique S3 ID for Permanent Storage (Proboscis Monkey)
**Epic Type:** Implementation Epic

## Scope

This epic has two different goals.
First of all, internal ID handling needs to be changed to use a unique ID for S3 objects instead of directly using the file ID.
The second task is the implementation of an ingestion service that processes metadata files produced by the file upload script.

### Outline:

#### Ingestion Service:

The ingestion service will provide a RESTful endpoint to process the output files of the upload script, one at a time.
This endpoint expects the assymetrically encrypted output metadata as body and an authentication token hash in the header.
To simplify the process, the private key of the encryption keypair is provided as a configuration option to the service, as is the token hash for authentication.
The actual token from which the hash is derived and the public key remain with the submitter.

The service needs to take care of
 1) firing a `FileUploadValidationSuccess` event to propagate information to the IFRS/DCS databases using existing mechanisms
 2) communication with the vault to store the encryption/decryption secret using `VaultAdapter` from the encryption key store

In addition, the data steward scripts need to be extended to include a script interacting with this endpoint.

#### Unique S3 ID:

Currently only one ID is used across all file services, however, a different, unique ID (in the form of a UUID4) should be used to identify the corresponding objects in S3.
This will allow to better separate internal only concerns from outward facing ones.
Each bucket (inbox, staging, permanent, outbox) should have their own S3 ID for an object, i.e. the S3 ID should not be shared between buckets.
These ID needs to be communicated to services further downstream that move data between buckets via existing events.

In addition, source bucket IDs should now be provided in the events coming from the corresponding upstream service instead of being part of the service config.

This task requires changes to the event schemas, and all file services excluding the encryption key store.

### Included/Required:

#### Upload Controller:

- `UploadService` shoud take care of generating the inbox bucket object ID
- Update `UploadAttempt` model to include object ID
- Update `FileMetadataUpsert` model to include object ID

#### Interrogation Room:

- `CipherSegmentProcessor` needs to take care of generating the staging bucket object ID

#### Download Controller:

- Change `DrsObject` model to include object ID
- `DataRepository` needs to take care of generating the outbox bucket object ID
- `DataRepositoryPort.cleanup_outbox` should use object ID instead of file ID for S3
- `DataRepositoryPort.delete_file` should use object ID instead of file ID for S3

#### Internal File Registry:

- Change `FileMetadata` model to include object ID
- `FileRegistry` needs to take care of generating the permantent storage bucket object ID
- `FileRegistryPort.delete_file` should use object ID instead of file ID for S3
- Change `ContentCopyService`:
  - `staging_to_permanent` needs source and taget object + bucket IDs now
  - `permanent_to_outbox` needs source and taget object + bucket IDs now


## API Definitions:

### Payload Schemas for Events:

- `FileUploadReceived` should include inbox object ID.
- `FileUploadValidationSuccess` should include staging object ID
- `FileInternallyRegistered` should include permanent storage object ID

All these events also need to have the corresponding bucket ID included.
## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
