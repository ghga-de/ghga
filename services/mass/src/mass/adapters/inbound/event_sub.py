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

"""Event subscriber details for searchable resource events"""

import logging

import ghga_event_schemas.pydantic_ as event_schemas
from ghga_event_schemas.configs import ResourceEventsConfig
from ghga_event_schemas.validation import (
    EventSchemaValidationError,
    get_validated_payload,
)
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from mass.core.models import Resource
from mass.ports.inbound.query_handler import QueryHandlerPort

CLASS_NOT_CONFIGURED_LOG_MSG = "Class with name %s not configured."

DELETION_FAILED_LOG_MSG = (
    "Failed to delete resource with ID '%s' because "
    + "no match was found in the database."
)
SCHEMA_VALIDATION_ERROR_LOG_MSG = "Failed to validate event schema for '%s'"

EVENT_RECEIVED_LOG_MESSAGE = "Received event of type '%s'"
UNEXPECTED_EVENT_LOG_MESSAGE = "Received unexpected event of type '%s'"

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(ResourceEventsConfig):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume events regarding searchable resources"""

    def __init__(
        self, *, config: EventSubTranslatorConfig, query_handler: QueryHandlerPort
    ):
        self.topics_of_interest = [config.resource_change_topic]
        self.types_of_interest = [
            config.resource_deletion_type,
            config.resource_upsertion_type,
        ]
        self._config = config
        self._query_handler = query_handler

    async def _handle_deletion(self, *, payload: JsonObject):
        """Delete the specified resource.

        Validates the schema, then makes a call to the query handler with the payload.
        If there's an error during schema validation, we're done (log and exit func).
        """
        try:
            validated_payload = get_validated_payload(
                payload=payload, schema=event_schemas.SearchableResourceInfo
            )
            await self._query_handler.delete_resource(
                resource_id=validated_payload.accession,
                class_name=validated_payload.class_name,
            )
        except EventSchemaValidationError:
            log.error(
                SCHEMA_VALIDATION_ERROR_LOG_MSG,
                event_schemas.SearchableResourceInfo.__name__,
            )
            raise
        except self._query_handler.ResourceNotFoundError:
            log.warning(DELETION_FAILED_LOG_MSG, validated_payload.accession)
            raise
        except self._query_handler.ClassNotConfiguredError:
            log.error(CLASS_NOT_CONFIGURED_LOG_MSG, validated_payload.class_name)
            raise

    async def _handle_upsertion(self, *, payload: JsonObject):
        """Load the specified resource.

        Validates the schema, then makes a call to the query handler with the payload.
        If there's an error during schema validation, we're done (log and exit func).
        """
        try:
            validated_payload = get_validated_payload(
                payload=payload, schema=event_schemas.SearchableResource
            )
            resource = Resource(
                id_=validated_payload.accession,
                content=validated_payload.content,
            )
            await self._query_handler.load_resource(
                resource=resource,
                class_name=validated_payload.class_name,
            )
        except EventSchemaValidationError:
            log.error(
                SCHEMA_VALIDATION_ERROR_LOG_MSG,
                event_schemas.SearchableResource.__name__,
            )
            raise
        except self._query_handler.ClassNotConfiguredError:
            log.error(CLASS_NOT_CONFIGURED_LOG_MSG, validated_payload.class_name)
            raise

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
    ) -> None:
        """Consumes an event"""
        log.info(EVENT_RECEIVED_LOG_MESSAGE, type)
        if type_ == self._config.resource_deletion_type:
            await self._handle_deletion(payload=payload)
        elif type_ == self._config.resource_upsertion_type:
            await self._handle_upsertion(payload=payload)
        else:
            log.warning(UNEXPECTED_EVENT_LOG_MESSAGE, type)
