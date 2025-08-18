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
#

"""Event subscriber for dataset deletion events."""

from ghga_event_schemas.configs import DatasetEventsConfig
from ghga_event_schemas.pydantic_ import MetadataDatasetID
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import UUID4

from auth_service.constants import TRACER

from ..ports.deletion import DatasetDeletionPort


class EventSubTranslatorConfig(DatasetEventsConfig):
    """Configuration for the event subscriber.

    This is only used to remove access grants for datasets
    which have been deleted.
    """


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume dataset deletion events"""

    def __init__(
        self, *, config: EventSubTranslatorConfig, handler: DatasetDeletionPort
    ):
        """Initialize the translator."""
        self.topics_of_interest = [config.dataset_change_topic]
        self.types_of_interest = [config.dataset_deletion_type]
        self._config = config
        self._handler = handler

    @TRACER.start_as_current_span("EventSubTranslator._consume_validated")
    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID4,
    ) -> None:
        """Consume an event which concerns the deletion of a dataset."""
        dataset = get_validated_payload(payload=payload, schema=MetadataDatasetID)
        await self._handler.handle_dataset_deletion(dataset_id=dataset.accession)
