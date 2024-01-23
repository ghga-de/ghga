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

"""GHGA specific policies using the AuthContext provider with FastAPI.

See the router.py module for how to use these policies in REST endpoints.
"""

from functools import partial
from typing import Annotated, Optional

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ghga_auth.dummies import AuthProviderDummy
from ghga_service_commons.auth.ghga import AuthContext, has_role
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)

__all__ = ["OptionalAuthContext", "UserAuthContext", "AdminAuthContext"]


async def get_auth_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> Optional[AuthContext]:
    """Get a GHGA authentication and authorization context using FastAPI."""
    return await get_auth_context_using_credentials(credentials, auth_provider)  # type: ignore


async def require_auth_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> AuthContext:
    """Require a GHGA authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(credentials, auth_provider)


is_admin = partial(has_role, role="admin")


async def require_admin_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> AuthContext:
    """Require a GHGA auth context with admin role using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_admin
    )


# policy for getting an auth context without requiring its existence
OptionalAuthContext = Annotated[Optional[AuthContext], Security(get_auth_context)]

# policy for requiring and getting an auth context
UserAuthContext = Annotated[AuthContext, Security(require_auth_context)]

# policy fo requiring and getting an auth context with admin role
AdminAuthContext = Annotated[AuthContext, Security(require_admin_context)]
