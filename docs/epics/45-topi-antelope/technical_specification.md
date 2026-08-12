# Structured Logging Tools (Topi Antelope)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
The aim of this epic is to implement tools that enable consistent structured logging,
with the result being a set of minimally-invasive, configurable logging tools. The
logging functionality is not meant to live within providers or protocols within hexkit,
but rather be provided as a utility similar to the basic correlation ID functionality.
In addition, `uvicorn` needs to be configured such that its formatting is consistent
with other logs.

### Included/Required:
- Logging Tools in Hexkit
- Consolidating Uvicorn Logging
- Pilot Repository

### Not Included:
- Updating services to use new logging tools.


## Additional Implementation Details:

### Logging Tools in `Hexkit`
There needs to be a way to easily invoke a logger object with minimal boilerplate code.
There should also be a dedicated logging configuration class that subclasses `BaseSettings`.

The configuration should at least include:
- The log level for the service (`log_level`),
- The service name (`service_name`)
- The service instance ID (`service_instance_id`)

When employing loggers in a service, it should be as easy as calling a function with a logger
name as an argument and then using the object to log as needed.
The logs should be emitted in a JSON string format (one line). An example log message is as
follows (formatted for ease of reading):

```json
{
  "timestamp": "2023-12-04T15:30:00Z",
  "service": "ucs",
  "instance": "001",
  "level": "ERROR",
  "correlation_id": "d826361b-3734-4590-b3e8-3cbed68b9236",
  "message": "The file with ID 123xyz is already in the inbox.",
  "details": {
    "file_id": "123xyz" // example detail
  }
}
```
Additional configurable properties could include:
- A flag to control uvicorn integration (e.g. for easier reading during development)
- A format string which, if used, will replace the JSON output format.

To summarize, this task includes all items in `hexkit`:
- Logging Configuration Class
- Logger factory
- The subclass implementations of any support `logging` classes, such as
Formatter and LoggerAdapter.

### Consolidating Uvicorn Logging
`ghga-service-commons` needs to be modified so uvicorn's logging can be configured using the same
config model used in hexkit.
Uvicorn uses a special formatter class and comes with colored output. However, it does
not include certain standard information by default, such as a timestamp.
Uvicorn should be configured or set up such that any log produced by it have the same
JSON format and contextual information. The logs should be shipped with timestamps and all
relevant information listed in the example above. Uvicorn is configured to use three different
loggers by default:
- "uvicorn"
- "uvicorn.error"
- "uvicorn.access"

### Pilot Repository
A single repository (which is to be determined) will be updated as part of this epic.
The purpose of this is to verify the aforementioned changes and identify any problems
before rolling out the changes to other services.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
