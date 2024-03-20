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

"""Translators that target the event publishing protocol."""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.custom_types import JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from ars.core import models
from ars.ports.outbound.event_pub import EventPublisherPort

__all__ = ["EventPubTranslatorConfig", "EventPubTranslator"]


class EventPubTranslatorConfig(BaseSettings):
    """Config for the event pub translator"""

    access_request_events_topic: str = Field(
        default=...,
        description="The topic used for events related to access requests.",
        examples=["access_requests"],
    )
    access_request_created_event_type: str = Field(
        default=...,
        description="The type to use for 'access request created' events",
        examples=["access_request_created"],
    )
    access_request_allowed_event_type: str = Field(
        default=...,
        description="The type to use for 'access request allowed' events",
        examples=["access_request_allowed"],
    )
    access_request_denied_event_type: str = Field(
        default=...,
        description="The type to use for 'access request denied' events",
        examples=["access_request_denied"],
    )


class EventPubTranslator(EventPublisherPort):
    """Translator from EventPublisherPort to EventPublisherProtocol."""

    def __init__(
        self,
        *,
        config: EventPubTranslatorConfig,
        event_publisher: EventPublisherProtocol,
    ):
        """Initialize with config and a provider of the EventPublisherProtocol."""
        self._config = config
        self._event_publisher = event_publisher

    async def _publish_access_request_event(
        self, *, request: models.AccessRequest, type_: str
    ) -> None:
        """Publish an access request-related event with the given details and type."""
        payload: JsonObject = event_schemas.AccessRequestDetails(
            user_id=request.user_id, dataset_id=request.dataset_id
        ).model_dump()

        await self._event_publisher.publish(
            payload=payload,
            type_=type_,
            key=request.user_id,
            topic=self._config.access_request_events_topic,
        )

    async def publish_request_allowed(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was allowed."""
        await self._publish_access_request_event(
            request=request,
            type_=self._config.access_request_allowed_event_type,
        )

    async def publish_request_created(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was created."""
        await self._publish_access_request_event(
            request=request,
            type_=self._config.access_request_created_event_type,
        )

    async def publish_request_denied(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was denied."""
        await self._publish_access_request_event(
            request=request,
            type_=self._config.access_request_denied_event_type,
        )
