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

"Routes for managing users"

import logging

from fastapi import APIRouter, Path, Response
from fastapi.exceptions import HTTPException
from ghga_service_chassis_lib.utils import now_as_utc
from hexkit.protocols.dao import (
    MultipleHitsFoundError,
    NoHitsFoundError,
    ResourceNotFoundError,
)

from ..auth import AuthToken, RequireAuthToken
from .deps import Depends, UserDao, get_user_dao
from .models.dto import (
    StatusChange,
    User,
    UserBasicData,
    UserData,
    UserModifiableData,
    UserRegisteredData,
    UserStatus,
)
from .utils import is_external_id, is_internal_id

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()

INITIAL_USER_STATUS = UserStatus.ACTIVE


@router.post(
    "/users",
    operation_id="post_user",
    tags=["users"],
    summary="Register a user",
    description="Endpoint used to register a new user."
    " May only be performed by the users themselves."
    " Data delivered by the OIDC provider may not be altered.",
    responses={
        201: {"model": User, "description": "User was successfully registered."},
        403: {"description": "Not authorized to register user."},
        409: {"description": "User was already registered."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def post_user(
    user_data: UserRegisteredData,
    user_dao: UserDao = Depends(get_user_dao),
    auth_token: AuthToken = Depends(RequireAuthToken(active=False)),
) -> User:
    """Register a user"""
    ext_id = user_data.ext_id
    # users can only register themselves
    if ext_id != auth_token.ext_id:
        raise HTTPException(status_code=403, detail="Not authorized to register user.")
    if (
        auth_token.id  # must not have been already registered
        or user_data.name != auth_token.name  # specified name must match token
        or user_data.email != auth_token.email  # specified email must match token
    ):
        raise HTTPException(status_code=422, detail="User cannot be registered.")
    try:
        user = await user_dao.find_one(mapping={"ext_id": ext_id})
    except NoHitsFoundError:
        pass
    else:
        raise HTTPException(status_code=409, detail="User was already registered.")
    full_user_data = UserData(
        **user_data.dict(), status=INITIAL_USER_STATUS, registration_date=now_as_utc()
    )
    try:
        user = await user_dao.insert(full_user_data)
    except Exception as error:
        log.error("Could not insert user: %s", error)
        raise HTTPException(
            status_code=500, detail="User cannot be registered."
        ) from error
    return user


@router.put(
    "/users/{id}",
    operation_id="put_user",
    tags=["users"],
    summary="Update a user",
    description="Endpoint used to update a registered user"
    " when their name or email used by LS Login have changed."
    " May only be performed by the users themselves."
    " Data delivered by the OIDC provider may not be altered.",
    responses={
        204: {"description": "User was successfully updated."},
        403: {"description": "Not authorized to update user."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=204,
)
async def put_user(
    user_data: UserBasicData,
    id_: str = Path(
        ...,
        alias="id",
        title="Internal ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    auth_token: AuthToken = Depends(RequireAuthToken(active=False)),
) -> Response:
    """Update a user"""
    # users can only update themselves,
    # invalid users are allowed to update themselves in order to become valid again
    if not (
        is_internal_id(id_)
        and id_ == auth_token.id
        and auth_token.status in (UserStatus.ACTIVE, UserStatus.INVALID)
    ):
        raise HTTPException(status_code=403, detail="Not authorized to update user.")
    if (
        user_data.name != auth_token.name  # specified name must match token
        or user_data.email != auth_token.email  # specified email must match token
    ):
        raise HTTPException(status_code=422, detail="User cannot be updated.")
    try:
        user = await user_dao.get_by_id(id_)
        user = user.copy(update=user_data.dict())
        await user_dao.update(user)
    except Exception as error:
        log.error("Could not update user: %s", error)
        raise HTTPException(
            status_code=500, detail="User cannot be updated."
        ) from error

    return Response(status_code=204)


@router.get(
    "/users/{id}",
    operation_id="get_user",
    tags=["users"],
    summary="Get user data",
    description="Endpoint used to get the user data for a specified user."
    " Can only be performed by a data steward or the same user.",
    responses={
        200: {"model": User, "description": "Requested user has been found."},
        401: {"description": "Not authorized to get user data."},
        403: {"description": "Not authorized to request user."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=200,
)
async def get_user(
    id_: str = Path(
        ...,
        alias="id",
        title="Internal ID or External (LS) ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    auth_token: AuthToken = Depends(RequireAuthToken(active=False)),
) -> User:
    """Get user data"""
    # Only data steward can request other user accounts
    if not (
        auth_token.has_role("data_steward")
        or (is_external_id(id_) and id_ == auth_token.ext_id)
        or (is_internal_id(id_) and id_ == auth_token.id)
    ):
        raise HTTPException(status_code=403, detail="Not authorized to request user.")
    try:
        if is_external_id(id_):
            user = await user_dao.find_one(mapping={"ext_id": id_})
        elif is_internal_id(id_):
            user = await user_dao.get_by_id(id_)
        else:
            raise ResourceNotFoundError(id_=id_)
    except (NoHitsFoundError, MultipleHitsFoundError, ResourceNotFoundError) as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except Exception as error:
        log.error("Could not request user: %s", error)
        raise HTTPException(
            status_code=500, detail="The user cannot be requested."
        ) from error
    if not auth_token.has_role("data_steward"):
        # only data stewards should be able to see the status change information
        if user.status_change is not None:
            user = user.copy(update=dict(status_change=None))
    return user


@router.patch(
    "/users/{id}",
    operation_id="patch_user",
    tags=["users"],
    summary="Modify user data",
    description="Endpoint used to modify the user data for a specified user."
    " Can only be performed by a data steward or the same user.",
    responses={
        204: {"description": "User data was successfully saved."},
        403: {"description": "Not authorized to make this modification."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def patch_user(
    user_data: UserModifiableData,
    id_: str = Path(
        ...,
        alias="id",
        title="Internal ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    auth_token: AuthToken = Depends(RequireAuthToken()),
) -> Response:
    """Modify user data"""
    update_data = user_data.dict(exclude_unset=True)
    # Everybody is allowed to modify their own data except the status,
    # but only data stewards are allowed to modify other accounts
    allowed = (
        "status" not in update_data
        if id_ == auth_token.id
        else auth_token.has_role("data_steward")
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="Not authorized to make this modification."
        )
    try:
        if not is_internal_id(id_):
            raise ResourceNotFoundError(id_=id_)
        user = await user_dao.get_by_id(id_)
        if "status" in update_data and update_data["status"] != user.status:
            update_data["status_change"] = StatusChange(
                previous=user.status,
                by=auth_token.id,
                context="manual change",
                change_date=now_as_utc(),
            )
        user = user.copy(update=update_data)
        await user_dao.update(user)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except Exception as error:
        log.error("Could not modify user: %s", error)
        raise HTTPException(
            status_code=500, detail="The user cannot be modified."
        ) from error

    return Response(status_code=204)


@router.delete(
    "/users/{id}",
    operation_id="delete_user",
    tags=["users"],
    summary="Delete user",
    description="Endpoint used to delete a user."
    " Can only be performed by a data steward.",
    responses={
        204: {"description": "User data was successfully deleted."},
        403: {"description": "Not authorized to delete this user."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=201,
)
async def delete_user(
    id_: str = Path(
        ...,
        alias="id",
        title="Internal ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    auth_token: AuthToken = Depends(RequireAuthToken(role="data_steward")),
) -> Response:
    """Delete user"""
    if id_ == auth_token.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user."
        )
    try:
        if not is_internal_id(id_):
            raise ResourceNotFoundError(id_=id_)
        await user_dao.delete(id_=id_)
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except Exception as error:
        log.error("Could not delete user: %s", error)
        raise HTTPException(
            status_code=500, detail="The user cannot be deleted."
        ) from error

    return Response(status_code=204)
