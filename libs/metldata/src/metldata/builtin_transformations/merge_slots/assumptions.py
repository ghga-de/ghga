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

"""Logic for checking transformation-specific model assumptions."""


from metldata.builtin_transformations.merge_slots.models import SlotMergeInstruction
from metldata.model_utils.assumptions import (
    MetadataModelAssumptionError,
    check_class_slot_exists,
)
from metldata.model_utils.essentials import MetadataModel


def check_source_slots_exist(
    model: MetadataModel, merge_instructions: list[SlotMergeInstruction]
) -> None:
    """Check that the source slots exist in the model."""
    for merge_instruction in merge_instructions:
        for source_slot in merge_instruction.source_slots:
            try:
                check_class_slot_exists(
                    model=model,
                    class_name=merge_instruction.class_name,
                    slot_name=source_slot,
                )
            except MetadataModelAssumptionError as error:
                raise MetadataModelAssumptionError(
                    f"Source slot {source_slot} of class "
                    + f"{merge_instruction.class_name} does not exist in the model."
                ) from error


def check_target_slots_not_exist(
    model: MetadataModel, merge_instructions: list[SlotMergeInstruction]
) -> None:
    """Check that the target slots do not exist in the model."""
    for merge_instruction in merge_instructions:
        try:
            check_class_slot_exists(
                model=model,
                class_name=merge_instruction.class_name,
                slot_name=merge_instruction.target_slot,
            )
        except MetadataModelAssumptionError:
            # this is expected
            continue
        else:
            raise MetadataModelAssumptionError(
                f"Target slot {merge_instruction.target_slot} of class "
                + f"{merge_instruction.class_name} already exists in the model."
            )


def check_model_class_slots(
    model: MetadataModel, merge_instructions: list[SlotMergeInstruction]
):
    """Check that the specified classes and slots exist in the model."""
    check_source_slots_exist(model=model, merge_instructions=merge_instructions)
    check_target_slots_not_exist(model=model, merge_instructions=merge_instructions)
