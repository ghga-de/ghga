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

"""Event subscriber logic"""

import logging
from uuid import UUID

from ghga_event_schemas.configs import FileUploadEventsConfig
from hexkit.protocols.daosub import DaoSubscriberProtocol

from fis.core.models import FileUnderInterrogation
from fis.ports.inbound.interrogation import InterrogationHandlerPort

log = logging.getLogger(__name__)


class OutboxSubConfig(FileUploadEventsConfig):
    """Config for the outbox subscriber"""


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
        await self._interrogation_handler.ack_file_cancellation(file_id=file_id)
