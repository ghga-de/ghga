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
from typing import Optional

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_auth.container import Container  # type: ignore

from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.ghga import AuthContext, has_role, is_active
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)

__all__ = ["AuthContext", "get_auth", "require_admin", "require_active", "require_auth"]


@inject
async def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    auth_provider: AuthContextProtocol[AuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> Optional[AuthContext]:
    """Get a GHGA authentication and authorization context using FastAPI."""
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    return context  # workaround mypy issue #12156


@inject
async def require_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    auth_provider: AuthContextProtocol[AuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> AuthContext:
    """Require a GHGA authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(credentials, auth_provider)


@inject
async def require_active_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    auth_provider: AuthContextProtocol[AuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> AuthContext:
    """Require an active GHGA auth context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_active
    )


is_admin = partial(has_role, role="admin")


@inject
async def require_admin_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    auth_provider: AuthContextProtocol[AuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> AuthContext:
    """Require an active GHGA auth context with admin role using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_admin
    )


# policy for getting an auth context without requiring its existence
get_auth = Security(get_auth_context)

# policy for requiring and getting an auth context
require_auth = Security(require_auth_context)

# policy for requiring and getting an active auth context
require_active = Security(require_active_context)

# policy fo requiring and getting an active auth context with admin role
require_admin = Security(require_admin_context)
