This service exposes an external API to commission file deletions from the whole
file backend.

### API endpoints:

#### `DELETE /files/{file_id}`:

This endpoint takes a file_id.
It commissions the deletion of the file with the given id from the whole file backend.
### Events published:

#### file_deletion_requested
This event is published after a file deletion was requested via an API call.
It contains the file_id of the file that should be deleted.
