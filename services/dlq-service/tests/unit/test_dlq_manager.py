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

"""Unit tests for the DLQ Manager"""

import base64
import json
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid1

import bson
import pytest

from dlqs.adapters.inbound.event_sub import DLQSubTranslator
from dlqs.core import dlq_manager as dlq_manager_module
from dlqs.core.dlq_manager import (
    UNKNOWN,
    degraded_copy,
    is_degraded_copy,
    stored_event_from_raw_event,
)
from dlqs.inject import prepare_core
from dlqs.models import EventCore, PublishableEventData, StoredDLQEvent
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import ResourceNotFoundError
from hexkit.protocols.dao import Dao, DaoError, DbTimeoutError
from hexkit.providers.akafka.provider.eventsub import HeaderNames
from hexkit.providers.testing.dao import new_mock_dao_class
from tests.fixtures import utils
from tests.fixtures.config import DEFAULT_CONFIG

TEST_UUID = UUID("25a2abf9-dc4a-4dcc-9b4c-0cafa9ae4001")

InMemDLQEventDao = new_mock_dao_class(dto_model=StoredDLQEvent, id_field="dlq_id")


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

    # extract some dlq info up here since the lines would get long otherwise
    og_topic = dlq_event.headers[HeaderNames.ORIGINAL_TOPIC]
    og_event_id = UUID(dlq_event.headers[HeaderNames.ORIGINAL_EVENT_ID])
    service = dlq_event.headers[HeaderNames.SERVICE_NAME]
    exc_class = dlq_event.headers[HeaderNames.EXC_CLASS]
    exc_msg = dlq_event.headers[HeaderNames.EXC_MSG]

    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    assert stored_dlq_event.dlq_id == dlq_event.dlq_id
    assert isinstance(stored_dlq_event.dlq_id, UUID)
    assert stored_dlq_event.dlq_info.service == service
    assert stored_dlq_event.dlq_info.original_event_id == og_event_id
    assert stored_dlq_event.dlq_info.exc_class == exc_class
    assert stored_dlq_event.dlq_info.exc_msg == exc_msg
    assert stored_dlq_event.topic == og_topic
    assert stored_dlq_event.payload == dlq_event.payload
    assert stored_dlq_event.headers == {
        HeaderNames.CORRELATION_ID: dlq_event.headers[HeaderNames.CORRELATION_ID],
    }
    assert stored_dlq_event.key == dlq_event.key
    assert stored_dlq_event.timestamp == dlq_event.timestamp
    assert isinstance(stored_dlq_event, StoredDLQEvent)


def test_stored_event_from_dlq_event_legacy():
    """Test that we can handle events published pre-hexkit-v6 (replay, for example)"""
    dlq_event = utils.graph_event()
    del dlq_event.headers[HeaderNames.ORIGINAL_EVENT_ID]
    dlq_event.headers["event_id"] = "fss,topic,0,123"
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    assert stored_dlq_event.dlq_info.original_event_id is None


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

    dao = InMemDLQEventDao()
    await dao.insert(stored_dlq_event)

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQSequenceError):
            await dlq_manager.process_event(
                service="fss",
                topic=stored_dlq_event.topic,
                dlq_id=incorrect_dlq_id,
                override=override_event,
                dry_run=False,
            )


