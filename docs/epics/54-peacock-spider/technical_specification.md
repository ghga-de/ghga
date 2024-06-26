# File Information Service (Peacock Spider)
**Epic Type:** Implementation Epic

## Scope
### Outline:

This epic aims to create a new service that provides an authoritative source of truth for file information.
File information includes (for now) file size and checksums.

### Included/Required:
    
To obtain the correct file information, the File Information Service needs to listen to events produced in the file service backend. 
The proposed event that should be captured by this new service is `FileInternallyRegistered`.
This event contains all relevant information and it is guaranteed that the file in question is actually stored in permanent storage at that point in time.

Additionally, the service needs to subscribe to file deletion events and remove all data as requested.

File information should be provided through one simple REST endpoint returning all relevant information.

### Not Included:

Return of internal only file metadata, i.e. encrypted part sizes as MD5 and SHA256 hashes and encrypted part size.

## API Definitions:

### RESTful/Synchronous:

- GET `/file_information/{file_id}`: Get file size and sha256 for the unencrypted file content

Here the `file_id` is the public accession for the given file.

This should return a payload including the unencrypted file size in bytes and SHA256 checksum for the given file ID,
hiding unnecessary details for the requester.
```
{
    'size': ...,
    'sha256_hash': ...,
}
```

### Payload Schemas for Events:

Incoming population event: [FileInternallyRegistered](https://github.com/ghga-de/ghga-event-schemas/blob/faf00f361facc4195f2b9e9a0a69ec9645464bc3/src/ghga_event_schemas/pydantic_.py#L270-L273)

From this event, only the `file_id`, `decrypted_size` and `decrypted_sha256` need to be stored in the service.
These represent publicly accessible metadata that should be exposed by the service.

Incoming deletion event: [FileDeletionRequested](https://github.com/ghga-de/ghga-event-schemas/blob/faf00f361facc4195f2b9e9a0a69ec9645464bc3/src/ghga_event_schemas/pydantic_.py#L372-L381)

## Additional Implementation Details:

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
