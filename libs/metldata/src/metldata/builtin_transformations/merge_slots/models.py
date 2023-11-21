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

"""Models to describe slot merging instructions."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class SlotMergeInstruction(BaseModel):
    """A model to describe slot merging instructions."""

    class_name: str = Field(..., description="The class to which the slots belong.")
    source_slots: list[str] = Field(
        ...,
        description="The slots that should be merged into the target slot.",
        min_length=2,
    )
    target_slot: str = Field(
        ..., description="The slot into which the source slots should be merged."
    )
    target_description: Optional[str] = Field(
        None,
        description="A description of the target slot.",
    )

    @model_validator(mode="before")
    def validate_overlapping_slots(cls, values) -> dict:
        """Validate that source and target slots do not overlap."""
        source_slots = set(values["source_slots"])
        target_slot = values["target_slot"]

        if target_slot in source_slots:
            raise ValueError("Source and target slots must not overlap.")

        return values
