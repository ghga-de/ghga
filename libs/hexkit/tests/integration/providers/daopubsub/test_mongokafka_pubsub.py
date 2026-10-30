# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Test the DAO pub/sub functionality based on the mongokafka/kafka providers."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable, Generator, Mapping, Sequence
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from pydantic import UUID4, BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection

from hexkit.correlation import (
    correlation_id_var,
    get_correlation_id,
    new_correlation_id,
    set_new_correlation_id,
)
from hexkit.custom_types import JsonObject
from hexkit.protocols.dao import (
    BatchOperationError,
    InvalidMappingError,
    PreconditionFailedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    UniqueConstraintViolationError,
    UUID4Field,
)
from hexkit.protocols.daopub import DaoPublisher
from hexkit.protocols.daosub import DaoSubscriberProtocol, DtoValidationError
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from hexkit.providers.akafka import (
    ComboTranslator,
    KafkaEventSubscriber,
    KafkaOutboxSubscriber,
)
from hexkit.providers.akafka.testutils import (
    ExpectedEvent,
    KafkaFixture,  # noqa: F401
    RecordedEvent,
    kafka_container_fixture,  # noqa: F401
    kafka_fixture,  # noqa: F401
)
from hexkit.providers.mongodb.provider import ConfiguredMongoClient, dto_to_document
from hexkit.providers.mongodb.provider.dao import MongoDbDao, MongoDbIndex
from hexkit.providers.mongodb.testutils import (
    mongodb_container_fixture,  # noqa: F401
    mongodb_fixture,  # noqa: F401
)
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory
from hexkit.providers.mongokafka.provider import (
    CHANGE_EVENT_TYPE,
    DELETE_EVENT_TYPE,
    document_to_dto,
)
from hexkit.providers.mongokafka.provider.daopub import (
    MAX_REPUBLISH_ROUNDS,
    mark_published,
)
from hexkit.providers.mongokafka.testutils import (
    MongoKafkaFixture,
    mongo_kafka_fixture,  # noqa: F401
)

from ..dao.test_mongodb_dao import (
    ComplexDto,
    ExampleDto,
    ExampleDtoWithIntID,
    ExampleDtoWithStrID,
)

pytestmark = pytest.mark.asyncio()

EXAMPLE_TOPIC = "example"


@pytest.fixture(autouse=True)
def correlation_id_fixture() -> Generator[UUID4, None, None]:
    """Provides a new correlation ID for each test case."""
    # Note: Using an async fixture doesn't work reliably with older Python versions,
    # because the context is not preserved even with pytest-asyncio 0.25.
    correlation_id = new_correlation_id()
    token = correlation_id_var.set(correlation_id)
    yield correlation_id
    correlation_id_var.reset(token)


def get_mongo_collection(mongo_kafka: MongoKafkaFixture, name: str) -> Collection:
    """Get the MongoDB collection with the provided name."""
    db_name = mongo_kafka.config.db_name
    return mongo_kafka.mongodb.client.get_database(db_name).get_collection(name)


