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

"""Unit tests for the DLQ Manager"""

from contextlib import nullcontext
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from hexkit.providers.akafka.provider.eventsub import HeaderNames

from dlqs.core.dlq_manager import stored_event_from_raw_event
from dlqs.inject import prepare_core
from dlqs.models import EventCore, PublishableEventData, StoredDLQEvent
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import AggregatorPort, ResourceNotFoundError
from tests.fixtures import utils
from tests.fixtures.config import DEFAULT_CONFIG

TEST_UUID = UUID("25a2abf9-dc4a-4dcc-9b4c-0cafa9ae4001")


def test_dlq_error_text():
    """Test the error text of all the DLQ error types"""
    dlq_operation_error = DLQManagerPort.DLQOperationError()
    assert str(dlq_operation_error) == ""

    # Validation error
    dlq_validation_error = DLQManagerPort.DLQValidationError(
        dlq_id=TEST_UUID, reason="reason"
    )
    msg = f"Validation failed for DLQ Event '{TEST_UUID}': reason"
    assert str(dlq_validation_error) == msg

    # Deletion error
    dlq_deletion_error = DLQManagerPort.DLQDeletionError(dlq_id=TEST_UUID)
    msg = (
        f"Could not delete DLQ event '{TEST_UUID}' from the database."
        + " Maybe the event was already deleted or the database is unreachable."
    )
    assert str(dlq_deletion_error) == msg

    # Insertion error from duplicate entry
    dlq_insertion_error = DLQManagerPort.DLQInsertionError(
        dlq_id=TEST_UUID, already_exists=True
    )
    msg = (
        f"Could not insert DLQ event '{TEST_UUID}' into the database."
        + " Event with same ID already exists."
    )
    assert str(dlq_insertion_error) == msg

    # Insertion error from other reason
    dlq_insertion_error = DLQManagerPort.DLQInsertionError(
        dlq_id=TEST_UUID, already_exists=False
    )
    msg = f"Could not insert DLQ event '{TEST_UUID}' into the database."
    assert str(dlq_insertion_error) == msg


def test_stored_event_from_dlq_event_info():
    """Test the conversion of a DLQEventInfo object to a StoredDLQEvent object"""
    dlq_event = utils.graph_event()
    assert dlq_event.headers["exc_class"] is not None

    og_topic = dlq_event.headers[HeaderNames.ORIGINAL_TOPIC]
    service, _, partition, offset = dlq_event.headers["event_id"].split(",")

    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    assert stored_dlq_event.dlq_id is not None
    assert isinstance(stored_dlq_event.dlq_id, UUID)
    assert stored_dlq_event.dlq_info.service == service
    assert stored_dlq_event.dlq_info.partition == int(partition)
    assert stored_dlq_event.dlq_info.offset == int(offset)
    assert stored_dlq_event.dlq_info.exc_class == dlq_event.headers["exc_class"]
    assert stored_dlq_event.dlq_info.exc_msg == dlq_event.headers["exc_msg"]
    assert stored_dlq_event.topic == og_topic
    assert stored_dlq_event.payload == dlq_event.payload
    assert stored_dlq_event.headers == {
        HeaderNames.CORRELATION_ID: dlq_event.headers[HeaderNames.CORRELATION_ID],
    }
    assert stored_dlq_event.key == dlq_event.key
    assert stored_dlq_event.timestamp == dlq_event.timestamp
    assert isinstance(stored_dlq_event, StoredDLQEvent)


@pytest.mark.asyncio
async def test_process_override_different_dlq_id():
    """Verify that the DLQManager stops processing with a DLQValidationError
    if the DLQ ID does not match the one from the next-in-topic event.
    """
    dlq_event = utils.graph_event()
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    override_event = EventCore(**dlq_event.model_dump())

    # The dlq id of the "next event to be processed" will be the one from stored_dlq_event
    #  so we need to pass some other DLQ ID to the process_event method to trigger the error
    incorrect_dlq_id = UUID("25a2abf9-dc4a-4dcc-9b4c-0cafa9ae4417")

    mock_agg = AsyncMock()
    mock_agg.aggregate.return_value = [stored_dlq_event]

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=AsyncMock(),
        aggregator_override=mock_agg,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQSequenceError):
            await dlq_manager.process_event(
                service="fss",
                topic=dlq_event.topic,
                dlq_id=incorrect_dlq_id,
                override=override_event,
                dry_run=False,
            )


