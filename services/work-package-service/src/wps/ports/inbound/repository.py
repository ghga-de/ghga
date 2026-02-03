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

"""Interface for the work package repository."""

from abc import ABC, abstractmethod

from ghga_service_commons.auth.ghga import AuthContext
from pydantic import UUID4

from wps.core.models import (
    BoxWithExpiration,
    Dataset,
    DatasetWithExpiration,
    ResearchDataUploadBoxBasics,
    UploadPathType,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
)


class WorkPackageRepositoryPort(ABC):
    """A repository for work packages."""

    class WorkPackageAccessError(RuntimeError):
        """Error that is raised when a work package cannot be accessed."""

    class DatasetNotFoundError(RuntimeError):
        """Error that is raised when a dataset does not exist."""

    class UploadBoxNotFoundError(RuntimeError):
        """Error that is raised when an upload box does not exist."""

    @abstractmethod
    async def create(
        self, *, creation_data: WorkPackageCreationData, auth_context: AuthContext
    ) -> WorkPackageCreationResponse:
        """Create a work package and store it in the repository."""

    @abstractmethod
    async def get(
        self,
        work_package_id: UUID4,
        *,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> WorkPackage:
        """Get a work package with the given ID from the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """

    @abstractmethod
    async def get_download_wot(
        self,
        *,
        work_package_id: UUID4,
        file_id: str,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> str:
        """Create a work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the file_id is not contained in the work package
        - if check_valid is set and the work package has expired
        - if the work package type is not DOWNLOAD
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """

    @abstractmethod
    async def get_upload_wot(  # noqa: PLR0913
        self,
        *,
        work_package_id: UUID4,
        work_type: UploadPathType,
        box_id: UUID4,
        alias: str | None = None,
        file_id: UUID4 | None = None,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> str:
        """Create a work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the work type is not valid, i.e. one of create, upload, close, or delete
        - if the work_type requires parameters that are not provided (alias or file ID)
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        - if an upload box is not found in the database
        """

    @abstractmethod
    async def register_dataset(self, dataset: Dataset) -> None:
        """Register a dataset with all of its files."""

    @abstractmethod
    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset with all of its files.

        If no such dataset exists, a DatasetNotFoundError will be raised.
        """

    @abstractmethod
    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get a registered dataset using the given ID.

        If no such dataset exists, a DatasetNotFoundError will be raised.
        """

    @abstractmethod
    async def get_datasets(self, user_id: UUID4) -> list[DatasetWithExpiration]:
        """Get the list of all datasets accessible to the specified user.

        The returned datasets also have an expiration date until when access is granted.

        Raises WorkPackageAccessError on failure.
        """

    @abstractmethod
    async def register_upload_box(
        self, upload_box: ResearchDataUploadBoxBasics
    ) -> None:
        """Register an upload box."""

    @abstractmethod
    async def delete_upload_box(self, box_id: UUID4) -> None:
        """Delete an upload box with the given ID.

        If no such box exists, an UploadBoxNotFoundError will be raised.
        """

    @abstractmethod
    async def get_upload_box(self, box_id: UUID4) -> ResearchDataUploadBoxBasics:
        """Get a registered upload box using the given ID.

        If no such box exists, an UploadBoxNotFoundError will be raised.
        """

    @abstractmethod
    async def get_upload_boxes(self, user_id: UUID4) -> list[BoxWithExpiration]:
        """Get the list of all upload boxes accessible to the specified user.

        The returned boxes also have an expiration date until when access is granted.

        Raises WorkPackageAccessError on failure.
        """
