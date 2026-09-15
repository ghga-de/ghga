# Kafka Dead Letter Queues (DLQ)

Date: 2024-07-10

## Summary

In the context of **inter-service communication**

facing **the need to triage and reprocess events that result in error when consumed**

we decided for **a self-built DLQ mechanism using the database and a dedicated service**

and neglected **the use of Kafka Connect or multiple dedicated Kafka topics**

to achieve **a lightweight, custom solution requiring no additional products**

accepting that **that we will forgo any of the more robust features offered by Kafka Connect**.

## Details

### Status

**Accepted**

### Context & Requirements

Before the change described here, an event that resulted in an unhandled exception when
consumed would stop the consumer without committing the consumer offsets, so that the
same event was consumed again after a restart. Without a dedicated mechanism, the only
quick remedy was to commit the offsets regardless of the outcome, i.e. to skip events.

We need a way to handle failed events more elegantly, especially since they can be caused
by a number of things: timeouts and connection errors, malformed payloads, database
corruption, application bugs, etc.

We need a mechanism that enables us to set a failed event aside, investigate the cause,
and ultimately dispose of it or try to consume it again.

### Decision

We propose to implement a custom solution that takes advantage of the tools already
available in `hexkit` and adapt them to provide the required functionality:
1. Move a failing event to a new topic (the dead letter queue).
2. Deal with the events from the dead letter queue by discarding them or republishing
them via a new service (DLQ Service).

We will publish failed events to a single DLQ topic, after which point they will be
stored in a database. Following a resolution process, we will publish the events
to a topic in a way that allows for them to be seamlessly reintroduced to the
original service _or_ we will delete the event from the database without republishing it.

### Consequences

The primary benefit to this solution is its simplicity. We are not required to learn,
configure, or be beholden to any new products, so the additional strain on DevOps is
minimized. Choosing not to apply the outbox pattern or rely on Kafka topics as the source
of truth for the dead letter queue means that there are fewer moving parts; complexity
of implementation is therefore also minimized.

On the other hand, we might miss out on some of the more robust features offered by
pre-existing products. Implementing a dead letter queue is not a new problem, so many of
the common pitfalls have probably been solved by such software.

Storing failed events in the database will allow us to more easily implement some
features, such as sending a clear signal to any observation layers that a failed event
has been dealt with, or modifying a payload before reprocessing. There are of course
some minor but manageable concerns, such as how to deal with events in sequence,
storage space, and so on.

Regardless of the approach taken, manual action will still be required to resolve the
underlying problem giving rise to a particular error.

### Alternatives

There are two primary alternatives. One is an existing product, and the other is merely
an alternate version of the custom implementation.

The first alternative is to use a product that handles DLQ logic for us. One such
tool is Kafka Connect. It ships with Kafka and the configuration is compact at the
connector level. However, it would require configuration for each service, and, perhaps
most importantly, would require retooling our services to use the connectors to consume
events instead of the providers that are already implemented in `hexkit`. Even if done,
that makes us more reliant on the maintenance of and limited to the functionality provided
by a 3rd party tool. Finally, it still does not provide any way to fix failed events,
only the DLQ process. Taken together, this option does not seem appropriate, especially
when the requirements are this small.

The other alternative is to rely on Kafka topics directly, which was the proposal of
the previous iteration of this document. In such a solution, failed events would be
published to dedicated Kafka topics -- one topic per service or even one topic per
service _per topic consumed by that service_. This approach presents a couple of
problems though. First, it's not failproof. If Kafka data is lost, there are no backups.
Second, the DLQ Service side of the equation would involve routine manipulation of
consumer offsets and likely multiple consumer instances, which increases the frequency
of rebalances and the like. Overall, it's a finicky solution that sounds okay on its
face but presents too many challenges in practice.

The database-focused approach is simple to implement, intuitive to understand,
and easy to back up.

### Addendum

The implementation in `hexkit` combines the dead letter queue with a preceding retry
stage. A failing event is first retried a configurable number of times
(`kafka_max_retries`), with a backoff between the attempts that is doubled for each retry
(`kafka_retry_backoff`). Only once these retries are exhausted is the event published to
the DLQ topic (`kafka_dlq_topic`). The dead letter queue itself is enabled per service via
`kafka_enable_dlq`; if it is disabled, the service still stops once the retries are
exhausted, as described above.
