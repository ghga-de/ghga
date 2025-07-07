# DLQ Service (Matamata Turtle)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
This epic is concerned with the implementation of a basic dead letter queue service,
which will provide the means to assess, process, and retry Kafka events that resulted
in errors during their initial processing.

### Included/Required:
- Implementation of the DLQ service (including its test suite)
- `hexkit`: Add exception information to DLQ event headers
- `hexkit`: Add event ID header consisting of the service, original topic, partition, 
  and offset.
- `hexkit`: DLQ-specific protocol to pass timestamp and headers to service translator.
- Enabling the DLQ in existing services


### Not included:
- A web-based user interface

## API Definitions:

### RESTful/Synchronous:

When interacting with DLQ topics via the API, only the service abbreviation and the 
plain topic name are required.

- `GET /{service}/{topic}`
  - *Returns the next events in the topic.*
    *This is a preview of the events and does not impact event ordering within the DLQ.*
  - Auth Header: internal token
  - Query parameters:
    - `skip` *(int)*: pagination param to skip the first `skip` results
    - `limit` *(int)*: the maximum number of events to preview per 'page'
  - Response Body: array of event objects
  - Response Status:
    - `200 OK`: The preview was successful
    - `401 Unauthorized`: auth error (not authenticated)
- `POST /{service}/{topic}`
  - *Processes the next event in the topic, optionally publishing the supplied event.*
    *Returns the payload passed to the publisher.*
  - Auth Header: internal token
  - Query parameters:
    - `dry_run` *(bool)*: if True, the endpoint will not actually publish the event to
    the retry topic or delete it from the database. This is useful for verifying what
    will get published before resolving an event.
  - Request Body: DLQ ID of the event to resolve and, optionally, a JSON
    representation of corrected event (see schema below).
  - Response Body: the event that was/would be published.
  - Response Status:
    - `200 OK`: The event test or publish was successful
    - `422 Unprocessable Entity`: The non-empty request body is not a valid event. 
    - `401 Unauthorized`: auth error (not authenticated)
- `DELETE /{dlq_id}`
  - *Directly discards the event with the specified DLQ ID*
  - Auth Header: internal token
  - Response Body: empty
  - Response Status:
    - `204 No Content`: The event has been discarded (or was already deleted)
    - `401 Unauthorized`: auth error (not authenticated)

All endpoints should require an internal auth token.

### Payload Schemas for Events:

**Outbound from DLQ Service**:  
The outbound events published to retry topics will look exactly like other Kafka events
published or consumed by the GHGA microservices, except they will feature the
`original_topic` header.

**Inbound to DLQ Service**:  
The inbound events in the DLQ topics will feature additional
headers to communicate exception information like the message and class name. That will
require a small modification to `hexkit`. In addition to the exception information,
DLQ events will feature a header containing the service abbreviation, original topic,
partition, and offset of the failed event in a single string. This enables devs to
quickly confirm that the event they see in the DLQ service is in fact the same event
from a given error log. The DLQS will extract this DLQ-specific information and
store it in a top-level field called `dlq_info` (see below for an example). The
original `event_id` field will not be persisted once its information is extracted.


**Previewed Events**:  
Previewed events will be formatted as seen below and return as JSON:
```json
{
  "dlq_id": "uuid4",  // Added by the DLQS
  "topic": "dlq",
  "type_": "upserted",
  "payload": {...},
  "key": "some key",
  "timestamp": "2025-02-10T16:55:05.751470+00:00",
  "headers": {
    "correlation_id": "uuid4",
    "original_topic": "users",
  },
  "dlq_info": {  // Extracted from the headers by the DLQS
    "service": "nos",
    "partition": 0,
    "offset": 17,
    "exc_cls": "RuntimeError",
    "exc_msg": "Useful error message"
  }
}
```

**Processed Events**:
The `POST` endpoint, used to process a DLQ event, requires the `dlq_id` in the body.
User-supplied events meant to be published to a retry topic in place of the stored DLQ
event must also supply the `topic`, `type`, `payload`, and `key`. The values for
those fields can differ from the stored DLQ event, but the `dlq_id` must be unchanged.
Other fields will be ignored if supplied. The correlation ID will be pulled
from the original DLQ event to re-use upon publishing to the retry queue.

```json
{
  "dlq_id": ...,  // Must match the DLQ ID of the corresponding DLQ event
  "topic": ...,
  "type_": ...,
  "payload": {...},
  "key": ...,
}
```

## Additional Implementation Details:

### Definitions:
- *Requeue/Republish an event*: In the context of the DLQ service, this means to publish
  the next Kafka event from a given DLQ topic to the corresponding retry topic.
- *Process an event*: Validate a DLQ event for a given service and topic in
  order to send it to the retry topic. The event will either be republished or
  discarded as a result.
- *Discard an event*: To decline to requeue/republish an event to the retry topic.
- *Resolve an event*: Process or discard an event.
- *Preview events*: Peek at the next N events without affecting the order of events in
  the DLQ topic. This is crucial functionality that enables the user to decide how to
  resolve the next event.

### DLQ Sequence Illustrated
![DLQ Flow](./images/db%20dlq%20flow.png)

1. A service tries to consume a newly published event, but encounters an error.
2. The service tries again, also unsuccessfully.
3. Retries are exhausted, so the service publishes the event to the global DLQ topic.
4. The DLQ Service consumes the event from Kafka and stores it in the database.
   - This involves extracting/adding the 'service' and 'event_id' fields.
