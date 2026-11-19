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
#

"""Logic to build REST APIs for querying artifacts."""

from fastapi import HTTPException
from fastapi.routing import APIRouter

from hexkit.protocols.dao import DaoFactoryProtocol, ResourceNotFoundError
from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection, DaoNotFoundError
from metldata.artifacts_rest.artifact_info import get_artifact_info_dict
from metldata.artifacts_rest.models import (
    ArtifactInfo,
    FileGovernanceQuery,
    GlobalStats,
)
from metldata.artifacts_rest.query_file_governance import query_file_governance
from metldata.artifacts_rest.query_resources import (
    ArtifactResourceNotFoundError,
    query_artifact_resource,
)
from metldata.custom_types import Json
from metldata.governance import DataAccessPolicy
from metldata.load.file_governance import get_file_governance_dao
from metldata.load.stats import STATS_COLLECTION_NAME


async def rest_api_factory(  # noqa: C901
    *, artifact_infos: list[ArtifactInfo], dao_factory: DaoFactoryProtocol
) -> APIRouter:
    """Factory to build a REST API for querying the provided artifact.

    Args:
        artifact_info: Information on the artifact to build the REST API for.
        dao_factory: An implementation of the DaoFactoryProtocol.

    Returns:
        A FastAPI router with RESTful endpoints to query artifacts.
    """
    artifact_info_dict = get_artifact_info_dict(artifact_infos=artifact_infos)
    dao_collection = await ArtifactDaoCollection.construct(
        dao_factory=dao_factory, artifact_infos=artifact_infos
    )
    stats_dao = await dao_factory.get_dao(
        name=STATS_COLLECTION_NAME, dto_model=GlobalStats, id_field="id"
    )
    file_governance_dao = await get_file_governance_dao(dao_factory=dao_factory)

    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        """Used to test if this service is alive"""
        return {"status": "OK"}

    @router.options("/artifacts")
    async def get_artifacts_info() -> list[ArtifactInfo]:
        """Get information on available artifacts."""
        return artifact_infos

    @router.options("/artifacts/{artifact_name}")
    async def get_artifact_info(artifact_name: str) -> ArtifactInfo:
        """Get information on the artifact with the given name."""
        artifact_info = artifact_info_dict.get(artifact_name)
        if artifact_info is None:
            raise HTTPException(status_code=404, detail="Artifact not found.")

        return artifact_info

    @router.get(
        "/artifacts/{artifact_name}/classes/{class_name}/resources/{resource_id}"
    )
    async def get_artifact_resource(
        artifact_name: str, class_name: str, resource_id: str
    ) -> Json:
        """Get the resource with the given id of the class with the given name from the
        artifact with the given name.
        """
        try:
            resource = await query_artifact_resource(
                artifact_name=artifact_name,
                class_name=class_name,
                resource_id=resource_id,
                dao_collection=dao_collection,
            )
        except DaoNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=f"Class '{class_name}' not found in artifact '{artifact_name}'.",
            ) from error
        except ArtifactResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return resource.content

    @router.get("/stats")
    async def get_stats() -> GlobalStats:
        """Get the global summary statistics for all resources."""
        try:
            resource = await stats_dao.get_by_id("global")
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return resource

    @router.post("/file-governance/query")
    async def get_file_governance(
        query: FileGovernanceQuery,
    ) -> dict[str, DataAccessPolicy | None]:
        """Get the data access policy, with its data access committee, governing each
        of the given file accessions. Unknown file accessions map to null.
        """
        return await query_file_governance(
            file_accessions=query.file_accessions, dao=file_governance_dao
        )

    return router
