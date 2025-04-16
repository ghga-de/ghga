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
"""Contains implementation of the EventsHandler class."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aiokafka import TopicPartition
from aiokafka.admin import AIOKafkaAdminClient, RecordsToDelete
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.providers.akafka.provider.utils import generate_ssl_context

from sms.config import Config
from sms.models import EventDetails
from sms.ports.inbound.events_handler import EventsHandlerPort


class EventsHandler(EventsHandlerPort):
    """A class to manage the state of kafka events."""

    def __init__(self, *, config: Config, event_publisher: EventPublisherProtocol):
        self._config = config
        self._event_publisher = event_publisher

    @asynccontextmanager
    async def get_admin_client(self) -> AsyncGenerator[AIOKafkaAdminClient, None]:
        """Construct and return an instance of AIOKafkaAdminClient that is closed after use."""
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self._config.kafka_servers,
            security_protocol=self._config.kafka_security_protocol,
            ssl_context=generate_ssl_context(self._config),
        )
        await admin_client.start()
        try:
            yield admin_client
        finally:
            await admin_client.close()

    async def clear_topics(self, *, topics: list[str], exclude_internal: bool = True):
        """Clear messages from given topic(s).

        If no topics are specified, all topics will be cleared, except internal topics
        unless otherwise specified.
        """
        async with self.get_admin_client() as admin_client:
            if not topics:
                topics = await admin_client.list_topics()
            if exclude_internal:
                topics = [topic for topic in topics if not topic.startswith("__")]
            topics_info = await admin_client.describe_topics(topics)
            records_to_delete = {
                TopicPartition(
                    topic=topic_info["topic"], partition=partition_info["partition"]
                ): RecordsToDelete(before_offset=-1)
                for topic_info in topics_info
                for partition_info in topic_info["partitions"]
            }
            await admin_client.delete_records(records_to_delete, timeout_ms=10000)

    async def publish_event(self, *, event_details: EventDetails):
        """Publish a single event to the given topic.

        Raises a `PublishError` if there's an problem with the publishing operation.
        """
        try:
            await self._event_publisher.publish(
                payload=event_details.payload,
                type_=event_details.type_,
                topic=event_details.topic,
                key=event_details.key,
                headers=event_details.headers,
            )
        except Exception as exc:
            raise self.PublishError(event_details=event_details) from exc
