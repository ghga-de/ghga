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
"""Event subscriber implementation"""

from collections.abc import Mapping
from datetime import datetime

from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import DLQSubscriberProtocol

from dlqs.models import RawDLQEvent
from dlqs.ports.inbound.dlq_manager import DLQManagerPort


class DLQSubTranslator(DLQSubscriberProtocol):
    """A translator that can consume events"""

    def __init__(self, *, dlq_manager: DLQManagerPort):
        """Set up the DLQ Sub Translator"""
        self.dlq_manager = dlq_manager

    async def _consume_validated(  # noqa: PLR0913
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        timestamp: datetime,
        headers: Mapping[str, str],
    ) -> None:
        """Consume an event"""
        event = RawDLQEvent(
            payload=payload,  # type: ignore
            type_=type_,
            topic=topic,
            key=key,
            timestamp=timestamp,
            headers=headers,  # type: ignore
        )
        await self.dlq_manager.store_event(event=event)