@pytest.mark.parametrize(
    "topic", [DEFAULT_CONFIG.kafka_dlq_topic, "retry-fss", "retry-"]
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

    dao = InMemDLQEventDao()
    await dao.insert(stored_dlq_event)

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQValidationError):
            await dlq_manager.process_event(
                service="fss",
                topic=stored_dlq_event.topic,
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

    dao = InMemDLQEventDao()
    await dao.insert(stored_dlq_event)
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        await dlq_manager.process_event(
            service="fss",
            topic=stored_dlq_event.topic,
            dlq_id=dlq_id,
            override=None,
            dry_run=True,
        )
        # Verify that the event was neither published nor deleted from the DLQ
        assert dao.latest == stored_dlq_event
        mock_publisher.publish.assert_not_called()


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
        topic=f"retry-{utils.FSS}",
        type_=override_event.type_,
        payload=override_event.payload,
        key=override_event.key,
        headers={HeaderNames.ORIGINAL_TOPIC: override_event.topic},
    )

    dao = InMemDLQEventDao()
    await dao.insert(stored_dlq_event)
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        result = await dlq_manager.process_event(
            service="fss",
            topic=stored_dlq_event.topic,
            dlq_id=dlq_id,
            override=override_event,
            dry_run=False,
        )
        assert result is not None and isinstance(result, PublishableEventData)

        # Verify that the event was published and deleted from the DLQ
        with pytest.raises(ResourceNotFoundError):
            await dao.get_by_id(stored_dlq_event.dlq_id)
        mock_publisher.publish.assert_called_once_with(**published.model_dump())

        # Verify the content returned from .process_event()
        assert result.headers[HeaderNames.ORIGINAL_TOPIC] == override_event.topic
        assert result.payload == override_event.payload
        assert result.type_ == override_event.type_
        assert result.key == override_event.key
        assert result.topic == f"retry-{utils.FSS}"


@pytest.mark.parametrize(
    "override",
    [None, EventCore(**utils.graph_event().model_dump())],
)
@pytest.mark.asyncio
async def test_process_with_empty_dlq(override: EventCore | None):
    """Make sure no errors are raised and that `None` is returned when calling
    `process_event` with an empty DLQ. Behavior should be equal regardless of `override`.
    """
    mock_dao = InMemDLQEventDao()

    async def ensure_delete_not_hit(id_) -> None:
        raise RuntimeError("Delete was called on the DAO but shouldn't have been.")

    mock_dao.delete = ensure_delete_not_hit
    mock_publisher = AsyncMock()
    dlq_id = TEST_UUID

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
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
        mock_publisher.publish.assert_not_called()


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
    """Test that `preview_events` calls the DAO with correct params."""
    mock_dao = Mock()

    class MockResults:
        async def __aiter__(self):
            return
            yield

    mock_dao.find_all.return_value = MockResults()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        _ = await dlq_manager.preview_events(
            service="test", topic="test2", limit=limit, skip=skip
        )
        mock_dao.find_all.assert_called_once_with(
            filter_={"dlq_info.service": "test", "topic": "test2"},
            sort=["timestamp"],
            skip=skip,
            limit=limit,
        )


@pytest.mark.parametrize("skip, limit", [(-1, 10), (0, -1), (-1, -1)])
@pytest.mark.asyncio
async def test_value_error_propagation(skip: int, limit: int):
    """Verify that `preview_events` lets ValueErrors bubble up."""
    dao = InMemDLQEventDao()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(DLQManagerPort.DLQPaginationError):
            _ = await dlq_manager.preview_events(
                service="NA", topic="NA2", skip=skip, limit=limit
            )


@pytest.mark.asyncio
async def test_preview_db_error():
    """Test that non-pagination errors are translated as DLQPreviewError"""
    error_mock = Mock()
    error_mock.find_all.side_effect = TypeError()
    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=error_mock,
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
    dlq_event = utils.user_event(service="fss", user_no=0)
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    dlq_id = stored_dlq_event.dlq_id

    mock_dao = AsyncMock()

    # If we want to simulate a deletion error, we raise an exception on the mock
    if error:
        mock_dao.delete.side_effect = DLQManagerPort.DLQDeletionError(
            dlq_id=stored_dlq_event.dlq_id
        )
    elif not event_exists:
        mock_dao.delete.side_effect = ResourceNotFoundError(id_=dlq_id)
    mock_publisher = AsyncMock()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQDeletionError) if error else nullcontext():
            await dlq_manager.discard_event(dlq_id=dlq_id)

        # The publisher should never be used for `discard_event`
        mock_publisher.publish.assert_not_called()

        # Verify that we called the DAO's "delete" method
        mock_dao.delete.assert_called_once_with(dlq_id)


