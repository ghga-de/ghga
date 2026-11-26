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

"""Checking user sessions against the current state of the user account."""

from hashlib import sha256

from fastapi import HTTPException, status

from auth_service.user_registry.models.users import UserStatus
from auth_service.user_registry.ports.dao import UserDao
from hexkit.protocols.dao import ResourceNotFoundError

from ..ports.dao import UserTokenDao
from ..ports.session_store import SessionStorePort
from .session_store import AsyncUserRoleFetcher, Session, SessionState
from .totp import TOTPToken

__all__ = [
    "account_deleted_error",
    "account_disabled_error",
    "check_session",
    "session_ended_error",
    "totp_token_hash",
]

# states in which the session carries the roles of the user
STATES_WITH_ROLES = frozenset(
    {
        SessionState.REGISTERED,
        SessionState.NEW_TOTP_TOKEN,
        SessionState.HAS_TOTP_TOKEN,
        SessionState.AUTHENTICATED,
    }
)


def account_deleted_error() -> HTTPException:
    """Get the error for a session whose user account has been deleted."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User account has been deleted",
    )


def account_disabled_error() -> HTTPException:
    """Get the error for a user whose account is disabled."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User account is disabled",
    )


def session_ended_error() -> HTTPException:
    """Get the error for a session that has been ended by the backend."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session has ended",
    )


def totp_token_hash(token: TOTPToken) -> str:
    """Get a hash that identifies the given TOTP token.

    The encrypted secret does not change while the token is in use,
    so the hash changes only when the token is replaced.
    """
    return sha256(token.encrypted_secret.encode("ascii")).hexdigest()


async def check_session(
    session: Session,
    *,
    session_store: SessionStorePort[Session],
    user_dao: UserDao,
    token_dao: UserTokenDao,
    get_roles: AsyncUserRoleFetcher,
) -> None:
    """Check the given session against the current state of the user account.

    If the user has been deleted or disabled, or if the TOTP token that
    authenticated the session has been replaced, then the session is deleted and
    an HTTPException is raised. Otherwise, the roles of the session are fetched
    again. The caller must save the session afterwards.
    """
    user_id = session.user_id
    if not user_id:
        return
    try:
        user = await user_dao.get_by_id(user_id)
    except ResourceNotFoundError as error:
        await session_store.delete_session(session.session_id)
        raise account_deleted_error() from error
    if user.status is not UserStatus.ACTIVE:
        await session_store.delete_session(session.session_id)
        raise account_disabled_error()
    if session.state is SessionState.AUTHENTICATED:
        try:
            user_token = await token_dao.get_by_id(user_id)
        except ResourceNotFoundError:
            user_token = None
        if (
            not user_token
            or totp_token_hash(user_token.totp_token) != session.totp_token_hash
        ):
            await session_store.delete_session(session.session_id)
            raise session_ended_error()
    if session.state in STATES_WITH_ROLES:
        session.roles = await get_roles(user)
