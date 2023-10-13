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

"""Logic for loading artifact resources."""

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.load_resources import (
    extract_all_resources_from_artifact,
    process_new_or_changed_resources,
    process_removed_resources,
)
from metldata.artifacts_rest.models import ArtifactInfo, ArtifactResource
from metldata.load.event_publisher import EventPublisherPort
from metldata.load.models import ArtifactResourceDict


class ArtifactResourcesInvalid(RuntimeError):
    """Raised when artifact resources are invalid."""


def check_artifact_resources(
    artifact_resources: ArtifactResourceDict, artifact_infos: dict[str, ArtifactInfo]
) -> None:
    """Check the provided artifact resources against the given artifact info.

    Raises:
        ArtifactResourcesInvalid: If the artifact resources are invalid.
    """
    for artifact_name in artifact_resources:
        if artifact_name not in artifact_infos:
            raise ArtifactResourcesInvalid(f"Artifact '{artifact_name}' is unknown.")


async def load_artifacts_using_dao(
    artifact_resources: ArtifactResourceDict,
    artifact_info_dict: dict[str, ArtifactInfo],
    event_publisher: EventPublisherPort,
    dao_collection: ArtifactDaoCollection,
) -> None:
    """Load artifact resources from multiple submissions using the given dao collection."""
    (
        removed_resource_tags,
        new_resources,
        changed_resources,
    ) = await _get_changed_resources(
        artifact_resources=artifact_resources,
        artifact_info_dict=artifact_info_dict,
        dao_collection=dao_collection,
    )

    await process_removed_resources(
        event_publisher=event_publisher,
        resource_tags=removed_resource_tags,
        dao_collection=dao_collection,
    )

    await process_new_or_changed_resources(
        artifact_info_dict=artifact_info_dict,
        event_publisher=event_publisher,
        resources=new_resources,
        dao_collection=dao_collection,
    )

    await process_new_or_changed_resources(
        artifact_info_dict=artifact_info_dict,
        event_publisher=event_publisher,
        resources=changed_resources,
        dao_collection=dao_collection,
    )


async def _get_changed_resources(  # pylint: disable=too-many-locals
    artifact_resources: ArtifactResourceDict,
    artifact_info_dict: dict[str, ArtifactInfo],
    dao_collection: ArtifactDaoCollection,
) -> tuple[
    set[tuple[str, str, str]],
    dict[tuple[str, str, str], ArtifactResource],
    dict[tuple[str, str, str], ArtifactResource],
]:
    """Extract changed resources using DAOs and currently submitted artifacts

    Returns the following collections in order:
     - A set of resource tags for artifact resources that have been removed
     - A dict of new artifact resources indexed by the corresponding resource_tag
     - A dict of changed artifact resources indexed by the corresponding resource_tag
    """
    # only need to collect resource tag to check if something needs to be deleted
    unchanged_resource_tags = []

    # collect new/changed resources indexed by their resource_tag for insert/upsert
    new_resources = {}
    changed_resources = {}

    existing_resource_tags = await dao_collection.get_all_resource_tags()

    for artifact_name, artifact_contents in artifact_resources.items():
        for artifact_content in artifact_contents:
            resources = extract_all_resources_from_artifact(
                artifact_content=artifact_content,
                artifact_info=artifact_info_dict[artifact_name],
            )

            # check for each resource if it does already exist and is changed
            for resource in resources:
                resource_tag = (artifact_name, resource.class_name, resource.id_)

                if resource_tag in existing_resource_tags:
                    dao = await dao_collection.get_dao(
                        artifact_name=artifact_name, class_name=resource.class_name
                    )
                    old_resource = await dao.get_by_id(resource.id_)

                    if old_resource == resource:
                        unchanged_resource_tags.append(resource_tag)
                    else:
                        changed_resources[resource_tag] = resource
                else:
                    new_resources[resource_tag] = resource

    removed_resource_tags = existing_resource_tags.difference(
        unchanged_resource_tags, new_resources, changed_resources
    )

    return removed_resource_tags, new_resources, changed_resources
