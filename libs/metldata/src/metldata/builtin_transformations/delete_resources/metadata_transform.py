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

"""Logic for transforming metadata."""

from typing import Any

from linkml_runtime import SchemaView

from metldata.metadata_utils import (
    get_resources_of_class,
    lookup_self_id,
    upsert_resources_in_metadata,
)
from metldata.model_utils.anchors import AnchorPoint
from metldata.transform.base import Json, MetadataTransformationError


def _is_marked(resource: Json, conditions: dict[str, Any]) -> bool:
    """Tell whether every slot named in the conditions equals the given value.

    A resource that lacks one of the slots is not marked.
    """
    return bool(conditions) and all(
        slot in resource and resource[slot] == value
        for slot, value in conditions.items()
    )


def _delete_marked_resources(
    *,
    metadata: Json,
    resources_to_delete: dict[str, dict[str, Any]],
    anchor_points_by_target: dict[str, AnchorPoint],
) -> tuple[Json, dict[str, set[str]]]:
    """Delete the marked resources of the configured classes.

    Returns a modified copy of the metadata and the identifiers of the deleted
    resources per class.
    """
    deleted_ids_by_class: dict[str, set[str]] = {}

    for class_name, conditions in resources_to_delete.items():
        identifier_slot = anchor_points_by_target[class_name].identifier_slot
        kept: list[Json] = []
        deleted_ids: set[str] = set()

        for resource in get_resources_of_class(
            class_name=class_name,
            global_metadata=metadata,
            anchor_points_by_target=anchor_points_by_target,
        ):
            if _is_marked(resource, conditions):
                deleted_ids.add(
                    lookup_self_id(resource=resource, identifier_slot=identifier_slot)
                )
            else:
                kept.append(resource)

        if deleted_ids:
            deleted_ids_by_class[class_name] = deleted_ids
            metadata = upsert_resources_in_metadata(
                resources=kept,
                class_name=class_name,
                global_metadata=metadata,
                anchor_points_by_target=anchor_points_by_target,
            )

    return metadata, deleted_ids_by_class


def _get_reference_slots(
    *, class_name: str, target_classes: set[str], schema_view: SchemaView
) -> dict[str, str]:
    """Get the slots of a class that reference one of the target classes by
    identifier. Returns the referenced class per slot name.
    """
    reference_slots: dict[str, str] = {}

    for slot_name in schema_view.class_slots(class_name):
        slot = schema_view.induced_slot(slot_name, class_name)
        if (
            slot.range in target_classes
            and not slot.inlined
            and not slot.inlined_as_list
        ):
            reference_slots[slot_name] = slot.range

    return reference_slots


def _prune_references(
    *,
    resource: Json,
    class_name: str,
    reference_slots: dict[str, str],
    deleted_ids_by_class: dict[str, set[str]],
) -> Json:
    """Remove the references to deleted resources from a resource. Returns a modified
    copy of the resource.

    Raises:
        MetadataTransformationError:
            if a single-valued slot references a deleted resource.
    """
    pruned = resource.copy()

    for slot_name, target_class in reference_slots.items():
        if slot_name not in resource:
            continue

        deleted_ids = deleted_ids_by_class[target_class]
        value = resource[slot_name]

        if isinstance(value, list):
            pruned[slot_name] = [item for item in value if item not in deleted_ids]
        elif value in deleted_ids:
            # dropping the slot would leave a resource that no longer says what it
            # refers to, and there is no other value to put in its place
            raise MetadataTransformationError(
                f"The single-valued slot '{slot_name}' of class '{class_name}'"
                + f" references the deleted resource '{value}' of class"
                + f" '{target_class}'."
            )

    return pruned


def delete_resources(
    *,
    metadata: Json,
    resources_to_delete: dict[str, dict[str, Any]],
    anchor_points_by_target: dict[str, AnchorPoint],
    schema_view: SchemaView,
) -> Json:
    """Delete the resources whose slots carry the configured values and the references
    to them. Returns a modified copy of the metadata.

    Raises:
        MetadataTransformationError:
            if a single-valued slot references a deleted resource.
    """
    metadata, deleted_ids_by_class = _delete_marked_resources(
        metadata=metadata,
        resources_to_delete=resources_to_delete,
        anchor_points_by_target=anchor_points_by_target,
    )

    if not deleted_ids_by_class:
        return metadata

    for class_name in anchor_points_by_target:
        reference_slots = _get_reference_slots(
            class_name=class_name,
            target_classes=set(deleted_ids_by_class),
            schema_view=schema_view,
        )
        if not reference_slots:
            continue

        resources = get_resources_of_class(
            class_name=class_name,
            global_metadata=metadata,
            anchor_points_by_target=anchor_points_by_target,
        )
        metadata = upsert_resources_in_metadata(
            resources=[
                _prune_references(
                    resource=resource,
                    class_name=class_name,
                    reference_slots=reference_slots,
                    deleted_ids_by_class=deleted_ids_by_class,
                )
                for resource in resources
            ],
            class_name=class_name,
            global_metadata=metadata,
            anchor_points_by_target=anchor_points_by_target,
        )

    return metadata
