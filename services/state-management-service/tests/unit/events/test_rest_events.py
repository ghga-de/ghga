# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test REST endpoints for kafka state management."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from tests.fixtures.config import DEFAULT_TEST_CONFIG
from tests.fixtures.utils import VALID_BEARER_TOKEN, get_rest_client_with_mocks

from sms.ports.inbound.events_handler import EventsHandlerPort

pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize(
    "topics",
    [["topic1", "topic2"], []],
    ids=[
        "BasicTopics",
        "EmptyTopicsList",
    ],
)
@pytest.mark.parametrize(
    "exclude_internal",
    [None, True, False],
    ids=[
        "ExcludeInternalNotSpecified",
        "ExcludeInternalTrue",
        "ExcludeInternalFalse",
    ],
)
async def test_delete_events(topics: list[str], exclude_internal: bool | None):
    """Test delete events endpoint with matrix of parameters."""
    query_parameters: list[tuple[str, Any]] = [("topics", topic) for topic in topics]

    if exclude_internal is not None:
        query_parameters.append(("exclude_internal", exclude_internal))

    mock = AsyncMock(spec=EventsHandlerPort)

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, events_handler_override=mock
    ) as rest_client:
        response = await rest_client.delete(
            "/events/",
            params=query_parameters,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        mock.clear_topics.assert_called_once_with(
            topics=topics,
            exclude_internal=exclude_internal if exclude_internal is not None else True,
        )

        assert response.status_code == 204


async def test_invalid_topics():
    """Test delete events endpoint with invalid topics."""
    mock = AsyncMock(spec=EventsHandlerPort)

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, events_handler_override=mock
    ) as rest_client:
        response = await rest_client.delete(
            "/events/?topics=[invalid]",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        mock.clear_topics.assert_not_called()

        assert response.status_code == 422


async def test_unhandled_error():
    """Verify that unhandled errors return a 500 status code."""
    mock = AsyncMock(spec=EventsHandlerPort)
    mock.clear_topics.side_effect = Exception("Unhandled error")

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, events_handler_override=mock
    ) as rest_client:
        response = await rest_client.delete(
            "/events/",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        mock.clear_topics.assert_called_once()

        assert response.status_code == 500


async def test_unauthenticated_calls():
    """Test unauthenticated calls, which should result in a 401 Unauthorized code."""
    mock = AsyncMock(spec=EventsHandlerPort)

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, events_handler_override=mock
    ) as rest_client:
        response = await rest_client.delete("/events/")

        mock.clear_topics.assert_not_called()

        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}