class DummyOutboxSubscriber(DaoSubscriberProtocol[ExampleDto]):
    """A dummy implementation of the `DaoSubscriberProtocol` for the `ExampleDto`."""

    event_topic = EXAMPLE_TOPIC
    dto_model = ExampleDto

    def __init__(self):
        """Initialize with a `received` attribute for inspecting events consumed.
        It is a list of tuples, each containing the resource ID and, in case of a
        change event, the dto.
        """
        self.received: list[tuple[str, UUID4, ExampleDto | None]] = []

    async def changed(self, resource_id: str, update: ExampleDto) -> None:
        """Consume change event (created or updated) for the given resource."""
        correlation_id = get_correlation_id()
        self.received.append((resource_id, correlation_id, update))

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of the given resource."""
        correlation_id = get_correlation_id()
        self.received.append((resource_id, correlation_id, None))


async def test_dao_outbox_with_non_existing_resource(mongo_kafka: MongoKafkaFixture):
    """Test operations on non-existing resources fail with MongoKafkaOutboxFactory."""
    kafka = mongo_kafka.kafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        example = ExampleDto()

        # first try with non-existing resource
        async with kafka.expect_events(events=[], in_topic=EXAMPLE_TOPIC):
            with pytest.raises(ResourceNotFoundError):
                await dao.get_by_id(example.id)
            with pytest.raises(ResourceNotFoundError):
                await dao.update(example)
            with pytest.raises(ResourceNotFoundError):
                await dao.delete(example.id)

        # create and delete the resource and try again with that state
        await dao.insert(example)
        await dao.delete(example.id)

        async with kafka.expect_events(events=[], in_topic=EXAMPLE_TOPIC):
            with pytest.raises(ResourceNotFoundError):
                await dao.get_by_id(example.id)
            with pytest.raises(ResourceNotFoundError):
                await dao.update(example)
            with pytest.raises(ResourceNotFoundError):
                await dao.delete(example.id)


@pytest.mark.parametrize(
    "dto_model", [ExampleDto, ExampleDtoWithIntID, ExampleDtoWithStrID]
)
async def test_dao_outbox_happy(dto_model: type, mongo_kafka: MongoKafkaFixture):
    """Test the happy path of using the MongoKafkaOutboxFactory.

    This tests UUID4 based as well as custom int and string based ID generators.
    """
    kafka = mongo_kafka.kafka
    assert issubclass(dto_model, ExampleDto)
    id_field = "id" if dto_model is ExampleDto else "custom_id"
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=dto_model,
            id_field=id_field,
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # insert an example resource:
        example = dto_model()
        assert hasattr(example, "custom_id") == (dto_model is not ExampleDto)
        example_id = getattr(example, id_field)

        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example_id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.insert(example)

            # check error on duplicate
            with pytest.raises(
                ResourceAlreadyExistsError,
                match=f'The resource with the id "{example_id}" already exists.',
            ):
                await dao.insert(example)

        # read the newly inserted resource:
        resource_read = await dao.get_by_id(example_id)
        assert resource_read == example

        # update the resource:
        example_update = example.model_copy(update={"field_c": False})
        assert example_update != example
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example_update.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example_id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.update(example_update)

        # read the updated resource again:
        resource_updated = await dao.get_by_id(example_id)
        assert resource_updated == example_update

        # upsert the original state of the resource:
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example_id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.upsert(example)

        # read the upserted resource:
        resource_read = await dao.get_by_id(example_id)
        assert resource_read == example

        # insert additional resources:
        example2 = dto_model(field_a="test2", field_b=27)
        example3 = dto_model(field_a="test3", field_c=True)
        example4 = dto_model(field_a="test4", field_c=False)
        for add_example in (example2, example3, example4):
            async with kafka.expect_events(
                events=[
                    ExpectedEvent(
                        payload=add_example.model_dump(),
                        type_=CHANGE_EVENT_TYPE,
                        key=str(getattr(add_example, id_field)),
                    )
                ],
                in_topic=EXAMPLE_TOPIC,
            ):
                await dao.insert(add_example)

        # perform a search for multiple resources:
        obtained_hits = {
            hit async for hit in dao.find_all(filter_={"field_b": 42, "field_c": True})
        }
        assert obtained_hits == {example, example3}

        # perform a search using values with non-standard data types
        # (note that in this case we need to serialize these values manually):
        filter_ = {id_field: example_id, "field_d": example.field_d}
        obtained_hit = await dao.find_one(filter_=filter_)
        assert obtained_hit == example
        obtained_hits = {hit async for hit in dao.find_all(filter_=filter_)}
        assert obtained_hits == {example}

        # make sure that 4 resources with different IDs were inserted:
        obtained_ids = {
            getattr(hit, id_field) async for hit in dao.find_all(filter_={})
        }
        assert len(obtained_ids) == 4
        assert example_id in obtained_ids
        for obtained_id in obtained_ids:
            if dto_model is ExampleDtoWithIntID:
                assert isinstance(obtained_id, int)
            elif dto_model is ExampleDtoWithStrID:
                assert isinstance(obtained_id, str) and obtained_id.startswith("id-")
            else:
                assert isinstance(obtained_id, uuid.UUID)

        # find a single resource:
        obtained_hit = await dao.find_one(filter_={"field_a": "test"})

        assert obtained_hit == example

        # delete the resource:
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload={},
                    type_=DELETE_EVENT_TYPE,
                    key=str(example_id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.delete(example_id)

        # confirm that the resource was deleted:
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(example_id)

        # make sure that only 3 resources are left:
        obtained_hits = {hit async for hit in dao.find_all(filter_={})}
        assert len(obtained_hits) == 3


async def test_complex_models(mongo_kafka: MongoKafkaFixture):
    """Tests whether complex pydantic models are correctly saved and retrieved."""
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=mongo_kafka.config) as factory,
        mongo_kafka.kafka.record_events(
            in_topic=EXAMPLE_TOPIC, capture_headers=True
        ) as recorder,
    ):
        dao = await factory.get_dao(
            name="complex",
            dto_model=ComplexDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
            autopublish=True,
        )

        # stage 1: insert
        resources_created: list[ComplexDto] = []
        for i in range(3):
            nested = ExampleDto(field_a=f"inserted-{i}")
            resource = ComplexDto(
                sub=nested,
                sub_tuple=("test-tuple", nested),
                sub_list=["test-list", nested],
                sub_dict={"test-dict": nested},
            )
            await dao.insert(resource)
            resources_created.append(resource)

        # stage 2: update
        resources: list[ComplexDto] = []
        for i in range(3):
            resource_created = resources_created[i]
            nested = ExampleDto(field_a=f"updated-{i}", field_e=Path(f"/path-{i}"))
            assert nested != resource_created.sub
            resource = ComplexDto(
                id=resource_created.id,
                sub=nested,
                sub_tuple=("test-tuple", nested),
                sub_list=["test-list", nested],
                sub_dict={"test-dict": nested},
            )
            await dao.update(resource)
            resources.append(resource)

        # stage 3: query
        for i in range(3):
            resource = resources[i]

            # fetch one newly inserted resource by its ID:
            resource_read = await dao.get_by_id(resource.id)
            assert resource_read == resource

            # fetch the resource by filtering via complex mappings:
            nested = resource.sub
            mapping_sub = {
                "id": nested.id,
                "field_a": nested.field_a,
                "field_b": nested.field_b,
                "field_c": nested.field_c,
                "field_d": nested.field_d,
                "field_e": str(nested.field_e),
            }
            mappings: list[dict[str, Any]] = [
                {"id": resource.id},
                {"sub": mapping_sub},
                {"sub_tuple": ("test-tuple", mapping_sub)},
                {"sub_list": ["test-list", mapping_sub]},
                {
                    "id": resource.id,
                    "sub": mapping_sub,
                    "sub_tuple": ("test-tuple", mapping_sub),
                    "sub_list": ["test-list", mapping_sub],
                },
            ]

            for filter_ in mappings:
                obtained_hit = await dao.find_one(filter_=filter_)
                assert obtained_hit == resource
                obtained_hits = await dao.find_all(filter_=filter_).to_list()
                assert obtained_hits == [resource]

        # stage 4: delete
        for i in range(3):
            await dao.delete(resources[i].id)
            obtained_hits = await dao.find_all(filter_={}).to_list()
            assert len(obtained_hits) == 2 - i

    # check that the expected events have been created
    events: list[RecordedEvent] = list(recorder.recorded_events)
    for stage in 1, 2, 4:
        # expected events for this stage
        for i in range(3):
            resource = (resources_created if stage == 1 else resources)[i]
            event = events.pop(0)
            assert event.type_ == DELETE_EVENT_TYPE if stage == 4 else CHANGE_EVENT_TYPE
            assert event.key == str(resource.id)
            if stage == 4:
                # empty payload for deletion events
                expected_payload = {}
            else:
                # construct expected payload for change events
                sub_payload = {
                    "id": str(resource.sub.id),
                    "field_a": f"{'inserted' if stage == 1 else 'updated'}-{i}",
                    "field_b": 42,
                    "field_c": True,
                    "field_d": resource.sub.field_d.isoformat(),
                    "field_e": str(resource.sub.field_e)
                    if stage == 1
                    else f"/path-{i}",
                }
                expected_payload = {
                    "id": str(resource.id),
                    "sub": sub_payload,
                    "sub_tuple": ["test-tuple", sub_payload],
                    "sub_list": ["test-list", sub_payload],
                    "sub_dict": {"test-dict": sub_payload},
                }
            assert event.payload == expected_payload, f"stage {stage} resource {i}"
    assert not events  # no further events should have been recorded


async def test_delay_publishing(mongo_kafka: MongoKafkaFixture):
    """Test delaying publishing of events."""
    kafka = mongo_kafka.kafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
            autopublish=False,
        )

        # insert an example resource:
        example = ExampleDto()

        async with kafka.record_events(in_topic=EXAMPLE_TOPIC) as recorder:
            await dao.insert(example)

        assert len(recorder.recorded_events) == 0

        # publish:
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example.id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.publish_pending()


async def test_suppress_publishing(mongo_kafka: MongoKafkaFixture):
    """Test suppress publishing of events."""
    kafka = mongo_kafka.kafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump() if dto.field_c else None,
            event_topic=EXAMPLE_TOPIC,
            autopublish=True,
        )

        # insert some example resources:
        examples = [
            ExampleDto(field_a="test1"),
            ExampleDto(field_a="test2", field_c=False),
            ExampleDto(field_a="test3"),
        ]

        async with kafka.record_events(in_topic=EXAMPLE_TOPIC) as recorder:
            for example in examples:
                await dao.insert(example)

        # check that all resources were saved:
        records = await dao.find_all(filter_={}).to_list()
        assert len(records) == 3
        assert any(record.field_c for record in records)

        # check that the second resource was not published:
        assert len(recorder.recorded_events) == 2
        assert all(event.payload["field_c"] for event in recorder.recorded_events)


async def test_publishing_after_failure(mongo_kafka: MongoKafkaFixture):
    """Test delaying publishing after the initial publishing failed."""
    kafka = mongo_kafka.kafka

    # a dto to event function that fails the first time:
    fail = True

    def dto_to_event(dto: ExampleDto):
        nonlocal fail

        if fail:
            fail = False
            raise RuntimeError()

        return dto.model_dump()

    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=dto_to_event,
            event_topic=EXAMPLE_TOPIC,
        )

        # insert an example resource:
        example = ExampleDto()

        with pytest.raises(RuntimeError):
            await dao.insert(example)

        # publish:
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example.id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.publish_pending()


async def test_republishing(mongo_kafka: MongoKafkaFixture):
    """Test republishing already published events."""
    kafka = mongo_kafka.kafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # insert an example resource:
        example = ExampleDto()
        expected_event = ExpectedEvent(
            payload=example.model_dump(),
            type_=CHANGE_EVENT_TYPE,
            key=str(example.id),
        )

        # initial insert:
        async with kafka.expect_events(events=[expected_event], in_topic=EXAMPLE_TOPIC):
            await dao.insert(example)

        # republish:
        async with kafka.expect_events(events=[expected_event], in_topic=EXAMPLE_TOPIC):
            await dao.republish()


@pytest.mark.parametrize(
    "subscriber_class", [KafkaOutboxSubscriber, KafkaEventSubscriber]
)
async def test_dao_pub_sub_happy(
    mongo_kafka: MongoKafkaFixture, subscriber_class: type[EventSubscriberProtocol]
):
    """Test the happy path of transmitting resource changes or deletions between the
    MongoKafkaOutboxFactory and the KafkaOutboxSubscriber.

    Also verify that the correlation ID is set on the event headers correctly.
    """
    sub_translator = DummyOutboxSubscriber()
    initial_correlation_id = get_correlation_id()

    # publish some changes and deletions:
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # insert an example resource:
        example = ExampleDto()

        async with set_new_correlation_id() as temp_correlation_id:
            await dao.insert(example)
            # update the resource:
            example_update = example.model_copy(update={"field_c": False})
            await dao.update(example_update)

            # delete the resource again:
            await dao.delete(example.id)

        example_id = str(example.id)
        expected_events = [
            (example_id, temp_correlation_id, example),
            (example_id, temp_correlation_id, example_update),
            (example_id, temp_correlation_id, None),
        ]

        # Verify that the context var is reverted to the initial correlation ID after
        # using the temporary one to publish the events
        assert get_correlation_id() == initial_correlation_id

        # consume events:
        construct = partial(
            KafkaOutboxSubscriber.construct, translators=[sub_translator]
        )
        if subscriber_class == KafkaEventSubscriber:
            construct = partial(
                KafkaEventSubscriber.construct,
                translator=ComboTranslator(translators=[sub_translator]),
            )

        async with construct(config=mongo_kafka.config) as subscriber:
            for _ in expected_events:
                await subscriber.run(forever=False)
            assert sub_translator.received == expected_events

            # Clear out the received list
            sub_translator.received.clear()

            # Republish and verify that the initial correlation ID is maintained
            await dao.republish()

            # Consume the republished events and check them again
            await subscriber.run(forever=False)
            assert sub_translator.received == [expected_events[-1]]


async def test_dao_pub_sub_invalid_dto(mongo_kafka: MongoKafkaFixture):
    """Test that using the KafkaOutboxSubscriber to consume an event with an
    unexpected payload raises a `DtoValidationError`.
    """
    sub_translator = DummyOutboxSubscriber()

    class ProducerDto(BaseModel):
        """Producer DTO that differs from the DTO expected by TestOutboxSubscriber"""

        id: UUID4 = UUID4Field()

        field_a: int  # this is a string field in the expected DTO

    # publish some changes and deletions:
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ProducerDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # insert an example resource:
        example = ProducerDto(field_a=42)
        await dao.insert(example)

    # consume events:
    async with KafkaOutboxSubscriber.construct(
        config=mongo_kafka.config,
        translators=[sub_translator],
    ) as subscriber:
        with pytest.raises(DtoValidationError):
            await subscriber.run(forever=False)


async def test_mongokafka_dao_correlation_id_upsert(mongo_kafka: MongoKafkaFixture):
    """Make sure the correlation ID is set on the document metadata in upsertion.

    Insert a new document and verify that the correct correlation ID is there.
    Perform an update with a new correlation ID and verify that the correlation ID is
    updated accordingly.
    """
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        example = ExampleDto()

        await dao.insert(dto=example)

        # Verify that the inserted document contains the correlation ID
        correlation_id = get_correlation_id()
        collection = get_mongo_collection(mongo_kafka, "example")
        inserted = collection.find_one({"__metadata__.correlation_id": correlation_id})
        assert inserted
        inserted_event_id = inserted["__metadata__"].pop("last_event_id", None)
        assert isinstance(inserted["__metadata__"].pop("write_id"), uuid.UUID)
        assert isinstance(inserted_event_id, uuid.UUID)

        # Check the other metadata (now that we've removed the unpredictable event ID)
        assert inserted["__metadata__"] == {
            "correlation_id": correlation_id,
            "deleted": False,
            "published": True,
        }

        # Remove the metadata field and restore the ID field name, check against original
        inserted_as_dto = document_to_dto(inserted, id_field="id", dto_model=ExampleDto)
        assert inserted_as_dto.model_dump() == example.model_dump()

        # Create a new correlation ID to simulate a subsequent request
        async with set_new_correlation_id() as temp_correlation_id:
            assert temp_correlation_id != correlation_id

            # Update, then verify old correlation ID is overwritten by the new one
            updated_example = example.model_copy(update={"field_a": "test2"}, deep=True)
            await dao.update(updated_example)

            updated = collection.find_one(
                {"__metadata__.correlation_id": temp_correlation_id}
            )
            assert updated

            # Make sure the event ID is new since mongokafka shouldn't reuse event IDs
            updated_event_id = updated["__metadata__"].pop("last_event_id", None)
            assert isinstance(updated["__metadata__"].pop("write_id"), uuid.UUID)
            assert isinstance(updated_event_id, uuid.UUID)
            assert updated_event_id != inserted_event_id

            assert updated["__metadata__"] == {
                "correlation_id": temp_correlation_id,
                "deleted": False,
                "published": True,
            }

            # Remove the metadata field and restore the ID field name
            updated_as_dto = document_to_dto(
                updated, id_field="id", dto_model=ExampleDto
            )
            assert updated_as_dto.model_dump() == updated_example.model_dump()

            # Verify nothing exists in the collection with the old correlation ID
            assert not collection.find_one(
                {"__metadata__.correlation_id": correlation_id}
            )


async def test_mongokafka_dao_correlation_id_delete(mongo_kafka: MongoKafkaFixture):
    """Make sure the correlation ID is set on the document metadata in deletion."""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        example = ExampleDto()

        # Insert, then verify that the inserted document contains the correlation ID
        await dao.insert(dto=example)
        collection = get_mongo_collection(mongo_kafka, "example")
        correlation_id = get_correlation_id()
        inserted = collection.find_one({"__metadata__.correlation_id": correlation_id})
        assert inserted

        metadata = inserted.pop("__metadata__")
        assert inserted == {
            "_id": example.id,
            "field_a": "test",
            "field_b": 42,
            "field_c": True,
            "field_d": example.field_d,
            "field_e": str(example.field_e),
        }
        inserted_event_id = metadata.pop("last_event_id", None)
        assert isinstance(metadata.pop("write_id"), uuid.UUID)
        assert metadata == {
            "correlation_id": correlation_id,
            "deleted": False,
            "published": True,
        }

        # Create a new correlation ID to simulate a subsequent request
        async with set_new_correlation_id() as temp_correlation_id:
            assert temp_correlation_id != correlation_id

            await dao.delete(example.id)
            deleted = collection.find_one(
                {"__metadata__.correlation_id": temp_correlation_id}
            )
            assert deleted
            metadata = deleted.pop("__metadata__")
            assert deleted == {"_id": example.id}
            deleted_event_id = metadata.pop("last_event_id", None)
            assert isinstance(metadata.pop("write_id"), uuid.UUID)
            assert isinstance(deleted_event_id, uuid.UUID)
            assert deleted_event_id != inserted_event_id
            assert metadata == {
                "correlation_id": temp_correlation_id,
                "deleted": True,
                "published": True,
            }

            search_for_inserted_again = collection.find_one(
                {"__metadata__.correlation_id": correlation_id}
            )
            assert not search_for_inserted_again


async def test_documents_without_metadata(mongo_kafka: MongoKafkaFixture):
    """Test that when an Outbox Dao updates or deletes documents with no metadata, the
    metadata is added and the documents published.

    The pre-patch behavior would result in an ResourceNotFoundError.
    """
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    example = ExampleDto(id=id1)
    doc1 = dto_to_document(example, id_field="id")
    doc2 = dto_to_document(ExampleDto(id=id2), id_field="id")

    # Insert two documents without metadata
    db_name = mongo_kafka.config.db_name
    mongo_client: MongoClient = mongo_kafka.mongodb.client
    mongo_client[db_name]["example"].insert_one(doc1)
    mongo_client[db_name]["example"].insert_one(doc2)

    # Attempt to interact with the document via MongoKafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        async with mongo_kafka.kafka.record_events(in_topic=EXAMPLE_TOPIC) as recorder:
            # Attempt to update the document
            await dao.update(example)

        assert len(recorder.recorded_events) == 1
        assert recorder.recorded_events[0].type_ == CHANGE_EVENT_TYPE

        # Verify that the document now has metadata
        correlation_id = get_correlation_id()
        document = mongo_client[db_name]["example"].find_one({"_id": doc1["_id"]})
        assert document is not None and "__metadata__" in document
        event_id = document["__metadata__"].pop("last_event_id", None)
        assert isinstance(document["__metadata__"].pop("write_id"), uuid.UUID)
        assert isinstance(event_id, uuid.UUID)

        # Check the other metadata (now that we've removed the unpredictable event ID)
        assert document["__metadata__"] == {
            "correlation_id": correlation_id,
            "deleted": False,
            "published": True,
        }

        async with mongo_kafka.kafka.record_events(in_topic=EXAMPLE_TOPIC) as recorder:
            await dao.delete(id2)
        assert len(recorder.recorded_events) == 1
        assert recorder.recorded_events[0].type_ == DELETE_EVENT_TYPE

        deleted_doc = mongo_client[db_name]["example"].find_one({"_id": doc2["_id"]})
        assert deleted_doc is not None and "__metadata__" in deleted_doc
        deletion_event_id = deleted_doc["__metadata__"].pop("last_event_id", None)
        assert isinstance(deleted_doc["__metadata__"].pop("write_id"), uuid.UUID)
        assert isinstance(event_id, uuid.UUID)
        assert deletion_event_id != event_id
        assert deleted_doc["__metadata__"] == {
            "correlation_id": correlation_id,
            "deleted": True,
            "published": True,
        }


async def test_find_returns_documents_without_metadata(mongo_kafka: MongoKafkaFixture):
    """Regression test for a publisher DAO dropping metadata-less documents from finds.

    A document written without outbox `__metadata__` (e.g. by a plain MongoDbDao, an
    external writer, or seeded directly) must still be returned by `find_all` and
    `find_one`. The 8.3.0 query filter `{"__metadata__.deleted": False}` matched only
    documents whose metadata was literally not-deleted, silently hiding metadata-less
    documents that 8.1.0 returned. This also re-aligns `find_all` with `update` and
    `delete`, which already tolerate metadata-less documents.
    """
    live_id = uuid.uuid4()
    deleted_id = uuid.uuid4()
    live_example = ExampleDto(id=live_id)

    # Seed a document with no metadata and a (soft-)deleted document with metadata.
    live_doc = dto_to_document(live_example, id_field="id")
    deleted_doc = dto_to_document(ExampleDto(id=deleted_id), id_field="id")
    deleted_doc["__metadata__"] = {"deleted": True, "published": True}

    db_name = mongo_kafka.config.db_name
    mongo_client: MongoClient = mongo_kafka.mongodb.client
    mongo_client[db_name]["example"].insert_one(live_doc)
    mongo_client[db_name]["example"].insert_one(deleted_doc)

    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # find_all must return the metadata-less document but not the deleted one.
        result = dao.find_all(filter_={})
        assert [hit async for hit in result] == [live_example]
        assert await result.total_count() == 1

        # find_one (which delegates to find_all) must locate it as well.
        assert await dao.find_one(filter_={"id": live_id}) == live_example


async def test_unique_index_error_handling(mongo_kafka: MongoKafkaFixture):
    """Make sure that DuplicateKeyErrors from unique index violations are
    handled correctly in the insert, upsert, and update methods of the mongokafka dao.
    """
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
            indexes=[
                MongoDbIndex(
                    fields={"field_a": 1, "field_b": 1}, properties={"unique": True}
                )
            ],
        )

        dto = ExampleDto()
        dto2 = ExampleDto()

        # Test insert
        await dao.insert(dto)
        with pytest.raises(ResourceAlreadyExistsError):
            await dao.insert(dto)

        with pytest.raises(UniqueConstraintViolationError):
            await dao.insert(dto2)

        # The first value in the unique index is different, but the second is the same
        dto3 = ExampleDto(field_a="banana")
        await dao.insert(dto3)

        # The second value in the unique index is different, but the first is the same
        dto4 = ExampleDto(field_b=700)
        await dao.insert(dto4)

        # Make sure both update and upsert perform the correct error handling too
        dto5 = dto3.model_copy(update={"field_a": dto.field_a})
        with pytest.raises(UniqueConstraintViolationError):
            await dao.update(dto5)

        with pytest.raises(UniqueConstraintViolationError):
            await dao.upsert(dto5)


async def test_update_precondition(mongo_kafka: MongoKafkaFixture):
    """Test that `update` with `precondition` only replaces and publishes a
    resource that exists, is not deleted, and matches the criteria.
    """
    kafka = mongo_kafka.kafka
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        example = ExampleDto(field_b=1)
        example_update = example.model_copy(update={"field_b": 2})

        # Non-existing resource should raise ResourceNotFoundError
        async with kafka.expect_events(events=[], in_topic=EXAMPLE_TOPIC):
            with pytest.raises(ResourceNotFoundError):
                await dao.update(example_update, precondition={"field_b": 1})

        await dao.insert(example)

        # Criteria mismatch should raise NotHitsFoundError
        # Bogus fields for precondition should raise InvalidMappingError
        # and in either of the above cases, no events should be published
        async with kafka.expect_events(events=[], in_topic=EXAMPLE_TOPIC):
            with pytest.raises(PreconditionFailedError):
                await dao.update(example_update, precondition={"field_b": 3})
            with pytest.raises(InvalidMappingError):
                await dao.update(example_update, precondition={"not_a_field": 1})
        assert await dao.get_by_id(example.id) == example

        # Criteria match, including the ID field and an MQL operator
        async with kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload=example_update.model_dump(),
                    type_=CHANGE_EVENT_TYPE,
                    key=str(example.id),
                )
            ],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.update(
                example_update,
                precondition={"id": example.id, "field_b": {"$lt": 2}},
            )

        # Verify that the document was updated
        assert await dao.get_by_id(example.id) == example_update

        # Deleted resource should behave the same as the non-existing resource case above
        await dao.delete(example.id)
        async with kafka.expect_events(events=[], in_topic=EXAMPLE_TOPIC):
            with pytest.raises(ResourceNotFoundError):
                await dao.update(example, precondition={"field_b": 2})


class HeldEventPublisher(EventPublisherProtocol):
    """Records published events and holds back the first one matching `hold` until
    `release` is set, so a test can let a second writer overtake the first.
    """

    def __init__(self, hold: Callable[[JsonObject, str], bool]):
        self._hold = hold
        self.held = asyncio.Event()
        self.release = asyncio.Event()
        self.published: list[tuple[str, JsonObject]] = []

    async def _publish_validated(
        self,
        *,
        payload: JsonObject,
        type_: str,
        key: str,
        topic: str,
        event_id: uuid.UUID,
        headers: Mapping[str, str],
    ) -> None:
        if not self.held.is_set() and self._hold(payload, type_):
            self.held.set()
            await self.release.wait()
        self.published.append((type_, payload))


@asynccontextmanager
async def dao_with_publisher(
    mongo_kafka: MongoKafkaFixture,
    event_publisher: EventPublisherProtocol,
    *,
    autopublish: bool = True,
) -> AsyncIterator[DaoPublisher[ExampleDto]]:
    """Provide an outbox DAO for `ExampleDto` that publishes via `event_publisher`."""
    async with ConfiguredMongoClient(config=mongo_kafka.config) as client:
        factory = MongoKafkaDaoPublisherFactory(
            config=mongo_kafka.config, event_publisher=event_publisher, db_client=client
        )
        yield await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(mode="json"),
            event_topic=EXAMPLE_TOPIC,
            autopublish=autopublish,
        )


async def test_update_overtaking_a_slow_publish(mongo_kafka: MongoKafkaFixture):
    """Test that a guarded update is kept when an earlier update finishes publishing
    after it.

    Marking the earlier update as published must not write its stale state back, and
    the last event must show the newer state again.
    """
    # field_b serves as the version that the updates use as precondition
    publisher = HeldEventPublisher(hold=lambda payload, _: payload["field_b"] == 2)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto(field_a="locked", field_b=1)
        await dao.insert(example)

        first = example.model_copy(update={"field_b": 2})
        first_update = asyncio.create_task(
            dao.update(first, precondition={"field_b": 1})
        )
        await publisher.held.wait()

        second = first.model_copy(update={"field_a": "open", "field_b": 3})
        await dao.update(second, precondition={"field_b": 2})

        publisher.release.set()
        await first_update

        assert await dao.get_by_id(example.id) == second
        assert [payload["field_b"] for _, payload in publisher.published] == [
            1,
            3,
            2,
            3,
        ]
        collection = get_mongo_collection(mongo_kafka, "example")
        document = collection.find_one({"_id": example.id})
        assert document and document["__metadata__"]["published"] is True


async def test_publish_pending_overtaken_by_update(mongo_kafka: MongoKafkaFixture):
    """Test that `publish_pending` does not revert an update made while it was
    publishing the previous state, and publishes that update after it.
    """
    publisher = HeldEventPublisher(hold=lambda payload, _: payload["field_b"] == 1)
    async with dao_with_publisher(mongo_kafka, publisher, autopublish=False) as dao:
        example = ExampleDto(field_b=1)
        await dao.insert(example)

        publishing = asyncio.create_task(dao.publish_pending())
        await publisher.held.wait()

        updated = example.model_copy(update={"field_b": 2})
        await dao.update(updated, precondition={"field_b": 1})

        publisher.release.set()
        await publishing

        assert await dao.get_by_id(example.id) == updated
        assert [payload["field_b"] for _, payload in publisher.published] == [1, 2]
        collection = get_mongo_collection(mongo_kafka, "example")
        document = collection.find_one({"_id": example.id})
        assert document and document["__metadata__"]["published"] is True


async def test_delete_overtaking_a_slow_publish(mongo_kafka: MongoKafkaFixture):
    """Test that a resource stays deleted when its insertion finishes publishing
    after the deletion.
    """
    publisher = HeldEventPublisher(hold=lambda _, type_: type_ == CHANGE_EVENT_TYPE)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        insertion = asyncio.create_task(dao.insert(example))
        await publisher.held.wait()

        await dao.delete(example.id)

        publisher.release.set()
        await insertion

        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(example.id)
        assert [type_ for type_, _ in publisher.published] == [
            DELETE_EVENT_TYPE,
            CHANGE_EVENT_TYPE,
            DELETE_EVENT_TYPE,
        ]


async def test_upsert_overtaking_a_slow_deletion(mongo_kafka: MongoKafkaFixture):
    """Test that a resource upserted again is kept when its deletion finishes
    publishing after the upsert.
    """
    publisher = HeldEventPublisher(hold=lambda _, type_: type_ == DELETE_EVENT_TYPE)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        await dao.insert(example)

        deletion = asyncio.create_task(dao.delete(example.id))
        await publisher.held.wait()

        recreated = example.model_copy(update={"field_b": 2})
        await dao.upsert(recreated)

        publisher.release.set()
        await deletion

        assert await dao.get_by_id(example.id) == recreated
        assert publisher.published[-2:] == [
            (DELETE_EVENT_TYPE, {}),
            (CHANGE_EVENT_TYPE, recreated.model_dump(mode="json")),
        ]


async def test_republishing_stops_under_constant_writes(
    mongo_kafka: MongoKafkaFixture, caplog: pytest.LogCaptureFixture
):
    """Test that republishing a superseded write gives up after a few rounds when
    every publish is overtaken by yet another write, and leaves the resource pending.
    """
    collection = get_mongo_collection(mongo_kafka, "example")

    class OvertakenEventPublisher(EventPublisherProtocol):
        """Simulates a newer write of the resource during every publish."""

        def __init__(self):
            self.published = 0

        async def _publish_validated(
            self,
            *,
            payload: JsonObject,
            type_: str,
            key: str,
            topic: str,
            event_id: uuid.UUID,
            headers: Mapping[str, str],
        ) -> None:
            self.published += 1
            collection.update_one(
                {"_id": uuid.UUID(key)},
                {"$set": {"__metadata__.write_id": uuid.uuid4()}},
            )

    publisher = OvertakenEventPublisher()
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        with caplog.at_level("WARNING"):
            await dao.insert(example)

    # the first publish plus one per republishing round
    assert publisher.published == 1 + MAX_REPUBLISH_ROUNDS
    assert "Stopped republishing resource" in caplog.text
    stored = collection.find_one({"_id": example.id})
    assert stored and stored["__metadata__"]["published"] is False


async def test_republishing_error_is_logged(
    mongo_kafka: MongoKafkaFixture, caplog: pytest.LogCaptureFixture
):
    """Test that a failure while republishing a newer write's state does not fail
    the write that was overtaken, since that write is already stored and published,
    and leaves the resource pending.
    """
    collection = get_mongo_collection(mongo_kafka, "example")

    class FailingRepublishPublisher(EventPublisherProtocol):
        """Simulates a newer write that is published and marked during the first
        publish, then fails.
        """

        def __init__(self):
            self.published = 0

        async def _publish_validated(
            self,
            *,
            payload: JsonObject,
            type_: str,
            key: str,
            topic: str,
            event_id: uuid.UUID,
            headers: Mapping[str, str],
        ) -> None:
            self.published += 1
            if self.published > 1:
                raise RuntimeError("broker unavailable")
            collection.update_one(
                {"_id": uuid.UUID(key)},
                {
                    "$set": {
                        "__metadata__.write_id": uuid.uuid4(),
                        "__metadata__.published": True,
                    }
                },
            )

    publisher = FailingRepublishPublisher()
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        with caplog.at_level("WARNING"):
            await dao.insert(example)

    assert publisher.published == 2
    assert "Could not republish the current state" in caplog.text
    stored = collection.find_one({"_id": example.id})
    assert stored and stored["__metadata__"]["published"] is False


async def test_late_mark_after_failed_republish(
    mongo_kafka: MongoKafkaFixture, caplog: pytest.LogCaptureFixture
):
    """Test that a newer write cannot clear the pending flag when its mark lands
    after a failed republish of its state set the flag, so that it republishes the
    current state itself.
    """
    collection = get_mongo_collection(mongo_kafka, "example")
    newer_write_id = uuid.uuid4()

    class FailingRepublishPublisher(EventPublisherProtocol):
        """Simulates a newer write that is not yet marked during the first publish,
        then fails the republish of its state.
        """

        def __init__(self):
            self.published = 0

        async def _publish_validated(
            self,
            *,
            payload: JsonObject,
            type_: str,
            key: str,
            topic: str,
            event_id: uuid.UUID,
            headers: Mapping[str, str],
        ) -> None:
            self.published += 1
            if self.published == 2:
                raise RuntimeError("broker unavailable")
            if self.published == 1:
                collection.update_one(
                    {"_id": uuid.UUID(key)},
                    {"$set": {"__metadata__.write_id": newer_write_id}},
                )

    publisher = FailingRepublishPublisher()
    async with (
        dao_with_publisher(mongo_kafka, publisher) as dao,
        ConfiguredMongoClient(config=mongo_kafka.config) as client,
    ):
        example = ExampleDto()
        with caplog.at_level("WARNING"):
            await dao.insert(example)
        assert publisher.published == 2
        assert "Could not republish the current state" in caplog.text

        # the mark of the newer write arrives only now and must miss
        async_collection = client.get_database(mongo_kafka.config.db_name)["example"]
        marked = await mark_published(
            async_collection,
            example.id,
            write_id=newer_write_id,
            deleted=False,
            event_id=None,
        )
        assert marked is False
        stored = collection.find_one({"_id": example.id})
        assert stored and stored["__metadata__"]["published"] is False
        assert stored["__metadata__"]["write_id"] != newer_write_id

        # so the newer write republishes the current state, as publish_pending does
        await dao.publish_pending()
        assert publisher.published == 3
        stored = collection.find_one({"_id": example.id})
        assert stored and stored["__metadata__"]["published"] is True


async def test_failed_publish_of_a_superseded_write_leaves_it_pending(
    mongo_kafka: MongoKafkaFixture,
):
    """Test that a write whose publish fails after a newer write replaced and
    published the resource leaves it pending, since the failed write's event may
    already be on the topic behind the newer write's event.
    """
    collection = get_mongo_collection(mongo_kafka, "example")

    class FailingPublisher(EventPublisherProtocol):
        """Simulates a newer write that is published and marked during the first
        publish, which then fails.
        """

        def __init__(self):
            self.published = 0

        async def _publish_validated(
            self,
            *,
            payload: JsonObject,
            type_: str,
            key: str,
            topic: str,
            event_id: uuid.UUID,
            headers: Mapping[str, str],
        ) -> None:
            self.published += 1
            if self.published == 1:
                collection.update_one(
                    {"_id": uuid.UUID(key)},
                    {
                        "$set": {
                            "__metadata__.write_id": uuid.uuid4(),
                            "__metadata__.published": True,
                        }
                    },
                )
                raise RuntimeError("broker unavailable")

    publisher = FailingPublisher()
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        with pytest.raises(RuntimeError):
            await dao.insert(example)
        stored = collection.find_one({"_id": example.id})
        assert stored and stored["__metadata__"]["published"] is False

        await dao.publish_pending()
        assert publisher.published == 2
        stored = collection.find_one({"_id": example.id})
        assert stored and stored["__metadata__"]["published"] is True


async def test_legacy_publish_keeps_a_deletion(mongo_kafka: MongoKafkaFixture):
    """Test that publishing a change written before the write ID existed does not
    revive the resource when it was deleted meanwhile by a writer that sets no write
    ID either, as an older service version would.
    """
    example = ExampleDto()
    document = dto_to_document(example, id_field="id")
    document["__metadata__"] = {
        "deleted": False,
        "published": False,
        "correlation_id": get_correlation_id(),
        "last_event_id": None,
    }
    collection = get_mongo_collection(mongo_kafka, "example")
    collection.insert_one(document)

    class DeletingEventPublisher(EventPublisherProtocol):
        """Replaces the resource with a deletion stub during the change event."""

        def __init__(self):
            self.published: list[str] = []

        async def _publish_validated(
            self,
            *,
            payload: JsonObject,
            type_: str,
            key: str,
            topic: str,
            event_id: uuid.UUID,
            headers: Mapping[str, str],
        ) -> None:
            self.published.append(type_)
            if type_ == CHANGE_EVENT_TYPE:
                collection.replace_one(
                    {"_id": uuid.UUID(key)},
                    {
                        "__metadata__": {
                            "deleted": True,
                            "published": False,
                            "correlation_id": get_correlation_id(),
                        }
                    },
                )

    publisher = DeletingEventPublisher()
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        await dao.publish_pending()
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(example.id)

    assert publisher.published == [CHANGE_EVENT_TYPE, DELETE_EVENT_TYPE]
    stored = collection.find_one({"_id": example.id})
    assert stored and stored["__metadata__"]["deleted"] is True
    assert stored["__metadata__"]["published"] is True


async def test_publish_pending_without_write_id(mongo_kafka: MongoKafkaFixture):
    """Test that `publish_pending` marks documents as published whose metadata was
    written before the write ID existed.
    """
    example = ExampleDto()
    document = dto_to_document(example, id_field="id")
    document["__metadata__"] = {
        "deleted": False,
        "published": False,
        "correlation_id": get_correlation_id(),
        "last_event_id": None,
    }
    collection = get_mongo_collection(mongo_kafka, "example")
    collection.insert_one(document)

    publisher = HeldEventPublisher(hold=lambda *_: False)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        await dao.publish_pending()
        assert len(publisher.published) == 1
        assert await dao.get_by_id(example.id) == example

    stored = collection.find_one({"_id": example.id})
    assert stored and stored["__metadata__"]["published"] is True


async def test_find_all_total_count_excludes_soft_deleted(
    mongo_kafka: MongoKafkaFixture,
):
    """Verify that total_count() doesn't include deleted outbox documents."""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # Add four docs and then delete two of them (the 'dead' ones)
        live1, live2, dead1, dead2 = (ExampleDto() for _ in range(4))
        for dto in (live1, live2, dead1, dead2):
            await dao.insert(dto)
        await dao.delete(dead1.id)
        await dao.delete(dead2.id)

        # Run a query and make sure total_count() is 2
        result = dao.find_all(filter_={})
        page = await result.to_list()
        assert len(page) == 2

        assert await result.total_count() == 2


