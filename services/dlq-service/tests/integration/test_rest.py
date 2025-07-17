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

"""Integration tests that focus on the REST API"""

from json import loads
from uuid import uuid4

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.log import configure_logging
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.provider import dto_to_document
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.inject import prepare_rest_app
from dlqs.models import DLQInfo, StoredDLQEvent
from tests.fixtures import utils
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio


async def test_get_event_success(joint_fixture: JointFixture, prepopped_events):
    """Test successful case of getting the next event(s) for a given service/topic"""
    stored = prepopped_events[utils.UFS][utils.USER_EVENTS]
    assert len(stored) > 0
    expected = [loads(event.model_dump_json()) for event in stored]

    response = await joint_fixture.rest_client.get(
        f"/{utils.UFS}/{utils.USER_EVENTS}", headers=utils.VALID_AUTH_HEADER
    )
    assert response.status_code == 200
    assert response.json() == expected


async def test_msg_too_big_to_publish(
    kafka: KafkaFixture, mongodb: MongoDbFixture, capsys
):
    """Test that a message that is too big to publish raises an error.

    The error should be logged along with the request parameters.
    """
    kafka_size_limit = 10000
    config = get_config(
        sources=[kafka.config, mongodb.config], kafka_max_message_size=kafka_size_limit
    )
    configure_logging(config=config)

    # Make test event that exceeds the Kafka size limit
    test_event = StoredDLQEvent(
        dlq_id=uuid4(),
        headers={"correlation_id": str(uuid4())},
        topic="test-topic",
        type_="test-type",
        key="test-key",
        payload={"field": "x" * (kafka_size_limit * 2)},  # 2 times the max size
        dlq_info=DLQInfo(
            service="test-service",
            partition=0,
            offset=0,
            exc_class="TestException",
            exc_msg="Test message",
        ),
    )

    # Insert test data
    db_name = config.db_name
    db = mongodb.client[db_name]
    test_json = dto_to_document(test_event, id_field="dlq_id")
    db["dlqEvents"].insert_one(test_json)

    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        # clear stderr/out buffers
        _, _ = capsys.readouterr()
        response = await client.post(
            "/test-service/test-topic",
            json={"dlq_id": str(test_event.dlq_id)},
            headers=utils.VALID_AUTH_HEADER,
        )
        assert response.status_code == 500

        out, err = capsys.readouterr()
        printed_log = out + err

        assert '"type": "MessageSizeTooLargeError"' in printed_log
        assert (
            '"request_parameters": {"service": "test-service", "topic":'
            + f' "test-topic", "dlq_id": "{test_event.dlq_id!r}"'
            + "}"
        ) in printed_log
