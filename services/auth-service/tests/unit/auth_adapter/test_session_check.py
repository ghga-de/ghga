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

"""Test checking user sessions against the user account."""

from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from pydantic import SecretStr

from auth_service.auth_adapter.adapters.memory_session_store import MemorySessionStore
from auth_service.auth_adapter.core.session_check import check_session, totp_token_hash
from auth_service.auth_adapter.core.session_store import Session, SessionState
from auth_service.auth_adapter.core.totp import TOTPHandler
from auth_service.auth_adapter.ports.dao import UserToken, UserTokenDao
from auth_service.config import Config
from auth_service.user_registry.models.users import UserStatus
from auth_service.user_registry.ports.dao import UserDao
from tests.fixtures.constants import ID_OF_JOHN

from ...fixtures.utils import MockUserDao, MockUserTokenDao

pytestmark = pytest.mark.asyncio()

config = Config(
    totp_encryption_key=SecretStr(TOTPHandler.random_encryption_key()),
)
totp_handler = TOTPHandler(config=config)


class Setup:
    """The session, store, DAOs and role fetcher for one test."""

    def __init__(self, session: Session, store: MemorySessionStore):
        self.session = session
        self.store = store
        self.user_dao = MockUserDao()
        self.token_dao = MockUserTokenDao()
        self.get_roles = AsyncMock(return_value=["role_from_database"])

    async def check(self) -> None:
        """Check the session."""
        await check_session(
            self.session,
            session_store=self.store,
            user_dao=cast(UserDao, self.user_dao),
            token_dao=cast(UserTokenDao, self.token_dao),
            get_roles=self.get_roles,
        )

    async def session_exists(self) -> bool:
        """Check whether the session is still in the store."""
        return bool(await self.store.get_session(self.session.session_id))


async def setup(state: SessionState = SessionState.AUTHENTICATED) -> Setup:
    """Set up a session of John in the given state with a stored TOTP token."""
    store = MemorySessionStore(config=config)
    session = await store.create_session(
        ext_id="john@aai.org",
        user_name="John Doe",
        user_email="john@home.org",
        user_id=ID_OF_JOHN,
        roles=["role_from_login"],
    )
    session.state = state
    result = Setup(session, store)
    token = totp_handler.generate_token()
    await result.token_dao.upsert(UserToken(user_id=ID_OF_JOHN, totp_token=token))
    if state is SessionState.AUTHENTICATED:
        session.totp_token_hash = totp_token_hash(token)
    return result


async def test_check_session_of_active_user():
    """Test that the session of an active user gets the current roles."""
    s = await setup()
    await s.check()
    s.get_roles.assert_awaited_once_with(s.user_dao.user)
    assert s.session.roles == ["role_from_database"]
    assert s.session.state is SessionState.AUTHENTICATED
    assert await s.session_exists()


async def test_check_session_of_deleted_user():
    """Test that the session of a deleted user ends."""
    s = await setup()
    s.user_dao.users.clear()
    with pytest.raises(HTTPException) as exc_info:
        await s.check()
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "User account has been deleted"
    s.get_roles.assert_not_called()
    assert not await s.session_exists()


async def test_check_session_of_disabled_user():
    """Test that the session of a disabled user ends."""
    s = await setup()
    s.user_dao.users[-1] = s.user_dao.user.model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    with pytest.raises(HTTPException) as exc_info:
        await s.check()
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User account is disabled"
    s.get_roles.assert_not_called()
    assert not await s.session_exists()


@pytest.mark.parametrize("deleted", [False, True], ids=["replaced", "deleted"])
async def test_check_session_with_changed_totp_token(deleted: bool):
    """Test that a session ends when its TOTP token is replaced or deleted."""
    s = await setup()
    if deleted:
        s.token_dao.user_tokens.clear()
    else:
        new_token = totp_handler.generate_token()
        await s.token_dao.upsert(UserToken(user_id=ID_OF_JOHN, totp_token=new_token))
    with pytest.raises(HTTPException) as exc_info:
        await s.check()
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Session has ended"
    s.get_roles.assert_not_called()
    assert not await s.session_exists()


@pytest.mark.parametrize(
    "state",
    [SessionState.REGISTERED, SessionState.NEW_TOTP_TOKEN, SessionState.HAS_TOTP_TOKEN],
)
async def test_check_session_before_second_factor(state: SessionState):
    """Test that the TOTP token is compared only for authenticated sessions.

    The roles are fetched for all registered sessions.
    """
    s = await setup(state)
    new_token = totp_handler.generate_token()
    await s.token_dao.upsert(UserToken(user_id=ID_OF_JOHN, totp_token=new_token))
    await s.check()
    assert s.session.roles == ["role_from_database"]
    assert s.session.state is state
    assert await s.session_exists()


@pytest.mark.parametrize(
    "state", [SessionState.NEEDS_REGISTRATION, SessionState.NEEDS_RE_REGISTRATION]
)
async def test_check_session_before_registration(state: SessionState):
    """Test that the roles of a session are kept before the user is registered."""
    s = await setup(state)
    await s.check()
    s.get_roles.assert_not_called()
    assert s.session.roles == ["role_from_login"]
    assert await s.session_exists()


async def test_check_session_without_user_id():
    """Test that a session without user ID is not checked."""
    s = await setup(SessionState.NEEDS_REGISTRATION)
    s.session.user_id = None
    s.user_dao.users.clear()
    await s.check()
    s.get_roles.assert_not_called()
    assert await s.session_exists()