async def test_pagination_against_deleted_docs(mongo_kafka: MongoKafkaFixture):
    """Test pagination when many outbox documents have been soft-deleted."""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # Add four docs and then delete all of them
        docs = [ExampleDto() for _ in range(4)]
        for dto in docs:
            await dao.insert(dto)
            await dao.delete(dto.id)

        # Insert a document that will be last when sorted
        live_id = uuid.UUID("99999999-9999-4999-9999-999999999999")
        live_doc = ExampleDto(id=live_id)
        await dao.insert(live_doc)

        # Only live_doc remains; the soft-deleted docs are excluded.
        #  If filtering is not done properly, this would return an empty list
        results_limit = [x async for x in dao.find_all(filter_={}, skip=None, limit=4)]
        assert results_limit == [live_doc]

        # Check that using skip=1 and no limit returns an empty list
        results_skip = [x async for x in dao.find_all(filter_={}, skip=1)]
        assert results_skip == []


async def test_pagination_against_metadataless_docs(mongo_kafka: MongoKafkaFixture):
    """Test pagination when many outbox documents lack metadata.

    Metadata-less documents are treated as live, so they must be retrieved rather than
    silently dropped.
    """
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # Add four docs and then strip their metadata
        docs = [ExampleDto() for _ in range(4)]
        for dto in docs:
            await dao.insert(dto)

        db = mongo_kafka.mongodb.client.get_database(mongo_kafka.config.db_name)
        collection = db["example"]
        retrieved_docs = collection.find().to_list()
        assert len(retrieved_docs) == 4
        for doc in retrieved_docs:
            del doc["__metadata__"]
            collection.replace_one({"_id": doc["_id"]}, doc)

        # Insert a document that will be last when sorted
        live_id = uuid.UUID("99999999-9999-4999-9999-999999999999")
        live_doc = ExampleDto(id=live_id)
        await dao.insert(live_doc)

        # The metadata-less docs are live, so they must be retrieved alongside live_doc.
        result = dao.find_all(filter_={})
        all_hits = {hit async for hit in result}
        assert all_hits == {*docs, live_doc}
        assert await result.total_count() == 5

        # Pagination still applies across all five live docs.
        page = await dao.find_all(filter_={}, limit=4).to_list()
        assert len(page) == 4
        remaining = await dao.find_all(filter_={}, skip=4).to_list()
        assert len(remaining) == 1


