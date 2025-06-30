# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from collections import defaultdict

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.load_resources import (
    extract_all_resources_from_artifact,
    process_new_or_changed_artifacts,
    process_new_or_changed_resources,
    process_removed_artifacts,
    process_removed_resources,
)
from metldata.artifacts_rest.models import ArtifactInfo, ArtifactResource
from metldata.load.event_publisher import EventPublisherPort
from metldata.load.models import ArtifactJson, ArtifactResourceDict


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


async def load_whole_artifacts_using_dao(
    publishable_artifacts: list[str],
    artifact_resources: ArtifactResourceDict,
    event_publisher: EventPublisherPort,
    dao_collection: ArtifactDaoCollection,
) -> None:
    """Load whole artifacts from multiple submissions using the given dao collection."""
    (
        deleted_artifacts,
        upserted_artifacts,
    ) = await _get_changed_artifacts(
        publishable_artifacts=publishable_artifacts,
        artifact_resources=artifact_resources,
        dao_collection=dao_collection,
    )

    await process_removed_artifacts(
        event_publisher=event_publisher,
        artifact_tags=deleted_artifacts,
        dao_collection=dao_collection,
    )

    await process_new_or_changed_artifacts(
        artifacts=upserted_artifacts,
        event_publisher=event_publisher,
        dao_collection=dao_collection,
    )


async def load_artifact_resources_using_dao(
    artifact_resources: ArtifactResourceDict,
    artifact_info_dict: dict[str, ArtifactInfo],
    publishable_artifacts: list[str],
    event_publisher: EventPublisherPort,
    dao_collection: ArtifactDaoCollection,
) -> None:
    """Load artifact resources from multiple submissions using the given dao collection."""
    # Do not process resources for artifacts that are slated to be published whole
    usable_artifact_resources = {
        key: value
        for key, value in artifact_resources.items()
        if key not in publishable_artifacts
    }

    (
        removed_resource_tags,
        new_resources,
        changed_resources,
    ) = await _get_changed_resources(
        artifact_resources=usable_artifact_resources,
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


async def _get_changed_artifacts(
    publishable_artifacts: list[str],
    artifact_resources: ArtifactResourceDict,
    dao_collection: ArtifactDaoCollection,
) -> tuple[
    set[tuple[str, str]],
    dict[str, list[ArtifactJson]],
]:
    """Extract the changeset of publishable whole artifacts by comparing the database
    contents with the currently submitted artifacts. Only the configured artifact types
    are stored whole.

    Returns the following data in this order:
     - A set of tuples (artifact_type, study_accession) for deleted artifacts
     - A dict of upserted artifacts, where the keys are artifact names and
        the values are lists of individual artifact instances as ArtifactTypedDicts
        - omits artifact instances that have not changed
    """
    deleted_artifacts: set[tuple[str, str]] = set()
    upserted_artifacts: dict[str, list[ArtifactJson]] = defaultdict(list)

    # First get all existing artifacts from the database by their "tags"
    # Using/defining "tag" here as a tuple of (artifact_name, study_accession) to avoid
    # confusing it for the study accession itself.
    existing_artifact_tags: set[
        tuple[str, str]
    ] = await dao_collection.get_all_whole_artifact_tags()
    submitted_artifact_tags: set[tuple[str, str]] = {
        (artifact_name, artifact["study_accession"])
        for artifact_name, artifacts in artifact_resources.items()
        for artifact in artifacts
    }

    # Get all deleted artifacts by checking which existing tags are not present in
    # the loaded artifacts
    deleted_artifacts = existing_artifact_tags - submitted_artifact_tags

    # Also delete any stored artifacts that are no longer configured to be publishable
    for artifact_name, study_accession in existing_artifact_tags:
        if artifact_name not in publishable_artifacts:
            deleted_artifacts.add((artifact_name, study_accession))

    # Iterate through the PROVIDED artifact resources and...:
    # - if the ID is in existing_artifact_tags, check if it has changed by loading
    #   the existing artifact and comparing it to the provided one
    for artifact_name, artifacts in artifact_resources.items():
        if artifact_name not in publishable_artifacts:
            continue
        for artifact_dict in artifacts:
            artifact_tag = (artifact_name, artifact_dict["study_accession"])
            if artifact_tag in existing_artifact_tags:
                dao = await dao_collection.get_whole_artifact_dao(
                    artifact_name=artifact_name
                )
                existing_artifact = await dao.get_by_id(
                    artifact_dict["study_accession"]
                )

                if existing_artifact.model_dump() != artifact_dict:
                    upserted_artifacts[artifact_name].append(artifact_dict)
            else:
                upserted_artifacts[artifact_name].append(artifact_dict)

    return deleted_artifacts, upserted_artifacts


async def _get_changed_resources(
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

    for artifact_name, artifact_instances in artifact_resources.items():
        for artifact_instance in artifact_instances:
            resources = extract_all_resources_from_artifact(
                artifact_content=artifact_instance["content"],
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
