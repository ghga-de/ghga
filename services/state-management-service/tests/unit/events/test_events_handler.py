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
"""Unit tests for the EventsHandler class."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiokafka import TopicPartition
from aiokafka.admin import AIOKafkaAdminClient, RecordsToDelete
from ghga_service_commons.utils.context import asyncnullcontext
from tests.fixtures.config import DEFAULT_TEST_CONFIG

from sms.core.events_handler import EventsHandler

pytestmark = pytest.mark.asyncio()

INTERNAL_TOPICS = ["__internal_topic1", "__internal_topic2"]


def mock_describe_topics(topics: list[str]) -> list[dict[str, Any]]:
    """Mock describe_topics method with data for each topic provided."""
    return [{"topic": topic, "partitions": [{"partition": 0}]} for topic in topics]


def get_expected_records_to_delete(
    topics_info: list[dict[str, Any]], exclude_internal: bool
) -> dict[TopicPartition, RecordsToDelete]:
    """Return expected records to delete for each topic."""
    topics_info_filtered = topics_info.copy()

    # if exclude_internal is True, remove 'internal' topics from the list
    if exclude_internal:
        topics_info_filtered = [
            info for info in topics_info if not info["topic"].startswith("__")
        ]

    records_to_delete = {
        TopicPartition(
            topic=topic_info["topic"], partition=partition_info["partition"]
        ): RecordsToDelete(before_offset=-1)
        for topic_info in topics_info_filtered
        for partition_info in topic_info["partitions"]
    }
    return records_to_delete


@pytest.mark.parametrize(
    "topics", [["topic1", "topic2"], []], ids=["BasicTopics", "EmptyTopicsList"]
)
@pytest.mark.parametrize(
    "exclude_internal", [True, False], ids=["DontClearInternal", "ClearInternal"]
)
async def test_topics_parameter_behavior(topics: list[str], exclude_internal: bool):
    """Test how clear_topics behaves based on the parameters."""
    # Set up a mock to replace the admin client
    mock = AsyncMock(spec=AIOKafkaAdminClient)
    mock_topics_info = mock_describe_topics(topics)
    mock.describe_topics.return_value = mock_topics_info
    mock.list_topics.return_value = INTERNAL_TOPICS + topics

    # Create an instance of the EventsHandler and patch with the mock
    handler = EventsHandler(config=DEFAULT_TEST_CONFIG, event_publisher=AsyncMock())
    handler.get_admin_client = lambda: asyncnullcontext(mock)  # type: ignore [method-assign]

    # Call the clear_topics method
    await handler.clear_topics(topics=topics, exclude_internal=exclude_internal)

    # If topics is empty, the list_topics method should have been called to get all topics
    if not topics:
        mock.list_topics.assert_awaited_once()
    else:
        # ... otherwise, it should not have been called
        mock.list_topics.assert_not_called()

    # Assert that the delete records function is called with the expected args
    expected_args = get_expected_records_to_delete(mock_topics_info, exclude_internal)
    mock.delete_records.assert_awaited_once()
    actual_args = mock.delete_records.await_args[0][0]
    assert actual_args.keys() == expected_args.keys()