@pytest.mark.asyncio
async def test_get_service_topic_summary():
    """Test to make sure `get_service_topic_summary()` returns the right data."""
    dao = cast(Dao[StoredDLQEvent], InMemDLQEventDao())

    for i in range(5):
        dlq_event = utils.user_event(service="fss", user_no=i)
        await dao.insert(stored_event_from_raw_event(dlq_event))

    for i in range(4):
        dlq_event = utils.user_event(service="ufs", user_no=i)
        await dao.insert(stored_event_from_raw_event(dlq_event))

    for i in range(19):
        dlq_event = utils.graph_event(user_no=i)  # service=fss
        await dao.insert(stored_event_from_raw_event(dlq_event))

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        results = await dlq_manager.get_service_topic_summary()
    assert results == {
        utils.FSS: {
            utils.USER_EVENTS: 5,
            utils.GRAPH_UPDATES: 19,
        },
        utils.UFS: {utils.USER_EVENTS: 4},
    }


@pytest.mark.parametrize(
    "header", [HeaderNames.ORIGINAL_TOPIC, HeaderNames.SERVICE_NAME]
)
@pytest.mark.parametrize(
    "value",
    [None, "", "a/b", "J\u00fcrgen", "x" * 250, ".", ".."],
    ids=["missing", "empty", "slash", "non_ascii", "too_long", "dot", "dot_dot"],
)
def test_stored_event_without_topic_or_service(header: str, value: str | None):
    """A missing or unusable original topic or service name is stored as 'unknown',
    since the API cannot address it in a path segment.
    """
    dlq_event = utils.graph_event()
    if value is None:
        del dlq_event.headers[header]
    else:
        dlq_event.headers[header] = value
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    stored_value = (
        stored_dlq_event.topic
        if header == HeaderNames.ORIGINAL_TOPIC
        else stored_dlq_event.dlq_info.service
    )
    assert stored_value == UNKNOWN


@pytest.mark.parametrize(
    "original_event_id",
    ["not-a-uuid", str(uuid1()), ""],
    ids=["garbage", "uuid1", "empty"],
)
def test_stored_event_with_invalid_original_event_id(original_event_id: str):
    """An original event ID that is not a UUID4 is stored as None."""
    dlq_event = utils.graph_event()
    dlq_event.headers[HeaderNames.ORIGINAL_EVENT_ID] = original_event_id
    stored_dlq_event = stored_event_from_raw_event(dlq_event)
    assert stored_dlq_event.dlq_info.original_event_id is None


@pytest.mark.asyncio
async def test_store_event_duplicate_is_success():
    """Storing a redelivered DLQ event succeeds without a second copy."""
    dlq_event = utils.graph_event()
    dao = InMemDLQEventDao()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        await dlq_manager.store_event(event=dlq_event)
        await dlq_manager.store_event(event=dlq_event)

    assert len(dao.resources) == 1


@pytest.mark.asyncio
async def test_store_event_other_db_error():
    """A database error other than a duplicate still raises."""
    mock_dao = AsyncMock()
    mock_dao.insert.side_effect = RuntimeError("database down")

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=mock_dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQInsertionError):
            await dlq_manager.store_event(event=utils.graph_event())


@pytest.mark.asyncio
async def test_translator_derives_uuid4_from_other_event_id():
    """An event ID of another UUID version is replaced by a UUID4 derived from it,
    so the event is stored once and a redelivery is still a duplicate.
    """
    event_id = uuid1()
    derived_id = UUID(int=event_id.int, version=4)
    dao = InMemDLQEventDao()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        translator = DLQSubTranslator(dlq_manager=dlq_manager)
        dlq_event = utils.graph_event()
        for _ in range(2):
            await translator.consume(
                payload=dlq_event.payload,
                type_=dlq_event.type_,
                topic=DEFAULT_CONFIG.kafka_dlq_topic,
                key=dlq_event.key,
                event_id=event_id,
                timestamp=datetime.now(UTC),
                headers=dlq_event.headers,
            )

    assert derived_id.version == 4
    assert list(dao.resources) == [derived_id]


