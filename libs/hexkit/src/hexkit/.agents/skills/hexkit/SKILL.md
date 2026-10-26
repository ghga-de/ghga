---
name: hexkit
description: Write or change Python service code that uses hexkit, the hexagonal-architecture toolkit - DAOs on MongoDB, Kafka events, the outbox, dead letter queues, migrations, config, dependency injection, and hexkit's test fixtures. Use whenever code imports hexkit.
license: Apache-2.0
---

# hexkit

This skill covers hexkit 10.
It holds the choices and the traps; the [user guide](https://ghga-de.github.io/ghga/hexkit/user-guide/index.md) holds the details and examples.
Every guide page linked here is Markdown, so fetch the one for the task at hand rather than guessing an API.
The [API reference](https://ghga-de.github.io/ghga/hexkit/reference/index.html) has every signature.

## Choose the building block

| Need | Protocol, in `hexkit.protocols` | Provider | Guide |
|---|---|---|---|
| Store resources | `dao.Dao`, `dao.DaoFactoryProtocol` | `MongoDbDaoFactory` | [DAO](https://ghga-de.github.io/ghga/hexkit/user-guide/protocols/dao.md), [MongoDB](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/mongodb.md) |
| Store resources and tell other services their latest state | `daopub.DaoPublisher` | `MongoKafkaDaoPublisherFactory` | [DAO Publisher](https://ghga-de.github.io/ghga/hexkit/user-guide/protocols/daopublisher.md) |
| Keep a copy of another service's resources | `daosub.DaoSubscriberProtocol` | `KafkaOutboxSubscriber` | [DAO Subscriber](https://ghga-de.github.io/ghga/hexkit/user-guide/protocols/daosubscriber.md) |
| Publish events | `eventpub.EventPublisherProtocol` | `KafkaEventPublisher`, or `PersistentKafkaPublisher` to re-emit them | [Publisher](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/kafka/publisher.md), [Publisher Variants](https://ghga-de.github.io/ghga/hexkit/user-guide/developer_help/outbox_v_persistent_pub.md) |
| Consume events | `eventsub.EventSubscriberProtocol` | `KafkaEventSubscriber` | [Subscriber](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/kafka/subscriber.md) |
| Store files | `objstorage.ObjectStorageProtocol` | `S3ObjectStorage` | [Object Storage](https://ghga-de.github.io/ghga/hexkit/user-guide/protocols/objstorage.md), [S3](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/s3.md) |
| Key-value pairs | `kvstore.KeyValueStoreProtocol` | `InMem*`, `Redis*`, `MongoDb*`, `S3*`, `Vault*KeyValueStore` | [Protocols](https://ghga-de.github.io/ghga/hexkit/user-guide/protocols/index.md) |
| Change the shape of stored documents | – | `MigrationDefinition`, `MigrationManager` | [MongoDB Migrations](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/mongodb_migrations.md) |

Each provider family sits behind an extra (`akafka`, `mongodb`, `s3`, `redis`, `vault`); the test fixtures behind `test-akafka`, `test-mongodb`, `test-s3` and so on.
Look at the stored data, not the event, when choosing between the outbox and the persistent publisher: the outbox publishes the latest state of a stored resource, the persistent publisher stores events that are not a resource, such as a command that starts a flow.

## Structure and wiring

- The core depends on ports only: `Protocol`s or abstract classes, received through keyword-only constructor parameters, the config among them.
  No hexkit provider, FastAPI or other infrastructure import belongs in the core ([Triple Hexagonal Architecture](https://ghga-de.github.io/ghga/hexkit/user-guide/arch_concepts/triple_hexagonal_arch.md)).
- Translators sit between: an inbound one receives an event and calls a core port, an outbound one gives the core a domain method such as `publish_user_created()` and calls the provider.
- Wire everything in one composition root, `inject.py`, as async context managers: `prepare_core` yields the core's inbound port, and `prepare_rest_app` and `prepare_event_subscriber` build on it ([Dependency Injection](https://ghga-de.github.io/ghga/hexkit/user-guide/arch_concepts/dependency_injection.md)).
  No dependency injection framework.
- Open every provider that holds a connection with `async with Provider.construct(config=...)`, once per process, and share it within that process; one `MongoDbDaoFactory` serves every DAO.
- Give each inbound prepare function an optional override of the core port, compared with `is not None`, so tests can run the real adapter against a mock core.
- Each entrypoint creates the config, calls `configure_logging` exactly once (a second call duplicates every line), and uses one prepare function.
  Call `configure_opentelemetry` before any app or client is constructed: a FastAPI app created earlier is silently left untraced.

## Configuration

- One config class inherits every hexkit config it needs (`KafkaConfig`, `MongoDbConfig` or `MigrationConfig`, `LoggingConfig`, `OpenTelemetryConfig`) plus the service's own fields ([Configuration](https://ghga-de.github.io/ghga/hexkit/user-guide/configuration.md)).
- Decorate it with `@config_from_yaml(prefix="my_service")` and always pass the prefix: it names `.my_service.yaml` and prefixes every environment variable (`MY_SERVICE_KAFKA_SERVERS`).
  A wrong prefix or casing fails silently, and the setting keeps its default.
- The resulting config is frozen; in tests, build a new instance instead of assigning to a field.
- Declare credentials as `SecretStr` or `Secret[...]`, or they appear in the config dump `configure_logging` writes at startup.
- Keep topic and event-type names in config fields, not literals in code.

## DAOs

- Bind each DAO to a frozen Pydantic DTO that carries its own ID (`UUID4Field()` generates one); change a resource with `model_copy(update=...)` and write it back.
- `insert` fails on an existing ID, `update` and `delete` on a missing one; use `upsert` only where create-or-replace is meant.
- `insert_many` and `upsert_many` write a batch in one call; they are not atomic, and their `BatchOperationError` maps each failed ID to the error that `insert` or `upsert` raises.
- Filter with `filter_=`; the old `mapping=` still works with a `DeprecationWarning` and goes in hexkit 11.
- `find_all` is not awaited: it returns a lazy `FindResult` with `to_list()` and `total_count()`.
  Always pass `sort` with `skip` and `limit`.
- For read-modify-write under concurrent writers, pass `precondition=` to `update` and wrap the read and the update in `race_condition_retries` from `hexkit.protocols.dao`, which retries on `PreconditionFailedError`; do not write a retry loop of your own.
- MongoDB keeps milliseconds: create timestamps with `hexkit.utils.now_utc_ms_prec()`, timezone-aware, or a value read back no longer equals the one written.
- MongoDB query operators (`{"$gt": 3}`) tie the caller to MongoDB; keep them in the outbound adapter.
- Declare indexes with `MongoDbIndex` in `get_dao(indexes=...)`, using model field names, never `_id`.
- Catch the `DaoError` subclasses (`ResourceNotFoundError`, ...) in the adapter and raise the core's own errors.
  `with_transaction()` is not implemented by any provider yet.

## Events

- Topic, type and key are ASCII; make the key the ID of the affected resource, since order holds per key.
- `publish()` returns once the broker has the event; a `KafkaEventPublisher` keeps no record of it, so use a persistent or outbox publisher where events must be re-emittable.
- A subscriber translator sets `topics_of_interest` and `types_of_interest` and implements `_consume_validated()`: validate the payload with a Pydantic model and raise `self.MalformedPayloadError` when it does not fit.
- Delivery is at least once, so every translator is idempotent.
- Let an exception propagate from the translator: it triggers the retries (`kafka_max_retries`, `kafka_retry_backoff`) and then the dead letter queue (`kafka_enable_dlq`), which needs a `dlq_publisher` passed to `construct()` ([Dead Letter Queue](https://ghga-de.github.io/ghga/hexkit/user-guide/arch_concepts/dlq.md)).
  A caught and logged exception commits the offset, and the event is lost.
- One subscriber takes one translator; combine several, outbox translators included, with `ComboTranslator`.
- `service_name` is the consumer group, so all instances of a service share the events.
- Correlation IDs travel with events and logs on their own; set one only where work starts without a request or event, such as a job, with `set_new_correlation_id()` ([Correlation IDs](https://ghga-de.github.io/ghga/hexkit/user-guide/observability_tools/correlation_ids.md)).

## The outbox

- A `DaoPublisher` is used like a DAO; each write publishes the resource's latest state as an `upserted` event, each delete a `deleted` event with an empty payload, keyed by the ID.
- `dto_to_event` decides what leaves the service: drop internal fields there, or return `None` to publish nothing for that change.
  Use one topic per resource type.
- A deleted resource keeps a stub with a `__metadata__` field in the collection; read and write it only through the DAO.
- Read and write a collection only through Outbox DAOs with the same model, topic and `dto_to_event`, never also through a plain DAO or directly: such access publishes nothing and breaks the outbox metadata.
  A consumer's copy in its own database is a different collection and may use any DAO ([One DAO per collection](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/mongokafka.md#one-dao-per-collection)).
- Offer `publish_pending()` and `republish()` as a command, such as `publish-events`, run as a job: it publishes what failed to publish, and fills a new consumer.
- On the consuming side, implement `changed()` as an upsert and let `deleted()` accept a resource that is already gone.

## Migrations

- Version 1 is reserved for the framework, so the first migration a service writes is version 2.
- Inherit the service config from `MigrationConfig`, map each version to its `MigrationDefinition` in a migration map, and run `MigrationManager(...).migrate_or_wait()` before the service starts work; a separate command, such as an init container, keeps migration failures apart.
- When the migration runs separately, the service checks with `check_db_version()` at startup and refuses a database that is behind or ahead.
- Implement `unapply()` (the `Reversible` mixin) unless the migration drops data that it cannot restore.

## Tests

- Test the core without infrastructure: a mock DAO class from `new_mock_dao_class(dto_model=..., id_field=...)`, which understands a subset of MongoDB's operators, `InMemEventPublisher` (its `event_store.get(topic)` raises `TopicExhaustedError` when nothing was published) and the `InMem*KeyValueStore` classes.
- Test a translator by calling its `consume()` directly; test a REST route through the prepare function's override with an `AsyncMock` core.
- Test adapters against real backends with the testcontainers fixtures, which need Docker.
  Import the session-scoped container fixture and the function-scoped fixture together, each with `# noqa: F401`, for example `mongodb_container_fixture` and `mongodb_fixture` from `hexkit.providers.mongodb.testutils`, then take `mongodb: MongoDbFixture` (its `dao_factory`), `kafka: KafkaFixture` or `s3: S3Fixture` as a test argument.
  The `get_*_fixture()` functions build the same fixtures with another scope or name.
- With `KafkaFixture`, feed events in with `publish_event()` and check what the code publishes with `expect_events()` (exact count and order) or `record_events()`; `run(forever=False)` consumes one event and waits until one arrives, so publish first ([Kafka Test Utils](https://ghga-de.github.io/ghga/hexkit/user-guide/providers/kafka/test_utils.md)).
- The clean fixtures empty their backend before every test; the `persistent_*` variants keep state across tests.
