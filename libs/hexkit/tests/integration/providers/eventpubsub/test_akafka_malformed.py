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

"""Test that a malformed record written by a foreign producer does not block the
subscriber, through aiokafka's own deserializer path.
"""

import base64

import pytest
from aiokafka import AIOKafkaProducer

from hexkit.providers.akafka.provider.eventsub import HeaderNames, KafkaEventSubscriber
from hexkit.providers.akafka.testutils import (  # noqa: F401
    KafkaFixture,
    kafka_container_fixture,
    kafka_fixture,
)
from tests.integration.providers.eventpubsub.test_akafka_dlqsub import (
    TEST_EVENT,
    TEST_TOPIC,
    TEST_TYPE,
    DummyTranslator,
    make_config,
)

pytestmark = pytest.mark.asyncio()

RAW_VALUE = b"\xffnot json"


async def publish_raw_record(kafka: KafkaFixture) -> None:
    """Write a record that no hexkit publisher would write."""
    producer = AIOKafkaProducer(bootstrap_servers=",".join(kafka.config.kafka_servers))
    await producer.start()
    try:
        await producer.send_and_wait(
            TEST_TOPIC,
            key=b"k\xff",
            value=RAW_VALUE,
            headers=[("type", TEST_TYPE.encode()), ("correlation_id", b"garbage")],
        )
    finally:
        await producer.stop()


async def test_malformed_record_goes_to_dlq(kafka: KafkaFixture):
    """With the DLQ on, the malformed record goes to the DLQ and the next record is
    consumed.
    """
    await publish_raw_record(kafka)
    await kafka.publisher.publish(**TEST_EVENT.asdict())

    config = make_config(kafka.config)
    translator = DummyTranslator(
        topics_of_interest=[TEST_TOPIC], types_of_interest=[TEST_TYPE]
    )
    async with (
        kafka.record_events(
            in_topic=config.kafka_dlq_topic, capture_headers=True
        ) as recorder,
        KafkaEventSubscriber.construct(
            config=config, translator=translator, dlq_publisher=kafka.publisher
        ) as subscriber,
    ):
        await subscriber.run(forever=False)
        await subscriber.run(forever=False)

    assert len(recorder.recorded_events) == 1
    dlq_event = recorder.recorded_events[0]
    assert dlq_event.key == "k\\xff"
    assert dlq_event.type_ == TEST_TYPE
    assert base64.b64decode(str(dlq_event.payload["raw_value_b64"])) == RAW_VALUE
    headers = dlq_event.headers
    assert headers is not None
    assert headers[HeaderNames.EXC_CLASS] == "MalformedRecordError"
    assert headers[HeaderNames.ORIGINAL_TOPIC] == TEST_TOPIC

    assert [event.payload for event in translator.successes] == [TEST_EVENT.payload]


async def test_malformed_record_without_dlq(kafka: KafkaFixture):
    """With the DLQ off, the malformed record stops the subscriber and is not
    committed, so a restarted subscriber meets it again.
    """
    await publish_raw_record(kafka)

    config = make_config(kafka.config, enable_dlq=False)
    translator = DummyTranslator(
        topics_of_interest=[TEST_TOPIC], types_of_interest=[TEST_TYPE]
    )
    for _ in range(2):
        async with KafkaEventSubscriber.construct(
            config=config, translator=translator
        ) as subscriber:
            with pytest.raises(KafkaEventSubscriber.MalformedRecordError):
                await subscriber.run(forever=False)
    assert not translator.successes
