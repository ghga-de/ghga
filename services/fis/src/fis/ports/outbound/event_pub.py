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

"""Abstract definition of an event publisher class"""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4


class EventPubTranslatorPort(ABC):
    """Abstract definition of an event publisher class"""

    @abstractmethod
    async def publish_interrogation_success(  # noqa: PLR0913
        self,
        *,
        file_id: UUID4,
        secret_id: str,
        storage_alias: str,
        bucket_id: str,
        object_id: UUID4,
        interrogated_at: UTCDatetime,
        encrypted_parts_md5: list[str],
        encrypted_parts_sha256: list[str],
        encrypted_size: int,
    ):
        """Publish a file interrogation success event"""
        ...

    @abstractmethod
    async def publish_interrogation_failed(
        self,
        *,
        file_id: UUID4,
        storage_alias: str,
        interrogated_at: UTCDatetime,
        reason: str,
    ):
        """Publish a file interrogation failure event"""
        ...
