# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Interface for broadcasting outbox events to other services."""

from abc import ABC, abstractmethod
from typing import TypeAlias

from ghga_event_schemas.pydantic_ import FileUploadReceived
from hexkit.protocols.daopub import DaoPublisher

__all__ = ["FileUploadReceivedDao", "OutboxPublisherFactoryPort"]

FileUploadReceivedDao: TypeAlias = DaoPublisher[FileUploadReceived]


class OutboxPublisherFactoryPort(ABC):
    """Port that provides a factory for user related data access objects.

    These objects will also publish changes according to the outbox pattern.
    """

    @abstractmethod
    async def get_file_upload_received_dao(self) -> FileUploadReceivedDao:
        """Construct a DAO for manipulating FileUploadReceived events in the DB."""
        ...
