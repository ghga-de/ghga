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

"""Logic for querying artifact resouces."""

from hexkit.protocols.dao import ResourceNotFoundError

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.models import ArtifactResource


class ArtifactResourceNotFoundError(RuntimeError):
    """Raised when a resource could not be found."""

    def __init__(self, *, artifact_name: str, class_name: str, resource_id: str):
        message = (
            f"Could not find resource with ID '{resource_id}' of class '{class_name}'"
            + f" in artifact '{artifact_name}'."
        )
        super().__init__(message)


async def query_artifact_resource(
    *,
    artifact_name: str,
    class_name: str,
    resource_id: str,
    dao_collection: ArtifactDaoCollection,
) -> ArtifactResource:
    """Query a single resource with the given ID of the given class from the given
    artifact.

    Raises:
        ArtifactResourceNotFoundError: If the resource could not be found.
    """
    dao = await dao_collection.get_dao(
        artifact_name=artifact_name, class_name=class_name
    )

    try:
        return await dao.get_by_id(resource_id)
    except ResourceNotFoundError as error:
        raise ArtifactResourceNotFoundError(
            artifact_name=artifact_name,
            class_name=class_name,
            resource_id=resource_id,
        ) from error
