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

"""Compose the main app and resolve dependencies."""

from fastapi import FastAPI
from ghga_service_commons.api import configure_app
from hexkit.providers.mongodb import MongoDbDaoFactory

from metldata.load.aggregator import MongoDbAggregator
from metldata.load.api import rest_api_factory
from metldata.load.config import ArtifactLoaderAPIConfig


async def get_app(config: ArtifactLoaderAPIConfig) -> FastAPI:
    """Get the FastAPI app for loading artifacts. Performs dependency injection."""
    app = FastAPI(
        title="Artifacts Loader",
        description="Load artifacts into services for querying via user-accessible API.",
    )
    configure_app(app=app, config=config)
    dao_factory = MongoDbDaoFactory(config=config)
    db_aggregator = MongoDbAggregator(config=config)

    api_router = await rest_api_factory(
        artifact_infos=config.artifact_infos,
        primary_artifact_name=config.primary_artifact_name,
        config=config,
        dao_factory=dao_factory,
        db_aggregator=db_aggregator,
        token_hashes=config.loader_token_hashes,
    )

    app.include_router(api_router)

    return app
