# File Deletion and Outbox Cache Strategy (Chinese Pangolin)
**Epic Type:** Implementation Epic

## Scope
### Outline:

This Epic adds a new service, which provides a deletion endpoint for files.
Calling this enpoint internally publishes an event.
All services subscribing to this event will then delete the corresponding file and information pertaining to it from their databases and from the S3 buckets they have write access to.

### Included/Required:

This Epic includes:

- The creation of a new service, the **Purge Controller Service (PCS)**, which provides a RESTfull HTTP DELETE enpoint /files/{file_id}.
- Upon receiving the deletion request and validation of the access token it publishes an event
- The following services subscribe to the new event and do the following after consuming:
    - IFRS: Deletes the file from permanent storage (IRS would be better, but IRS does not have the connection between outward-facing file_id and S3 file name)
    - IFRS: Delete file entry from its database
    - DCS: Delete file entry from its database
    - IFRS: Send API Call to EKSS to delete the secret
    - IFRS: Delete file from outbox
    - Both services: Publish confirmation event afterwards
- The EKSS provides a new RESTful HTTP DELETE endpoint /sercets/{secret_id} that deletes the corresponding secret from vault.

These parts of the epic are described in detail below.

### Optional: Caching Strategy for DCS/Outbox

- Add a "last_accessed" field for each entry in the DCS files database
- Each time a file is sucessfully accessed via a download request, update its "last_accessed" field
- Provide a script that scans the "last_accessed" field of all files currently present in the Outbox. If the timedelta since the last access is above a certain (to be determined) threshold, delete the respective file from the Outbox.

### Not included:

Any functionality concerning caching/cleanup of the upload path.

- Delete file entries from UCS Database
- Delete files from Inbox
- Delete files from Staging

## API Definitions:

### RESTful/Synchronous:

The PCS should have a single endpoint that can be accessed to delete files, conforming to the GDPR's right to be forgotten.

- PCS: DELETE /files/{file_id}
    - auth header: internal access token
    - Response: 204 'No Content'
    - If the validation of the auth header fails: 403 'Forbidden'

This will internally send out a deletion event (See below.)

The EKSS will get a corresponding endpoint to delete a file secret.

- EKSS: DELETE /secrets/{secret_id}:
    - no header, no body
    - Response: 202 'Accepted'
    - If the secret could not be found, send 404 with a "secretNotFoundError"

### Payload Schemas for Events:

A deletion event schema will be defined in the ghga-event-schemas repository.
The event schema will detail contain:
    - file_id (outward-facing id of that file)
The exact field names and constraints will be provided in the ghga-event-schemas repository, which is considered the source of truth.

This event will be used to announce a file deletion by the PCS.

A deletion event confimation schema will be defined in the ghga-event-schemas repository.
The event schema will contain:
    - file_id (outward-facing id of that file)
The exact field names and constraints will be provided in the ghga-event-schemas repository, which is considered the source of truth.

This event will announce the deletion of a file from the S3 storage buckets that fall within the responsibility of the service emitting the event and the removal of all corresponding entries in the service database.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
