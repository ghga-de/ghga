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

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestStatus,
)


class AccessRequestRepositoryPort(ABC):
    """A repository for access requests."""

    class AccessRequestError(RuntimeError):
        """Error that is raised when an access request cannot be processed."""

    class AccessRequestAuthorizationError(AccessRequestError):
        """Error that is raised when the user is not authorized."""

    class AccessRequestInvalidState(AccessRequestError):
        """Error raised when the status for access is invalid."""

    class AccessRequestInvalidDuration(AccessRequestError):
        """Error raised when the time frame for access is invalid."""

    class AccessRequestNotFoundError(AccessRequestError):
        """Error raised when an access request cannot be found."""

    class AccessRequestServerError(AccessRequestError):
        """Error raised when there was some kind of a server error."""

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
        """
        ...

    @abstractmethod
    async def get(
        self,
        *,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[AccessRequestStatus] = None,
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
        status: AccessRequestStatus,
        auth_context: AuthContext,
    ) -> None:
        """Update the status of the access request.

        Only data stewards may use this method.

        Raises:
        - `AccessRequestAuthorizationError` if the user is not authorized.
        - `AccessRequestNotFoundError` if the specified request was not found.
        - `AccessRequestInvalidState` error if the specified state is invalid.
        - `AccessRequestServerError` if the grant could not be registered.
        """
        ...
