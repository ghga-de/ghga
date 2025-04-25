# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test user specific DAOs."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from ghga_service_commons.utils.utc_dates import utc_datetime
from hexkit.correlation import set_new_correlation_id
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import KafkaFixture, RecordedEvent
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from auth_service.config import Config
from auth_service.user_registry.models.ivas import Iva, IvaType
from auth_service.user_registry.models.users import (
    AcademicTitle,
    StatusChange,
    User,
    UserStatus,
)
from auth_service.user_registry.ports.dao import (
    UserDaoPublisherFactoryPort,
)
from auth_service.user_registry.translators.dao import (
    UserDaoPublisherFactory,
)


@pytest_asyncio.fixture(name="user_dao_publisher_factory")
async def fixture_user_dao(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[UserDaoPublisherFactoryPort, None]:
    """Create a user DAO factory for testing and set a random correlation ID."""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
    )
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
        set_new_correlation_id(),
    ):
        yield UserDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_publisher_factory
        )


@pytest.mark.asyncio()
async def test_user_crud(
    user_dao_publisher_factory: UserDaoPublisherFactoryPort, kafka: KafkaFixture
):
    """Test creating, updating and deleting via the user DAO"""
    user_dao = await user_dao_publisher_factory.get_user_dao()
    user = User(
        ext_id="max@ls.org",
        status=UserStatus.ACTIVE,
        name="Max Headroom",
        title=AcademicTitle.DR,
        email="max@example.org",
        registration_date=utc_datetime(2022, 9, 1, 12, 0),
        status_change=StatusChange(previous=None, by=None, context="test"),
        active_submissions=["sub-1"],
        active_access_requests=["req-1", "req-2"],
    )

    async with kafka.record_events(in_topic="users") as recorder:
        await user_dao.insert(user)

        user_dto = await user_dao.get_by_id(user.id)

        assert user_dto == user

        changed_user = user.model_copy(update={"email": "max@changed.org"})
        await user_dao.update(changed_user)
        user_dto = await user_dao.get_by_id(user.id)
        assert user_dto == changed_user

        await user_dao.delete(user.id)
        with pytest.raises(ResourceNotFoundError):
            await user_dao.get_by_id(user.id)

    # changes should be automatically published
    assert recorder.recorded_events == [
        RecordedEvent(
            payload={
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "title": user.title,
            },
            type_="upserted",
            key=user.id,
        ),
        RecordedEvent(
            payload={
                "user_id": user.id,
                "name": user.name,
                "email": changed_user.email,
                "title": user.title,
            },
            type_="upserted",
            key=user.id,
        ),
        RecordedEvent(
            payload={},
            type_="deleted",
            key=user.id,
        ),
    ]


@pytest.mark.asyncio()
async def test_iva_crud(
    user_dao_publisher_factory: UserDaoPublisherFactoryPort, kafka: KafkaFixture
):
    """Test creating, updating and deleting via the user DAO"""
    iva_dao = await user_dao_publisher_factory.get_iva_dao()
    iva = Iva(
        user_id="some-user-id",
        created=utc_datetime(2022, 9, 1, 12, 0),
        changed=utc_datetime(2023, 4, 1, 12, 0),
        type=IvaType.PHONE,
        value="(0123)456789",
    )

    async with kafka.record_events(in_topic="ivas") as recorder:
        await iva_dao.insert(iva)

        iva_dto = await iva_dao.get_by_id(iva.id)

        assert iva_dto == iva

        changed_iva = iva.model_copy(update={"value": "(0123)444555"})
        await iva_dao.update(changed_iva)
        iva_dto = await iva_dao.get_by_id(iva.id)
        assert iva_dto == changed_iva

        await iva_dao.delete(iva.id)
        with pytest.raises(ResourceNotFoundError):
            await iva_dao.get_by_id(iva.id)

    # changes should not be automatically published
    assert not recorder.recorded_events
