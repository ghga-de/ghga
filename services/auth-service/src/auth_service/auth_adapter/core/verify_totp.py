# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import logging
from contextlib import suppress
from typing import Any

from fastapi import HTTPException, status

from auth_service.user_registry.models.users import (
    User,
    UserModifiableData,
    UserStatus,
)
from auth_service.user_registry.ports.registry import UserRegistryPort
from hexkit.protocols.dao import PreconditionFailedError, ResourceNotFoundError

from ..ports.dao import UserToken, UserTokenDao
from ..ports.session_store import SessionStorePort
from ..ports.totp import TOTPHandlerPort
from .session_check import (
    account_deleted_error,
    account_disabled_error,
    totp_token_hash,
)
from .session_store import AsyncUserRoleFetcher, Session, SessionState

__all__ = ["verify_totp"]

log = logging.getLogger(__name__)


def _token_state(user_token: UserToken) -> dict[str, Any]:
    """Get the state of a stored TOTP token as a precondition for writing it back."""
    totp_token = user_token.totp_token
    return {
        "totp_token.encrypted_secret": totp_token.encrypted_secret,
        "totp_token.last_counter": totp_token.last_counter,
        "totp_token.counter_attempts": totp_token.counter_attempts,
        "totp_token.total_attempts": totp_token.total_attempts,
    }


async def _write_back_token(
    token_dao: UserTokenDao, user_token: UserToken, state: dict[str, Any]
) -> bool:
    """Write back a stored TOTP token if it still has the given state.

    Returns False if another request has changed or replaced the token meanwhile.
    """
    try:
        await token_dao.update(user_token, precondition=state)
    except PreconditionFailedError, ResourceNotFoundError:
        return False
    return True


async def verify_totp(  # noqa: C901, PLR0912, PLR0913, PLR0915
    totp: str,
    *,
    session_store: SessionStorePort,
    session: Session,
    totp_handler: TOTPHandlerPort,
    user_registry: UserRegistryPort,
    token_dao: UserTokenDao,
    get_roles: AsyncUserRoleFetcher,
) -> None:
    """Verify the given TOTP code for the user with the given ID.

    As a side effect, the TOTP token is stored in the database if it is still only
    available in the session. In that case, already verified IVAs are reset.
    The roles of the session are fetched again, since they depend on these IVAs.
    A token that was already stored is written back when an attempt has changed
    its usage counters, unless it has been changed or replaced concurrently.
    """
    user_id = session.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not registered",
        )
    try:
        user = await user_registry.get_user(user_id)
    except user_registry.UserDoesNotExistError as error:
        # the account was deleted after the user logged in
        await session_store.delete_session(session.session_id)
        raise account_deleted_error() from error
    if user.status is not UserStatus.ACTIVE:
        # the account was disabled after the user logged in
        await session_store.delete_session(session.session_id)
        raise account_disabled_error()
    user_token: UserToken | None = None
    if session.state == SessionState.NEW_TOTP_TOKEN:
        # get not yet verified TOTP token from the session
        totp_token = session.totp_token
        # failed attempts with a token that is not stored yet end the session only
        account_to_disable: User | None = None
    else:
        # get verified TOTP token from the database
        with suppress(ResourceNotFoundError):
            user_token = await token_dao.get_by_id(user.id)
        totp_token = user_token.totp_token if user_token else None
        account_to_disable = user
    # The usage counters of a stored token change with every attempt.
    # Concurrent attempts must not overwrite each other's counters,
    # so the token is written back only if it is still in the state read here.
    token_state = _token_state(user_token) if user_token else {}
    if totp_token and totp:
        if totp_handler.is_invalid(totp_token):
            limit = True
            verified = None
            # reset the TOTP token again
            totp_handler.reset(totp_token)
            # too many invalid TOTP codes
            if account_to_disable and user_token:
                # Disable the user account first (only the specified fields will be
                # changed), so that the token stays at the limit if this fails.
                modified_user_data = UserModifiableData(status=UserStatus.INACTIVE)
                await user_registry.update_user(
                    account_to_disable.id,
                    modified_user_data,
                    context="Too many failed TOTP login attempts",
                    changed_by=session.user_id,
                )
                log.warning(
                    "Too many failed TOTP login attempts for user %s (%s)",
                    account_to_disable.id,
                    account_to_disable.name,
                )
                # Then store the cleared token, so that users can work again after
                # they have been reactivated, unless it has changed concurrently.
                await _write_back_token(token_dao, user_token, token_state)
            # remove the session (logging the user out)
            await session_store.delete_session(session.session_id)
        else:
            limit = False
            verified = totp_handler.verify_code(totp_token, totp)
    else:
        limit = False
        verified = None
    if (
        user_token
        and verified is not None
        and not await _write_back_token(token_dao, user_token, token_state)
    ):
        # the token has been changed or replaced concurrently, so this attempt fails
        verified = False
    if not verified:
        if verified is not None:
            await session_store.save_session(session)
        if limit and account_to_disable:
            # the account is disabled now, which login() will report as well
            raise account_disabled_error()
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
    # the roles depend on the IVAs, which may have changed since login
    session.roles = await get_roles(user)
    # remember the token, so that the session ends when the token is replaced
    session.totp_token_hash = totp_token_hash(totp_token) if totp_token else None
    session.totp_token = None  # remove verified TOTP token from the session
    session.state = SessionState.AUTHENTICATED
    await session_store.save_session(session, checked=True)
