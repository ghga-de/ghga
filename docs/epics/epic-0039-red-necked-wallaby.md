# Upload refactoring and cleanup (Red-necked Wallaby)
**Epic Type:** Implementation Epic

## Scope

This epic consists of refactoring tasks for the preliminary and non-preliminary upload path.
This includes changes to 1) the datasteward-kit and file ingest service, regarding how file encryption/decryption secrets are ingested, 2) finishing the ongoing refactoring of the GHGA Connector to make the code base less rigid for future modifications and 3) bringing the upload controller up to speed with the rest of the microservice landscape.

### Outline:

All three major tasks are independent of each other and can be done in parallel.

#### Datasteward-Kit Changes:

- Keep the existing ingest and file upload commands, but rename them and mark them as legacy/deprecated (e.g. legacy-files upload/legacy-files batch-upload)

- Add new upload commands to that are based on the existing ones, but have one slight difference: The output metadata contains the secret ID instead of the actual file encryption/decryption secret. This means the following changes are necessary
    - Before writing the output metadata file, the file secret is stored and a secret ID returned by calling the new `POST /federated/ingest_secret` endpoint
    - If the secret deposition fails, the uploaded file needs to be cleaned up, i.e. deleted after retry logic is exhausted

#### File Ingest Service Changes:

- Keep the existing `POST /ingest` endpoint to handle metadata for already updated files
- Add two new endpoints that split the existing functionality between them:
    - `POST /federated/ingest_metadata` that should be used by a central data steward to ingest the metadata into the file services, i.e. this endpoint no longer communicates with the vault but directly gets the secret ID in the received file metadata
    - `POST /federated/ingest_secret` that should be used by local data stewards during file uploads to ingest the secret into vault and return the corresponding secret ID

- All endpoints should use the security measures employed by the existing endpoint, i.e. token/token hash pairs for authentication, asymmetric payload encryption using Crypt4GH keypairs and communication only over HTTPS

#### GHGA Connector Changes:

- The Connector currently is a bit brittle with regard to being modifiable/extendable. Existing upload/download code should be refactored to a more object oriented approach, using abstract base classes to decouple concerns between different parts of the functionality where possible.

#### Upload Controller Changes:

- The upload controller is currently the most outdated service in the file backend microservice landscape. Thus two subtasks are needed to bring it up to state with the other microservices: 1) Investigate what needs to be changed/updated and 2) implement the required changes.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
