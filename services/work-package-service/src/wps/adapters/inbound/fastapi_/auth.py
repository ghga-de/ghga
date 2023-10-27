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

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.ghga import AuthContext, is_active
from ghga_service_commons.auth.policies import require_auth_context_using_credentials

from wps.adapters.inbound.fastapi_.dummies import auth_provider

__all__ = ["RequiresAuthContext", "RequiresWorkPackageAccessToken"]


async def require_active_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))
    ],
    auth_provider: Annotated[AuthContextProtocol[AuthContext], Depends(auth_provider)],
) -> AuthContext:
    """Require an active GHGA auth context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_active
    )


async def require_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))
    ],
) -> str:
    """Require an access token using FastAPI."""
    return credentials.credentials


# policy that requires (and returns) an active auth context
RequiresAuthContext = Annotated[AuthContext, Security(require_active_context)]

# policy that requires (and returns) a work package access token
RequiresWorkPackageAccessToken = Annotated[str, Security(require_access_token)]
