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

"""Test the config module."""

from contextlib import nullcontext

import pytest
from pydantic import ValidationError

from metldata.builtin_transformations.merge_slots.config import SlotMergingConfig


@pytest.mark.parametrize(
    "merge_instructions, valid",
    [
        (
            # valid since two different classes:
            [
                {
                    "class_name": "class_a",
                    "source_slots": ["some_slot", "another_slot"],
                    "target_slot": "merged_slot",
                },
                {
                    "class_name": "class_b",
                    "source_slots": ["merged_slot", "yet_another_slot"],
                    "target_slot": "some_slot",
                },
            ],
            True,
        ),
        (
            # invalid since using target slot of one merge instruction as source slot
            # for another:
            [
                {
                    "class_name": "class_a",
                    "source_slots": ["some_slot", "another_slot"],
                    "target_slot": "merged_slot",
                },
                {
                    "class_name": "class_a",
                    "source_slots": ["merged_slot", "yet_another_slot"],
                    "target_slot": "another_merged_slot",
                },
            ],
            False,
        ),
        (
            # invalid since two merge instruction target the same slot:
            [
                {
                    "class_name": "class_a",
                    "source_slots": ["some_slot", "another_slot"],
                    "target_slot": "merged_slot",
                },
                {
                    "class_name": "class_a",
                    "source_slots": ["another_slot", "yet_another_slot"],
                    "target_slot": "merged_slot",
                },
            ],
            False,
        ),
    ],
)
def test_slot_merging_config(merge_instructions: list, valid: bool):
    """Test that validation of SlotMergingConfig."""

    with nullcontext() if valid else pytest.raises(ValidationError):  # type: ignore
        SlotMergingConfig(merge_instructions=merge_instructions)
