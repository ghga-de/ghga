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

"""Test how the Kafka subscriber handles records it cannot decode.

The records go through the subscriber's real deserializers into a mock consumer, and
the DLQ copies through a real publisher into a mock producer, so the tests see what
would reach the broker.
"""

import base64
import json
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid1, uuid4

import pytest
from pydantic import UUID4

from hexkit.correlation import get_correlation_id
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import DLQSubscriberProtocol, EventSubscriberProtocol
from hexkit.providers.akafka import (
    KafkaConfig,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.akafka.provider.eventsub import HeaderNames

pytestmark = pytest.mark.asyncio()

TOPIC = "test-topic"
TYPE = "test_type"
DLQ_TOPIC = "dlq"
CORRELATION_ID = UUID("7041eb31-7333-4b57-97d7-90f5562c3383")
MAX_MESSAGE_SIZE = 20_000

Outcome = Literal["consumed", "ignored", "malformed", "translator_error"]


@dataclass
class RawRecord:
    """A record as the broker holds it, before deserialization."""

    key: bytes | None = b"key1"
    value: bytes | None = b'{"field": 1}'
    headers: list[tuple[str, bytes | None]] = field(
        default_factory=lambda: [
            ("type", TYPE.encode()),
            ("event_id", str(uuid4()).encode()),
            ("correlation_id", str(CORRELATION_ID).encode()),
        ]
    )

    def with_header(self, name: str, value: bytes | None) -> "RawRecord":
        """Return a copy with the named header replaced, added, or dropped if None."""
        headers = [(k, v) for k, v in self.headers if k != name]
        if value is not None:
            headers.append((name, value))
        return RawRecord(key=self.key, value=self.value, headers=headers)


@dataclass
class Event:
    """A record as the consumer yields it."""

    topic: str
    key: Any
    value: Any
    headers: list[tuple[str, bytes | None]]
    partition: int = 0
    offset: int = 42
    timestamp: int = 1_700_000_000_000


class RecordingTranslator(EventSubscriberProtocol):
    """Records the events it receives and can fail with a given error."""

    def __init__(self, *, error: Exception | None = None):
        self.topics_of_interest = [TOPIC]
        self.types_of_interest = [TYPE]
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID4,
    ) -> None:
        self.calls.append(
            {
                "payload": payload,
                "key": key,
                "correlation_id": get_correlation_id(),
            }
        )
        if self.error:
            raise self.error


@dataclass
class RunResult:
    """What one `run(forever=False)` did."""

    translator: RecordingTranslator
    consumer: AsyncMock
    producer: AsyncMock
    error: Exception | None

    @property
    def committed(self) -> bool:
        """Whether the run committed the offset."""
        return self.consumer.commit.await_count == 1

    @property
    def dlq_publish(self) -> dict[str, Any] | None:
        """The kwargs of the DLQ publish, with the headers as a dict, if any."""
        if not self.producer.send_and_wait.await_count:
            return None
        call = self.producer.send_and_wait.await_args
        assert call.args == (DLQ_TOPIC,)
        return {
            **call.kwargs,
            "headers": {k: v.decode("ascii") for k, v in call.kwargs["headers"]},
        }


async def run_once(
    record: RawRecord, *, enable_dlq: bool, translator: RecordingTranslator
) -> RunResult:
    """Feed one raw record to a subscriber and run it once."""
    config = KafkaConfig(
        service_name="test-service",
        service_instance_id="1",
        kafka_servers=["my-fake-kafka-server"],
        kafka_enable_dlq=enable_dlq,
        kafka_max_message_size=MAX_MESSAGE_SIZE,
        # the subscriber must set a correlation ID before it publishes to the DLQ
        generate_correlation_id=False,
    )
    consumer = AsyncMock()
    consumer_cls = Mock(return_value=consumer)
    producer = AsyncMock()
    error: Exception | None = None

    async with (
        KafkaEventPublisher.construct(
            config=config, kafka_producer_cls=Mock(return_value=producer)
        ) as publisher,
        KafkaEventSubscriber.construct(
            config=config,
            translator=translator,
            kafka_consumer_cls=consumer_cls,
            dlq_publisher=publisher,
        ) as subscriber,
    ):
        kwargs = consumer_cls.call_args.kwargs
        consumer.__anext__.return_value = Event(
            topic=TOPIC,
            key=kwargs["key_deserializer"](record.key),
            value=kwargs["value_deserializer"](record.value),
            headers=record.headers,
        )
        try:
            await subscriber.run(forever=False)
        except Exception as err:
            error = err

    return RunResult(
        translator=translator, consumer=consumer, producer=producer, error=error
    )


