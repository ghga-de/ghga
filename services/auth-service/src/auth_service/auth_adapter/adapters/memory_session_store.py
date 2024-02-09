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

"""An adapter for a memory based session store."""

import asyncio
from contextlib import suppress
from typing import Optional

from auth_service.auth_adapter.core.session_store import (
    Session,
    SessionConfig,
    SessionStore,
)


class MemorySessionStore(SessionStore):
    """Memory based store for user sessions."""

    def __init__(
        self,
        *,
        config: SessionConfig,
    ):
        """Initialize the memory based session store."""
        super().__init__(config=config)
        self.store: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> Session:
        """Create a new user session in the store and return it."""
        for _ in range(100):
            session = self._create_session()
            # avoid overwriting an existing session
            if session.session_id not in self.store:
                self.store[session.session_id] = session
                return session
        # should never happen with a large session ID size
        raise RuntimeError("Could not create a new session.")

    async def save_session(self, session: Session) -> None:
        """Save an existing user session back to the store.

        This also sets the last used time to the current time.
        """
        session.last_used = self._now()
        self.store[session.session_id] = session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a valid user session with a given ID.

        If no such user session exists, return None.
        If it exists but is invalid, remove it from the store and return None.
        """
        async with self._lock:
            session = self.store.get(session_id)
            if session and not self._validate_session(session):
                await self.delete_session(session.session_id)
                session = None
        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a user session with a given ID.

        If no such user session exists, do nothing.
        """
        with suppress(KeyError):
            del self.store[session_id]

    async def get_size(self) -> int:
        """Get the number of currently stored sessions."""
        return len(self.store)

    async def sweep(self) -> None:
        """Remove all invalid sessions from the store."""
        get_session = self.store.get
        validate = self._validate_session
        delete_session = self.delete_session
        lock = self._lock
        sleep = asyncio.sleep
        session_ids = list(self.store)
        for session_id in session_ids:
            async with lock:
                session = get_session(session_id)
                if session and not validate(session):
                    await delete_session(session_id)
            await sleep(0)
