# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Adapter for publishing events to other services."""

import json

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from pcs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(BaseSettings):
    """Config for publishing file deletion related events."""

    files_to_delete_topic: str = Field(
        ...,
        description="The name of the topic to receive events informing about files to delete.",
        examples=["file_deletions"],
    )
    files_to_delete_type: str = Field(
        ...,
        description="The type used for events informing about a file to be deleted.",
        examples=["file_deletion_requested"],
    )


class EventPubTranslator(EventPublisherPort):
    """A translator according to  the triple hexagonal architecture implementing
    the EventPublisherPort.
    """

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with configs and a provider of the EventPublisherProtocol."""
        self._config = config
        self._provider = provider

    async def delete_file(self, *, file_id: str) -> None:
        """Communicate the event that a file needs to be deleted."""
        payload = event_schemas.FileDeletionRequested(file_id=file_id)
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.files_to_delete_type,
            topic=self._config.files_to_delete_topic,
            key=file_id,
        )