@pytest.mark.parametrize(
    "topic", [DEFAULT_CONFIG.kafka_dlq_topic, "fss-retry", "-retry"]
)
@pytest.mark.asyncio
async def test_process_override_forbidden_topic(topic: str):
    """Verify that the DLQManager stops processing with a DLQValidationError
    if the override event's topic is not allowed.
    """
    dlq_event = utils.graph_event()
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    override_event = EventCore(**dlq_event.model_dump())

    # The override event's topic is not allowed
    override_event.topic = topic

    mock_agg = AsyncMock()
    mock_agg.aggregate.return_value = [stored_dlq_event]

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=AsyncMock(),
        aggregator_override=mock_agg,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQValidationError):
            await dlq_manager.process_event(
                service="fss",
                topic=dlq_event.topic,
                dlq_id=stored_dlq_event.dlq_id,
                override=override_event,
                dry_run=False,
            )


@pytest.mark.asyncio
async def test_process_dry_run():
    """Ensure `process` doesn't actually publish the event if `dry_run` is True."""
    dlq_event = utils.graph_event()
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    dlq_id = stored_dlq_event.dlq_id

    mock_dao = AsyncMock()
    mock_agg = AsyncMock()
    mock_agg.aggregate.return_value = [stored_dlq_event]
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        aggregator_override=mock_agg,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        await dlq_manager.process_event(
            service="fss",
            topic=dlq_event.topic,
            dlq_id=dlq_id,
            override=None,
            dry_run=True,
        )
        # Verify that the event was neither published nor deleted from the DLQ
        mock_dao.delete.assert_not_called()
        mock_publisher.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_process_override_success():
    """Verify that the DLQManager successfully processes an event with an override."""
    dlq_event = utils.graph_event()
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    dlq_id = stored_dlq_event.dlq_id

    # Let's imagine the schema and type were outdated, so update those and retry
    payload = {
        "from_node_id": dlq_event.payload["source_id"],
        "to_node_id": dlq_event.payload["dest_id"],
    }
    override_event = EventCore(
        payload=payload,
        type_="conn_added",
        topic=stored_dlq_event.topic,
        key=stored_dlq_event.key,
    )
    published = PublishableEventData(
        topic=f"{utils.FSS}-retry",
        type_=override_event.type_,
        payload=override_event.payload,
        key=override_event.key,
        headers={HeaderNames.ORIGINAL_TOPIC: override_event.topic},
    )

    mock_dao = AsyncMock()
    mock_agg = AsyncMock()
    mock_agg.aggregate.return_value = [stored_dlq_event]
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        aggregator_override=mock_agg,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        result = await dlq_manager.process_event(
            service="fss",
            topic=dlq_event.topic,
            dlq_id=dlq_id,
            override=override_event,
            dry_run=False,
        )
        assert result is not None and isinstance(result, PublishableEventData)

        # Verify that the event was published and deleted from the DLQ
        mock_dao.delete.assert_called_once_with(stored_dlq_event.dlq_id)
        mock_publisher.publish.assert_called_once_with(**published.model_dump())

        # Verify the content returned from .process_event()
        assert result.headers[HeaderNames.ORIGINAL_TOPIC] == override_event.topic
        assert result.payload == override_event.payload
        assert result.type_ == override_event.type_
        assert result.key == override_event.key
        assert result.topic == f"{utils.FSS}-retry"


