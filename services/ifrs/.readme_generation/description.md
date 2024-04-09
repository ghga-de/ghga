This service provides functionality to administer files stored in an S3-compatible
object storage.
All file-related metadata is stored in an internal mongodb database, owned and controlled
by this service.
It exposes no REST API enpoints and communicates with other services via events.

### Events consumed:

#### files_to_register
This event signals that there is a file to register in the database.
The file-related metadata from this event gets saved in the database and the file is
moved from the incoming staging bucket to the permanent storage.

#### files_to_stage
This event signals that there is a file that needs to be staged for download.
The file is then copied from the permanent storage to the outbox for the actual download.
### Events published:

#### file_internally_registered
This event is published after a file was registered in the database.
It contains all the file-related metadata that was provided by the files_to_register event.

#### file_staged_for_download
This event is published after a file was successfully staged to the outbox.
