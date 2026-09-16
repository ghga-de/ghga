# Preliminary Storage Selection (Madagascan Sunset Moth)
**Epic Type:** Implementation Epic

## Scope
### Outline:

This epic aims to change the current quasi hardcoded solution for propagating the correct storage location of files uploaded via the Datasteward Kit to a user facing decision.
Instead of setting a storage alias in the config of the File Ingest Service, the alias information should be part of the information the DS Kit sends to the File Ingest Service.

### Included/Required:

Storage alias information in the DS Kit should be provided during the file upload step.
Therefore, the current metadata needs to be updated to include the storage alias for the specific file.
To simplify interaction with the DS Kit, the alias should be provided as config option in addition to the storage config.
For compatibility with older, already created metadata, the storage alias from config should be added during ingest in the DS Kit, if none is provided in the metadata.
The corresponding documentation should highlight this feature.

The local storage configuration needs to match what is configured for the services in the backend.
To this end, the Well Known Value Service should provide a map of all configured storage aliases and their respective URLs.
Credentials for the different storage nodes still need to be set locally.

In addition, the File Ingest Service also needs to have all valid storge aliases configured to validate the data sent by the DS Kit.

## API Definitions:

### RESTful/Synchronous:

The following existing File Ingest Service endpoints need to be changed:

- POST /legacy/ingest
- POST /federated/ingest_metadata

The expected payload for both endpoints now includes the storage alias.
Additionally, for the non-legacy endpoint, the metadata payload no longer needs to be encrypted as the plain text secret is not present in the payload.

In addition, the Well Known Value Service needs to provide a new value at the existing

- GET /values/{value_name}

endpoint. 
The proposed value name is `storage_aliases` and this endpoint should return a map of all configured storage aliases and their respective URLs.

## Additional Implementation Details:

The Datasteward Kit/File Ingest Service interaction for both non-secret ingest endpoints is changed slightly, by only including the storage alias in the payload sent and received. Theoretically this results in an additional overhead of calling the WKVS for each payload received, but as aliases should not be removed, results can simply be cached in memory and only re-requested when an alias is not found in the local cache.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