VALID = RawRecord()
LARGE_GARBAGE = bytes(range(256)) * (MAX_MESSAGE_SIZE // 256)

CASES: list[tuple[str, RawRecord, Outcome]] = [
    ("valid", VALID, "consumed"),
    ("non_ascii_key", RawRecord(key="schlüssel".encode()), "malformed"),
    ("invalid_utf8_key", RawRecord(key=b"\xff\xfe"), "malformed"),
    ("null_key", RawRecord(key=None), "consumed"),
    ("non_ascii_header", VALID.with_header("x-note", "Grüße".encode()), "consumed"),
    ("invalid_utf8_header", VALID.with_header("x-note", b"\xff"), "consumed"),
    ("null_header", VALID.with_header("x-note", None), "consumed"),
    ("non_ascii_value", RawRecord(value='{"name": "Jürgen"}'.encode()), "consumed"),
    ("invalid_utf8_value", RawRecord(value=b'{"name": "\xff"}'), "malformed"),
    ("non_json_value", RawRecord(value=b"hello"), "malformed"),
    ("empty_value", RawRecord(value=b""), "malformed"),
    ("json_array_value", RawRecord(value=b"[1, 2]"), "malformed"),
    ("json_null_value", RawRecord(value=b"null"), "malformed"),
    ("tombstone", RawRecord(value=None), "malformed"),
    ("oversized_value", RawRecord(value=LARGE_GARBAGE), "malformed"),
    ("uuid1_correlation_id", VALID.with_header("correlation_id", str(uuid1()).encode()), "consumed"),
    ("garbage_correlation_id", VALID.with_header("correlation_id", b"not-a-uuid"), "consumed"),
    ("invalid_utf8_correlation_id", VALID.with_header("correlation_id", b"\xff"), "consumed"),
    ("missing_correlation_id", VALID.with_header("correlation_id", None), "consumed"),
    ("missing_type", VALID.with_header("type", None), "ignored"),
    ("non_ascii_type", VALID.with_header("type", "tÿpe".encode()), "ignored"),
    ("invalid_utf8_type", VALID.with_header("type", b"\xff"), "ignored"),
    ("garbage_event_id", VALID.with_header("event_id", b"\xffnope"), "consumed"),
]  # fmt: skip


@pytest.mark.parametrize("enable_dlq", [True, False], ids=["dlq_on", "dlq_off"])
@pytest.mark.parametrize(
    "record, outcome", [case[1:] for case in CASES], ids=[case[0] for case in CASES]
)
async def test_malformed_record(record: RawRecord, outcome: Outcome, enable_dlq: bool):
    """Each record is consumed, ignored, sent to the DLQ or, with the DLQ off,
    stops the consumer with a malformed-record error; nothing else escapes.
    """
    result = await run_once(
        record, enable_dlq=enable_dlq, translator=RecordingTranslator()
    )

    if outcome == "malformed" and not enable_dlq:
        assert isinstance(result.error, KafkaEventSubscriber.MalformedRecordError)
        assert not result.committed
        assert not result.translator.calls
        return

    assert result.error is None
    assert result.committed
    assert len(result.translator.calls) == (outcome == "consumed")

    if outcome == "consumed":
        assert result.dlq_publish is None
        call = result.translator.calls[0]
        assert call["payload"] == json.loads(record.value)  # type: ignore[arg-type]
        assert call["key"] == (record.key or b"").decode("ascii")
        header_cid = dict(record.headers).get("correlation_id")
        if header_cid == str(CORRELATION_ID).encode():
            assert call["correlation_id"] == CORRELATION_ID
        else:
            assert call["correlation_id"].version == 4
            assert call["correlation_id"] != CORRELATION_ID
    elif outcome == "ignored":
        assert result.dlq_publish is None
    else:
        assert_dlq_copy(record, result)


def assert_dlq_copy(record: RawRecord, result: RunResult) -> None:
    """Check the DLQ copy of a malformed record."""
    published = result.dlq_publish
    assert published is not None
    headers = published["headers"]
    assert headers[HeaderNames.EXC_CLASS] == "MalformedRecordError"
    assert headers[HeaderNames.ORIGINAL_TOPIC] == TOPIC
    assert headers["type"] == TYPE
    UUID(headers[HeaderNames.CORRELATION_ID])  # the context ID, valid

    key = published["key"]
    assert key.isascii()
    if record.key is not None and not record.key.isascii():
        assert key == record.key.decode("ascii", errors="backslashreplace")

    serialized = KafkaEventPublisher._default_event_value_serializer(published["value"])
    assert len(serialized) + len(key) < MAX_MESSAGE_SIZE

    payload = published["value"]
    not_json = object()
    try:
        original = json.loads(record.value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        original = not_json
    if isinstance(original, dict):
        assert payload == original  # only the key was malformed
    elif original is not not_json:
        assert payload == {"non_object_value": original}
    elif record.value is None:
        assert payload["raw_value_b64"] is None
        assert "tombstone" in payload["decode_error"]
    else:
        raw = base64.b64decode(payload["raw_value_b64"])
        assert payload["decode_error"]
        if payload.get("raw_value_truncated"):
            assert record.value.startswith(raw)
            assert len(raw) < len(record.value)
        else:
            assert raw == record.value


@pytest.mark.parametrize("enable_dlq", [True, False], ids=["dlq_on", "dlq_off"])
async def test_translator_error_with_non_ascii_message(enable_dlq: bool):
    """A translator error that echoes a non-ASCII value reaches the DLQ escaped."""
    error = ValueError("unexpected name 'Jürgen' " + "x" * 2000)
    result = await run_once(
        RawRecord(value='{"name": "Jürgen"}'.encode()),
        enable_dlq=enable_dlq,
        translator=RecordingTranslator(error=error),
    )
    if not enable_dlq:
        assert result.error is error
        assert not result.committed
        return
    assert result.error is None
    assert result.committed
    published = result.dlq_publish
    assert published is not None
    exc_msg = published["headers"][HeaderNames.EXC_MSG]
    assert exc_msg.startswith("unexpected name 'J\\xfcrgen'")
    assert len(exc_msg) == 1000
    assert published["value"] == {"name": "Jürgen"}


def mutate(record: RawRecord, rng: random.Random) -> RawRecord:
    """Return a copy of the record with one random part damaged."""

    def damage(data: bytes | None) -> bytes | None:
        if data is None or rng.random() < 0.1:
            return None if rng.random() < 0.5 else rng.randbytes(rng.randint(0, 20))
        buf = bytearray(data)
        for _ in range(rng.randint(1, 4)):
            choice = rng.random()
            pos = rng.randint(0, len(buf))
            if choice < 0.4 and buf:
                buf[min(pos, len(buf) - 1)] = rng.randint(0, 255)
            elif choice < 0.7:
                buf[pos:pos] = rng.randbytes(rng.randint(1, 3))
            else:
                del buf[pos:]
        return bytes(buf)

    part = rng.choice(["key", "value", "header"])
    if part == "key":
        return RawRecord(key=damage(record.key), value=record.value)
    if part == "value":
        return RawRecord(key=record.key, value=damage(record.value))
    name = rng.choice(["type", "event_id", "correlation_id"])
    return record.with_header(name, damage(dict(record.headers)[name]))


@pytest.mark.parametrize("enable_dlq", [True, False], ids=["dlq_on", "dlq_off"])
async def test_fuzzed_records(enable_dlq: bool):
    """Random damage to a valid record never escapes as anything but a
    malformed-record error, and only with the DLQ off.
    """
    rng = random.Random(4711)
    seen: set[str] = set()
    for _ in range(200):
        record = mutate(VALID, rng)
        result = await run_once(
            record, enable_dlq=enable_dlq, translator=RecordingTranslator()
        )
        if result.error is not None:
            assert not enable_dlq, record
            assert isinstance(
                result.error, KafkaEventSubscriber.MalformedRecordError
            ), record
            assert not result.committed
            seen.add("raised")
        else:
            assert result.committed, record
            if result.translator.calls:
                seen.add("consumed")
            elif result.dlq_publish:
                seen.add("dlq")
            else:
                seen.add("ignored")
    # the seed must reach every path, or the loop proves little
    expected = {"consumed", "ignored", "dlq" if enable_dlq else "raised"}
    assert seen == expected


class RecordingDLQTranslator(DLQSubscriberProtocol):
    """Records the events it receives from the DLQ topic."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID4,
        timestamp: datetime,
        headers: Mapping[str, str],
    ) -> None:
        self.calls.append(
            {"payload": payload, "key": key, "timestamp": timestamp, "headers": headers}
        )


async def test_dlq_subscriber_gets_wrapper():
    """A subscriber on the DLQ topic cannot route to a DLQ, so it passes a malformed
    record to its translator wrapped, and copes with an out-of-range timestamp.
    """
    config = KafkaConfig(
        service_name="dlqs",
        service_instance_id="1",
        kafka_servers=["my-fake-kafka-server"],
    )
    consumer = AsyncMock()
    consumer_cls = Mock(return_value=consumer)
    translator = RecordingDLQTranslator()
    async with KafkaEventSubscriber.construct(
        config=config, translator=translator, kafka_consumer_cls=consumer_cls
    ) as subscriber:
        kwargs = consumer_cls.call_args.kwargs
        record = RawRecord(key=b"k\xff", value=b"\x00garbage").with_header(
            "correlation_id", None
        )
        consumer.__anext__.return_value = Event(
            topic=DLQ_TOPIC,
            key=kwargs["key_deserializer"](record.key),
            value=kwargs["value_deserializer"](record.value),
            headers=record.headers,
            timestamp=10**18,
        )
        await subscriber.run(forever=False)

    consumer.commit.assert_awaited_once()
    assert len(translator.calls) == 1
    call = translator.calls[0]
    assert call["key"] == "k\\xff"
    assert base64.b64decode(call["payload"]["raw_value_b64"]) == b"\x00garbage"
    assert isinstance(call["timestamp"], datetime)
    UUID(call["headers"][HeaderNames.CORRELATION_ID])  # replaced, so it is valid
