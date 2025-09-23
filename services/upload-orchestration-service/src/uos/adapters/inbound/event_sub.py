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

"""Inbound adapter for event subscription"""

import logging

from ghga_event_schemas.configs import FileUploadBoxEventsConfig
from ghga_event_schemas.pydantic_ import FileUploadBox
from hexkit.protocols.daosub import DaoSubscriberProtocol

from uos.ports.inbound.orchestrator import UploadOrchestratorPort

log = logging.getLogger(__name__)


class OutboxSubConfig(FileUploadBoxEventsConfig):
    """Configuration for subscribing to outbox events"""


class OutboxSubTranslator(DaoSubscriberProtocol):
    """Subscriber that translates inbound FileUploadBox outbox events"""

    event_topic: str
    dto_model = FileUploadBox

    def __init__(
        self, *, config: OutboxSubConfig, upload_orchestrator: UploadOrchestratorPort
    ):
        """Configure the class instance"""
        self.event_topic = config.file_upload_box_topic
        self._upload_orchestrator = upload_orchestrator

    async def changed(self, resource_id: str, update: FileUploadBox) -> None:
        """Consume an upserted FileUploadBox and update its parent ResearchDataUploadBox"""
        await self._upload_orchestrator.upsert_file_upload_box(file_upload_box=update)

    async def deleted(self, resource_id: str) -> None:
        """Consume a deleted FileUploadBox event -- these don't exist and are ignored"""
        log.warning(
            "Encountered 'deleted' event for FileUploadBox %s. Ignoring.", resource_id
        )
