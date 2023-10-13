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

"""A combined service for artifact loading and browsing."""

from fastapi import FastAPI
from ghga_service_commons.api import configure_app
from hexkit.providers.mongodb import MongoDbDaoFactory

from metldata.artifacts_rest.api_factory import (
    rest_api_factory as query_rest_api_factory,
)
from metldata.config import Config
from metldata.load.aggregator import MongoDbAggregator
from metldata.load.api import rest_api_factory as load_rest_api_factory


async def get_app(config: Config) -> FastAPI:
    """Get the FastAPI app for artifacts loading and browsing."""
    app = FastAPI(
        title="Artifacts Loader and Browser API",
        description="Load and browse artifacts user-accessible API.",
    )
    configure_app(app=app, config=config)
    dao_factory = MongoDbDaoFactory(config=config)
    db_aggregator = MongoDbAggregator(config=config)

    load_router = await load_rest_api_factory(
        artifact_infos=config.artifact_infos,
        primary_artifact_name=config.primary_artifact_name,
        config=config,
        dao_factory=dao_factory,
        db_aggregator=db_aggregator,
        token_hashes=config.loader_token_hashes,
    )

    query_router = await query_rest_api_factory(
        artifact_infos=config.artifact_infos, dao_factory=dao_factory
    )

    app.include_router(load_router)
    app.include_router(query_router)

    return app