async def test_find_all_pagination_total_count(mongo_kafka: MongoKafkaFixture):
    """Test that a paginated find_all() returns only the paginated slice via to_list()
    while total_count() reflects the full number of documents matching the filter.
    """
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # Five documents match the filter (field_c=True), two others should be excluded.
        c_true_docs = [ExampleDto(field_b=b, field_c=True) for b in range(5)]
        for doc in c_true_docs:
            await dao.insert(doc)
        for field_b in (100, 101):
            await dao.insert(ExampleDto(field_b=field_b, field_c=False))

        result = dao.find_all(
            filter_={"field_c": True}, skip=1, limit=3, sort=["field_b"]
        )

        # to_list() returns only the paginated slice: field_b in [1, 2, 3]
        page = await result.to_list()
        assert page == c_true_docs[1:4]

        # total_count() reflects all documents matching the filter, ignoring skip/limit
        assert await result.total_count() == 5


async def test_find_all_to_list(mongo_kafka: MongoKafkaFixture):
    """Test that to_list() collects all results into a list."""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=mongo_kafka.config
    ) as factory:
        dao = await factory.get_dao(
            name="example",
            dto_model=ExampleDto,
            id_field="id",
            dto_to_event=lambda dto: dto.model_dump(),
            event_topic=EXAMPLE_TOPIC,
        )

        # Test on empty list
        assert await dao.find_all(filter_={}).to_list() == []

        # Insert 3 docs
        dtos = [ExampleDto(field_b=i) for i in range(3)]
        for dto in dtos:
            await dao.insert(dto)

        # Verify that to_list does what it should
        result = dao.find_all(filter_={}, sort=["field_b"])
        items = await result.to_list()
        assert isinstance(items, list)
        assert items == dtos
        assert await result.total_count() == 3


