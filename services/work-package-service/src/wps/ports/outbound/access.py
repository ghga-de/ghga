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

"""Outbound access checks"""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4

__all__ = ["AccessCheckPort"]


class AccessCheckPort(ABC):
    """A port for checking access permissions for datasets and upload boxes."""

    class AccessCheckError(RuntimeError):
        """Raised when the access check failed without result."""

    @abstractmethod
    async def check_download_access(
        self, user_id: UUID4, dataset_id: str
    ) -> UTCDatetime | None:
        """Check until when the given user has download access for the given dataset."""

    @abstractmethod
    async def get_accessible_datasets_with_expiration(
        self, user_id: UUID4
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download.

        This method returns a mapping from dataset IDs to access expiration dates.
        """

    @abstractmethod
    async def check_upload_access(
        self, user_id: UUID4, box_id: UUID4
    ) -> UTCDatetime | None:
        """Check until when the given user has upload access for the given box."""

    @abstractmethod
    async def get_accessible_boxes_with_expiration(
        self, user_id: UUID4
    ) -> dict[UUID4, UTCDatetime]:
        """Get all upload boxes that the given user is allowed to upload to.

        This method returns a mapping from box IDs to access expiration dates.
        """
