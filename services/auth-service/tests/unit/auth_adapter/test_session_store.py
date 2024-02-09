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
from typing import Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime, utc_datetime

from auth_service.auth_adapter.core.session_store import (
    Session,
    SessionConfig,
    SessionStore,
)


class CoreSessionStore(SessionStore):
    """A core user session store for testing."""

    def _now(self) -> UTCDatetime:
        """Get a fixed for testing."""
        return utc_datetime(2024, 12, 24, 12, 24, 48)

    async def create_session(self) -> Session:
        """Create a new user session in the store and return it."""
        raise NotImplementedError

    async def save_session(self, session: Session) -> None:
        """Save an existing user session back to the store."""
        raise NotImplementedError

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
    expected_length = session_id_bytes * 4 // 3  # because of base64 encoding
    store = CoreSessionStore(config=config)
    now = store._now()
    create_session = store._create_session
    session_ids = []
    for _ in range(100):
        session = create_session()
        assert isinstance(session, Session)
        session_id = session.session_id
        assert isinstance(session_id, str)
        assert len(session_id) == expected_length
        # check that the session ID contains only URL safe characters
        assert session_id.replace("-", "").replace("_", "").isalnum()
        session_ids.append(session_id)
        assert session.created == now
        assert session.last_used == now
    # make sure that no duplicates are created
    assert len(session_ids) == len(set(session_ids))


def test_validate_session():
    """Test validation of sessions."""
    config = SessionConfig()
    timeout_seconds = config.timeout_seconds
    max_lifetime_seconds = config.max_lifetime_seconds
    store = CoreSessionStore(config=config)
    validate = store._validate_session
    create_session = store._create_session
    session = create_session()

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
