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

"""Event subscriber logic"""

import logging
from uuid import UUID

from fis.core.models import (
    FileUnderInterrogation,
    UploadBoxPriority,
    UploadBoxPriorityEntry,
)
from fis.ports.inbound.interrogation import InterrogationHandlerPort
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    FileUploadEventsConfig,
    UploadBoxPriorityEventsConfig,
)
from hexkit.protocols.daosub import DaoSubscriberProtocol

log = logging.getLogger(__name__)


class OutboxSubConfig(FileUploadEventsConfig, UploadBoxPriorityEventsConfig):
    """Config for the outbox subscribers"""


class OutboxSubTranslator(DaoSubscriberProtocol):
    """Translator class for outbox-pattern event subscription.

    Though the published events actually conform to the `FileUpload` schema, FIS
    is only interested in the subset of fields which conform to the
    `FileUnderInterrogation` model.
    """

    event_topic: str
    dto_model = FileUnderInterrogation

    def __init__(
        self,
        *,
        config: OutboxSubConfig,
        interrogation_handler: InterrogationHandlerPort,
    ):
        self._config = config
        self._interrogation_handler = interrogation_handler
        self.event_topic = config.file_upload_topic

    async def changed(self, resource_id: str, update: FileUnderInterrogation) -> None:
        """Consume change event (created or updated) for FileUpload data."""
        await self._interrogation_handler.process_file_upload(file=update)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the cancellation or removal of a FileUpload."""
        file_id = UUID(resource_id)  # this ID is canonically a UUID4
        await self._interrogation_handler.delete_file(file_id=file_id)


class UploadBoxPrioritySubTranslator(DaoSubscriberProtocol):
    """Translator class for the upload box priority list, which RS publishes via
    the outbox.

    FIS knows only file upload boxes, so it keeps just their IDs, as `box_id`.
    """

    event_topic: str
    dto_model = event_schemas.UploadBoxPriority

    def __init__(
        self,
        *,
        config: OutboxSubConfig,
        interrogation_handler: InterrogationHandlerPort,
    ):
        self._config = config
        self._interrogation_handler = interrogation_handler
        self.event_topic = config.upload_box_priority_topic

    async def changed(
        self, resource_id: str, update: event_schemas.UploadBoxPriority
    ) -> None:
        """Consume change event for the upload box priority list."""
        priority = UploadBoxPriority(
            id=update.id,
            version=update.version,
            entries=[
                UploadBoxPriorityEntry(box_id=entry.file_upload_box_id)
                for entry in update.entries
            ],
        )
        await self._interrogation_handler.store_upload_box_priority(priority=priority)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the removal of the upload box priority list."""
        await self._interrogation_handler.clear_upload_box_priority(
            priority_id=resource_id
        )
