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

"""Kafka-based event publishing adapters and the exception they may throw."""

import json

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import FileDeletedEventsConfig
from hexkit.protocols.eventpub import EventPublisherProtocol

from ucs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(FileDeletedEventsConfig):
    """Config for publishing file upload-related events."""


class EventPubTranslator(EventPublisherPort):
    """A translator (according to the triple hexagonal architecture) for publishing
    events using the EventPublisherProtocol.
    """

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with a suitable protocol provider."""
        self._config = config
        self._provider = provider

    async def publish_deletion_successful(self, *, file_id: str) -> None:
        """Publish event informing that deletion of data and metadata for the given file ID has succeeded."""
        event_payload = event_schemas.FileDeletionSuccess(file_id=file_id)

        await self._provider.publish(
            payload=json.loads(event_payload.model_dump_json()),
            type_=self._config.file_deleted_type,
            topic=self._config.file_deleted_topic,
            key=file_id,
        )
