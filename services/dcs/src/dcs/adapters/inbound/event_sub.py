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

"""Adapter for receiving events providing metadata on files"""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from dcs.core import models
from dcs.ports.inbound.data_repository import DataRepositoryPort


class EventSubTranslatorConfig(BaseSettings):
    """Config for receiving events providing metadata on files."""

    files_to_register_topic: str = Field(
        ...,
        description=(
            "The name of the topic to receive events informing about new files that shall"
            + " be made available for download."
        ),
        examples=["internal_file_registry"],
    )
    files_to_register_type: str = Field(
        ...,
        description=(
            "The type used for events informing about new files that shall"
            + " be made available for download."
        ),
        examples=["file_registered"],
    )

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


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received new files to register as DRS objects.
    """

    def __init__(
        self,
        config: EventSubTranslatorConfig,
        data_repository: DataRepositoryPort,
    ):
        """Initialize with config parameters and core dependencies."""
        self.topics_of_interest = [config.files_to_register_topic]
        self.types_of_interest = [config.files_to_register_type]

        self._data_repository = data_repository
        self._config = config

    async def _consume_files_to_register(self, *, payload: JsonObject) -> None:
        """Consume file registration events."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.FileInternallyRegistered
        )

        file = models.DrsObjectBase(
            file_id=validated_payload.file_id,
            decryption_secret_id=validated_payload.decryption_secret_id,
            decrypted_sha256=validated_payload.decrypted_sha256,
            decrypted_size=validated_payload.decrypted_size,
            creation_date=validated_payload.upload_date,
            s3_endpoint_alias=validated_payload.s3_endpoint_alias,
        )

        await self._data_repository.register_new_file(file=file)

    async def _consume_file_deletions(self, *, payload: JsonObject) -> None:
        """Consume file deletion events."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.FileDeletionRequested
        )

        await self._data_repository.delete_file(
            file_id=validated_payload.file_id,
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii, key: str
    ) -> None:
        """Consume events from the topics of interest."""
        if type_ == self._config.files_to_register_type:
            await self._consume_files_to_register(payload=payload)
        elif type_ == self._config.files_to_delete_type:
            await self._consume_file_deletions(payload=payload)
        else:
            raise RuntimeError(f"Unexpected event of type: {type_}")
