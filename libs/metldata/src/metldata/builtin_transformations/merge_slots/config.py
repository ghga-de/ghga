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

"""Config parameters and their defaults."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from metldata.builtin_transformations.merge_slots.models import SlotMergeInstruction


class SlotMergingConfig(BaseSettings):
    """Config containing slots to be deleted from models and associated metadata."""

    model_config = SettingsConfigDict(extra="forbid")

    merge_instructions: list[SlotMergeInstruction] = Field(
        ...,
        description=(
            "A list of slot merging instructions. Each instruction specifies a class"
            + " and a target slot into which the source slots should be merged."
            + " You may specify merge instructions for the same class."
            + " However, the target slot of one merge instruction cannot be used as"
            + " a source slot in another merge instruction."
            + " The source slots will not be deleted."
        ),
        examples=[
            {
                "class_name": "class_a",
                "source_slots": ["some_slot", "another_slot"],
                "target_slot": "merged_slot",
            },
        ],
    )

    @field_validator("merge_instructions")
    def validate_merge_instructions(
        cls, filtered_merge_instructions: list[SlotMergeInstruction]
    ) -> list[SlotMergeInstruction]:
        """Validate that source and target slots do not overlap across merge
        instructions and that no target slot is reused for the same
        class.
        """
        class_names = {merge.class_name for merge in filtered_merge_instructions}
        for class_name in class_names:
            filtered_merge_instructions = [
                merge
                for merge in filtered_merge_instructions
                if merge.class_name == class_name
            ]
            source_slots = {
                slot
                for merge in filtered_merge_instructions
                for slot in merge.source_slots
            }

            target_slot_list = [
                merge.target_slot for merge in filtered_merge_instructions
            ]
            target_slots = set(target_slot_list)

            if len(target_slot_list) != len(target_slots):
                raise ValueError(
                    f"Multiple merge instructions for class '{class_name}'"
                    + " have the same target slot."
                )

            if source_slots.intersection(target_slots):
                raise ValueError(
                    f"Source and target slots for class '{class_name}' overlap."
                )

        return filtered_merge_instructions
