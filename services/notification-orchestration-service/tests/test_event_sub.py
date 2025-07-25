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
"""Tests for the event subscriber."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from nos.adapters.outbound.dao import get_event_id_dao
from nos.inject import prepare_event_subscriber
from tests.conftest import TEST_USER
from tests.fixtures.config import get_config


@pytest.mark.asyncio
async def test_event_sub_idempotence(kafka: KafkaFixture, mongodb: MongoDbFixture):
    """Test that the event subscriber does not process the same event multiple times."""
    # Prepare the event subscriber
    config = get_config(sources=[kafka.config, mongodb.config])
    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as event_subscriber:
        # Create a trigger event
        trigger_event = event_schemas.UserIvaState(
            user_id=TEST_USER.user_id,
            state=event_schemas.IvaState.CODE_REQUESTED,
            value=None,
            type=event_schemas.IvaType.FAX,
        )

        # Publish the trigger event with a known event ID
        event_id = uuid4()
        await kafka.publish_event(
            payload=trigger_event.model_dump(),
            type_=config.iva_state_changed_type,
            topic=config.iva_state_changed_topic,
            key=str(TEST_USER.user_id),
            event_id=event_id,
        )

        # Consume the event
        await event_subscriber.run(forever=False)

        # Assert that the orchestrator's process_iva_state_change method was called
        core_mock.process_iva_state_change.assert_awaited_once()
        core_mock.reset_mock()

        # Check the nosEventIds collection and verify that the event ID is there now
        event_id_dao = await get_event_id_dao(dao_factory=mongodb.dao_factory)
        await event_id_dao.get_by_id(event_id)

        # Publish and consume again
        await kafka.publish_event(
            payload=trigger_event.model_dump(),
            type_=config.iva_state_changed_type,
            topic=config.iva_state_changed_topic,
            key=str(TEST_USER.user_id),
            event_id=event_id,
        )
        await event_subscriber.run(forever=False)

        # Verify that the process_iva_state_change method was not called again
        core_mock.process_iva_state_change.assert_not_awaited()
