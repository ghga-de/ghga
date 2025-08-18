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

"""Routes for managing users and IVAs"""

from contextlib import suppress
from enum import Enum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Path, Query, Response
from fastapi.exceptions import HTTPException
from hexkit.protocols.dao import ResourceNotFoundError
from pydantic import UUID4

from auth_service.auth_adapter.deps import UserTokenDaoDependency
from auth_service.constants import TRACER

from ...auth_adapter.rest.dto import TOTPTokenResponse
from ...rest.auth import (
    StewardAuthContext,
    UserAuthContext,
    is_steward,
)
from ..deps import UserRegistryDependency
from ..models.ivas import (
    IvaAndUserData,
    IvaBasicData,
    IvaData,
    IvaId,
    IvaState,
    IvaVerificationCode,
)
from ..models.users import (
    User,
    UserBasicData,
    UserModifiableData,
    UserRegisteredData,
    UserStatus,
    UserWithRoles,
)

__all__ = ["router"]

router = APIRouter()

TAGS_USERS: list[str | Enum] = ["users"]
TAGS_SESSION: list[str | Enum] = ["session"]
TAGS_TOTP: list[str | Enum] = ["totp"]


@router.get(
    "/users",
    operation_id="get_users",
    tags=TAGS_USERS,
    summary="Get user data of all users",
    description="Endpoint used to retrieve user data for all users including all their roles."
    " Can only be performed by a data steward.",
    responses={
        200: {
            "model": list[User],
            "description": "User data was successfully retrieved.",
        },
        401: {"description": "Not authorized to request user data."},
        409: {"description": "User was already registered."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("router.get_users")
async def get_users(
    user_registry: UserRegistryDependency,
    _auth_context: StewardAuthContext,
    status: Annotated[
        UserStatus | None,
        Query(
            description="Filter for the status of the user",
        ),
    ] = None,
) -> list[UserWithRoles]:
    """Get user data of all users including their roles."""
    try:
        return await user_registry.get_users_with_roles(status=status)
    except user_registry.IvaRetrievalError as error:
        raise HTTPException(status_code=500, detail="Cannot retrieve users.") from error


@router.post(
    "/users",
    operation_id="post_user",
    tags=TAGS_USERS,
    summary="Register a user",
    description="Endpoint used to register a new user."
    " May only be performed by the users themselves."
    " Data delivered by the OIDC provider may not be altered.",
    responses={
        201: {
            "model": UserWithRoles,
            "description": "User was successfully registered.",
        },
        401: {"description": "Not authorized to register users."},
        403: {"description": "Not authorized to register this user."},
        409: {"description": "User was already registered."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("router.post_user")
async def post_user(
    user_data: UserRegisteredData,
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> UserWithRoles:
    """Register a user."""
    ext_id = user_data.ext_id
    # note that the auth context contains the external ID for this endpoint (only)
    if ext_id != auth_context.id:  # users can only register themselves
        raise HTTPException(status_code=403, detail="Not authorized to register user.")
    if not (
        user_registry.is_external_user_id(ext_id)
        and user_data.name == auth_context.name  # specified name must match token
        and user_data.email == auth_context.email  # specified email must match token
    ):
        raise HTTPException(status_code=422, detail="User cannot be registered.")
    try:
        return await user_registry.create_user(user_data)
    except user_registry.UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=409, detail="User was already registered."
        ) from error
    except user_registry.UserCreationError as error:
        raise HTTPException(
            status_code=500, detail="User cannot be registered."
        ) from error


@router.put(
    "/users/{id}",
    operation_id="put_user",
    tags=TAGS_USERS,
    summary="Update a user",
    description="Endpoint used to update a registered user"
    " when their name or email used by LS Login have changed."
    " May only be performed by the users themselves."
    " Data delivered by the OIDC provider may not be altered.",
    responses={
        204: {"description": "User was successfully updated."},
        401: {"description": "Not authorized to update users."},
        403: {"description": "Not authorized to update this user."},
        404: {"description": "User does not exist."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.put_user")
async def put_user(
    user_data: UserBasicData,
    id_: Annotated[
        UUID4,
        Path(
            ...,
            alias="id",
            description="Internal ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> Response:
    """Update a user."""
    if str(id_) != auth_context.id:  # users can only update themselves
        raise HTTPException(status_code=403, detail="Not authorized to update user.")
    if not (
        user_data.name == auth_context.name  # specified name must match token
        and user_data.email == auth_context.email  # specified email must match token
    ):
        raise HTTPException(status_code=422, detail="User cannot be updated.")
    try:
        await user_registry.update_user(id_, user_data)
    except user_registry.UserDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="User does not exist.") from error
    except user_registry.UserUpdateError as error:
        raise HTTPException(
            status_code=500, detail="User cannot be updated."
        ) from error
    return Response(status_code=204)


@router.get(
    "/users/{id}",
    operation_id="get_user",
    tags=TAGS_USERS,
    summary="Get user data",
    description="Endpoint used to get the user data for a specified user including all roles."
    " Can only be performed by a data steward or the same user.",
    responses={
        200: {"model": User, "description": "Requested user has been found."},
        401: {"description": "Not authorized to request user data."},
        403: {"description": "Not authorized to request data of this user."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("router.get_user")
async def get_user(
    id_: Annotated[
        UUID4,
        Path(
            ...,
            alias="id",
            description="Internal User ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> UserWithRoles:
    """Get user data including their roles."""
    # only data stewards can request other user accounts
    if not (is_steward(auth_context) or str(id_) == auth_context.id):
        raise HTTPException(status_code=403, detail="Not authorized to request user.")
    try:
        user = await user_registry.get_user_with_roles(id_)
    except user_registry.UserDoesNotExistError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except user_registry.UserRetrievalError as error:
        raise HTTPException(
            status_code=500, detail="The user cannot be requested."
        ) from error
    if not is_steward(auth_context) and user.status_change is not None:
        # only data stewards should be able to see the status change information
        user = user.model_copy(update={"status_change": None})
    return user


@router.patch(
    "/users/{id}",
    operation_id="patch_user",
    tags=TAGS_USERS,
    summary="Modify user data",
    description="Endpoint used to modify the user data for a specified user."
    " Can only be performed by a data steward or the same user.",
    responses={
        204: {"description": "User data was successfully saved."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to make this modification."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("router.patch_user")
async def patch_user(
    user_data: UserModifiableData,
    id_: Annotated[
        UUID4,
        Path(
            ...,
            alias="id",
            description="Internal ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> Response:
    """Modify user data."""
    # Everybody is allowed to modify their own data except the status,
    # but only data stewards are allowed to modify other accounts
    allowed = (
        "status" not in user_data.model_fields_set
        if str(id_) == auth_context.id
        else is_steward(auth_context)
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="Not authorized to make this modification."
        )
    try:
        await user_registry.update_user(
            id_,
            user_data,
            changed_by=UUID(auth_context.id),
            context="manual change",
        )
    except user_registry.UserDoesNotExistError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except user_registry.UserRetrievalError as error:
        raise HTTPException(
            status_code=500, detail="The user cannot be modified."
        ) from error
    return Response(status_code=204)


@router.delete(
    "/users/{id}",
    operation_id="delete_user",
    tags=TAGS_USERS,
    summary="Delete user",
    description="Endpoint used to delete a user."
    " Can only be performed by a data steward.",
    responses={
        204: {"description": "User data was successfully deleted."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to delete this user."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("router.delete_user")
async def delete_user(
    id_: Annotated[
        UUID4,
        Path(
            ...,
            alias="id",
            description="Internal ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    token_dao: UserTokenDaoDependency,
    auth_context: StewardAuthContext,
) -> Response:
    """Delete user."""
    if str(id_) == auth_context.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user."
        )
    try:
        # delete the user data belonging to this service
        await user_registry.delete_user(id_)
        # delete associated tokens belonging to the auth adapter
        with suppress(ResourceNotFoundError):
            await token_dao.delete(id_)
    except user_registry.UserDoesNotExistError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500, detail="The user cannot be deleted."
        ) from error
    return Response(status_code=204)


@router.get(
    "/users/{user_id}/ivas",
    operation_id="get_user_ivas",
    tags=TAGS_USERS,
    summary="Get all IVAs of a user",
    description="Endpoint used to get all IVAs for a specified user."
    " Can only be performed by a data steward or the same user.",
    responses={
        200: {
            "model": list[IvaData],
            "description": "User IVAs have been retrieved.",
        },
        401: {"description": "Not authorized to request IVAs."},
        403: {"description": "Not authorized to request these IVAs."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("router.get_user_ivas")
async def get_user_ivas(
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="Internal User ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> list[IvaData]:
    """Get all IVAs of a user."""
    # only data stewards can request IVAs of other user accounts
    if not (is_steward(auth_context) or str(user_id) == auth_context.id):
        raise HTTPException(
            status_code=403, detail="Not authorized to request these IVAs."
        )
    try:
        return await user_registry.get_ivas(user_id)
    except user_registry.IvaRetrievalError as error:
        raise HTTPException(status_code=500, detail="Cannot retrieve IVAs.") from error


@router.post(
    "/users/{user_id}/ivas",
    operation_id="post_user_iva",
    tags=TAGS_USERS,
    summary="Create a new IVA",
    description="Endpoint used to create a new IVA for a specified user.",
    responses={
        201: {"model": IvaId, "description": "User IVA has been successfully created."},
        401: {"description": "Not authorized to create IVAs."},
        403: {"description": "Not authorized to create this IVA."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("router.post_user_iva")
async def post_user_iva(
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="Internal User ID",
        ),
    ],
    data: IvaBasicData,
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> IvaId:
    """Create new IVA for a given user."""
    # only data stewards can create IVAs for other user accounts
    if not (is_steward(auth_context) or str(user_id) == auth_context.id):
        raise HTTPException(
            status_code=403, detail="Not authorized to create this IVA."
        )
    basic_data = IvaBasicData(**data.model_dump())
    try:
        id_ = await user_registry.create_iva(user_id, basic_data)
    except user_registry.UserDoesNotExistError as error:
        raise HTTPException(
            status_code=404, detail="The user was not found."
        ) from error
    except user_registry.IvaRetrievalError as error:
        raise HTTPException(status_code=500, detail="Cannot create IVA") from error
    return IvaId(id=id_)


@router.delete(
    "/users/{user_id}/ivas/{iva_id}",
    operation_id="delete_user_iva",
    tags=TAGS_USERS,
    summary="Delete an IVA",
    description="Endpoint used to delete an IVA for a specified user.",
    responses={
        204: {"description": "User IVA was successfully deleted."},
        401: {"description": "Not authorized to delete IVAs."},
        403: {"description": "Not authorized to delete this IVA."},
        404: {"description": "The IVA was not found."},
        422: {"description": "Validation error in submitted user identification."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.delete_user_iva")
async def delete_user_iva(
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="Internal User ID",
        ),
    ],
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> Response:
    """Delete an IVA of the given user."""
    # only data stewards can delete IVAs for other user accounts
    if not (is_steward(auth_context) or str(user_id) == auth_context.id):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this IVA."
        )
    try:
        await user_registry.delete_iva(iva_id, user_id=user_id)
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.IvaDeletionError as error:
        raise HTTPException(status_code=500, detail="Cannot delete IVA") from error
    return Response(status_code=204)


@router.post(
    "/rpc/ivas/{iva_id}/unverify",
    operation_id="unverify_iva",
    tags=TAGS_USERS,
    summary="Unverify an IVA",
    description="Endpoint used to reset an IVA to the unverified state.",
    responses={
        204: {"description": "The state of the IVA has been reset to unverified."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to unverify IVAs."},
        404: {"description": "The IVA was not found."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.unverify_iva")
async def unverify_iva(
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: StewardAuthContext,
) -> Response:
    """Unverify the specified IVA."""
    try:
        await user_registry.unverify_iva(iva_id)
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.UserRegistryIvaError as error:
        raise HTTPException(
            status_code=500, detail="Cannot unverify the IVA"
        ) from error
    return Response(status_code=204)


@router.post(
    "/rpc/ivas/{iva_id}/request-code",
    operation_id="request_code_for_iva",
    tags=TAGS_USERS,
    summary="Request verification code for an IVA",
    description="Endpoint used to request a verification code for a given IVA.",
    responses={
        204: {"description": "A verification code for the IVA has been requested."},
        401: {"description": "Not authorized to request verification codes for IVAs."},
        404: {"description": "The IVA was not found."},
        409: {"description": "The IVA does not have the proper state."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.request_code_for_iva")
async def request_code_for_iva(
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> Response:
    """Request verification code for the specified IVA."""
    try:
        await user_registry.request_iva_verification_code(
            iva_id, user_id=UUID(auth_context.id)
        )
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.IvaUnexpectedStateError as error:
        raise HTTPException(
            status_code=409, detail="The IVA does not have the proper state."
        ) from error
    except user_registry.UserRegistryIvaError as error:
        raise HTTPException(
            status_code=500, detail="Cannot request a verification code for the IVA"
        ) from error
    return Response(status_code=204)


@router.post(
    "/rpc/ivas/{iva_id}/create-code",
    operation_id="create_code_for_iva",
    tags=TAGS_USERS,
    summary="Create verification code for an IVA",
    description="Endpoint used to create a verification code for a given IVA.",
    responses={
        201: {"description": "A verification code for the IVA has been created."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to create verification codes for IVAs."},
        404: {"description": "The IVA was not found."},
        409: {"description": "The IVA does not have the proper state."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("router.create_code_for_iva")
async def create_code_for_iva(
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: StewardAuthContext,
) -> IvaVerificationCode:
    """Create a verification code for the specified IVA."""
    try:
        code = await user_registry.create_iva_verification_code(iva_id)
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.IvaUnexpectedStateError as error:
        raise HTTPException(
            status_code=409, detail="The IVA does not have the proper state."
        ) from error
    except user_registry.UserRegistryIvaError as error:
        raise HTTPException(
            status_code=500, detail="Cannot create a verification code for the IVA"
        ) from error
    return IvaVerificationCode(verification_code=code)


@router.post(
    "/rpc/ivas/{iva_id}/code-transmitted",
    operation_id="code_transmitted_for_iva",
    tags=TAGS_USERS,
    summary="Confirm verification code transmission for an IVA",
    description="Endpoint used to confirm"
    " that the verification code for an IVA has been transmitted.",
    responses={
        204: {
            "description": "The verification code for the IVA has been confirmed"
            " as transmitted."
        },
        401: {"description": "Not authenticated."},
        403: {
            "description": "Not authorized to confirm"
            " the transmission of verification codes for IVAs."
        },
        404: {"description": "The IVA was not found."},
        409: {"description": "The IVA does not have the proper state."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.confirm_code_for_iva_transmitted")
async def confirm_code_for_iva_transmitted(
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    user_registry: UserRegistryDependency,
    auth_context: StewardAuthContext,
) -> Response:
    """Confirm the transmission of a verification code for the specified IVA."""
    try:
        await user_registry.confirm_iva_code_transmission(iva_id)
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.IvaUnexpectedStateError as error:
        raise HTTPException(
            status_code=409, detail="The IVA does not have the proper state."
        ) from error
    except user_registry.UserRegistryIvaError as error:
        raise HTTPException(
            status_code=500,
            detail="Cannot confirm the transmission of a verification code for the IVA",
        ) from error
    return Response(status_code=204)


@router.post(
    "/rpc/ivas/{iva_id}/validate-code",
    operation_id="validate_code_for_iva",
    tags=TAGS_USERS,
    summary="Validate the verification code for an IVA",
    description="Endpoint used to validate the verification code for an IVA.",
    responses={
        204: {"description": "The IVA has been successfully verified."},
        401: {"description": "Not authorized to validate verification codes for IVAs."},
        403: {"description": "The submitted verification code was invalid."},
        404: {"description": "The IVA was not found."},
        409: {"description": "The IVA does not have the proper state."},
        422: {"description": "Validation error in submitted verification data."},
        429: {"description": "Too many attempts, IVA was reset to unverified state."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("router.validate_code_for_iva")
async def validate_code_for_iva(
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="IVA ID",
        ),
    ],
    data: IvaVerificationCode,
    user_registry: UserRegistryDependency,
    auth_context: UserAuthContext,
) -> Response:
    """Validate a verification code for the specified IVA."""
    try:
        verified = await user_registry.validate_iva_verification_code(
            iva_id, code=data.verification_code, user_id=UUID(auth_context.id)
        )
    except user_registry.IvaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail="The IVA was not found.") from error
    except user_registry.IvaUnexpectedStateError as error:
        raise HTTPException(
            status_code=409, detail="The IVA does not have the proper state."
        ) from error
    except user_registry.IvaTooManyVerificationAttemptsError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts, IVA was reset to unverified state.",
        ) from error
    except user_registry.UserRegistryIvaError as error:
        raise HTTPException(
            status_code=500,
            detail="Cannot validate the verification code for the IVA",
        ) from error
    if not verified:
        raise HTTPException(
            status_code=403, detail="The submitted verification code was invalid."
        )
    return Response(status_code=204)


@router.get(
    "/ivas",
    operation_id="get_all_ivas",
    tags=TAGS_USERS,
    summary="Get all IVAs",
    description="Endpoint used to get all IVAs and their corresponding users."
    " Can only be performed by a data steward.",
    responses={
        200: {
            "model": list[IvaData],
            "description": "IVAs have been retrieved.",
        },
        403: {"description": "Not authorized to request IVAs."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("router.get_all_ivas")
async def get_all_ivas(
    user_registry: UserRegistryDependency,
    _auth_context: StewardAuthContext,
    user_id: Annotated[
        UUID4 | None,
        Query(
            description="Filter for the internal user ID",
        ),
    ] = None,
    state: Annotated[
        IvaState | None,
        Query(
            description="Filter for the state of the IVA",
        ),
    ] = None,
) -> list[IvaAndUserData]:
    """Get all IVAs and their corresponding users."""
    try:
        return await user_registry.get_ivas_with_users(user_id=user_id, state=state)
    except user_registry.IvaRetrievalError as error:
        raise HTTPException(status_code=500, detail="Cannot retrieve IVAs.") from error


# The following endpoints are actually shadowed and handled by the auth adapter.
# They are duplicated here as stubs in order to provide the complete OpenAPI spec.

not_implemented = NotImplementedError("Implemented by the auth adapter.")


@router.post(
    "/rpc/login",
    operation_id="login",
    tags=TAGS_SESSION,
    summary="Create or get user session",
    description="Endpoint used when a user wants to log in",
    status_code=204,
)
async def login(
    authorization: Annotated[str | None, Header()] = None,
    x_authorization: Annotated[str | None, Header()] = None,
) -> Response:
    raise not_implemented


@router.post(
    "/rpc/logout",
    operation_id="logout",
    tags=TAGS_SESSION,
    summary="End user session",
    description="Endpoint used when a user wants to log out",
    status_code=204,
)
async def logout() -> Response:
    raise not_implemented


@router.post(
    "/totp-token",
    operation_id="create_new_totp_token",
    tags=TAGS_TOTP,
    summary="Create a new TOTP token",
    description="Endpoint used to create or replace a TOTP token",
    status_code=201,
)
async def create_new_totp_token(
    force: bool = Query(False, title="Overwrite existing token"),
) -> TOTPTokenResponse:
    raise not_implemented


@router.post(
    "/rpc/verify-totp",
    operation_id="verify_totp",
    tags=TAGS_TOTP,
    summary="Verify a TOTP code",
    description="Endpoint used to verify a TOTP code",
    status_code=204,
)
async def rpc_verify_totp(
    x_authorization: Annotated[
        str | None, Header(title="the TOTP code to verify")
    ] = None,
) -> Response:
    raise not_implemented
