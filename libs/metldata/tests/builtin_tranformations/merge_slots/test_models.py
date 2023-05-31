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

"""Test the models module."""

import pytest
from pydantic import ValidationError

from metldata.builtin_transformations.merge_slots.models import SlotMergeInstruction


def test_slot_merge_instruction_overlap():
    """Test that an overlap in source and target slots fails with the expected
    exception."""

    with pytest.raises(ValidationError):
        SlotMergeInstruction(
            class_name="class_a",
            source_slots=["some_slot", "another_slot"],
            target_slot="some_slot",
        )
