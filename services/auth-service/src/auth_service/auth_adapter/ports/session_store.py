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

"""Port for managing user sessions that keep track of authentication state."""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


class BaseSession(BaseModel, ABC):
    """Base class for user sessions."""

    session_id: str = Field(default=..., description="Unique session ID")

    model_config = {"extra": "forbid"}


T = TypeVar("T", bound=BaseSession)


class SessionStorePort(ABC, Generic[T]):
    """Port providing a store for user sessions."""

    @abstractmethod
    async def create_session(self, **kwargs: Any) -> T:
        """Create a new user session in the store and return it.

        Non-default fields of the session must be passed as keyword arguments.
        """
        ...

    @abstractmethod
    async def save_session(self, session: T, **kwargs: Any) -> None:
        """Save an existing user session back to the store.

        Pass additional data used for updating the session as keyword arguments.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[T]:
        """Get a valid user session with a given ID.

        If no such valid user session exists, return None.
        If it exists but is invalid, remove it from the store and return None.
        """
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a user session with a given ID.

        If no such user session exists, do nothing.
        """
        ...

    @abstractmethod
    async def get_size(self) -> int:
        """Get the number of currently stored sessions."""
        ...

    @abstractmethod
    async def sweep(self) -> None:
        """Remove all invalid sessions from the store."""
        ...

    @abstractmethod
    def timeouts(self, session: T) -> tuple[int, int]:
        """Get the soft and hard expiration times of the given session in seconds."""
        ...