5. Developers query the DLQ Service via the HTTP API to resolve an event.
6. The DLQ Service gets the event from the DB and does basic validation.
7. The event is sent to the original service's retry topic.
8. The DLQ Service returns the published event information to the client.
9. The service consumes the previously-DLQ'd event from its retry topic.

### DLQ Topic Arrangement
There is one global DLQ topic. The DLQ topic name is set in configuration for some degree of
flexibility should it be needed, but all services should use the same configured value.
The default is `dlq`.

### Persisting DLQ Events
The DLQ Service will continually consume from the DLQ topic. When it gets an event,
it will immediately transform and store the event in the database.
Under the initial implementation, all events will go into a single collection.
MongoDB's `aggregate` functionality will be used (as in `mass`) to pull back the
correct events for a given `service` and `topic`, sorted by timestamp.

### Event Ordering:
Dead letter queues inherently present a potential threat to system-wide event ordering.
However, ordering events by keys, the idempotent design of our services, and
sorting events by timestamp (oldest first) prevents sequence problems
as long as events are designed to use the correct keys and topics in the first place.

### Event identification:
Right now, events can be identified through a combination of correlation ID + event
type and topic. It would be easier if there were a single field to associate a given
event in a DLQ topic with its source event in the original topic. The combination of
service name, topic name, partition, and offset uniquely identify an event, so we
can concatenate the values in a single string and pass it along as an event header.

E.g.: `dcs,file-registrations,0,123` would indicate an event from the "file-registrations"
topic, partition 0, offset 123. The information is only seen by the consumer, not by the
publisher, which is the only downside of doing it this way instead of generating a UUID
right before publishing the event.

The event ID is always created, but only propagated if it enters the DLQ cycle.
This differs from the correlation ID, which is propagated across services and persisted
in the database in the case of outbox events.

Consider this example where some unnamed service publishes an event to the
the `users` topic, where the event is stored in partition 0 at offset 17 and later
consumed by the `NOS`:

![Event ID usage](./images/event%20ID.png)
1. The `hexkit` Kafka provider used by the `NOS` gets the message from `aiokafka`.
2. The `aiokafka` version of the event is formatted into an instance of the
   `ExtractedEventInfo` class, where its event ID is created.
3. The Kafka provider hands the transformed event over to the service-defined
   translator, which performs some business logic driven by the event.
   - Here, an error occurs, and all retries fail as well.
   - The Kafka provider logs the error, including the event ID (`"nos,users,0,17"`).
4. The Kafka provider publishes the event with the event ID header to the DLQ topic.
5. We use the DLQ service to take a look at the failed event.
   - We learn the problem was actually a database issue that we've since fixed.
6.  We use the DLQ service to publish the event to the retry topic, sans event ID header.
Instead, the DLQ service includes a special header with the original topic ("users").
1.  The `NOS` encounters the republished event, this time from its dedicated retry
  topic. The Kafka provider understands that the retry topic is special, so it obtains
  the topic field from the original topic header. If the retry event fails again, the
  old event ID would be misleading had we modified the event in the DLQ service.

If the translator encounters no errors, the event ID is not used (except for debug
logging that might take place in `hexkit`).


### Event processing:
When we resolve the next event in a given DLQ topic, it can go one of two ways:
- We can discard the event, meaning it is not republished to a retry queue and is
  effectively ignored.
- We can process the event, where the event is published to the retry topic or
  discarded (e.g. if the service info is missing). The processing can also be bypassed
  by directly supplying a JSON event to the API, which publishes the event outright
  as long as the correlation ID matches.

In both cases, the event's `dlq_id` must be accurately provided to prevent mistaken
event resolution (imagine two developers call the `DELETE` endpoint simultaneously...).
This will ensure idempotent operation.

Another useful piece of information for the DLQ service is the exception information.
There is currently no mechanism to provide that to the DLQ service, but the info could
be passed through event headers. The exception header would then be removed upon
republishing the event to a retry topic.

This [Java DLQ implementation](https://medium.com/nerd-for-tech/-to-re-queue-apache-kafka-dlq-messages-95941525ca77)
uses such headers (toward the bottom).


### Previewing Events:
Events will be aggregated by the requested service and type, then sorted by timestamp,
before finally applying any pagination (if applicable) using the `skip` and `limit` 
parameters. The returned events will include the `dlq_info` and `dlq_id` fields, the
latter of which must be referenced for event resolution.


### Discarding Events:
Events can be discarded by calling the `DELETE` endpoint and supplying the `dlq_id`.
The `DELETE` endpoint is unique in that it disregards event order. Because the
operation removes the event and does nothing further with it, events don't have to be
deleted from the head of the topic, i.e. in order of timestamp. Deleting events by
their DLQ ID also ensures idempotence. If the event has already been deleted, nothing
needs to be done. Finally, this approach means that the `service` and `topic`
parameters required for the `GET` and `POST` endpoints are not required.


### Tests:
At the very least, the DLQ service tests should cover the following:
- Test that previewing is idempotent and returns events in consistent order
- Test that endpoints are secured
- Test that API calls trigger the correct action
- Test that events are published to the correct retry topics
- Test that only one event is processed or discarded per API call
- Test that the preview endpoint returns the next N events (e.g. not off by 1)
- Test that only events for the requested service/topic are retrieved from the DB
- Test that events are deleted from the DB upon discard or processing
- Test that events are retrieved from the DB in chronological order


### Usage:
- Startup: 
  - `dlqs run-rest`: Start up the REST API
  - `dlqs consume-events`: Run the event consumer
- Preview & resolve events: Done via HTTP API calls.

### Scaling:
The DLQ Service should not be scaled, because the manual intervention required will
be the limiting factor rather than infrastructure.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
