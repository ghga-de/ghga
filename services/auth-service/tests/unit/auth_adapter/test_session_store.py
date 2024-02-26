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

"""Test the core user session store functionality."""

from datetime import timedelta
from typing import Any, Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime, utc_datetime
from pytest import mark

from auth_service.auth_adapter.core.session_store import (
    Session,
    SessionConfig,
    SessionState,
    SessionStore,
)
from auth_service.user_management.user_registry.models.dto import User, UserStatus


class CoreSessionStore(SessionStore):
    """A core user session store for testing."""

    def _now(self) -> UTCDatetime:
        """Get a fixed for testing."""
        return utc_datetime(2024, 12, 24, 12, 24, 48)

    async def create_session(self, **kwargs: Any) -> Session:
        """Create a new user session in the store and return it."""
        raise NotImplementedError

    async def save_session(self, session: Session, **kwargs: Any) -> None:
        """Save an existing user session back to the store."""
        await self._update_session(session, **kwargs)
        self.saved_session = session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a valid user session with a given ID."""
        raise NotImplementedError

    async def delete_session(self, session_id: str) -> None:
        """Delete a user session with a given ID.

        If no such user session exists, do nothing.
        """
        raise NotImplementedError

    async def get_size(self) -> int:
        """Get the number of currently stored sessions."""
        raise NotImplementedError

    async def sweep(self) -> None:
        """Remove all invalid sessions from the store."""
        raise NotImplementedError


def test_create_session():
    """Test generation of sessions."""
    config = SessionConfig()
    session_id_bytes = config.session_id_bytes
    assert session_id_bytes >= 16
    session_id_length = session_id_bytes * 4 // 3  # because of base64 encoding
    csrf_token_bytes = config.csrf_token_bytes
    assert csrf_token_bytes >= 16
    csrf_token_length = csrf_token_bytes * 4 // 3
    store = CoreSessionStore(config=config)
    now = store._now()
    create_session = store._create_session
    session_ids = []
    csrf_tokens = []
    for _ in range(100):
        session = create_session(
            user_id="some-user-id", user_name="John Doe", user_email="john@home.org"
        )
        assert isinstance(session, Session)
        session_id = session.session_id
        assert isinstance(session_id, str)
        assert len(session_id) == session_id_length
        assert session_id.replace("-", "").replace("_", "").isalnum()
        csrf_token = session.csrf_token
        assert isinstance(csrf_token, str)
        assert len(csrf_token) == csrf_token_length
        # check that the session ID contains only URL safe characters
        assert csrf_token.replace("-", "").replace("_", "").isalnum()
        session_ids.append(session_id)
        csrf_tokens.append(csrf_token)
        assert session.user_id == "some-user-id"
        assert session.user_name == "John Doe"
        assert session.user_email == "john@home.org"
        assert session.created == now
        assert session.last_used == now
    # make sure that no duplicate session IDs are created
    session_id_set = set(session_ids)
    assert len(session_id_set) == len(session_ids)
    # make sure that different CSRF tokens are created
    csrf_token_set = set(csrf_tokens)
    assert len(csrf_token_set) >= len(csrf_tokens) * 0.75
    # make sure that they are different from the session IDs
    assert len(session_id_set & csrf_token_set) < len(session_ids) * 0.25


def test_validate_session():
    """Test validation of sessions."""
    config = SessionConfig()
    timeout_seconds = config.session_timeout_seconds
    max_lifetime_seconds = config.session_max_lifetime_seconds
    store = CoreSessionStore(config=config)
    validate = store._validate_session
    create_session = store._create_session
    session = create_session(
        user_id="some-user-id", user_name="John Doe", user_email="john@home.org"
    )

    now = store._now()
    assert validate(session)

    session.created = now - timedelta(seconds=1.5 * max_lifetime_seconds)
    assert not validate(session)
    session.created = now - timedelta(seconds=0.5 * max_lifetime_seconds)
    assert validate(session)
    session.last_used = now - timedelta(seconds=1.5 * timeout_seconds)
    assert not validate(session)

    session.created = session.last_used = now - timedelta(seconds=1)
    assert validate(session)
    session.created = session.last_used = now + timedelta(seconds=1)
    assert not validate(session)


@mark.asyncio
@mark.parametrize(
    "original_state",
    [
        SessionState.NEEDS_REGISTRATION,
        SessionState.NEEDS_RE_REGISTRATION,
        SessionState.REGISTERED,
        SessionState.HAS_TOTP_TOKEN,
    ],
)
async def test_update_session_last_used_without_user(original_state: SessionState):
    """Test updating a session without user object, should not update state."""
    config = SessionConfig()
    store = CoreSessionStore(config=config)
    now = store._now()
    before = now - timedelta(seconds=10)
    session = Session(
        session_id="test",
        state=original_state,
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=before,
        last_used=before,
    )
    await store.save_session(session)
    assert store.saved_session is session
    assert session.state == original_state
    assert session.created == before
    assert session.last_used == now


@mark.asyncio
@mark.parametrize("changed_field", ["name", "email"])
async def test_update_session_with_user_to_needs_re_registration(changed_field: str):
    """Test updating a session to the needs-re-registration state."""
    config = SessionConfig()
    store = CoreSessionStore(config=config)
    now = store._now()
    before = now - timedelta(seconds=10)
    session = Session(
        session_id="test",
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=before,
        last_used=before,
    )
    assert session.state is SessionState.NEEDS_REGISTRATION
    user = User(
        id="some-user-id",
        ext_id="some-ext-id@home.org",
        name="John Doe",
        email="john@home.org",
        status=UserStatus.ACTIVE,
        registration_date=before,
    )
    changed_value = getattr(user, changed_field).replace("ohn", "oe")
    user = user.model_copy(update={changed_field: changed_value})
    await store.save_session(session, user=user)
    assert store.saved_session is session
    assert session.created == before
    assert session.last_used == now
    assert session.state is SessionState.NEEDS_RE_REGISTRATION


@mark.asyncio
@mark.parametrize(
    "original_state",
    [
        SessionState.NEEDS_REGISTRATION,
        SessionState.NEEDS_RE_REGISTRATION,
        SessionState.REGISTERED,
    ],
)
async def test_update_session_with_user_to_registered(original_state: SessionState):
    """Test updating a session to the registered state."""
    config = SessionConfig()
    store = CoreSessionStore(config=config)
    now = store._now()
    before = now - timedelta(seconds=10)
    session = Session(
        session_id="test",
        state=original_state,
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=before,
        last_used=before,
    )
    user = User(
        id="some-user-id",
        ext_id="some-ext-id@home.org",
        name="John Doe",
        email="john@home.org",
        status=UserStatus.ACTIVE,
        registration_date=before,
    )
    await store.save_session(session, user=user)
    assert store.saved_session is session
    assert session.created == before
    assert session.last_used == now
    assert session.state is SessionState.REGISTERED


@mark.asyncio
@mark.parametrize(
    "original_state",
    [
        SessionState.NEEDS_REGISTRATION,
        SessionState.NEEDS_RE_REGISTRATION,
        SessionState.REGISTERED,
        SessionState.HAS_TOTP_TOKEN,
    ],
)
async def test_update_session_with_user_to_has_totp_token(original_state: SessionState):
    """Test updating a session to the has-totp-state."""
    config = SessionConfig()
    store = CoreSessionStore(config=config)
    now = store._now()
    before = now - timedelta(seconds=10)
    session = Session(
        session_id="test",
        state=original_state,
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=before,
        last_used=before,
    )
    user = User(
        id="some-user-id",
        ext_id="some-ext-id@home.org",
        name="John Doe",
        email="john@home.org",
        status=UserStatus.ACTIVE,
        registration_date=before,
    )

    async def has_totp_token(user: User) -> bool:
        return True

    await store.save_session(session, user=user, has_totp_token=has_totp_token)
    assert store.saved_session is session
    assert session.created == before
    assert session.last_used == now
    assert session.state is SessionState.HAS_TOTP_TOKEN


def test_timeouts():
    """Test getting the session timeouts."""
    config = SessionConfig()
    store = CoreSessionStore(config=config)
    now = store._now()
    session = Session(
        session_id="test",
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=now - timedelta(seconds=2 * 60 * 60),
        last_used=now - timedelta(seconds=20 * 60),
    )
    assert store.timeouts(session) == (40 * 60, 10 * 60 * 60)
    session.created = now - timedelta(seconds=12 * 60 * 60 - 10 * 60)
    assert store.timeouts(session) == (10 * 60, 10 * 60)
