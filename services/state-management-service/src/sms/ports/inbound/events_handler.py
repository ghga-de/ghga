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

"""Defines the API of a class that interfaces between inbound requests and kafka."""

from abc import ABC, abstractmethod

from sms.models import EventDetails


class EventsHandlerPort(ABC):
    """A class to manage the state of kafka events."""

    class PublishError(RuntimeError):
        """Raised when there's an error during the event publish operation."""

        def __init__(self, *, event_details: EventDetails):
            msg = (
                "There was an error trying to publish the"
                + f" following event: {event_details}"
            )
            super().__init__(msg)

    @abstractmethod
    async def clear_topics(self, *, topics: list[str], exclude_internal: bool = True):
        """Clear messages from given topic(s).

        If no topics are specified, all topics will be cleared, except internal topics
        unless otherwise specified.
        """
        ...

    @abstractmethod
    async def publish_event(self, *, event_details: EventDetails):
        """Publish a single event to the given topic.

        Raises a `PublishError` if there's an problem with the publishing operation.
        """
        ...
