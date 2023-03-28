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

"""Authentication and authorization policies that can be used with FastAPI.

See the auth_demo and ghga_auth examples for how to use these policies.
"""

from typing import Callable, Optional

from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.status import HTTP_403_FORBIDDEN

from ghga_service_commons.auth.context import AuthContext, AuthContextProtocol

__all__ = [
    "get_auth_context_using_credentials",
    "require_auth_context_using_credentials",
]


async def get_auth_context_using_credentials(
    credentials: HTTPAuthorizationCredentials,
    auth_provider: AuthContextProtocol[AuthContext],
) -> Optional[AuthContext]:
    """Get an authentication and authorization context using FastAPI.

    Unauthenticated access is allowed and will return None as auth context.
    """
    token = credentials.credentials if credentials else None
    if not token:
        return None
    try:
        return await auth_provider.get_context(token)
    except auth_provider.AuthContextValidationError as error:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials",
        ) from error


async def require_auth_context_using_credentials(
    credentials: HTTPAuthorizationCredentials,
    auth_provider: AuthContextProtocol[AuthContext],
    predicate: Callable[[AuthContext], bool] = lambda _context: True,
) -> AuthContext:
    """Require an authentication and authorization context using FastAPI.

    Unauthenticated access is not allowed and will raise a "Forbidden" error.
    If a predicate function is specified, it will be also checked.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
    try:
        context = await auth_provider.get_context(token)
        if not context:
            raise auth_provider.AuthContextValidationError("Not authenticated")
    except auth_provider.AuthContextValidationError as error:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials",
        ) from error
    if not predicate(context):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authorized")
    return context
