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

"""In this module object construction and dependency injection is carried out."""

from fastapi import FastAPI
from ghga_service_commons.api import configure_app, run_server

from ars.adapters.inbound.http.openapi import get_openapi_schema
from ars.adapters.inbound.http.routes import router
from ars.config import Config
from ars.container import Container


def get_container(*, config: Config) -> Container:
    """Create, configure and wire the DI container."""

    container = Container()
    container.config.load_config(config)
    container.wire(
        modules=[
            "ars.adapters.inbound.http.auth",
            "ars.adapters.inbound.http.openapi",
            "ars.adapters.inbound.http.routes",
        ]
    )
    return container


def get_rest_api(*, config: Config) -> FastAPI:
    """Create a FastAPI app.

    For full functionality of the AP, run in the context of a CI container with
    correct wiring and initialized resources (see the run_rest function below).
    """

    api = FastAPI()
    api.include_router(router)
    configure_app(api, config=config)

    def custom_openapi():
        if api.openapi_schema:
            return api.openapi_schema
        openapi_schema = get_openapi_schema(api)
        api.openapi_schema = openapi_schema
        return api.openapi_schema

    api.openapi = custom_openapi  # type: ignore [assignment]

    return api


async def run_rest():
    """Run the HTTP REST API."""

    config = Config()  # pyright: ignore

    async with get_container(config=config):
        api = get_rest_api(config=config)
        await run_server(app=api, config=config)
