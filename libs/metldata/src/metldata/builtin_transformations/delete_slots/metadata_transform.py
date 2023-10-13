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

"""Logic for transforming metadata."""


from metldata.metadata_utils import get_resources_of_class, upsert_resources_in_metadata
from metldata.model_utils.anchors import AnchorPoint
from metldata.transform.base import Json, MetadataModelTransformationError


def delete_slot_from_resource(resource: Json, slot_name: str) -> Json:
    """Delete a slot from a resource. Returns a modified copy of the resource."""
    if slot_name not in resource:
        raise MetadataModelTransformationError(
            f"Slot '{slot_name}' not found in resource '{resource}'"
        )

    modified_resource = resource.copy()
    del modified_resource[slot_name]
    return modified_resource


def delete_class_slot(
    metadata: Json,
    class_name: str,
    slot_name: str,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Delete a slot from a class in the provided metadata. Returns a modified copy of
    the metadata.
    """
    resources = get_resources_of_class(
        class_name=class_name,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    )

    modified_resources = [
        delete_slot_from_resource(resource=resource, slot_name=slot_name)
        for resource in resources
    ]

    return upsert_resources_in_metadata(
        resources=modified_resources,
        class_name=class_name,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    )


def delete_class_slots(
    metadata: Json,
    slots_to_delete: dict[str, list[str]],
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Delete slots from provided metadata. Returns a modified copy of the metadata."""
    for class_name, slot_names in slots_to_delete.items():
        for slot_name in slot_names:
            metadata = delete_class_slot(
                metadata=metadata,
                class_name=class_name,
                slot_name=slot_name,
                anchor_points_by_target=anchor_points_by_target,
            )

    return metadata
