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

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestPatchData,
    AccessRequestStatus,
    Dataset,
)


class AccessRequestRepositoryPort(ABC):
    """A repository for access requests."""

    class AccessRequestError(RuntimeError):
        """Error that is raised when an access request cannot be processed."""

    class AccessRequestAuthorizationError(AccessRequestError):
        """Error that is raised when the user is not authorized."""

    class AccessRequestMissingIva(AccessRequestError):
        """Error raised when an IVA is needed, but not provided."""

    class AccessRequestClosed(AccessRequestError):
        """Error raised when the access request was already processed."""

    class AccessRequestInvalidDuration(AccessRequestError):
        """Error raised when the time frame for access is invalid."""

    class AccessRequestNotFoundError(AccessRequestError):
        """Error raised when an access request cannot be found."""

    class AccessRequestServerError(AccessRequestError):
        """Error raised when there was some kind of server error."""

    class DatasetNotFoundError(RuntimeError):
        """Error raised when a dataset cannot be found."""

    @abstractmethod
    async def create(
        self, creation_data: AccessRequestCreationData, *, auth_context: AuthContext
    ) -> AccessRequest:
        """Create an access request and store it in the repository.

        Returns the created access request object.

        Users may only create access requests for themselves.

        Raises:
        - `AccessRequestAuthorizationError` if the user is not authorized.
        - `AccessRequestInvalidDuration` error if the dates are invalid.
        - `DatasetNotFoundError` if no dataset with given ID is found.
        """
        ...

    @abstractmethod
    async def get(
        self,
        *,
        dataset_id: str | None = None,
        user_id: str | None = None,
        status: AccessRequestStatus | None = None,
        auth_context: AuthContext,
    ) -> list[AccessRequest]:
        """Get the list of all access requests with the given properties.

        Only data stewards may list requests created by other users.

        Raises an `AccessRequestAuthorizationError` if the user is not authorized.
        """
        ...

    @abstractmethod
    async def update(
        self,
        access_request_id: str,
        *,
        patch_data: AccessRequestPatchData,
        auth_context: AuthContext,
    ) -> None:
        """Update the status or other fields of the access request.

        If the status is set to allowed, an IVA ID must be provided or already exist.

        Only data stewards may use this method.

        Raises:
        - `AccessRequestNotFoundError` if the specified request was not found
        - `AccessRequestAuthorizationError` if the user is not authorized
        - `AccessRequestClosed` if the access request was already processed
        - `AccessRequestMissingIva` if an IVA is needed but not provided
        - `AccessRequestInvalidDuration` if the end date isn't later than the start date
        - `AccessRequestServerError` if the access grant could not be registered
        """
        ...

    @abstractmethod
    async def register_dataset(self, dataset: Dataset) -> None:
        """Register a dataset in the repository.

        If the dataset already exists, it will be updated.
        """
        ...

    @abstractmethod
    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete the registered dataset with the given ID.

        Raises a `DatasetNotFoundError` if the dataset was not found.
        """
        ...

    @abstractmethod
    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get the registered dataset with the given ID.

        Raises a `DatasetNotFoundError` if the dataset was not found.
        """
        ...
