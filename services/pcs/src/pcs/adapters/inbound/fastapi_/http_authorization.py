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
"""Authorization specific code for FastAPI"""

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.policies import require_auth_context_using_credentials
from ghga_service_commons.utils.simple_token import check_token
from pydantic import BaseModel, Field

from pcs.adapters.inbound.fastapi_ import dummies

__all__ = ["require_token", "TokenAuthContext"]


class TokenAuthContext(BaseModel):
    """Auth context holding the ingest token."""

    token: str = Field(
        ...,
        description="A simple alphanumeric token to authenticate the deletion request",
    )


class TokenAuthProvider(AuthContextProtocol[TokenAuthContext]):
    """Provider for the ingest token auth context"""

    def __init__(self, *, token_hashes: list[str]):
        self._token_hashes = token_hashes

    async def get_context(self, token: str) -> TokenAuthContext:
        """Get ingest token auth context"""
        if not check_token(token=token, token_hashes=self._token_hashes):
            raise self.AuthContextValidationError("Invalid Token")

        return TokenAuthContext(token=token)


async def require_token_context(
    service_config: dummies.TokenHashConfigDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> TokenAuthContext:
    """Require a VIP authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials=credentials,
        auth_provider=TokenAuthProvider(token_hashes=service_config.token_hashes),
    )


require_token = Security(require_token_context)