class EncodingDao(InMemDLQEventDao):  # type: ignore[valid-type,misc]
    """An in-memory DAO that encodes each document as BSON, as MongoDB would."""

    async def insert(self, dto):
        """Insert the document if it can be encoded."""
        bson.encode(dto.model_dump(mode="json"))
        await super().insert(dto)


class FailingDao(InMemDLQEventDao):  # type: ignore[valid-type,misc]
    """An in-memory DAO whose first inserts fail with the given errors."""

    def __init__(self, *errors: Exception):
        super().__init__()
        self.errors = list(errors)

    async def insert(self, dto):
        """Raise the next error, or insert the document if none is left."""
        if self.errors:
            raise self.errors.pop(0)
        await super().insert(dto)


def assert_degraded(stored: StoredDLQEvent, original: dict, *, error_class: str):
    """Assert that the stored event is a degraded copy of the original payload."""
    assert is_degraded_copy(stored)
    payload = stored.payload
    assert payload["payload_truncated"] is False
    assert payload["store_error"].startswith(error_class + ":")
    assert json.loads(base64.b64decode(payload["payload_json_b64"])) == original


@pytest.mark.parametrize(
    "payload, error_class",
    [
        ({"a\x00b": 1}, "InvalidDocument"),
        ({"a": "\ud800"}, "UnicodeEncodeError"),
        ({"n": 10**20}, "OverflowError"),
    ],
    ids=["nul_in_key", "lone_surrogate", "big_integer"],
)
@pytest.mark.asyncio
async def test_store_event_unencodable_payload(payload: dict, error_class: str):
    """A payload that BSON cannot encode is stored as a degraded copy."""
    dlq_event = utils.graph_event()
    dlq_event.payload = payload
    dao = EncodingDao()

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        await dlq_manager.store_event(event=dlq_event)
        await dlq_manager.store_event(event=dlq_event)  # a redelivery

    assert len(dao.resources) == 1
    assert_degraded(dao.latest, payload, error_class=error_class)


@pytest.mark.asyncio
async def test_store_event_rejected_by_server():
    """A payload the server rejects, like a too deeply nested one, is stored as a
    degraded copy, since such a DaoError can be permanent.
    """
    dlq_event = utils.graph_event()
    dao = FailingDao(DaoError("document is nested too deeply"))

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        await dlq_manager.store_event(event=dlq_event)

    assert_degraded(dao.latest, dlq_event.payload, error_class="DaoError")


@pytest.mark.asyncio
async def test_store_event_degraded_payload_truncated(
    monkeypatch: pytest.MonkeyPatch,
):
    """The degraded copy cuts a payload that would not fit into a document."""
    monkeypatch.setattr(dlq_manager_module, "_DEGRADED_PAYLOAD_MAX_BYTES", 10)
    dlq_event = utils.graph_event()
    dao = FailingDao(DaoError("document too large"))

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        await dlq_manager.store_event(event=dlq_event)

    payload = dao.latest.payload
    assert payload["payload_truncated"] is True
    raw = json.dumps(dlq_event.payload).encode()
    assert base64.b64decode(payload["payload_json_b64"]) == raw[:10]


@pytest.mark.parametrize(
    "errors",
    [
        (DbTimeoutError("timed out"),),
        (DaoError("connection lost"), DaoError("connection lost")),
    ],
    ids=["timeout", "degraded_copy_fails_too"],
)
@pytest.mark.asyncio
async def test_store_event_transient_error_raises(errors: tuple[Exception, ...]):
    """A timeout raises at once, and another error raises when the degraded copy
    fails as well, so the event is redelivered rather than lost.
    """
    dao = FailingDao(*errors)

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=AsyncMock(),
    ) as dlq_manager:
        with pytest.raises(dlq_manager.DLQInsertionError):
            await dlq_manager.store_event(event=utils.graph_event())

    assert not dao.resources


def wrapper_event() -> StoredDLQEvent:
    """A stored event whose payload is a subscriber's wrapper."""
    stored = stored_event_from_raw_event(utils.graph_event())
    return stored.model_copy(
        update={"payload": {"raw_value_b64": "/w==", "decode_error": "too large"}}
    )


