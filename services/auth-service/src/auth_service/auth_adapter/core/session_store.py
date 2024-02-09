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

"""Managing user sessions that keep track of authentication state."""

import secrets
from typing import Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import Field
from pydantic_settings import BaseSettings

from ..ports.session_store import BaseSession, SessionStorePort


class Session(BaseSession):
    """Model for storing user sessions."""

    user_id: Optional[str] = Field(
        default=None, description="the internal ID of the associated user"
    )
    created: UTCDatetime = Field(description="Time when the session was created")
    last_used: UTCDatetime = Field(description="Time when the session was last used")


class SessionConfig(BaseSettings):
    """Configuration parameters for the sessions."""

    session_id_bytes: int = Field(
        default=24,
        title="Session ID size",
        description="Number of bytes to be used for the session ID.",
    )
    timeout_seconds: int = Field(
        default=1 * 60 * 60,
        title="Session timeout",
        description="Session timeout in seconds",
    )
    max_lifetime_seconds: int = Field(
        default=12 * 60 * 60,
        title="Max. session duration",
        description="Maximum lifetime of a session in seconds",
    )


class SessionStore(SessionStorePort[Session]):
    """A store for user sessions that is independent of the storage mechanism."""

    def __init__(
        self,
        *,
        config: SessionConfig,
    ):
        """Create a session store.

        Functions for creating and validating sessions must be provided.
        """
        self.config = config

    def _now(self) -> UTCDatetime:
        """Get the current time. Override this method for testing."""
        return now_as_utc()

    def _generate_session_id(self) -> str:
        """Generate a random session ID."""
        return secrets.token_urlsafe(self.config.session_id_bytes)

    def _create_session(self) -> Session:
        """Create a new session without saving it."""
        session_id = self._generate_session_id()
        created = self._now()
        return Session(session_id=session_id, created=created, last_used=created)

    def _validate_session(self, session: Session) -> bool:
        """Validate a session."""
        config = self.config
        now = self._now()
        return (
            0 <= (now - session.created).seconds < config.max_lifetime_seconds
            and 0 <= (now - session.last_used).seconds < config.timeout_seconds
        )
