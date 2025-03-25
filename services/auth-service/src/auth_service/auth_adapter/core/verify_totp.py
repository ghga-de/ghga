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

"""Application logic for verifying user TOTP tokens."""

from fastapi import HTTPException, status
from hexkit.protocols.dao import ResourceNotFoundError

from auth_service.user_management.user_registry.models.users import (
    UserModifiableData,
    UserStatus,
)
from auth_service.user_management.user_registry.ports.registry import UserRegistryPort

from ..ports.dao import UserToken, UserTokenDao
from ..ports.session_store import SessionStorePort
from ..ports.totp import TOTPHandlerPort
from .session_store import Session, SessionState

__all__ = ["verify_totp"]


async def verify_totp(  # noqa: C901, PLR0912, PLR0913, PLR0915
    totp: str,
    *,
    session_store: SessionStorePort,
    session: Session,
    totp_handler: TOTPHandlerPort,
    user_registry: UserRegistryPort,
    token_dao: UserTokenDao,
) -> None:
    """Verify the given TOTP code for the user with the given ID.

    As a side effect, the TOTP token is stored in the database if it is still only
    available in the session, and possibly already verified IVAs are reset.
    """
    user_id = session.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not registered",
        )
    if session.state == SessionState.NEW_TOTP_TOKEN:
        # get not yet verified TOTP token from the session
        user = user_token = None
        totp_token = session.totp_token
    else:
        # get verified TOTP token from the database
        try:
            user = await user_registry.get_user(user_id)
        except user_registry.UserDoesNotExistError:
            user = user_token = None
        else:
            try:
                user_token = await token_dao.get_by_id(user.id)
            except ResourceNotFoundError:
                user_token = None
        totp_token = user_token.totp_token if user_token else None
    if totp_token and totp:
        if totp_handler.is_invalid(totp_token):
            limit = True
            verified = None
            # too many invalid TOTP codes
            if user and user.status is UserStatus.ACTIVE:
                # disable the user account (only the specified fields will be changed)
                modified_user_data = UserModifiableData(status=UserStatus.INACTIVE)
                await user_registry.update_user(
                    user.id,
                    modified_user_data,
                    context="Too many failed TOTP login attempts",
                    changed_by=session.user_id,
                )
            # reset the TOTP token again
            totp_handler.reset(totp_token)
            # remove the session (logging the user out)
            await session_store.delete_session(session.session_id)
        else:
            limit = False
            verified = totp_handler.verify_code(totp_token, totp)
    else:
        limit = False
        verified = None
    if not verified:
        if verified is not None:
            await session_store.save_session(session)
            if user_token:
                await token_dao.update(user_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many failed attempts" if limit else "Invalid TOTP code",
        )
    if session.state == SessionState.NEW_TOTP_TOKEN and totp_token:
        # reset all already verified IVAs
        await user_registry.reset_verified_ivas(user_id)
        # store token in the database
        user_token = UserToken(
            user_id=user_id,
            totp_token=totp_token,
        )
        # check whether a token already existed
        try:
            await token_dao.get_by_id(user_id)
        except ResourceNotFoundError:
            pass
        else:
            # notify user about the recreation of the TOTP token
            await user_registry.notify_2fa_recreation(user_id)
        # insert or update the token
        await token_dao.upsert(user_token)
    session.totp_token = None  # remove verified TOTP token from the session
    session.state = SessionState.AUTHENTICATED
    await session_store.save_session(session)