def change_event(dto: ExampleDto) -> ExpectedEvent:
    """The change event that a DAO from `dao_with_publisher` sends for `dto`."""
    return ExpectedEvent(
        payload=dto.model_dump(mode="json"), type_=CHANGE_EVENT_TYPE, key=str(dto.id)
    )


def delete_event(id_: uuid.UUID) -> ExpectedEvent:
    """The delete event that an outbox DAO sends for the resource with this ID."""
    return ExpectedEvent(payload={}, type_=DELETE_EVENT_TYPE, key=str(id_))


def is_published(mongo_kafka: MongoKafkaFixture, id_: uuid.UUID) -> bool:
    """Whether the stored document of the resource is marked as published."""
    document = get_mongo_collection(mongo_kafka, "example").find_one({"_id": id_})
    assert document is not None
    return document["__metadata__"]["published"]


def reject_on_write(mongo_kafka: MongoKafkaFixture, validator: dict[str, Any]) -> None:
    """Make the example collection reject every write of a document that does not
    match the validator.
    """
    collection = get_mongo_collection(mongo_kafka, "example")
    collection.database.command(
        "collMod",
        collection.name,
        validator=validator,
        # command() otherwise ignores the collection's UUID representation
        codec_options=collection.codec_options,
    )


async def test_insert_many_publishes_written(mongo_kafka: MongoKafkaFixture):
    """Test that insert_many publishes the resources it created in input order, and
    that a tombstoned ID counts as existing.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        existing, tombstoned = ExampleDto(), ExampleDto()
        await dao.insert(existing)
        await dao.insert(tombstoned)
        await dao.delete(tombstoned.id)
        first, last = ExampleDto(), ExampleDto()

        async with mongo_kafka.kafka.expect_events(
            events=[change_event(first), change_event(last)], in_topic=EXAMPLE_TOPIC
        ):
            with pytest.raises(BatchOperationError) as caught:
                await dao.insert_many([first, existing, tombstoned, last])

        assert set(caught.value.errors) == {existing.id, tombstoned.id}
        for error in caught.value.errors.values():
            assert isinstance(error, ResourceAlreadyExistsError)
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(tombstoned.id)
        assert is_published(mongo_kafka, first.id)
        assert is_published(mongo_kafka, last.id)


async def test_insert_many_publishes_nothing_it_skipped(mongo_kafka: MongoKafkaFixture):
    """Test that an ordered insert_many publishes neither the failed resource nor the
    ones it skipped, and leaves the skipped ones unwritten.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        existing = ExampleDto()
        await dao.insert(existing)
        first, skipped = ExampleDto(), ExampleDto()

        async with mongo_kafka.kafka.expect_events(
            events=[change_event(first)], in_topic=EXAMPLE_TOPIC
        ):
            with pytest.raises(BatchOperationError) as caught:
                await dao.insert_many([first, existing, skipped], ordered=True)

        assert list(caught.value.not_attempted) == [skipped.id]
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(skipped.id)


