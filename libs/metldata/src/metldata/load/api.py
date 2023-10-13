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

"""API for loading artifacts into running services."""

from typing import Optional

from fastapi import Depends, HTTPException, Response, Security
from fastapi.routing import APIRouter
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.policies import require_auth_context_using_credentials
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.akafka import KafkaEventPublisher
from pydantic import BaseModel, Field

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.artifact_info import get_artifact_info_dict
from metldata.artifacts_rest.models import ArtifactInfo
from metldata.load.aggregator import DbAggregator
from metldata.load.auth import check_token
from metldata.load.config import ArtifactLoaderAPIConfig
from metldata.load.event_publisher import EventPubTranslator
from metldata.load.load import (
    ArtifactResourcesInvalid,
    check_artifact_resources,
    load_artifacts_using_dao,
)
from metldata.load.models import ArtifactResourceDict
from metldata.load.stats import create_stats_using_aggregator


class LoaderTokenAuthContext(BaseModel):
    """An auth context used to contain the loader token."""

    token: str = Field(
        ...,
        description="A simple alphanumeric token to authenticate for loading artifacts.",
    )


class LoaderTokenAuthProvider(AuthContextProtocol[LoaderTokenAuthContext]):
    """A provider for the loader token auth context."""

    def __init__(self, *, token_hashes: list[str]):
        """Initialize the loader token auth provider."""
        self._token_hashes = token_hashes

    async def get_context(self, token: str) -> Optional[LoaderTokenAuthContext]:
        """Get a loader token auth context."""
        if not token:
            return None

        if not check_token(token=token, token_hashes=self._token_hashes):
            raise self.AuthContextValidationError("Invalid token.")

        return LoaderTokenAuthContext(token=token)


async def rest_api_factory(
    *,
    artifact_infos: list[ArtifactInfo],
    primary_artifact_name: str,
    config: ArtifactLoaderAPIConfig,
    dao_factory: DaoFactoryProtocol,
    db_aggregator: DbAggregator,
    token_hashes: list[str],
) -> APIRouter:
    """Return a router for an API for loading artifacts."""
    artifact_info_dict = get_artifact_info_dict(artifact_infos=artifact_infos)
    dao_collection = await ArtifactDaoCollection.construct(
        dao_factory=dao_factory, artifact_infos=artifact_infos
    )

    async def require_token_context(
        credentials: HTTPAuthorizationCredentials = Depends(
            HTTPBearer(auto_error=True)
        ),
    ) -> LoaderTokenAuthContext:
        """Require a VIP authentication and authorization context using FastAPI."""
        return await require_auth_context_using_credentials(
            credentials=credentials,
            auth_provider=LoaderTokenAuthProvider(token_hashes=token_hashes),
        )

    require_token = Security(require_token_context)

    router = APIRouter()

    @router.post("/rpc/load-artifacts")
    async def load_artifacts(
        artifact_resources: ArtifactResourceDict,
        _token: LoaderTokenAuthContext = require_token,
    ):
        """Load artifacts into services for querying via user-accessible API."""
        try:
            check_artifact_resources(
                artifact_resources=artifact_resources,
                artifact_infos=artifact_info_dict,
            )
        except ArtifactResourcesInvalid as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        async with KafkaEventPublisher.construct(config=config) as event_pub_provider:
            event_publisher = EventPubTranslator(
                config=config, provider=event_pub_provider
            )
            await load_artifacts_using_dao(
                artifact_resources=artifact_resources,
                artifact_info_dict=artifact_info_dict,
                event_publisher=event_publisher,
                dao_collection=dao_collection,
            )

            await create_stats_using_aggregator(
                artifact_infos=artifact_info_dict,
                primary_artifact_name=primary_artifact_name,
                db_aggregator=db_aggregator,
            )

            return Response(status_code=204)

    return router
