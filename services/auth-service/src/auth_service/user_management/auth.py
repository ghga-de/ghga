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

"""Helper dependencies for requiring authentication and authorization."""

from functools import partial
from typing import Optional

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.ghga import (
    AuthContext,
    GHGAAuthContextProvider,
    has_role,
    is_active,
)
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)

from auth_service.config import CONFIG

__all__ = [
    "AuthContext",
    "get_auth",
    "require_active",
    "require_auth",
    "require_steward",
]


auth_provider = GHGAAuthContextProvider(config=CONFIG, context_class=AuthContext)


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> Optional[AuthContext]:
    """Get a GHGA authentication and authorization context."""
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    return context  # workaround mypy issue #12156


async def require_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> AuthContext:
    """Require a GHGA authentication and authorization context."""
    return await require_auth_context_using_credentials(credentials, auth_provider)


is_steward = partial(has_role, role="data_steward")


async def require_active_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> AuthContext:
    """Require an active GHGA auth context."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_active
    )


async def require_steward_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> AuthContext:
    """Require an active GHGA auth context with data steward role."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_steward
    )


# policy for getting an auth token without requiring its existence
get_auth = Security(get_auth_context)

# policy for requiring and getting an auth context
require_auth = Security(require_auth_context)

# policy for requiring and getting an active context
require_active = Security(require_active_context)

# policy fo requiring and getting an active auth context with admin role
require_steward = Security(require_steward_context)
