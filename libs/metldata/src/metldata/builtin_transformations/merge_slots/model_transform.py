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

"""Logic for transforming metadata models."""

from linkml_runtime.linkml_model.meta import AnonymousSlotExpression, SlotDefinition

from metldata.builtin_transformations.merge_slots.models import SlotMergeInstruction
from metldata.model_utils.essentials import ExportableSchemaView, MetadataModel
from metldata.model_utils.manipulate import upsert_class_slot
from metldata.transform.base import MetadataModelTransformationError


def get_source_range(
    *, schema_view: ExportableSchemaView, class_name: str, source_slot: str
) -> str:
    """Get the range of a source slot for the provided class.

    Raises:
        MetadataModelTransformationError:
            If the slot has no defined range, or if the slot is using a union range
            with the `all_of` or `any_of` properties.
    """
    slot = schema_view.induced_slot(class_name=class_name, slot_name=source_slot)

    if not slot.range:
        raise MetadataModelTransformationError(
            f"Source slot {source_slot} of class {class_name} has no defined range."
        )

    if slot.all_of or slot.any_of:
        raise MetadataModelTransformationError(
            f"Source slot {source_slot} of class {class_name} is using a union range."
        )

    return str(slot.range)


def get_source_ranges(
    *, schema_view: ExportableSchemaView, class_name: str, source_slots: list[str]
) -> list[str]:
    """Get the ranges of the given source slots."""
    source_ranges: list[str] = []
    for source_slot in source_slots:
        source_range = get_source_range(
            schema_view=schema_view, class_name=class_name, source_slot=source_slot
        )
        if source_range not in source_ranges:
            source_ranges.append(source_range)

    return source_ranges


def is_source_slot_inlined(
    *, schema_view: ExportableSchemaView, class_name: str, slot_name: str
) -> tuple[bool, bool]:
    """Check if a class slot is inlined. Returns a tuple of booleans where the first
    element indicates if the slot is inlined, and the second element indicates if the
    slot is inlined_as_list
    """
    slot = schema_view.induced_slot(class_name=class_name, slot_name=slot_name)

    return bool(slot.inlined), bool(slot.inlined_as_list)


def are_source_slots_inlined(
    *, schema_view: ExportableSchemaView, class_name: str, source_slots: list[str]
) -> tuple[bool, bool]:
    """Check if all source slots are inlined. Returns a tuple of booleans where the
    first element indicates if the slots are inlined, and the second element indicates
    if the slots are inlined_as_list
    """
    # inspect first slot:
    inlined, inlined_as_list = is_source_slot_inlined(
        schema_view=schema_view, class_name=class_name, slot_name=source_slots[0]
    )

    # make sure that all other slots are identical:
    for source_slot in source_slots[1:]:
        other_inlined, other_inlined_as_list = is_source_slot_inlined(
            schema_view=schema_view, class_name=class_name, slot_name=source_slot
        )

        if inlined != other_inlined or inlined_as_list != other_inlined_as_list:
            raise MetadataModelTransformationError(
                f"Source slots {source_slots} of class {class_name} are not identical."
                + " They differ in their inlined and/or inlined_as_list properties."
            )

    return inlined, inlined_as_list


def get_target_slot(
    *, schema_view: ExportableSchemaView, merge_instruction: SlotMergeInstruction
) -> SlotDefinition:
    """Get a definition of the target slot."""
    source_ranges = get_source_ranges(
        schema_view=schema_view,
        class_name=merge_instruction.class_name,
        source_slots=merge_instruction.source_slots,
    )

    inlined, inlined_as_list = are_source_slots_inlined(
        schema_view=schema_view,
        class_name=merge_instruction.class_name,
        source_slots=merge_instruction.source_slots,
    )

    target_slot_definition = SlotDefinition(
        name=merge_instruction.target_slot,
        required=True,
        multivalued=True,
        description=merge_instruction.target_description,
    )

    if len(source_ranges) == 1:
        target_slot_definition.range = source_ranges.pop()
    else:
        target_slot_definition.any_of = [
            AnonymousSlotExpression(range=source_range)
            for source_range in source_ranges
        ]

    target_slot_definition.inlined = inlined
    if inlined_as_list:
        target_slot_definition.inlined_as_list = inlined_as_list

    return target_slot_definition


def apply_merge_instruction(
    *, schema_view: ExportableSchemaView, merge_instruction: SlotMergeInstruction
) -> ExportableSchemaView:
    """Apply the provided merge instructions to the provided schema_view."""
    target_slot_definition = get_target_slot(
        schema_view=schema_view, merge_instruction=merge_instruction
    )

    return upsert_class_slot(
        schema_view=schema_view,
        class_name=merge_instruction.class_name,
        new_slot=target_slot_definition,
    )


def merge_slots_in_model(
    *, model: MetadataModel, merge_instructions: list[SlotMergeInstruction]
) -> MetadataModel:
    """Merge slots in the provided model according to the provided instructions."""
    schema_view = model.schema_view

    for merge_instruction in merge_instructions:
        schema_view = apply_merge_instruction(
            schema_view=schema_view, merge_instruction=merge_instruction
        )

    return schema_view.export_model()
