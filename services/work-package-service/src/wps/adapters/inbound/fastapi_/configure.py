# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Utils to configure the FastAPI app"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from ghga_service_commons.api import ApiConfigBase, configure_app

from wps import __version__
from wps.adapters.inbound.fastapi_.routes import router

__all__ = ["get_openapi_schema"]


def get_openapi_schema(app: FastAPI, config: ApiConfigBase) -> dict[str, Any]:
    """Generate a custom OpenAPI schema for the service."""
    return get_openapi(
        title="Work Package Service",
        version=__version__,
        description="A service managing work packages for the GHGA CLI",
        servers=[{"url": config.api_root_path}],
        tags=[{"name": "WorkPackages"}, {"name": "Datasets"}],
        routes=app.routes,
    )


def get_configured_app(*, config: ApiConfigBase) -> FastAPI:
    """Create and configure a FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    configure_app(app, config=config)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi_schema(app, config=config)
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app
