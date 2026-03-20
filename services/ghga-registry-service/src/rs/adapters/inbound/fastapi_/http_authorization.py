# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from rs.adapters.inbound.fastapi_ import dummies
from rs.adapters.inbound.fastapi_ import rest_models as models

__all__ = ["require_map_file_ids_work_order"]

MapFileIdsProvider = JWTAuthContextProvider[models.MapFileIdsWorkOrder]


async def _require_map_file_ids_work_order(
    auth_provider: Annotated[
        JWTAuthContextProvider[models.MapFileIdsWorkOrder],
        Depends(dummies.auth_provider_dummy),
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.MapFileIdsWorkOrder:
    """Require a "map file IDs" work order context using FastAPI."""
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        context = await auth_provider.get_context(token)
    except JWTAuthContextProvider.AuthContextValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        ) from err

    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return context


require_map_file_ids_work_order = Security(_require_map_file_ids_work_order)
