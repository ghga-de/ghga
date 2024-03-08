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

"""Implementation of the core user registry."""

import logging
from typing import Optional, Union

from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import (
    NoHitsFoundError,
    ResourceNotFoundError,
)
from pydantic_settings import BaseSettings

from ..models.ivas import IvaBasicData, IvaData, IvaFullData
from ..models.users import (
    StatusChange,
    User,
    UserBasicData,
    UserData,
    UserModifiableData,
    UserRegisteredData,
    UserStatus,
)
from ..ports.registry import UserRegistryPort
from ..translators.dao import IvaDao, UserDao

log = logging.getLogger(__name__)

INITIAL_USER_STATUS = UserStatus.ACTIVE


class UserRegistryConfig(BaseSettings):
    """Configuration for the user registry."""


class UserRegistry(UserRegistryPort):
    """Registry for users including their IVAs."""

    def __init__(
        self, *, config: UserRegistryConfig, user_dao: UserDao, iva_dao: IvaDao
    ):
        """Initialize the user registry."""
        self.config = config
        self.user_dao = user_dao
        self.iva_dao = iva_dao

    @staticmethod
    def is_internal_user_id(id_: str) -> bool:
        """Check if the passed ID is an internal user id."""
        if not id_ or not isinstance(id_, str):
            return False
        return len(id_) == 36 and id_.count("-") == 4 and "@" not in id_

    @staticmethod
    def is_external_user_id(id_: str) -> bool:
        """Check if the passed ID is an external user id."""
        if not id_ or not isinstance(id_, str):
            return False
        return len(id_) > 8 and id_.count("@") == 1

    async def create_user(
        self,
        user_data: UserRegisteredData,
    ) -> User:
        """Create a user with the given registration data.

        May raise a UserAlreadyExistsError or a UserCreationError.
        """
        ext_id = user_data.ext_id
        try:
            if not self.is_external_user_id(ext_id):
                raise ValueError(f"Invalid user ID: {ext_id}")
            user = await self.user_dao.find_one(mapping={"ext_id": ext_id})
        except NoHitsFoundError:
            pass
        except Exception as error:
            log.error("Could not insert user: %s", error)
            raise self.UserCreationError from error
        else:
            raise self.UserAlreadyExistsError
        full_user_data = UserData(
            **user_data.model_dump(),
            status=INITIAL_USER_STATUS,
            registration_date=now_as_utc(),
        )
        try:
            user = await self.user_dao.insert(full_user_data)
        except Exception as error:
            log.error("Could not insert user: %s", error)
            raise self.UserCreationError from error
        return user

    async def get_user(self, user_id: str) -> User:
        """Get user data.

        May raise a UserDoesNotExistError or a UserRetrievalError.
        """
        try:
            if not self.is_internal_user_id(user_id):
                raise ResourceNotFoundError(id_=user_id)
            user = await self.user_dao.get_by_id(user_id)
        except ResourceNotFoundError as error:
            raise self.UserDoesNotExistError from error
        except Exception as error:
            log.error("Could not request user: %s", error)
            raise self.UserRetrievalError from error
        return user

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
        update_data = user_data.model_dump(exclude_unset=True)
        try:
            user = await self.get_user(user_id)
        except self.UserRetrievalError as error:
            raise self.UserUpdateError from error
        if "status" in update_data and user.status != update_data["status"]:
            update_data["status_change"] = StatusChange(
                previous=user.status,
                by=(changed_by or "").strip() or None,
                context=(context or "").strip() or None,
                change_date=now_as_utc(),
            )
        try:
            user = user.model_copy(update=update_data)
            await self.user_dao.update(user)
        except ResourceNotFoundError as error:
            log.warning("User not found: %s", error)
            raise self.UserDoesNotExistError from error
        except Exception as error:
            log.error("Could not update user: %s", error)
            raise self.UserUpdateError from error

    async def delete_user(self, user_id: str) -> None:
        """Delete a user.

        This also deletes all IVAs belonging to the user.

        May raise a UserDoesNotExistError or a UserDeletionError.
        """
        try:
            if not self.is_internal_user_id(user_id):
                raise ResourceNotFoundError(id_=user_id)
            await self.user_dao.delete(id_=user_id)
        except ResourceNotFoundError as error:
            raise self.UserDoesNotExistError from error
        except Exception as error:
            log.error("Could not delete user: %s", error)
            raise self.UserDeletionError from error
        try:
            try:
                async for iva in self.iva_dao.find_all(mapping={"user_id": user_id}):
                    await self.iva_dao.delete(id_=iva.id)
            except ResourceNotFoundError:
                pass
        except Exception as error:
            log.error("Could not delete IVAs of user: %s", error)
            raise self.UserDeletionError from error

    async def create_iva(self, user_id: str, data: IvaBasicData) -> str:
        """Create an IVA for the given user with the given basic data.

        Returns the internal ID of the newly createdIVA.

        May raise a UserDoesNotExistError or an IvaCreationError.
        """
        try:
            await self.get_user(user_id)
        except self.UserRetrievalError as error:
            raise self.IvaCreationError from error
        created = changed = now_as_utc()
        iva_data = IvaFullData(
            **data.model_dump(), user_id=user_id, created=created, changed=changed
        )
        try:
            iva = await self.iva_dao.insert(iva_data)
        except Exception as error:
            log.error("Could not create IVA: %s", error)
            raise self.IvaCreationError from error
        return iva.id

    async def get_ivas(self, user_id: str) -> list[IvaData]:
        """Get all IVAs of a user.

        The internal data of the IVAs is not included in the result.

        May raise an IvaRetrievalError.
        """
        external_fields = IvaData.model_fields
        try:
            return [
                IvaData(**iva.model_dump(include=external_fields))
                async for iva in self.iva_dao.find_all(mapping={"user_id": user_id})
            ]
        except Exception as error:
            log.error("Could not retrieve IVAs: %s", error)
            raise self.IvaRetrievalError from error

    async def delete_iva(self, iva_id: str, *, user_id: Optional[str] = None) -> None:
        """Delete the IVA with the ID.

        If the user ID is given, the IVA is only deleted if it belongs to the user.

        May raise an IvaDoesNotExistError or an IvaDeletionError.
        """
        if user_id:
            try:
                iva = await self.iva_dao.get_by_id(iva_id)
            except ResourceNotFoundError as error:
                raise self.IvaDoesNotExistError from error
            except Exception as error:
                log.error("Could not retrieve IVA: %s", error)
                raise self.IvaDeletionError from error
            if iva.user_id != user_id:
                raise self.IvaDoesNotExistError
        try:
            iva = await self.iva_dao.delete(id_=iva_id)
        except ResourceNotFoundError as error:
            raise self.IvaDoesNotExistError from error
        except Exception as error:
            log.error("Could not delete IVA: %s", error)
            raise self.IvaDeletionError from error
