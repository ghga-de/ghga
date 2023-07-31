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
"""Top-level functionality for the microservice"""
from fastapi import FastAPI
from ghga_service_commons.api import configure_app, run_server

from mass.adapters.inbound.fastapi_.routes import router
from mass.config import Config
from mass.container import Container


def get_configured_container(*, config: Config) -> Container:
    """Create and configure a DI container."""

    container = Container()
    container.config.load_config(config)
    container.wire(modules=["mass.adapters.inbound.fastapi_.routes"])

    return container


def get_rest_api(*, config: Config) -> FastAPI:
    """
    Creates a FastAPI app.
    For full functionality of the api, run in the context of a CI container with
    correct wiring and initialized resources (see the run_api function below).
    """

    api = FastAPI()
    api.include_router(router=router)
    configure_app(api, config=config)
    return api


async def run_rest():
    """Run the server"""
    config = Config()

    async with get_configured_container(config=config):
        api = get_rest_api(config=config)
        await run_server(app=api, config=config)


async def consume_events(run_forever: bool = True):
    """Run the event consumer"""

    config = Config()

    async with get_configured_container(config=config) as container:
        event_subscriber = await container.event_subscriber()
        await event_subscriber.run(forever=run_forever)
