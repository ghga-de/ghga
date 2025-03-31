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
"""Event pub translator implementation for publishing FileDeletionRequested events."""

from ghga_event_schemas.configs import FileDeletionRequestEventsConfig
from ghga_event_schemas.pydantic_ import FileDeletionRequested
from hexkit.protocols.eventpub import EventPublisherProtocol

from pcs.ports.outbound.event_pub import EventPubTranslatorPort

__all__ = ["EventPubTranslator", "EventPubTranslatorConfig"]


class EventPubTranslatorConfig(FileDeletionRequestEventsConfig):
    """Configuration for publishing events"""


class EventPubTranslator(EventPubTranslatorPort):
    """A translator that handles publishing FileDeletionRequested events."""

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with the provider for the event publisher."""
        self._provider = provider
        self._config = config

    async def translate_file_deletion(
        self, *, file_deletion_request: FileDeletionRequested
    ):
        """Translate a file deletion request into an event."""
        payload = file_deletion_request.model_dump()
        await self._provider.publish(
            payload=payload,
            topic=self._config.file_deletion_request_topic,
            type_=self._config.file_deletion_request_type,
            key=file_deletion_request.file_id,
        )
