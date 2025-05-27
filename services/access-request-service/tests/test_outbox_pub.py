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

"""Tests for the events published by the access request outbox DAO"""

from datetime import UTC, datetime

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import set_new_correlation_id
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from ars.adapters.outbound.daos import get_access_request_dao, get_dataset_dao
from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestStatus,
    Dataset,
)
from ars.core.repository import AccessRequestRepository
from tests.test_repository import AccessGrantsDummy

pytestmark = pytest.mark.asyncio()


CREATION_DATA = AccessRequestCreationData(
    user_id="id-of-john-doe@ghga.de",
    iva_id="some-iva",
    dataset_id="DS001",
    email="me@john-doe.name",
    request_text="Can I access some dataset?",
    access_starts=datetime(2025, 5, 6, 6, 45, 29, tzinfo=UTC),
    access_ends=datetime(2025, 10, 6, 7, 45, 29, tzinfo=UTC),
)

access_request = AccessRequest(
    **CREATION_DATA.model_dump(),
    full_user_name="John Doe",
    dataset_title="Dataset1",
    dataset_description="Some Description",
    dac_alias="Some DAC",
    dac_email="dac@org.dev",
    request_created=now_as_utc(),
)

DATASET = Dataset(
    id="DS001",
    title="Dataset1",
    description="Some Description",
    dac_alias="Some DAC",
    dac_email="dac@org.dev",
)


async def test_upsert(config, kafka: KafkaFixture, mongodb: MongoDbFixture):
    """Verify the event published as a result of upserting an access request.

    We trust the deletion to work because it is tested via hexkit -- only the upsert
    contains logic specific to the ARS.
    """
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
        set_new_correlation_id(),
    ):
        # Insert an access request
        dao = await get_access_request_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        async with kafka.record_events(
            in_topic=config.access_request_topic
        ) as recorder:
            await dao.insert(access_request)
        assert len(recorder.recorded_events) == 1
        event = recorder.recorded_events[0]
        assert event.type_ == "upserted"
        assert event.key == event.payload["id"] == access_request.id
        assert event.payload["status"] == "pending"

        # Perform an update to the request
        access_request_update = access_request.model_copy(
            update={"status": AccessRequestStatus.ALLOWED}
        )
        async with kafka.record_events(
            in_topic=config.access_request_topic
        ) as recorder:
            await dao.update(access_request_update)
        assert len(recorder.recorded_events) == 1
        event = recorder.recorded_events[0]
        assert event.type_ == "upserted"
        assert event.key == event.payload["id"] == access_request.id
        assert event.payload["status"] == "allowed"


async def test_delete(config, kafka: KafkaFixture, mongodb: MongoDbFixture):
    """Verify the event published as a result of upserting an access request.

    We trust the deletion to work because it is tested via hexkit -- only the upsert
    contains logic specific to the ARS.
    """
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
        set_new_correlation_id(),
    ):
        # Insert an access request
        request_dao = await get_access_request_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        async with kafka.record_events(
            in_topic=config.access_request_topic
        ) as recorder:
            await request_dao.insert(access_request)

        assert len(recorder.recorded_events) == 1
        event = recorder.recorded_events[0]
        assert event.type_ == "upserted"
        assert event.key == event.payload["id"] == access_request.id
        assert event.payload["status"] == "pending"

        dao_factory = MongoDbDaoFactory(config=config)
        dataset_dao = await get_dataset_dao(dao_factory=dao_factory)
        await dataset_dao.insert(DATASET)

        # Test effect on access request if dataset is deleted
        repository = AccessRequestRepository(
            config=config,
            access_request_dao=request_dao,
            dataset_dao=dataset_dao,
            access_grants=AccessGrantsDummy(),
        )
        async with kafka.record_events(
            in_topic=config.access_request_topic
        ) as recorder:
            await repository.delete_dataset(DATASET.id)

        assert len(recorder.recorded_events) == 1
        event = recorder.recorded_events[0]
        assert event.type_ == "upserted"
        assert event.key == event.payload["id"] == access_request.id
        assert event.payload["status"] == "denied"
