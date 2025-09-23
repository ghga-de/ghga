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
"""Event subscriber configuration and class"""

from uuid import UUID

from ghga_event_schemas.configs import FileUploadReportEventsConfig
from ghga_event_schemas.pydantic_ import FileUploadReport
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from ucs.ports.inbound.controller import UploadControllerPort


class EventSubConfig(FileUploadReportEventsConfig):
    """Event sub translator configuration"""


class EventSubTranslator(EventSubscriberProtocol):
    """An event subscriber translator class"""

    topics_of_interest: list[str]
    types_of_interest: list[str]

    def __init__(
        self, *, config: EventSubConfig, upload_controller: UploadControllerPort
    ):
        """Configure the translator"""
        self.topics_of_interest = [config.file_upload_reports_topic]
        self.types_of_interest = [config.file_upload_reports_type]
        self._upload_controller = upload_controller

    async def _consume_new_report(self, *, payload: JsonObject):
        """Consume a new FileUploadReport"""
        validated_payload = get_validated_payload(payload, FileUploadReport)
        await self._upload_controller.process_file_upload_report(
            file_upload_report=validated_payload
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: str, topic: str, key: str, event_id: UUID
    ) -> None:
        await self._consume_new_report(payload=payload)
