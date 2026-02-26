# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Authorization specific code for FastAPI"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.jwt_auth import JWTAuthContextProvider
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import BaseModel, Field

from fis.adapters.inbound.fastapi_ import dummies
from fis.constants import GHGA

__all__ = ["AuthProviders", "require_data_hub_jwt"]


class JWT(BaseModel):
    """A JSON Web Token model"""

    iss: str = Field(default=..., title="Issuer")
    aud: str = Field(default=..., title="Audience")
    sub: str = Field(default=..., title="Subject")
    iat: UTCDatetime = Field(default=..., title="Issued at")
    exp: UTCDatetime = Field(default=..., title="Expiration time")


AuthProviders = dict[str, JWTAuthContextProvider[JWT]]


async def _require_data_hub_jwt(
    storage_alias: str,
    auth_providers: Annotated[AuthProviders, Depends(dummies.auth_providers_dummy)],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> JWT:
    """Require a JWT signed by the Data Hub (storage_alias) making the request."""
    provider = auth_providers.get(storage_alias)
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if provider is None:
        raise RuntimeError(f"No auth provider found for storage_alias {storage_alias}")

    try:
        context = await provider.get_context(token)
    except JWTAuthContextProvider.AuthContextValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        ) from err

    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if (
        context.exp < context.iat
        or context.iss != GHGA
        or context.aud != GHGA
        or context.sub != storage_alias
        or context.exp <= now_as_utc()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    return context


require_data_hub_jwt = Security(_require_data_hub_jwt)
