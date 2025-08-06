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
from uuid import UUID

from ghga_service_commons.utils.utc_dates import UTCDatetime

__all__ = ["AccessCheckPort"]


class AccessCheckPort(ABC):
    """A port for checking access permissions for datasets."""

    class AccessCheckError(RuntimeError):
        """Raised when the access check failed without result."""

    @abstractmethod
    async def check_download_access(
        self, user_id: UUID, dataset_id: str
    ) -> UTCDatetime | None:
        """Check until when the given user has download access for the given dataset."""

    @abstractmethod
    async def get_accessible_datasets_with_expiration(
        self, user_id: UUID
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download.

        This method returns a mapping from dataset IDs to access expiration dates.
        """