def malformed_event() -> StoredDLQEvent:
    """A stored event of a record the subscriber could not decode."""
    stored = stored_event_from_raw_event(utils.graph_event())
    dlq_info = stored.dlq_info.model_copy(update={"exc_class": "MalformedRecordError"})
    return stored.model_copy(update={"dlq_info": dlq_info})


def degraded_event() -> StoredDLQEvent:
    """A stored event that is a degraded copy."""
    stored = stored_event_from_raw_event(utils.graph_event())
    return degraded_copy(stored, error=DaoError("too deep"))


def truncated_degraded_event() -> StoredDLQEvent:
    """A stored event that is a degraded copy with its payload cut."""
    stored = degraded_event()
    payload = {**stored.payload, "payload_truncated": True}
    return stored.model_copy(update={"payload": payload})


def unknown_service_event() -> StoredDLQEvent:
    """A stored event without a usable service name."""
    dlq_event = utils.graph_event()
    del dlq_event.headers[HeaderNames.SERVICE_NAME]
    return stored_event_from_raw_event(dlq_event)


def unknown_topic_event() -> StoredDLQEvent:
    """A stored event without a usable original topic."""
    dlq_event = utils.graph_event()
    del dlq_event.headers[HeaderNames.ORIGINAL_TOPIC]
    return stored_event_from_raw_event(dlq_event)


@pytest.mark.parametrize(
    "make_event, with_override, allowed",
    [
        (malformed_event, False, False),
        (malformed_event, True, True),
        (degraded_event, False, True),
        (degraded_event, True, True),
        (truncated_degraded_event, False, False),
        (truncated_degraded_event, True, True),
        (wrapper_event, False, False),
        (wrapper_event, True, True),
        (unknown_topic_event, False, False),
        (unknown_topic_event, True, True),
        (unknown_service_event, False, False),
        (unknown_service_event, True, False),
    ],
    ids=[
        "malformed",
        "malformed_override",
        "degraded",
        "degraded_override",
        "degraded_truncated",
        "degraded_truncated_override",
        "wrapper",
        "wrapper_override",
        "unknown_topic",
        "unknown_topic_override",
        "unknown_service",
        "unknown_service_override",
    ],
)
@pytest.mark.parametrize("dry_run", [True, False], ids=["dry_run", "real"])
@pytest.mark.asyncio
async def test_process_event_that_cannot_be_requeued_as_is(
    make_event, with_override: bool, allowed: bool, dry_run: bool
):
    """An event whose payload is not the original needs an override, one without a
    usable topic needs one that names it, and one of an unknown service can only be
    discarded. Nothing is published or deleted otherwise, in a dry run neither.
    A degraded copy that holds its whole payload is requeued with that payload.
    """
    stored = make_event()
    dao = InMemDLQEventDao()
    await dao.insert(stored)
    mock_publisher = AsyncMock()
    override = (
        EventCore(
            payload={"source_id": "a", "dest_id": "b"},
            type_=stored.type_,
            topic=utils.GRAPH_UPDATES,
            key=stored.key,
        )
        if with_override
        else None
    )

    async with prepare_core(
        config=DEFAULT_CONFIG,
        dao_override=dao,
        publisher_override=mock_publisher,
    ) as dlq_manager:
        process = dlq_manager.process_event(
            service=stored.dlq_info.service,
            topic=stored.topic,
            dlq_id=stored.dlq_id,
            override=override,
            dry_run=dry_run,
        )
        if allowed:
            await process
        else:
            with pytest.raises(dlq_manager.DLQValidationError):
                await process

    if not allowed or dry_run:
        mock_publisher.publish.assert_not_called()
        assert await dao.get_by_id(stored.dlq_id)
    else:
        mock_publisher.publish.assert_called_once()
        if make_event is degraded_event and not with_override:
            published = mock_publisher.publish.call_args.kwargs
            assert published["payload"] == utils.graph_event().payload
