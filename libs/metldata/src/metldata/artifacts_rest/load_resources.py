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

from typing import cast

from ghga_event_schemas.pydantic_ import (
    MetadataDatasetFile,
    MetadataDatasetOverview,
    MetadataDatasetStage,
    SearchableResource,
)
from ghga_service_commons.utils.files import get_file_extension

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.models import (
    ArtifactInfo,
    ArtifactResource,
    ArtifactResourceClass,
)
from metldata.custom_types import Json
from metldata.load.event_publisher import EventPublisherPort
from metldata.metadata_utils import (
    SlotNotFoundError,
    get_resources_of_class,
    lookup_self_id,
    lookup_slot_in_resource,
)


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
    as specified in the artifact info.
    """
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
    dao_collection: ArtifactDaoCollection,
) -> None:
    """Save the given resource into the database using the given DAO collection."""
    dao = await dao_collection.get_dao(
        artifact_name=artifact_name, class_name=resource.class_name
    )
    await dao.upsert(resource)


async def remove_artifact_resource(
    *,
    resource_id: str,
    class_name: str,
    artifact_name: str,
    dao_collection: ArtifactDaoCollection,
) -> None:
    """Remove a given artifact resource from the database using the given DAO collection"""
    dao = await dao_collection.get_dao(
        artifact_name=artifact_name, class_name=class_name
    )
    await dao.delete(id_=resource_id)


async def load_artifact_resources(
    *,
    artifact_content: Json,
    artifact_info: ArtifactInfo,
    dao_collection: ArtifactDaoCollection,
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


async def process_removed_resources(
    *,
    event_publisher: EventPublisherPort,
    resource_tags: set[tuple[str, str, str]],
    dao_collection: ArtifactDaoCollection,
):
    """Delete no longer needed artifact resources from DB and send corresponding events"""
    for resource_tag in resource_tags:
        artifact_name, class_name, resource_id = resource_tag
        # resource tag was obtained from querying the db, so resource with given ID
        # should be present
        await remove_artifact_resource(
            artifact_name=artifact_name,
            class_name=class_name,
            resource_id=resource_id,
            dao_collection=dao_collection,
        )

        await event_publisher.process_resource_deletion(
            accession=resource_id, class_name=class_name
        )
        if event_publisher.is_primary_dataset_source(
            artifact_name=artifact_name, resource_class_name=class_name
        ):
            await event_publisher.process_dataset_deletion(accession=resource_id)


async def process_new_or_changed_resources(
    *,
    artifact_info_dict: dict[str, ArtifactInfo],
    event_publisher: EventPublisherPort,
    resources: dict[tuple[str, str, str], ArtifactResource],
    dao_collection: ArtifactDaoCollection,
):
    """Insert newly received artifact resources into DB and send corresponding events"""
    for resource_tag, resource in resources.items():
        artifact_name = resource_tag[0]
        # no resource tag was obtained from querying the db, so the resource with the
        # given ID should not be present
        await save_artifact_resource(
            resource=resource,
            artifact_name=artifact_name,
            dao_collection=dao_collection,
        )

        if event_publisher.is_primary_dataset_source(
            artifact_name=artifact_name, resource_class_name=resource.class_name
        ):
            await process_resource_upsert(
                artifact_info_dict=artifact_info_dict,
                artifact_name=artifact_name,
                event_publisher=event_publisher,
                resource=resource,
            )


async def process_resource_upsert(  # pylint: disable=too-many-locals
    *,
    artifact_info_dict: dict[str, ArtifactInfo],
    artifact_name: str,
    event_publisher: EventPublisherPort,
    resource: ArtifactResource,
):
    """Convert available data to correct event model and delegate firing appropriate events"""
    artifact_info = artifact_info_dict[artifact_name]
    file_slots = get_file_slots(artifact_info=artifact_info, resource=resource)

    metadata_dataset_files = convert_file_information(file_slots=file_slots)

    dataset_description = cast(
        str,
        lookup_slot_in_resource(resource=resource.content, slot_name="description"),
    )
    dataset_title = cast(
        str,
        lookup_slot_in_resource(resource=resource.content, slot_name="title"),
    )

    dataset_overview = MetadataDatasetOverview(
        accession=resource.id_,
        title=dataset_title,
        stage=MetadataDatasetStage.DOWNLOAD,
        description=dataset_description,
        files=metadata_dataset_files,
    )
    await event_publisher.process_dataset_upsert(dataset_overview=dataset_overview)

    searchable_resource = SearchableResource(
        accession=resource.id_, class_name=resource.class_name, content=resource.content
    )
    await event_publisher.process_resource_upsert(resource=searchable_resource)


def get_file_slots(artifact_info: ArtifactInfo, resource: ArtifactResource):
    """Get files resource slots from file class names"""
    file_slots = []
    for class_name, resource_class in artifact_info.resource_classes.items():
        if class_name.endswith("File"):
            anchor_point = resource_class.anchor_point
            slot_name = anchor_point.root_slot

            try:
                file_slot = lookup_slot_in_resource(
                    resource=resource.content, slot_name=slot_name
                )
                # file slots should be lists
                file_slot = cast(list[Json], file_slot)
            except SlotNotFoundError:
                continue

            file_slots.append(file_slot)

    return file_slots


def convert_file_information(file_slots: list[list[Json]]) -> list[MetadataDatasetFile]:
    """Convert file slot information into MetadataDatasetFiles"""
    files = []
    for file_slot in file_slots:
        for file in file_slot:
            extension = get_file_extension(filename=file["name"])

            files.append(
                MetadataDatasetFile(
                    accession=file["accession"],
                    description=None,
                    file_extension=extension,
                )
            )

    return files
