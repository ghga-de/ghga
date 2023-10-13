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

"""Logic for subscribing to source events."""

from collections.abc import Awaitable
from typing import Callable

from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from metldata.event_handling.models import SubmissionEventPayload
from metldata.event_handling.submission_events import SourceEventConfig


class SourceEventSubscriberConfig(SourceEventConfig):
    """Config parameters and their defaults."""


class SourceEventSubscriber(EventSubscriberProtocol):
    """Consumes source events."""

    def __init__(
        self,
        *,
        config: SourceEventSubscriberConfig,
        run_workflow_func: Callable[[SubmissionEventPayload], Awaitable[None]],
    ):
        """Initialize with config parameters."""
        self.topics_of_interest = [config.source_event_topic]
        self.types_of_interest = [config.source_event_type]
        self._run_workflow_func = run_workflow_func

    # pylint: disable=unused-argument
    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii
    ) -> None:
        """
        Receive and process an event with already validated topic and type.

        Args:
            payload (JsonObject): The data/payload to send with the event.
            type_ (str): The type of the event.
            topic (str): Name of the topic the event was published to.
        """
        submission_event_payload = SubmissionEventPayload(**payload)
        await self._run_workflow_func(submission_event_payload)