async def test_insert_many_overtaken_by_a_deletion(mongo_kafka: MongoKafkaFixture):
    """Test that a resource stays deleted when insert_many finishes publishing its
    creation after another writer deleted it, and that the last event is the delete.
    """
    publisher = HeldEventPublisher(hold=lambda _, type_: type_ == CHANGE_EVENT_TYPE)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        batch = asyncio.create_task(dao.insert_many([example]))
        await publisher.held.wait()

        await dao.delete(example.id)

        publisher.release.set()
        await batch

        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(example.id)
        assert [type_ for type_, _ in publisher.published] == [
            DELETE_EVENT_TYPE,
            CHANGE_EVENT_TYPE,
            DELETE_EVENT_TYPE,
        ]
        assert is_published(mongo_kafka, example.id)


async def test_upsert_many_publishes(mongo_kafka: MongoKafkaFixture):
    """Test that upsert_many publishes each resource it wrote in input order and
    recreates a tombstoned one.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        tombstoned = ExampleDto()
        await dao.insert(tombstoned)
        await dao.delete(tombstoned.id)
        recreated = tombstoned.model_copy(update={"field_b": 7})
        new = ExampleDto()

        async with mongo_kafka.kafka.expect_events(
            events=[change_event(recreated), change_event(new)], in_topic=EXAMPLE_TOPIC
        ):
            await dao.upsert_many([recreated, new])

        assert await dao.get_by_id(tombstoned.id) == recreated


async def test_upsert_many_publishes_written_on_failure(mongo_kafka: MongoKafkaFixture):
    """Test that upsert_many publishes the resources it wrote when another one fails,
    and nothing for the failed one.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        kept, rejected = ExampleDto(), ExampleDto()
        await dao.insert(kept)
        reject_on_write(mongo_kafka, {"_id": {"$ne": rejected.id}})
        changed = kept.model_copy(update={"field_b": 7})

        async with mongo_kafka.kafka.expect_events(
            events=[change_event(changed)], in_topic=EXAMPLE_TOPIC
        ):
            with pytest.raises(BatchOperationError) as caught:
                await dao.upsert_many([changed, rejected])

        assert list(caught.value.errors) == [rejected.id]


