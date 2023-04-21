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

"""Interface for the work package repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ghga_service_commons.auth.ghga import AuthContext

from wps.core.models import (
    Dataset,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
)


class WorkPackageRepositoryPort(ABC):
    """A repository for work packages."""

    class WorkPackageAccessError(KeyError):
        """Error that is raised when a work package cannot be accessed."""

    class DatasetNotFoundError(KeyError):
        """Error that is raised when a dataset does not exist."""

    @abstractmethod
    async def create(
        self, creation_data: WorkPackageCreationData, auth_context: AuthContext
    ) -> WorkPackageCreationResponse:
        """Create a work package and store it in the repository."""
        ...

    @abstractmethod
    async def get(
        self,
        work_package_id: str,
        check_valid: bool = True,
        work_package_access_token: Optional[str] = None,
    ) -> WorkPackage:
        """Get a work package with the given ID from the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        ...

    @abstractmethod
    async def work_order_token(
        self,
        work_package_id: str,
        file_id: str,
        check_valid: bool = True,
        work_package_access_token: Optional[str] = None,
    ) -> str:
        """Create a work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the file_id is not contained in the work package
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        ...

    @abstractmethod
    async def register_dataset(self, dataset: Dataset) -> None:
        """Register a dataset with all of its files."""
        ...

    @abstractmethod
    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get a registered dataset using the given ID.

        If the dataset does not exist, a DatasetNotFoundError will be raised.
        """
        ...
