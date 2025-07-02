# Kafka Event IDs (Eurasian Blackbird)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).


## Scope
### Outline:
The aim of this epic is to provide Kafka event identification for deduplication by
canonizing a UUID4 header for all events (`event_id`). The `NOS`, `NS`, and `DLQS` will
receive updates targeting this change after updating `hexkit`.

Changes for `hexkit` should be included in the same release as the changes from the
[Slow Worm](../74-slow-worm/technical_specification.md) epic.

### Motivation:
Currently, idempotence is only achievable
by consumers when they store some portion of an event, directly or indirectly,
in the database. Thus, the method of implementing idempotence is different for each
context. That's not a problem until it is.

Consumer idempotence has to handle two cases:
1. Kafka event replay - seeing the exact same Kafka event again, as when consumer offsets are reset due to a group ID change or some other occurrence.
2. Event republish - which creates Kafka events that are technically new but carry
the same payload or are spiritually identical to a past event.
- Republishing can include "outbox" events and "persistent" events
- "Outbox" events are stateful and carry the last known state of an object, so they
  carry minimal concern with regard to idempotency.
- "Persistent" events are stateless, so it's crucial to know if it's a repeat.

The `NOS` and `NS` have shown the need
for a more durable and consistent way to deduplicate inbound Kafka events. The `NOS`
sources events from various topics, and currently has no idempotence checks in place
for some of those events. If we modify the consumer group ID or republish events from
one of those upstream services, the `NOS` will issue *new* Notification events, and
the `NS` will send new emails. We could store the event as a whole, or store its hash
(like in the `NS`), or store a deduplication key based on certain values, but they
have problems:
- *Whole event*: waste of space
- *Hash of event*: opaque, unable to modify if we need a migration
- *Semantic Dedupe Key*: heterogeneous format, possibility to clash
- *All of the above*: vulnerable to upstream republish post-DB migration

If all Kafka events have a standard UUID4 header, stored and revived like the
correlation ID, then deduplication becomes significantly easier. Services can store
the IDs and perform an idempotence check atomically via `.insert()`.

In the highly improbable case that an inbound event's ID collides with that of another
event in a deduplication store, the event will go to the DLQ and we can just give it
another ID.

### Included/Required:
Hexkit:
- Protocols:
  - Event Pub: no change
  - Event Sub: expose `event_id` header to translators (similar to "type_")
- Providers:
  - Event Sub: 
    - Extract `event_id` header, convert to UUID4, and pass to translator.
      - This should *replace* the `event_id` used by the DLQ.
    - Move the `service` info to its own header in the DLQ case.
  - Event Pub:
    - Generate UUID4 to use as `event_id` if no value is provided as an argument.
  - Persistent Pub:
    - Generate the `event_id` explicitly instead of relying on the underlying provider 
      to generate it automatically. That way, we know the value and can store it.
    - Ensure `event_id` is stored and successfully reused during republish.
      - Generate and store `event_id` if it doesn't exist during republish.
    - There is already a one-off variable named `event_id` in `publish_validated()`,
      which we need to rename to avoid confusion. New name should be `compaction_key`
      or similar (should not produce any side effects).
  - DAO Pub (outbox):
    - Here, `event_id` should only be stored, not reused during republish. The stored
      value should reflect the ID of the event created the last time the DTO was 
      published to Kafka, to be used for traceability only.
      - Every time outbox events are republished, they'll have a *new* `event_id`.
      - The outbox events are intended to be stored by consumers, so idempotence
        is not performed via `event_id`. This is why we won't update the daosub
        protocol or try to reuse the previous `event_id` when republishing outbox
        events.

NOS:
- Grab new version of `hexkit`.
- Store the event ID for all non-outbox events the NOS consumes.
- Check for the ID's presence before processing the event.

NS:
- Grab new version of `hexkit`.
- Store the event ID for all Notification events consumed.
- Check for ID's presence before acting on the Notification event.

DLQ Service:
- Grab new version of `hexkit`.
- Update `stored_event_from_raw_event()` to operate with new header structure.
- Migrate stored events in DB by generating new UUIDs.


### Optional:
- Configure retention and cleanup policy for `notifications` topic, set matching 
  duration for a TTL index on the NS's event ID collection.
- Log the `event_id` from inside `KafkaEventPublisher` when publishing an event.


## API Definitions:

### `EventSubscriberProtocol`:

The subscriber protocol gets the new event_id field as shown below. It's up to service
code to decide how to handle the value, if at all.

```python
async def consume(
    self,
    *,
    payload: JsonObject,
    type_: Ascii,
    topic: Ascii,
    key: Ascii,
    event_id: UUID,
) -> None:
...

@abstractmethod
async def _consume_validated(
    self,
    *,
    payload: JsonObject,
    type_: Ascii,
    topic: Ascii,
    key: Ascii,
    event_id: UUID,
) -> None:
...
```


### Event Header Overview:

To summarize, most events' headers will only change by gaining an `event_id` field.

DLQ events will gain a `service` header. This is because `event_id` was already used
by the DLQ process, but carried a concatenation of `topic`, `service`, `partition`, and
`offset`, which served as a unique ID. The `partition` and `offset` were only ever used
in this context, so we'll drop them again in this change. The `service` field still
provides value, however, and will be preserved in its own field.

```json
{
    "headers": {
        // In all cases:
        "correlation_id": ...,
        "type": ..., 
        "event_id": ...,

        // Events published to the DLQ will have additional headers:
        "exc_class": ...,
        "exc_msg": ...,
        "original_topic": ...,
        "service": ...
    }
}
```


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
