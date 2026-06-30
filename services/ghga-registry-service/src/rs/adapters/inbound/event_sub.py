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

"""Inbound adapter for event subscription"""

import logging

import ghga_event_schemas.pydantic_ as event_schemas
from ghga_event_schemas.configs import FileUploadBoxEventsConfig, ResourceEventsConfig
from ghga_event_schemas.validation import (
    EventSchemaValidationError,
    get_validated_payload,
)
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import UUID4

from rs.core.models import FileUploadBox
from rs.ports.inbound.registry import RegistryPort

log = logging.getLogger(__name__)


class OutboxSubConfig(FileUploadBoxEventsConfig):
    """Configuration for subscribing to outbox events"""


class OutboxSubTranslator(DaoSubscriberProtocol):
    """Subscriber that translates inbound FileUploadBox outbox events"""

    event_topic: str
    dto_model = FileUploadBox

    def __init__(self, *, config: OutboxSubConfig, registry: RegistryPort):
        """Configure the class instance"""
        self.event_topic = config.file_upload_box_topic
        self._registry = registry

    async def changed(self, resource_id: str, update: FileUploadBox) -> None:
        """Consume an upserted FileUploadBox and update its parent ResearchDataUploadBox"""
        await self._registry.rdub_manager.upsert_file_upload_box(file_upload_box=update)

    async def deleted(self, resource_id: str) -> None:
        """Consume a FileUploadBox deletion event.

        Normally the RS itself initiates FUB deletion and removes the matching RDUB in
        the same flow. To avoid race conditions, this method merely logs.
        """
        log.info("Received 'deletion' event for FileUploadBox %s.", resource_id)


# LEGACY: Everything below subscribes to "searchable resource" events emitted by the
# metldata producer. This is a legacy concept: metldata is the current origin
# and source of truth for the studies and experimental metadata that these searchable
# resources are derived from. We add this consumer ONLY to fetch that legacy data into
# this service; the embedded studies are extracted from these resources and stored in
# the existing study DAO (see LegacyResourceManager). Once this service becomes the
# full owner and manager of studies and experimental metadata, metldata and this
# consumer become obsolete and should be removed.


class ResourceSubConfig(ResourceEventsConfig):
    """Configuration for subscribing to legacy searchable resource events.

    Reuses ResourceEventsConfig from ghga_event_schemas (exactly as metldata, the
    producer, does) so the topic and event type strings can never drift apart.
    """


class ResourceSubTranslator(EventSubscriberProtocol):
    """Consumes legacy searchable resource upsertion/deletion events.

    All resource-change events arrive on a single topic and are distinguished by their
    event type. We route on `type_` (not the event key) and validate every payload
    against the corresponding ghga_event_schemas model before handing it to the core.
    """

    def __init__(self, *, config: ResourceSubConfig, registry: RegistryPort) -> None:
        self.topics_of_interest = [config.resource_change_topic]
        self.types_of_interest = [
            config.resource_upsertion_type,
            config.resource_deletion_type,
        ]
        self._config = config
        self._registry = registry

    async def _handle_upsertion(self, *, payload: JsonObject) -> None:
        """Validate a SearchableResource payload and upsert the resource."""
        try:
            validated_payload = get_validated_payload(
                payload=payload, schema=event_schemas.SearchableResource
            )
        except EventSchemaValidationError:
            log.error(
                "Failed to validate event schema for '%s'",
                event_schemas.SearchableResource.__name__,
            )
            raise

        await self._registry.legacy_resource_manager.upsert_resource(
            resource=validated_payload
        )

    async def _handle_deletion(self, *, payload: JsonObject) -> None:
        """Validate a SearchableResourceInfo payload and delete the resource."""
        try:
            validated_payload = get_validated_payload(
                payload=payload, schema=event_schemas.SearchableResourceInfo
            )
        except EventSchemaValidationError:
            log.error(
                "Failed to validate event schema for '%s'",
                event_schemas.SearchableResourceInfo.__name__,
            )
            raise

        await self._registry.legacy_resource_manager.delete_resource(
            resource_info=validated_payload
        )

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID4,
    ) -> None:
        """Route a resource-change event to its handler based on the event type.

        Note: the event key (`dataset_embedded_{accession}`) is informational only and
        a metldata quirk - we route on `type_`, never on the key.
        """
        log.info("Received event of type '%s'", type_)
        if type_ == self._config.resource_upsertion_type:
            await self._handle_upsertion(payload=payload)
        elif type_ == self._config.resource_deletion_type:
            await self._handle_deletion(payload=payload)
        else:
            log.warning("Received unexpected event of type '%s'", type_)
