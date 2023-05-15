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

"""
Module containing the main FastAPI router and (optionally) top-level API endpoints.
Additional endpoints might be structured in dedicated modules
(each of them having a sub-router).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from ghga_service_commons.api import configure_app

from auth_service.config import configure_logging
from auth_service.deps import get_config
from auth_service.user_management import (
    CONTACT,
    DESCRIPTION,
    LICENSE_INFO,
    TAGS_METADATA,
    TITLE,
    VERSION,
)
from auth_service.user_management.claims_repository.core.seed import (
    seed_data_steward_claims,
)
from auth_service.user_management.claims_repository.router import (
    router as claims_router,
)
from auth_service.user_management.user_registry.router import router as users_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    """Setup the FastAPI application.

    This function runs on startup and shutdown of the application.
    We currently use it to seed the database with the data steward claims.
    """
    config = app.dependency_overrides.get(get_config, get_config)()
    await seed_data_steward_claims(config)
    yield


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    contact=CONTACT,
    license_info=LICENSE_INFO,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

configure_app(app, config=get_config())

app.include_router(users_router)
app.include_router(claims_router)


@app.get("/health", summary="health", tags=["health"], status_code=status.HTTP_200_OK)
async def health():
    """Used to check that this service is alive"""

    return {"status": "OK"}
