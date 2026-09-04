# Consistency between Events and Databases of Services

Date: 2024-03-21

## Summary

In the context of **inter-service communication**

facing **the need for consistency between the database of a service and published events**

we decided for **a solution similar to the outbox pattern**

and neglected **solutions based on the change data capture (CDC) pattern**

to achieve **a simple backup solution focusing on the databases**

accepting that **event consumers must allow consuming the same event multiple times**.

## Details

### Status

**proposed**

### Context & Requirements

In a microservice architecture coupling between services should be avoided as much as
possible. However, as soon as services collaborate to realize a user journey, their
states become dependent on each other. A mechanism must be in place to ensure
consistency between the services' states.

To achieve that, we rely on publishing
state changes occurring in one service as events that are consumed by other services.
The state of a microservice is usually managed in MongoDB database. For event exchange,
we use Apache Kafka.

To ensure consistency between service states via events, it must first be guaranteed
that the events in Apache Kafka are consistent with the state stored in MongoDB.

### Decision

We realize consistency between published events and the database by making it possible
to create events from the state of the database.

The following assumptions are made:
- each MongoDB collection contains data on one resource type (it might have other
  resource types embedded)
- each document in a collection focuses on one instance of the resource type
- each Kafka topic contains events informing about the change (creation or update) or the
  deletion of resources of one resource type
- each event in a topic focuses on one instance of the resource type
- events are cumulative so that they carry the entire state of the resource they are
  focusing on
- events are published at least once but can be published multiple times

To achieve the construction of events from the state stored in the database, a function
has to be defined for each collection that transforms a document contained in the
collection into the payload for an event to be published. This transformation can be
used to hide internal details of the service state from the service API.

In addition to the actual resource content, each document in MongoDB contains
metadata on whether:
- the current version of the resource content has already been
published
- the resource has been deleted

We have implemented a triple hexagonal protocol for a factory to generate DAOs that automatically take
care of the publication of state changes
(https://github.com/ghga-de/hexkit/blob/6a86fdd31daa8faeb4f0434b82758992e778995d/src/hexkit/protocols/dao_outbox.py#L53)
and an associated provider based on MongoDB and Apache Kafka
(https://github.com/ghga-de/hexkit/blob/6a86fdd31daa8faeb4f0434b82758992e778995d/src/hexkit/providers/mongokafka/provider.py#L363).

In brief, the workflow for creating or changing a resource is the following:
1. A DAO is used to alter the state (including creation and deletion) of a resource in the database.
2. The update to the resource will be persisted to the database, thereby the metadata
   in the corresponding document will indicate that the document has not been published,
   yet.
3. The DAO will attempt to immediately publish the updated resource to Apache Kafka
   (using the transformation function mapping the document to an event representation).
4. If the publishing succeeds, the metadata in the database document is updated
   accordingly and the DAO method returns to the client. Otherwise, an exception is
   raised.
5. The DAO also provides a method that searches for all unpublished documents, publishes
   them and updates their metadata accordingly. If this method is run periodically, it
   can recover from inconsistencies introduced by failures occurring in step 4.

For the deletion of a resource, the process is identical. It should be pointed out that
the deletion does not result in the deletion of the corresponding document in the
database. Instead, the document is emptied and its metadata is changed to indicate that
the resource has been deleted. All DAO methods that are retrieving data from the
database will ignore these documents. However, they are kept available to construct
deletion events.

In the published events, the event key is identical to the ID of the resource the event
is focusing on. The event type is used to distinguish change (create or update) events
from deletion events. The payloads of deletion events are empty.

The DAO also provides a method for republishing all documents independent of whether
their current state has already been published or not. This can be used to repopulate
the Apache Kafka topic in case it gets lost. Since events are cumulative, topics
can be compacted, which supports our data minimization and erasure requirements and
reduces the storage requirements of Apache Kafka.

This pattern is similar to the outbox pattern. However, the outbox pattern uses a
dedicated data structure (a table or collection) to store event representations
separately from the data structures storing the primary database state. With the
assumptions we made, a single data structure can be used for both the events and the
primary state.

### Consequences

The proposed implementation provides a simple mechanism for ensuring consistency between
the published events and the state in the database and, thereby, it also guarantees
consistency between the state of services. It requires only little changes to the
DAO and event handling interface of services. Moreover, since the state of Apache Kafka
can be reconstructed from the database, it is only necessary to backup the database.
A disadvantage is that all consumers must be idempotent, i.e. prepared to receive
the same event multiple times. Moreover, in addition to the main service process(es),
a cron job must be periodically executed to publish changes that failed to publish
initially. This adds additional deployment complexity.

### Alternatives

We have evaluated the following alternatives:

It would be possible to use the original outbox pattern. However, the database setup
would be more complex since separate data structures are required for storing the
primary state and the event representations. This would also require cross-document
transactions to be implemented into our DAO providers and enabled in MongoDB.

Another alternative would be to use CDC. However, the produced events would mirror
the documents in the database and thus leak internal details on the service state.

To fix the mentioned issue, CDC could be extended with an additional process that
consumes the CDC-produced events and transforms them into a public representation. This
would functionally be equivalent to the proposed solution. However, we would have to
rely on an additional infrastructure tool, e.g. Kafka Connect. This adds overhead to
the deployment and operation.

In general, it is desirable to work around the issue of event and database consistency
by making services entirely stateless, i.e. not requiring a database, but only consuming
and producing events. While this is not applicable to all services, it is complementary
to the proposed solution and should be evaluated per service.

### Addendum

This approach has since been implemented in `hexkit`. The `MongoKafkaDaoPublisher`
provider keeps the publication state in a `__metadata__` field of the same document that
holds the resource, and provides a `publish_pending()` method for publishing documents
whose events have not been published yet, as well as a `republish()` method for
repopulating a topic.
