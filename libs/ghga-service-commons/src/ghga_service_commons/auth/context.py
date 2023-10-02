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

"""Protocol for retrieving a context for authentication and authorization."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

__all__ = ["AuthContext", "AuthContextProtocol"]


# type variable for handling different kinds of auth contexts
AuthContext = TypeVar("AuthContext", bound=BaseModel)


class AuthContextProtocol(ABC, Generic[AuthContext]):
    """A protocol for retrieving an authentication and authorization context."""

    class AuthContextValidationError(RuntimeError):
        """Error that is raised when the underlying token is invalid."""

    @abstractmethod
    async def get_context(self, token: str) -> Optional[AuthContext]:
        """Derive an authentication and authorization context from a token.

        The protocol is independent of the underlying serialization format.

        Raises an AuthContextValidationError if the provided token cannot establish
        a valid authentication and authorization context.

        Calling this may involve fetching public keys or other data over the network.
        """
        ...
