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

"""Interface for broadcasting events to other services."""

from abc import ABC, abstractmethod

from ars.core import models


class EventPublisherPort(ABC):
    """An interface for an adapter that publishes events happening to this service."""

    @abstractmethod
    async def publish_request_allowed(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was allowed."""

    @abstractmethod
    async def publish_request_created(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was created."""
        ...

    @abstractmethod
    async def publish_request_denied(self, *, request: models.AccessRequest) -> None:
        """Publish an event relaying that an access request was denied."""
        ...
