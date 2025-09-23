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
#

"""FastAPI router for the GHGA auth example application."""

from fastapi import APIRouter

from ghga_auth.policies import AdminAuthContext, OptionalAuthContext, UserAuthContext

router = APIRouter()


@router.get("/get_auth")
async def get_auth_route(context: OptionalAuthContext):
    """Get and return auth context without requiring it."""
    return {"context": context.model_dump() if context else None}


@router.get("/require_auth")
async def require_auth_route(context: UserAuthContext):
    """Require and return auth context."""
    return {"context": context.model_dump()}


@router.get("/require_admin")
async def require_admin_route(context: AdminAuthContext):
    """Require and return auth context with admin role."""
    return {"context": context.model_dump()}
