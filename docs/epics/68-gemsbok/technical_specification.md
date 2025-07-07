# Persistent Kafka Publisher (Gemsbok)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope
### Outline:
Implement a special event publisher that incorporates a DAO to automatically
store *stateless* events in the database. The functionality will be similar to
that of the `MongoKafkaDaoPublisher`, but where the `MongoKafkaDaoPublisher` is
a DAO that happens to publish events, the `PersistentKafkaPublisher` will be an event
publisher that happens to use a DAO to store events in the database.

We can publish most (or all) *stateless* events using this new class. The
gained benefit is the ability to re-publish *stateless* events in the
same way as *stateful* (outbox) events while maintaining a clear distinction
between the two categories both conceptually and in code.

The new class will be called `PersistentKafkaPublisher` and reside within the
`mongokafka` subpackage.

### Included/Required:
- New `PersistentKafkaPublisher` in `hexkit`
- Add event types to stateless config classes in `ghga-event-schema` that lack one
- Rollout to services that use the outbox functionality for non-outbox events

### Optional:
- Incorporate stored event deletion and expose via CLI commands
  - What are the criteria used? Timestamp? Is it configurable or supplied via CLI?
  - Should we mirror log compaction in our database or not, and if so, how?


## API Definitions:
The `PersistentKafkaPublisher` will subclass `EventPublisherProtocol` just like the
`KafkaEventPublisher`, so it will expose the same `publish` function. In addition,
it will feature both a `publish_pending` and `republish` function. Those
are the same functions featured in the `DaoPublisherProtocol`, but the difference
is that these functions are added to the event publishing provider, not the
DAO provider.

```python
class PersistentKafkaPublisher(EventPublisherProtocol):
    async def _publish_validated(self, *, **our_publishing_kwargs) -> None:
      ...

    async def publish_pending(self) -> None:
      ...

    async def republish(self) -> None:
      ...
```


## Additional Implementation Details:

### Background - Different Event Categories
We currently publish two categories of events ("categories" is used to avoid confusion 
with the event `type`):

1. "Normal"/"non-outbox"-category Events
   - E.g. file staging requests, file upload validation success, notifications, etc.
   - These events communicate, for example, that something happened or must be done
   - They are inherently concerned with *action* and are therefore *stateless*.
   - These events are not currently stored in the database and there is no easy way
     to retrigger them if Kafka data is lost.
   - This event category predates the outbox category is considered our default
2. "Outbox"-category Events
   - E.g. user info published by the `UMS`.
   - These events share the latest state of domain object info with the goal of
     helping other services maintain their own copy of the shared information.
   - They are inherently *stateful* and do not suggest any action *per se*.
   - These events, or rather data they contain, are stored in a database where every
     change results in publishing "outbox" events that convey the new latest state.
   - These events can be easily re-published.
   - The event `type` is either `upserted` or `deleted`, and the `DaoSubscriberProtocol`
     defined in `hexkit` requires matching `changed()` and `deleted()`
     methods to be defined on the service's translator implementation.
   - Only one kind of outbox event can be published to an outbox topic. E.g., you
     can't publish `foo` and `bar` outbox events to the same topic, because they
     will use the same event `type`. Hence, consumers can't distinguish between the two.

These should instead be called *stateless* and *stateful*, respectively.
We've recently come to understand that we also need to be able to
re-publish *stateless* events, which means we need to save them in the database.


### Why Not Recycle MongoKafkaDaoPublisher
A question, perhaps obvious, is *"Why not just use the `MongoKafkaDaoPublisher`?*
*Surely it can be adapted out of the box!"*  
While it is *technically* possible, it would require defining a DAO publisher factory
that supplies `publish_change` and `publish_delete` args to the `MongoKafkaDaoPublisher`
that don't really do what they say. If we want to periodically delete old events
from the database, the `MongoKafkaDaoPublisher` only updates a field called
`__metadata__.deleted` to `True` instead of actually removing them from the database.
The functionality we need from `MongoKafkaDaoPublisher` is straightforward to implement,
so it's cleaner to write everything in a dedicated module that uses a
regular `MongoDbDao`.

The `MongoKafkaDaoPublisher` also takes a `dto_to_event` parameter that allows us
to transform the data from the database into a format that matches a public schema.
The persistent publisher doesn't need custom transformation functions because it
saves the events as is. Any ancillary information saved along with the event
will be managed entirely by `hexkit` and be applied uniformly across services.

What we can do with the `PersistentKafkaPublisher` is track whether or not the event has
been successfully published, which *is* something the `MongoKafkaDaoPublisher` does.
To do this, we insert the event info into the database when `publish()` is
called, then publish the event to Kafka, and finally update the database document
to set the `published` flag to True.

### Event in the Database
The `PersistentKafkaPublisher` class will have a `construct` method that takes a 
`collection_name` parameter to determine where to put the events. The
default value will append the string `PersistedEvents` to the
configured `service_name`, e.g. `dcsPersistedEvents` in the case of the DCS.

The events will be stored in the database with the following schema:

```
id_ (UUID) - ID generated at publish time to serve as a PK in the database
topic (str)
type_ (str)
payload (dict[str, Any])
key (str)
headers (dict[str, str])
correlation_id (UUID) 
created (datetime) - Timestamp of first publish (not updated on republish), used for 
                     ordering events during republish.
published (bool) - Tracks publish status
```

### Prioritized Rollout
The first places to use the `PersistentKafkaPublisher` are the places where the
outbox pattern is used with *stateless* events in order to keep a persistent
copy of those events. This includes:
- UCS: "File Upload Received"
- IRS: "File Upload Validation Success"
- FIS: "File Upload Validation Success"
- DCS: "Non-staged Download Requested"
- PCS: "File Deletion Requested"

Since the services have used the outbox pattern to persist events in the database,
the events will be stored in collections already. However, these collections will
have different names and different content structure than what will be produced
by the `PersistentKafkaPublisher`. Options to resolve:
1. Forget the old events and drop the old collection
2. Copy the prototype framework from IFRS or DCS and write a migration script for it
3. Same as #2, but wait for the migration framework to be in `hexkit`

Finally, the consumers of these currently-outbox events are listening for
the event type `upserted`, which is not configurable. As a result, we
must deploy all the changes at once or configure the event type as `upserted`
for the listed events until the consumers are updated as well. It's probably easiest to
deploy all at once, especially considering that the 3 sprint window should suffice
to execute all upgrades alongside existing tasks.

### Republish/Publish Pending CLI command
The services above already expose a CLI command that enables republishing events
from the database which were stored there via the outbox pattern. These entrypoints
will be updated to use the `PersistentKafkaPublisher` instead.


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
