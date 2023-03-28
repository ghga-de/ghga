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

"""App specific policies using the AuthContext provider with FastAPI.

See the router.py module for how to use these policies in REST endpoints.
"""

from typing import Optional

from auth_demo.auth.config import DemoAuthContext
from auth_demo.container import Container  # type: ignore
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)

__all__ = ["DemoAuthContext", "get_auth", "require_auth", "require_vip"]


@inject
async def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    auth_provider: AuthContextProtocol[DemoAuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> Optional[DemoAuthContext]:
    """Get an authentication and authorization context using FastAPI."""
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    return context  # workaround mypy issue #12156


@inject
async def require_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    auth_provider: AuthContextProtocol[DemoAuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> DemoAuthContext:
    """Require an authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(credentials, auth_provider)


def check_vip(context: DemoAuthContext) -> bool:
    """Check if the given auth context belongs to a VIP."""
    return context.is_vip


@inject
async def require_vip_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    auth_provider: AuthContextProtocol[DemoAuthContext] = Depends(
        Provide[Container.auth_provider]
    ),
) -> DemoAuthContext:
    """Require a VIP authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, check_vip
    )


# policy for getting an auth token without requiring its existence
get_auth = Security(get_auth_context)

# policy for requiring and getting an auth token
require_auth = Security(require_auth_context)

# policy fo requiring and getting an auth token with VIP status
require_vip = Security(require_vip_context)
