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

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from aiokafka import TopicPartition
from aiokafka.admin import AIOKafkaAdminClient, RecordsToDelete
from aiokafka.admin.config_resource import ConfigResource, ConfigResourceType
from hexkit.protocols.eventpub import EventPublisherProtocol

from sms.config import Config
from sms.models import EventDetails
from sms.ports.inbound.events_handler import EventsHandlerPort


class EventsHandler(EventsHandlerPort):
    """A class to manage the state of kafka events."""

    def __init__(self, *, config: Config, event_publisher: EventPublisherProtocol):
        self._config = config
        self._event_publisher = event_publisher
        self._admin_client: AIOKafkaAdminClient | None = None

    @asynccontextmanager
    async def get_admin_client(self):
        """An async context manager that provides a running AIOKafkaAdminClient
        as a singleton instance.

        If a running client already exists, it is yielded directly.
        If not, this is considered the root use of the CM, so we start a new client,
        yield it, then close the client within a `finally` block.
        """
        if self._admin_client:
            yield self._admin_client
            return

        # No running client exists, so create one and make sure to clean up afterward.
        self._admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self._config.kafka_servers
        )
        await self._admin_client.start()
        try:
            yield self._admin_client
        finally:
            await self._admin_client.close()
            self._admin_client = None

    async def _get_cleanup_policy(self, *, topic: str) -> str | None:
        """Get the current cleanup policy for a topic or None if the topic doesn't exist"""
        return await self._get_topic_config(topic=topic, config_name="cleanup.policy")

    async def _get_topic_config(self, *, topic: str, config_name: str) -> str | None:
        """Get the current config for a topic or None if the topic/config doesn't exist"""
        async with self.get_admin_client() as admin_client:
            # fetch a list containing a response for each requested topic
            config_list = await admin_client.describe_configs(
                [ConfigResource(ConfigResourceType.TOPIC, name=topic)]
            )

        # We only requested one topic, so get the first/only element from the list
        config_response = config_list[0]

        # Each config response has a 'resources' attribute
        resources = config_response.resources

        # The resources attr is a list containing one tuple for each requested topic.
        #  We only requested one topic, so our target is the first element.
        requested_resource = resources[0]

        # The resource itself is a list, and the topic config is at the end
        configs = requested_resource[-1]
        value = None
        config_name = config_name.lower()

        # The `configs` item is a list of tuples, where each tuple is a config item
        # The first item is the config name, the second is the value, and the rest are ancillary
        for item in configs:
            if item[0].lower() == config_name:
                value = item[1]
                break
        return value

    async def _set_cleanup_policy(self, *, topic: str, policy: str):
        """Set the cleanup policy for the given topic. The topic must already exist."""
        await self._set_topic_config(topic=topic, config={"cleanup.policy": policy})

    async def _set_topic_config(self, *, topic: str, config: dict[str, Any]):
        """Set an arbitrary config value(s) for a topic"""
        async with self.get_admin_client() as admin_client:
            await admin_client.alter_configs(
                config_resources=[
                    ConfigResource(
                        ConfigResourceType.TOPIC,
                        name=topic,
                        configs=config,
                    )
                ]
            )

    async def clear_topics(self, *, topics: list[str], exclude_internal: bool = True):
        """Clear messages from given topic(s).

        If no topics are specified, all topics will be cleared, except internal topics
        unless otherwise specified.

        To enable topic clearing for compacted topics, the cleanup policy is temporarily
        set to 'delete' while the action is performed. Afterward, the policy is set to
        its original value (either 'compact' or 'compact,delete').
        """
        async with self.get_admin_client() as admin_client:
            available_topics = await admin_client.list_topics()
            if not topics:
                topics = available_topics
            elif isinstance(topics, str):
                topics = [topics]
            if exclude_internal:
                topics = [topic for topic in topics if not topic.startswith("__")]

            # Filter out any topics that don't exist
            topics = [topic for topic in topics if topic in available_topics]
            if not topics:
                return

            # Record the current cleanup policies before modifying them
            topics_info = await admin_client.describe_topics(topics)
            for topic_info in topics_info:
                topic = topic_info["topic"]
                original_policy = await self._get_cleanup_policy(topic=topic)
                if original_policy and "compact" in original_policy.split(","):
                    await self._set_cleanup_policy(topic=topic, policy="delete")
                    await asyncio.sleep(0.2)  # brief pause to wait for policy changes
                else:
                    original_policy = None  # don't need to revert 'delete' topics

                records_to_delete = {
                    TopicPartition(
                        topic=topic, partition=partition_info["partition"]
                    ): RecordsToDelete(before_offset=-1)
                    for partition_info in topic_info["partitions"]
                }

                # Delete any events in the topic
                try:
                    await admin_client.delete_records(
                        records_to_delete, timeout_ms=10000
                    )
                finally:
                    # Always set compacted topics back to their original policy
                    if original_policy:
                        await self._set_cleanup_policy(
                            topic=topic, policy=original_policy
                        )

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
                event_id=event_details.event_id,
                headers=event_details.headers,
            )
        except Exception as exc:
            raise self.PublishError(event_details=event_details) from exc