@pytest.mark.parametrize(
    "override",
    [None, EventCore(**utils.graph_event().model_dump())],
)
@pytest.mark.asyncio
async def test_process_with_empty_dlq(override: EventCore | None):
    """Make sure no errors are raised and that `None` is returned when calling
    `process_event` with an empty DLQ. Behavior should be equal regardless of `override`.
    """
    mock_dao = AsyncMock()
    mock_agg = AsyncMock()
    mock_agg.aggregate.return_value = []
    mock_publisher = AsyncMock()
    dlq_id = TEST_UUID

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        aggregator_override=mock_agg,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQEmptyError):
            _ = await dlq_manager.process_event(
                service="fss",
                topic=utils.USER_EVENTS,
                dlq_id=dlq_id,
                override=override,
                dry_run=False,
            )
        mock_dao.delete.assert_not_called()
        mock_publisher.send_to_retry_topic.assert_not_called()


@pytest.mark.parametrize(
    "skip, limit",
    [(0, 5), (5, 5), (10, 5), (15, None)],
    ids=[
        "Beginning to Middle",
        "Middle to End",
        "Past end limited",
        "Past end unlimited",
    ],
)
@pytest.mark.asyncio
async def test_preview_pagination_valid_params(skip: int, limit: int):
    """Test that `preview_events` calls the aggregator with correct params."""
    mock_agg = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=AsyncMock(),
        aggregator_override=mock_agg,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        _ = await dlq_manager.preview_events(
            service="test", topic="test2", limit=limit, skip=skip
        )
        mock_agg.aggregate.assert_called_once_with(
            service="test", topic="test2", skip=skip, limit=limit
        )


@pytest.mark.asyncio
async def test_value_error_propagation():
    """Verify that `preview_events` lets ValueErrors bubble up."""
    error_mock = AsyncMock()
    error_mock.aggregate.side_effect = ValueError("Invalid params")
    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=AsyncMock(),
        aggregator_override=error_mock,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(ValueError, match="Invalid params"):
            _ = await dlq_manager.preview_events(service="NA", topic="NA2")


@pytest.mark.asyncio
async def test_preview_db_error():
    """Test that AggregatorPort.AggregationError is translated to DLQPreviewError"""
    error_mock = AsyncMock()
    error_mock.aggregate.side_effect = AggregatorPort.AggregationError(parameters="")
    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=AsyncMock(),
        aggregator_override=error_mock,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(DLQManagerPort.DLQPreviewError):
            _ = await dlq_manager.preview_events(service="test", topic="test2")


@pytest.mark.parametrize(
    "event_exists, error",
    [(True, False), (True, True), (False, False)],
    ids=["Event Exists", "Deletion Error", "Event Does Not Exist"],
)
@pytest.mark.asyncio
async def test_discard_event(event_exists: bool, error: bool):
    """Test what happens when we call `discard_event`.

    Should cover the following cases:
    - Event exists in the DLQ for the requested service (happy path)
    - Event exists but delete fails
    - Event does not exist in the DLQ (no errors, just quietly attempts delete)
    """
    dlq_event = utils.user_event(service="fss", offset=0)
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    dlq_id = stored_dlq_event.dlq_id

    mock_dao = AsyncMock()

    # To simulate an existing event, we return it from the mock (otherwise raise an error)
    if event_exists:
        mock_dao.get_by_id.return_value = stored_dlq_event
    else:
        mock_dao.get_by_id.side_effect = ResourceNotFoundError(id_=dlq_id)

    # If we want to simulate a deletion error, we raise an exception on the mock
    if error:
        mock_dao.delete.side_effect = DLQManagerPort.DLQDeletionError(
            dlq_id=stored_dlq_event.dlq_id
        )
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        aggregator_override=AsyncMock(),
        publisher_override=mock_publisher,
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQDeletionError) if error else nullcontext():
            await dlq_manager.discard_event(dlq_id=dlq_id)

        # The publisher should never be used for `discard_event`
        mock_publisher.publish.assert_not_called()

        # Verify that we called the DAO's "delete" method
        mock_dao.delete.assert_called_once_with(dlq_id)
