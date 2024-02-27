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
from enum import Enum
from typing import Optional, Protocol

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings

from auth_service.user_management.user_registry.models.dto import User

from ..ports.session_store import BaseSession, SessionStorePort
from .totp import TOTPToken


class SessionState(str, Enum):
    """The state of a user session."""

    NEEDS_REGISTRATION = "NeedsRegistration"
    NEEDS_RE_REGISTRATION = "NeedsReRegistration"
    REGISTERED = "Registered"
    NEW_TOTP_TOKEN = "NewTotpToken"  # noqa: S105
    HAS_TOTP_TOKEN = "HasTotpToken"  # noqa: S105
    AUTHENTICATED = "Authenticated"


class Session(BaseSession):
    """Model for storing user sessions."""

    ext_id: str = Field(
        default=...,
        description="External ID of the associated user",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Internal ID of the associated user, if registered",
    )
    user_name: str = Field(default=..., description="The full name of the user")
    user_email: EmailStr = Field(
        default=..., description="The email address of the user"
    )
    user_title: Optional[str] = Field(
        default=None, description="Optional academic title of the user"
    )
    state: SessionState = Field(
        default=SessionState.NEEDS_REGISTRATION,
        description="The authentication state of the user session",
    )
    csrf_token: str = Field(default=..., description="The CSRF token for the session")
    totp_token: Optional[TOTPToken] = Field(
        default=None, description="The TOTP token of the user if available"
    )
    created: UTCDatetime = Field(description="Time when the session was created")
    last_used: UTCDatetime = Field(description="Time when the session was last used")


class SessionConfig(BaseSettings):
    """Configuration parameters for the sessions."""

    session_id_bytes: int = Field(
        default=24,
        title="Session ID size",
        description="Number of bytes to be used for a session ID.",
    )
    csrf_token_bytes: int = Field(
        default=24,
        title="CSRF token size",
        description="Number of bytes to be used for a CSRF token.",
    )
    session_timeout_seconds: int = Field(
        default=1 * 60 * 60,
        title="Session timeout",
        description="Session timeout in seconds",
    )
    session_max_lifetime_seconds: int = Field(
        default=12 * 60 * 60,
        title="Max. session duration",
        description="Maximum lifetime of a session in seconds",
    )


class AsyncUserPredicate(Protocol):
    """An async predicate function for users."""

    async def __call__(self, user: User) -> bool:
        """Call the predicate function."""
        ...


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

    def _generate_csrf_token(self) -> str:
        """Generate a random CSRF token."""
        return secrets.token_urlsafe(self.config.csrf_token_bytes)

    def _create_session(  # noqa: PLR0913
        self,
        ext_id: str,
        user_name: str,
        user_email: str,
        user_id: Optional[str] = None,
        user_title: Optional[str] = None,
    ) -> Session:
        """Create a new user session without saving it."""
        session_id = self._generate_session_id()
        csrf_token = self._generate_csrf_token()
        created = self._now()
        return Session(
            session_id=session_id,
            ext_id=ext_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            user_title=user_title,
            csrf_token=csrf_token,
            created=created,
            last_used=created,
        )

    def _validate_session(self, session: Session) -> bool:
        """Validate a session."""
        config = self.config
        now = self._now()
        return (
            0 <= (now - session.created).seconds < config.session_max_lifetime_seconds
            and 0 <= (now - session.last_used).seconds < config.session_timeout_seconds
        )

    @staticmethod
    def _check_re_registration(session: Session, user: User) -> bool:
        """Check if the user needs to re-register."""
        return (
            not user
            or session.user_id != user.id
            or session.ext_id != user.ext_id
            or session.user_name != user.name
            or session.user_email != user.email
        )

    async def _update_session(
        self,
        session: Session,
        user: Optional[User] = None,
        has_totp_token: Optional[AsyncUserPredicate] = None,
    ) -> None:
        """Update the given user session."""
        if user is not None and user.ext_id == session.ext_id:
            if session.state is SessionState.NEEDS_REGISTRATION:
                session.user_id = user.id
                session.state = SessionState.NEEDS_RE_REGISTRATION
            if (
                session.state is SessionState.NEEDS_RE_REGISTRATION
                and not self._check_re_registration(session, user)
            ):
                session.user_name = user.name
                session.user_email = user.email
                session.user_title = user.title
                session.state = SessionState.REGISTERED
            if (
                session.state is SessionState.REGISTERED
                and has_totp_token
                and await has_totp_token(user)
            ):
                session.state = SessionState.HAS_TOTP_TOKEN
        session.last_used = self._now()

    def timeouts(self, session: Session) -> tuple[int, int]:
        """Get the soft and hard timeouts of the given session in seconds."""
        now = self._now().timestamp()
        timeout_soft = self.config.session_timeout_seconds
        timeout_hard = self.config.session_max_lifetime_seconds
        last_used = session.last_used.timestamp()
        created = session.created.timestamp()
        timeout_soft = max(0, int(last_used + timeout_soft - now + 0.5))
        timeout_hard = max(0, int(created + timeout_hard - now + 0.5))
        if timeout_soft > timeout_hard:
            timeout_soft = timeout_hard
        return (timeout_soft, timeout_hard)
