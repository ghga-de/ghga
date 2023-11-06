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
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.ghga import AuthContext, has_role, is_active
from ghga_service_commons.auth.policies import require_auth_context_using_credentials

from ars.adapters.inbound.fastapi_ import dummies
from ars.core.roles import DATA_STEWARD_ROLE

__all__ = ["require_user_context", "require_steward_context"]


async def _require_user_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))
    ],
    auth_provider: dummies.AuthProviderDummy,
) -> AuthContext:
    """Require an active GHGA auth context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_active
    )


is_steward = partial(has_role, role=DATA_STEWARD_ROLE)


async def _require_steward_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))
    ],
    auth_provider: dummies.AuthProviderDummy,
) -> AuthContext:
    """Require an active GHGA auth context of a data steward using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, is_steward
    )


# policy for requiring an active user auth context
require_user_context = Security(_require_user_context)

# policy for requiring an active data steward auth context
require_steward_context = Security(_require_steward_context)