async def test_update_many_keeps_tombstones(mongo_kafka: MongoKafkaFixture):
    """Test that update_many publishes only the replaced resources and treats a
    tombstoned ID as missing.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        live, tombstoned = ExampleDto(), ExampleDto()
        await dao.insert(live)
        await dao.insert(tombstoned)
        await dao.delete(tombstoned.id)
        changed = live.model_copy(update={"field_b": 7})
        missing = ExampleDto()

        async with mongo_kafka.kafka.expect_events(
            events=[change_event(changed)], in_topic=EXAMPLE_TOPIC
        ):
            with pytest.raises(BatchOperationError) as caught:
                await dao.update_many(
                    [changed, tombstoned.model_copy(update={"field_b": 7}), missing]
                )

        assert set(caught.value.errors) == {tombstoned.id, missing.id}
        for error in caught.value.errors.values():
            assert isinstance(error, ResourceNotFoundError)
        assert await dao.get_by_id(live.id) == changed
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(tombstoned.id)


async def test_update_many_skips_resource_created_meanwhile(
    mongo_kafka: MongoKafkaFixture, monkeypatch: pytest.MonkeyPatch
):
    """Test that update_many neither overwrites nor publishes a resource that another
    writer creates between the batch's write and its lookup of the missing IDs.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        stored = ExampleDto()
        await dao.insert(stored)
        changed = stored.model_copy(update={"field_b": 7})
        created = ExampleDto(field_a="created by the other writer")
        lookup = MongoDbDao._existing_ids
        other_writer_done = False

        async def lookup_after_other_writer(
            self: MongoDbDao, ids: Sequence[Any], extra: Mapping[str, Any]
        ) -> set[Any]:
            nonlocal other_writer_done
            if not other_writer_done:
                other_writer_done = True
                await dao.insert(created)
            return await lookup(self, ids, extra)

        monkeypatch.setattr(MongoDbDao, "_existing_ids", lookup_after_other_writer)
        batch_version = created.model_copy(update={"field_a": "updated by the batch"})
        async with mongo_kafka.kafka.expect_events(
            events=[change_event(created), change_event(changed)],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.update_many([changed, batch_version])

        assert await dao.get_by_id(created.id) == created


async def test_update_many_skips_resource_changed_meanwhile(
    mongo_kafka: MongoKafkaFixture, monkeypatch: pytest.MonkeyPatch
):
    """Test that update_many publishes nothing for a resource that another writer
    changes between the batch's write and its publish, since that writer publishes
    its own event.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        first, second = ExampleDto(), ExampleDto()
        for dto in (first, second):
            await dao.insert(dto)
        theirs = second.model_copy(update={"field_a": "changed by the other writer"})
        replace_existing = MongoDbDao._replace_existing

        async def other_writer_after(
            self: MongoDbDao,
            documents: list[dict[str, Any]],
            extra: Mapping[str, Any],
            *,
            ordered: bool,
        ) -> None:
            await replace_existing(self, documents, extra, ordered=ordered)
            await dao.update(theirs)

        monkeypatch.setattr(MongoDbDao, "_replace_existing", other_writer_after)
        ours = [dto.model_copy(update={"field_b": 7}) for dto in (first, second)]
        async with mongo_kafka.kafka.expect_events(
            events=[change_event(theirs), change_event(ours[0])],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.update_many(ours)

        assert await dao.get_by_id(second.id) == theirs
        assert is_published(mongo_kafka, first.id)


async def test_update_many_overtaken_during_its_publish(
    mongo_kafka: MongoKafkaFixture,
):
    """Test that update_many keeps a newer update made while the batch's event is
    on its way, and publishes the newer state again after the batch's event.
    """
    publisher = HeldEventPublisher(hold=lambda payload, _: payload["field_b"] == 2)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto(field_b=1)
        await dao.insert(example)
        batch = asyncio.create_task(
            dao.update_many([example.model_copy(update={"field_b": 2})])
        )
        await publisher.held.wait()

        theirs = example.model_copy(update={"field_b": 3})
        await dao.update(theirs)

        publisher.release.set()
        await batch

        assert await dao.get_by_id(example.id) == theirs
        assert [payload["field_b"] for _, payload in publisher.published] == [
            1,
            3,
            2,
            3,
        ]
        assert is_published(mongo_kafka, example.id)


async def test_delete_many_tombstones_live_ids(mongo_kafka: MongoKafkaFixture):
    """Test that delete_many tombstones the live resources and publishes one delete
    each in input order, and nothing for missing, deleted or repeated IDs.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        first, second, deleted = ExampleDto(), ExampleDto(), ExampleDto()
        for dto in (first, second, deleted):
            await dao.insert(dto)
        await dao.delete(deleted.id)
        missing = uuid.uuid4()

        async with mongo_kafka.kafka.expect_events(
            events=[delete_event(first.id), delete_event(second.id)],
            in_topic=EXAMPLE_TOPIC,
        ):
            await dao.delete_many([first.id, missing, deleted.id, second.id, first.id])

        for dto in (first, second):
            with pytest.raises(ResourceNotFoundError):
                await dao.get_by_id(dto.id)
            assert is_published(mongo_kafka, dto.id)
        collection = get_mongo_collection(mongo_kafka, "example")
        assert collection.find_one({"_id": missing}) is None


@pytest.mark.parametrize("recreate", [False, True])
async def test_delete_many_skips_resource_deleted_meanwhile(
    recreate: bool, mongo_kafka: MongoKafkaFixture, monkeypatch: pytest.MonkeyPatch
):
    """Test that delete_many publishes nothing for a resource that another writer
    deletes just before the batch's write, and leaves it as that writer left it, also
    when the writer recreates it right after.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        raced, plain = ExampleDto(), ExampleDto()
        for dto in (raced, plain):
            await dao.insert(dto)
        recreated = raced.model_copy(
            update={"field_a": "recreated by the other writer"}
        )
        bulk_replace = MongoDbDao._bulk_replace

        async def around_other_writer(
            self: MongoDbDao,
            documents: list[dict[str, Any]],
            extra: Mapping[str, Any],
            **kwargs: Any,
        ) -> tuple[int, BatchOperationError | None]:
            await dao.delete(raced.id)
            result = await bulk_replace(self, documents, extra, **kwargs)
            if recreate:
                await dao.upsert(recreated)
            return result

        monkeypatch.setattr(MongoDbDao, "_bulk_replace", around_other_writer)
        theirs = [delete_event(raced.id)]
        if recreate:
            theirs.append(change_event(recreated))
        async with mongo_kafka.kafka.expect_events(
            events=[*theirs, delete_event(plain.id)], in_topic=EXAMPLE_TOPIC
        ):
            await dao.delete_many([raced.id, plain.id])

        if recreate:
            assert await dao.get_by_id(raced.id) == recreated
        else:
            with pytest.raises(ResourceNotFoundError):
                await dao.get_by_id(raced.id)


async def test_delete_many_overtaken_during_its_publish(
    mongo_kafka: MongoKafkaFixture,
):
    """Test that a resource recreated while delete_many's event is on its way is
    kept, and that its state is published again after the delete.
    """
    publisher = HeldEventPublisher(hold=lambda _, type_: type_ == DELETE_EVENT_TYPE)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        example = ExampleDto()
        await dao.insert(example)
        batch = asyncio.create_task(dao.delete_many([example.id]))
        await publisher.held.wait()

        recreated = example.model_copy(update={"field_b": 2})
        await dao.upsert(recreated)

        publisher.release.set()
        await batch

        assert await dao.get_by_id(example.id) == recreated
        assert publisher.published[1:] == [
            (CHANGE_EVENT_TYPE, recreated.model_dump(mode="json")),
            (DELETE_EVENT_TYPE, {}),
            (CHANGE_EVENT_TYPE, recreated.model_dump(mode="json")),
        ]
        assert is_published(mongo_kafka, example.id)


async def test_delete_many_publishes_before_raising(mongo_kafka: MongoKafkaFixture):
    """Test that delete_many publishes the tombstones it wrote before it raises the
    error of a failed one.
    """
    async with dao_with_publisher(mongo_kafka, mongo_kafka.kafka.publisher) as dao:
        kept, deleted = ExampleDto(), ExampleDto()
        for dto in (kept, deleted):
            await dao.insert(dto)
        reject_on_write(
            mongo_kafka,
            {"$or": [{"_id": {"$ne": kept.id}}, {"__metadata__.deleted": False}]},
        )

        async with mongo_kafka.kafka.expect_events(
            events=[delete_event(deleted.id)], in_topic=EXAMPLE_TOPIC
        ):
            with pytest.raises(BatchOperationError) as caught:
                await dao.delete_many([kept.id, deleted.id])

        assert list(caught.value.errors) == [kept.id]
        assert await dao.get_by_id(kept.id) == kept


class FailingPublisher(EventPublisherProtocol):
    """Records the keys of published and failed events, and fails the first publish
    of each key in `fail_keys`.
    """

    def __init__(self, fail_keys: set[str]):
        self.fail_keys = fail_keys
        self.published: list[str] = []
        self.failed: list[str] = []

    async def _publish_validated(
        self,
        *,
        payload: JsonObject,
        type_: str,
        key: str,
        topic: str,
        event_id: uuid.UUID,
        headers: Mapping[str, str],
    ) -> None:
        if key in self.fail_keys:
            self.fail_keys.remove(key)
            self.failed.append(key)
            raise RuntimeError("broker unavailable")
        self.published.append(key)


async def test_batch_raises_at_first_failed_publish(mongo_kafka: MongoKafkaFixture):
    """Test that a batch raises at its first failed publish, as a single write does,
    and that publish_pending sends what the batch left.
    """
    first, failing, after = ExampleDto(), ExampleDto(), ExampleDto()
    publisher = FailingPublisher(fail_keys={str(failing.id)})
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        with pytest.raises(RuntimeError, match="broker unavailable"):
            await dao.insert_many([first, failing, after])

        assert publisher.published == [str(first.id)]
        assert publisher.failed == [str(failing.id)]
        for dto in (first, failing, after):
            assert await dao.get_by_id(dto.id) == dto
            assert is_published(mongo_kafka, dto.id) is (dto == first)

        await dao.publish_pending()
        assert set(publisher.published[1:]) == {str(failing.id), str(after.id)}


async def test_batch_with_write_errors_logs_failed_publish(
    mongo_kafka: MongoKafkaFixture, caplog: pytest.LogCaptureFixture
):
    """Test that a batch whose write failed for some IDs logs a failed publish and
    raises its BatchOperationError instead, and that publish_pending sends what the
    batch left.
    """
    existing, failing, after = ExampleDto(), ExampleDto(), ExampleDto()
    publisher = FailingPublisher(fail_keys={str(failing.id)})
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        await dao.insert(existing)
        with (
            caplog.at_level("WARNING"),
            pytest.raises(BatchOperationError) as caught,
        ):
            await dao.insert_many([existing, failing, after])

        assert list(caught.value.errors) == [existing.id]
        assert publisher.failed == [str(failing.id)]
        assert (
            f"Could not publish the event for {failing.id}; leaving it and the rest"
            " of the batch to publish_pending." in caplog.text
        )
        for dto in (failing, after):
            assert not is_published(mongo_kafka, dto.id)

        await dao.publish_pending()
        assert set(publisher.published[1:]) == {str(failing.id), str(after.id)}


async def test_batch_without_autopublish(mongo_kafka: MongoKafkaFixture):
    """Test that a batch without autopublish writes but publishes nothing, and leaves
    its resources to publish_pending.
    """
    publisher = HeldEventPublisher(hold=lambda *_: False)
    async with dao_with_publisher(mongo_kafka, publisher, autopublish=False) as dao:
        dtos = [ExampleDto(), ExampleDto()]
        await dao.insert_many(dtos)
        await dao.delete_many([dtos[0].id])
        assert publisher.published == []

        await dao.publish_pending()
        assert publisher.published == [
            (DELETE_EVENT_TYPE, {}),
            (CHANGE_EVENT_TYPE, dtos[1].model_dump(mode="json")),
        ]


@pytest.mark.parametrize(
    "method", ["insert_many", "upsert_many", "update_many", "delete_many"]
)
async def test_empty_batch_through_the_outbox(
    method: str, mongo_kafka: MongoKafkaFixture
):
    """Test that an empty batch through an outbox DAO writes and publishes nothing."""
    publisher = HeldEventPublisher(hold=lambda *_: False)
    async with dao_with_publisher(mongo_kafka, publisher) as dao:
        await getattr(dao, method)([])

    assert publisher.published == []
    assert get_mongo_collection(mongo_kafka, "example").count_documents({}) == 0
