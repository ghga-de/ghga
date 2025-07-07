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

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs.stateful import ArtifactEventsConfig
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from rts.models import StudyMetadata
from rts.ports.inbound.rev_tran import ReverseTranspilerPort

__all__ = ["EventSubTranslator", "EventSubTranslatorConfig"]

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(ArtifactEventsConfig):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """Event subscriber that translates events for the reverse transpiler"""

    def __init__(
        self,
        *,
        config: EventSubTranslatorConfig,
        reverse_transpiler: ReverseTranspilerPort,
    ):
        self.topics_of_interest = [config.artifact_topic]
        self.types_of_interest = ["upserted", "deleted"]
        self._config = config
        self._reverse_transpiler = reverse_transpiler

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
    ) -> None:
        """Consumes an event"""
        if key.split(":")[0] != "added_accessions":
            # Ignore events that are not related to added_accessions
            log.debug("Ignored event with key: %s because it's not the right kind", key)
            return

        if type_ == "upserted":
            log.info("Consuming artifact upsert event for key: %s", key)
            await self._consume_upsert(payload=payload)
        elif type_ == "deleted":
            log.info("Consuming artifact delete event for key: %s", key)
            study_accession = key.split(":")[1]
            await self._consume_delete(study_accession=study_accession)

    async def _consume_upsert(self, payload: JsonObject) -> None:
        """Consume change event (created or updated) for an artifact."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.Artifact
        )
        study_metadata = StudyMetadata(
            study_accession=validated_payload.study_accession,
            content=validated_payload.content,
        )
        await self._reverse_transpiler.upsert_metadata(study_metadata=study_metadata)

    async def _consume_delete(self, study_accession: str) -> None:
        """Consume event indicating the deletion of an artifact."""
        await self._reverse_transpiler.delete_metadata(study_accession=study_accession)
