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

"""Port for the core user registry."""

from abc import ABC, abstractmethod
from typing import Optional, Union

from ..models.ivas import IvaBasicData, IvaData
from ..models.users import User, UserBasicData, UserModifiableData, UserRegisteredData


class UserRegistryPort(ABC):
    """Port providing a registry for users and IVAs."""

    class UserRegistryError(RuntimeError):
        """Base class for user registry errors."""

    class UserCreationError(UserRegistryError):
        """Raised when a user cannot be created in the database."""

    class UserAlreadyExistsError(UserCreationError):
        """Raised when trying to create a that already exists."""

    class UserRetrievalError(UserRegistryError):
        """Raised when a user cannot be retrieved from the database."""

    class UserDoesNotExistError(UserRegistryError):
        """Raised when trying to access a non-existing user."""

    class UserUpdateError(UserRegistryError):
        """Raised when a user cannot be updated in the database."""

    class UserDeletionError(UserRegistryError):
        """Raised when a user cannot be deleted in the database."""

    class IvaCreationError(UserRegistryError):
        """Raised when an IVA cannot be created in the database."""

    class IvaRetrievalError(UserRegistryError):
        """Raised when IVAs cannot be retrieved from the database."""

    class IvaDoesNotExistError(UserRegistryError):
        """Raised when trying to access a non-existing IVA."""

    class IvaDeletionError(UserRegistryError):
        """Raised when IVAs cannot be deleted from the database."""

    @staticmethod
    @abstractmethod
    def is_internal_user_id(id_: str) -> bool:
        """Check if the passed ID is an internal user id."""
        ...

    @staticmethod
    @abstractmethod
    def is_external_user_id(id_: str) -> bool:
        """Check if the passed ID is an external user id."""
        ...

    @abstractmethod
    async def create_user(
        self,
        user_data: UserRegisteredData,
    ) -> User:
        """Create a user with the given registration data.

        May raise a UserAlreadyExistsError or a UserCreationError.
        """
        ...

    @abstractmethod
    async def get_user(self, user_id: str) -> User:
        """Get user data.

        May raise a UserDoesNotExistError or a UserRetrievalError.
        """
        ...

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        user_data: Union[UserBasicData, UserModifiableData],
        *,
        changed_by: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        """Update user data.

        Status change is allowed and recorded with the specified context.

        May raise UserDoesNotExistError or a UserUpdateError.
        """
        ...

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete a user.

        May raise a UserDoesNotExistError or a UserDeletionError.
        """
        ...

    @abstractmethod
    async def create_iva(self, user_id: str, data: IvaBasicData) -> str:
        """Create an IVA for the given user with the given basic data.

        Returns the internal ID of the newly createdIVA.

        May raise a UserDoesNotExistError or an IvaCreationError.
        """
        ...

    @abstractmethod
    async def get_ivas(self, user_id: str) -> list[IvaData]:
        """Get all IVAs of a user.

        The internal data of the IVAs is not included in the result.

        May raise an IvaRetrievalError.
        """
        ...

    @abstractmethod
    async def delete_iva(self, iva_id: str, *, user_id: Optional[str] = None) -> None:
        """Delete the IVA with the ID.

        If the user ID is given, the IVA is only deleted if it belongs to the user.

        May raise an IvaDoesNotExistError or an IvaDeletionError.
        """
        ...
