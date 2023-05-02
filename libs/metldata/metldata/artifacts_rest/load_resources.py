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

"""Logic for loading artifacts."""


from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.models import (
    ArtifactInfo,
    ArtifactResource,
    ArtifactResourceClass,
)
from metldata.custom_types import Json
from metldata.metadata_utils import get_resources_of_class, lookup_self_id


def extract_class_resources_from_artifact(
    *, artifact_content: Json, resource_class: ArtifactResourceClass
) -> list[ArtifactResource]:
    """Extract the resources from the given artifact content for the given class."""

    resource_jsons = get_resources_of_class(
        class_name=resource_class.name,
        global_metadata=artifact_content,
        anchor_points_by_target={resource_class.name: resource_class.anchor_point},
    )

    return [
        ArtifactResource(
            id_=lookup_self_id(
                resource=resource_json,
                identifier_slot=resource_class.anchor_point.identifier_slot,
            ),
            class_name=resource_class.name,
            content=resource_json,
        )
        for resource_json in resource_jsons
    ]


def extract_all_resources_from_artifact(
    artifact_content: Json, artifact_info: ArtifactInfo
) -> list[ArtifactResource]:
    """Extract all resources from the given artifact content for all resource classes
    as specified in the artifact info."""

    return [
        resource
        for resource_class in artifact_info.resource_classes.values()
        for resource in extract_class_resources_from_artifact(
            artifact_content=artifact_content,
            resource_class=resource_class,
        )
    ]


async def save_artifact_resource(
    *,
    resource: ArtifactResource,
    artifact_name: str,
    dao_collection: ArtifactDaoCollection
) -> None:
    """Save the given resource into the database using the given DAO collection."""

    dao = await dao_collection.get_dao(
        artifact_name=artifact_name, class_name=resource.class_name
    )
    await dao.upsert(resource)


async def load_artifact_resources(
    *,
    artifact_content: Json,
    artifact_info: ArtifactInfo,
    dao_collection: ArtifactDaoCollection
) -> None:
    """Load the resources from the given artifacts into the database using the given
    DAO collection.
    """

    resources = extract_all_resources_from_artifact(
        artifact_content=artifact_content, artifact_info=artifact_info
    )

    for resource in resources:
        await save_artifact_resource(
            resource=resource,
            artifact_name=artifact_info.name,
            dao_collection=dao_collection,
        )
