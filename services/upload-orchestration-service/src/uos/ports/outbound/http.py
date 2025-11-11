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

"""Ports centered around outbound http calls"""

from abc import ABC, abstractmethod

from ghga_event_schemas.pydantic_ import FileUpload
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4

from uos.core.models import UploadGrant


class AccessClientPort(ABC):
    """An adapter for interacting with the access API to manage upload access grants"""

    class AccessAPIError(RuntimeError):
        """Raised when there's an error while communicating with the Access API"""

    class GrantNotFoundError(RuntimeError):
        """Raise when an the access API reports that it failed to find a grant."""

    @abstractmethod
    async def grant_upload_access(
        self,
        *,
        user_id: UUID4,
        iva_id: UUID4,
        box_id: UUID4,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant upload access to a user for a box.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        ...

    @abstractmethod
    async def revoke_upload_access(self, *, grant_id: UUID4) -> None:
        """Revoke a user's access to an upload box.

        Raises:
            GrantNotFoundError: if the grant wasn't found.
            AccessAPIError: if there's a problem during the operation.
        """

    @abstractmethod
    async def get_upload_access_grants(
        self,
        *,
        user_id: UUID4 | None = None,
        iva_id: UUID4 | None = None,
        box_id: UUID4 | None = None,
        valid: bool | None = None,
    ) -> list[UploadGrant]:
        """Get a list of upload grants.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        ...

    @abstractmethod
    async def get_accessible_upload_boxes(self, user_id: UUID4) -> list[UUID4]:
        """Get list of upload box IDs accessible to a user.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        ...

    @abstractmethod
    async def check_box_access(self, *, user_id: UUID4, box_id: UUID4) -> bool:
        """Check if a user has access to a specific upload box.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        ...


class FileBoxClientPort(ABC):
    """An adapter for interacting with the service that owns FileUploadBoxes.

    This class is responsible for WOT generation and all pertinent error handling.
    """

    class OperationError(RuntimeError):
        """Raised when there's an error while communicating with the service"""

    @abstractmethod
    async def create_file_upload_box(self, *, storage_alias: str) -> UUID4:
        """Create a new FileUploadBox in owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        ...

    @abstractmethod
    async def lock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Lock a FileUploadBox in the owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        ...

    @abstractmethod
    async def unlock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Unlock a FileUploadBox in the owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        ...

    @abstractmethod
    async def get_file_upload_list(self, *, box_id: UUID4) -> list[FileUpload]:
        """Get list of file uploads in a FileUploadBox.

        Raises:
            OperationError if there's a problem with the operation.
        """
        ...
