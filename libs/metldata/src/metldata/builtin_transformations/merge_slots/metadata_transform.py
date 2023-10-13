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

from copy import deepcopy

from metldata.builtin_transformations.merge_slots.models import SlotMergeInstruction
from metldata.custom_types import Json
from metldata.metadata_utils import (
    SlotNotFoundError,
    get_resources_of_class,
    lookup_slot_in_resource,
    upsert_resources_in_metadata,
)
from metldata.model_utils.anchors import AnchorPoint
from metldata.transform.base import MetadataTransformationError


def apply_merge_instruction_to_resource(
    *, resource: Json, merge_instruction: SlotMergeInstruction
) -> Json:
    """Merge slots in a metadata resource according to the given instruction.

    Args:
        resource: The resource to transform.
        merge_instruction: The merge instruction to apply.

    Returns:
        The transformed resource.
    """
    modified_resource = deepcopy(resource)

    try:
        lookup_slot_in_resource(
            resource=resource, slot_name=merge_instruction.target_slot
        )
    except SlotNotFoundError:
        # this is expected
        pass
    else:
        raise MetadataTransformationError(
            f"Target slot {merge_instruction.target_slot} already exists in resource"
            + f" of target class {merge_instruction.class_name}."
        )

    modified_resource[merge_instruction.target_slot] = []
    for source_slot in merge_instruction.source_slots:
        content = lookup_slot_in_resource(resource=resource, slot_name=source_slot)
        if isinstance(content, list):
            modified_resource[merge_instruction.target_slot].extend(content)
        else:
            modified_resource[merge_instruction.target_slot].append(content)

    return modified_resource


def apply_merge_instruction_to_metadata(
    *,
    metadata: Json,
    merge_instruction: SlotMergeInstruction,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Merge slots in metadata according to the given instruction.

    Args:
        metadata: The metadata to transform.
        merge_instruction: The merge instruction to apply.

    Returns:
        The transformed metadata.
    """
    resources = get_resources_of_class(
        class_name=merge_instruction.class_name,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    )

    modified_resources = [
        apply_merge_instruction_to_resource(
            resource=resource, merge_instruction=merge_instruction
        )
        for resource in resources
    ]

    return upsert_resources_in_metadata(
        resources=modified_resources,
        class_name=merge_instruction.class_name,
        global_metadata=metadata,
        anchor_points_by_target=anchor_points_by_target,
    )


def apply_merge_instructions_to_metadata(
    *,
    metadata: Json,
    merge_instructions: list[SlotMergeInstruction],
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Merge slots in metadata according to the given instructions.

    Args:
        metadata: The metadata to transform.
        merge_instructions: The merge instructions to apply.

    Returns:
        The transformed metadata.
    """
    for merge_instruction in merge_instructions:
        metadata = apply_merge_instruction_to_metadata(
            metadata=metadata,
            merge_instruction=merge_instruction,
            anchor_points_by_target=anchor_points_by_target,
        )

    return metadata
